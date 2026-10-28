#!/usr/bin/env python3
"""E1 W5 Kaggle job 12 (GPU): video -> detector -> tracker -> track log + do do lien ket (issue #57, ADR-0008).

Chay detector da chon (baseline A, ADR-0007) voi tung cau hinh tracker tren TOAN BO frame cua cac video kha kien
tap VAL cua e1-yolo-v1 (lay danh sach video tu yolo_manifest.csv.gz). Test KHONG dung.

Stage: env -> inputs -> track -> metrics -> demo -> bundle (ghi stage_status.json sau moi stage).
Dau ra (--out/w5_track/):
  tracks/<tracker>/<video>.csv   frame,id,cls,conf,x,y,w,h (pixel, goc tren-trai), moi dong la mot hop co track ID
  per_video_metrics.csv          do do theo video x tracker x nguong IoU (w5_track_metrics.video_metrics)
  track_summary.json             tong hop theo tracker x nguong IoU, va theo lop
  timing.csv                     so frame, giay, FPS moi video (doc + detector + tracker; chi tham khao, benchmark o W9)
  demo/*.mp4                     video demo co ID (KHONG nam trong zip bang chung; tai rieng len Drive)
  env.json, inputs.json, stage_status.json
  -> w5_track_evidence.zip, w5_track_demo.zip

    python w5_track_videos.py --data-root <raw> --manifest yolo_manifest.csv.gz --audit annotation_audit.csv \
        --weights best.pt --weights-sha 65dd67fb... --trackers tracker_bytetrack_default.yaml tracker_botsort_default.yaml \
        --out /kaggle/working --commit <sha>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import platform
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from w3_export_yolo import find_video_dir, load_labels, sha256  # noqa: E402
from w5_track_metrics import summarize, video_metrics  # noqa: E402

LOG = logging.getLogger("w5_track")
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]
TRACK_FIELDS = ["frame", "id", "cls", "conf", "x", "y", "w", "h"]
IOU_THRS = (0.5, 0.3)


def read_csv(p: Path) -> list[dict]:
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(p: Path, rows: list[dict], fields: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


def load_model(weights: str):
    from ultralytics import YOLO
    return YOLO(weights)


def track_video(model, video: Path, tracker_cfg: Path, a) -> tuple[list[dict], int, float]:
    """Chay model.track tren mot video; persist=False => tracker khoi tao lai cho moi video. Tra ve (dong track, so frame, giay)."""
    rows, n, t0 = [], 0, time.perf_counter()
    for r in model.track(source=str(video), tracker=str(tracker_cfg), conf=a.conf, iou=a.iou, imgsz=a.imgsz,
                         device=a.device, persist=False, stream=True, verbose=False):
        b = r.boxes
        if b is not None and b.id is not None and len(b):
            for xyxy, tid, c, s in zip(b.xyxy.tolist(), b.id.tolist(), b.cls.tolist(), b.conf.tolist()):
                x1, y1, x2, y2 = xyxy
                rows.append({"frame": n, "id": int(tid), "cls": int(c), "conf": round(float(s), 4),
                             "x": round(x1, 2), "y": round(y1, 2), "w": round(x2 - x1, 2), "h": round(y2 - y1, 2)})
        n += 1
    return rows, n, time.perf_counter() - t0


def render_demo(video: Path, gt: list, tracks: list[dict], out: Path, title: str) -> int:
    import cv2
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"khong mo duoc {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    by_f: dict[int, list[dict]] = {}
    for t in tracks:
        by_f.setdefault(int(t["frame"]), []).append(t)
    pal = [(214, 120, 42), (52, 104, 235), (122, 175, 27), (0, 161, 237), (214, 92, 122), (120, 75, 214)]
    f = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        g = gt[f] if f < len(gt) else None
        if g is not None:
            x, y, w, h = map(int, g)
            cv2.rectangle(im, (x, y), (x + w, y + h), (255, 255, 255), 1)
        for t in by_f.get(f, []):
            c = pal[int(t["id"]) % len(pal)]
            x, y, w, h = int(t["x"]), int(t["y"]), int(t["w"]), int(t["h"])
            cv2.rectangle(im, (x, y), (x + w, y + h), c, 2)
            cv2.putText(im, f"ID {t['id']} {CLASSES[int(t['cls'])]} {float(t['conf']):.2f}", (x, max(12, y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1, cv2.LINE_AA)
        cv2.putText(im, f"{title} | frame {f} | trang: nhan goc", (6, H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        vw.write(im); f += 1
    cap.release(); vw.release()
    if f == 0 or not out.is_file():
        raise RuntimeError(f"ghi demo that bai: {out}")
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True, help="yolo_manifest.csv.gz cua e1-yolo-v1 (lay danh sach video val)")
    ap.add_argument("--audit", type=Path, required=True, help="annotation_audit.csv (frames_decoded de doi chieu)")
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--weights-sha", default="", help="SHA-256 ky vong cua weights; rong = khong kiem (khong dung cho run chinh thuc)")
    ap.add_argument("--trackers", type=Path, nargs="+", required=True)
    ap.add_argument("--split", default="val")
    ap.add_argument("--conf", type=float, default=0.1, help="nguong detector dua vao tracker (<= track_low_thresh de ByteTrack dung hop diem thap)")
    ap.add_argument("--iou", type=float, default=0.7, help="IoU cua NMS")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="0")
    ap.add_argument("--demo", type=int, default=3)
    ap.add_argument("--max-videos", type=int, default=0, help="chi de kiem thu")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ev = a.out / "w5_track"
    if ev.exists():
        shutil.rmtree(ev)
    ev.mkdir(parents=True)
    status, ctx = {}, {}

    def run(name, fn):
        try:
            r = fn()
            status[name] = {"status": "OK", **(r if isinstance(r, dict) else {})}
            return r
        except Exception as exc:  # noqa: BLE001
            LOG.error("%s FAILED: %s", name, exc)
            status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
            return None
        finally:
            (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def env():
        info = {"python": sys.version.split()[0], "platform": platform.platform(), "commit": a.commit, "args": {k: str(v) for k, v in vars(a).items()}}
        for mod in ("torch", "ultralytics", "cv2", "numpy", "lap"):
            try:
                m = __import__(mod); info[mod] = getattr(m, "__version__", "present")
            except Exception as exc:  # noqa: BLE001
                info[mod] = f"MISSING ({exc.__class__.__name__})"
        try:
            import torch
            info["cuda"] = torch.cuda.is_available()
            info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
        except Exception:  # noqa: BLE001
            info["gpu"] = "none"
        try:
            info["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                                capture_output=True, text=True, timeout=20).stdout.strip() or "none"
        except Exception:  # noqa: BLE001
            info["nvidia_smi"] = "none"
        (ev / "env.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"gpu": info["gpu"], "ultralytics": info["ultralytics"]}

    def inputs():
        if a.weights_sha and sha256(a.weights) != a.weights_sha:
            raise ValueError(f"SHA-256 weights khac ky vong: {sha256(a.weights)[:16]} != {a.weights_sha[:16]}")
        man = read_csv(a.manifest)
        vids = sorted({(m["video_id"], m["class_name"]) for m in man if m["split"] == a.split})
        if a.max_videos:
            vids = vids[: a.max_videos]
        if not vids:
            raise ValueError(f"khong co video {a.split} trong manifest")
        audit = {r["video_id"]: r for r in read_csv(a.audit)}
        data = find_video_dir(a.data_root)
        videos = []
        for vid, cls in vids:
            mp4 = data / "Video_V" / f"{vid}.mp4"
            if not mp4.is_file():
                raise FileNotFoundError(mp4)
            n = int(audit[vid]["frames_decoded"])
            lab = load_labels(data / "Video_V" / f"{vid}_LABELS.mat")
            bad = [i for i, b in enumerate(lab[:n]) if b == "MALFORMED"]
            if bad:
                raise ValueError(f"{vid}: nhan loi o frame {bad[:5]}")
            gt = list(lab[:n]) + [None] * max(0, n - len(lab))     # offset0 (ADR-0006): frame i <-> muc nhan i
            videos.append({"video_id": vid, "class_name": cls, "cls": CLASSES.index(cls), "mp4": mp4, "frames": n, "gt": gt})
        trk = []
        for p in a.trackers:
            import yaml
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            if "tracker_type" not in cfg:
                raise ValueError(f"{p}: thieu tracker_type")
            diff = {}
            try:                                          # so voi cau hinh mac dinh cua ban Ultralytics dang chay
                import ultralytics
                d0 = yaml.safe_load((Path(ultralytics.__file__).parent / "cfg" / "trackers" / f"{cfg['tracker_type']}.yaml").read_text())
                diff = {k: {"e1": cfg.get(k), "ultralytics": d0.get(k)} for k in sorted(set(cfg) | set(d0)) if cfg.get(k) != d0.get(k)}
            except Exception as exc:  # noqa: BLE001
                diff = {"error": str(exc)}
            trk.append({"name": p.stem, "path": p, "cfg": cfg, "sha256": sha256(p), "diff_vs_default": diff})
        ctx.update(videos=videos, trackers=trk)
        info = {"split": a.split, "videos": len(videos), "by_class": {c: sum(v["class_name"] == c for v in videos) for c in CLASSES},
                "gt_frames": sum(sum(g is not None for g in v["gt"]) for v in videos), "weights_sha256": sha256(a.weights),
                "manifest_sha256": sha256(a.manifest), "audit_sha256": sha256(a.audit),
                "trackers": {t["name"]: {"sha256": t["sha256"], "cfg": t["cfg"], "diff_vs_ultralytics_default": t["diff_vs_default"]} for t in trk},
                "detector": {"conf": a.conf, "nms_iou": a.iou, "imgsz": a.imgsz}, "label_offset": "offset0 (ADR-0006)", "test_used": False}
        (ev / "inputs.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
        return {k: info[k] for k in ("videos", "gt_frames", "by_class")}

    def track():
        model = load_model(str(a.weights))
        timing, mismatch = [], []
        for t in ctx["trackers"]:
            for v in ctx["videos"]:
                rows, n, sec = track_video(model, v["mp4"], t["path"], a)
                write_csv(ev / "tracks" / t["name"] / f"{v['video_id']}.csv", rows, TRACK_FIELDS)
                v.setdefault("tracks", {})[t["name"]] = rows
                timing.append({"tracker": t["name"], "video_id": v["video_id"], "frames": n, "seconds": round(sec, 3),
                               "fps": round(n / sec, 2) if sec else ""})
                if n != v["frames"]:
                    mismatch.append(f"{v['video_id']}: doc {n} frame, audit {v['frames']}")
                LOG.info("%s %s: %d frame, %d hop, %.1f FPS", t["name"], v["video_id"], n, len(rows), n / sec if sec else 0)
        write_csv(ev / "timing.csv", timing, ["tracker", "video_id", "frames", "seconds", "fps"])
        if mismatch:
            raise ValueError("so frame doc duoc khac audit: " + "; ".join(mismatch[:5]))
        return {"track_files": len(timing), "median_fps": sorted(x["fps"] for x in timing)[len(timing) // 2]}

    def metrics():
        rows, summary = [], {}
        for t in ctx["trackers"]:
            for thr in IOU_THRS:
                per = []
                for v in ctx["videos"]:
                    m = video_metrics(v["gt"], v["tracks"][t["name"]], v["cls"], iou_thr=thr)
                    per.append({"tracker": t["name"], "iou_thr": thr, "video_id": v["video_id"], "class_name": v["class_name"], **m})
                rows += per
                key = f"{t['name']}@{thr}"
                summary[key] = {"all": summarize(per), **{c: summarize([r for r in per if r["class_name"] == c])
                                                          for c in CLASSES if any(r["class_name"] == c for r in per)}}
        write_csv(ev / "per_video_metrics.csv", rows, list(rows[0]))
        (ev / "track_summary.json").write_text(json.dumps({"note": "GT dan xuat 1 track/video (ADR-0008); khong phai MOTA/IDF1/HOTA chuan",
                                                           "summary": summary}, indent=2, ensure_ascii=False), encoding="utf-8")
        ctx["per"] = rows
        return {k: {"idsw_per_1000": v["all"]["idsw_per_1000_gt_frames"], "median_dom_cov": v["all"]["median_dominant_id_coverage"]}
                for k, v in summary.items()}

    def demo():
        if a.demo <= 0:
            return {"skipped": True}
        t0 = ctx["trackers"][0]["name"]
        per = [r for r in ctx["per"] if r["tracker"] == t0 and r["iou_thr"] == 0.5]
        by = {r["video_id"]: r for r in per}
        vids = {v["video_id"]: v for v in ctx["videos"]}
        pick = []
        for c in ("Drone", "Bird"):                       # luat chon dat truoc: video co nhieu frame GT nhat cua lop
            cand = sorted((r for r in per if r["class_name"] == c), key=lambda r: (-r["gt_frames"], r["video_id"]))
            if cand:
                pick.append(cand[0]["video_id"])
        worst = sorted((r for r in per if r["class_name"] == "Drone" and r["video_id"] not in pick),
                       key=lambda r: (-r["id_switches"], r["video_id"]))      # va video Drone co nhieu ID switch nhat
        if worst:
            pick.append(worst[0]["video_id"])
        (ev / "demo").mkdir(exist_ok=True)
        done = []
        for vid in pick[: a.demo]:
            v = vids[vid]
            out = ev / "demo" / f"{vid}_{t0}.mp4"
            n = render_demo(v["mp4"], v["gt"], v["tracks"][t0], out, f"{vid} {t0} IDSW={by[vid]['id_switches']}")
            done.append({"video_id": vid, "frames": n, "file": out.name, "sha256": sha256(out)})
        (ev / "demo" / "demo_index.json").write_text(json.dumps(done, indent=2), encoding="utf-8")
        return {"videos": [d["video_id"] for d in done]}

    def bundle():
        z1, z2 = a.out / "w5_track_evidence.zip", a.out / "w5_track_demo.zip"
        with zipfile.ZipFile(z1, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(ev.rglob("*")):
                if p.is_file() and p.suffix != ".mp4":
                    zf.write(p, p.relative_to(ev.parent))
        with zipfile.ZipFile(z2, "w", zipfile.ZIP_STORED) as zf:
            for p in sorted((ev / "demo").glob("*")) if (ev / "demo").is_dir() else []:
                zf.write(p, p.relative_to(ev.parent))
        return {"evidence_zip": z1.name, "evidence_sha256": sha256(z1), "demo_zip": z2.name, "demo_sha256": sha256(z2)}

    run("env", env)
    if run("inputs", inputs) is not None and run("track", track) is not None and run("metrics", metrics) is not None:
        run("demo", demo)
    run("bundle", bundle)
    print(json.dumps({k: v.get("status") for k, v in status.items()}, indent=2))
    return 0 if all(v.get("status") == "OK" for v in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
