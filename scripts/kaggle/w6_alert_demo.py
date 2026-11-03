#!/usr/bin/env python3
"""E1 W6 Kaggle job 15 (CPU): video demo co ve ROI va canh bao (issue #76, ADR-0009).

Doc bang chung run 14 (tracks, dets, meta), tinh lai canh bao R0/R1 bang scripts/alert/alert_engine.py voi
configs/roi_w6.yaml + configs/alert_e1.yaml (ROI chinh, diem tam hop), roi ve len video goc:
  polygon ROI (vang), hop nhan goc (trang), hop track co ID (mau theo ID), dai canh bao R1 (do) va R0 (cam),
  danh dau canh bao som (xanh). Khong dua mp4 vao Git.

Luat chon video (dat truoc, ghi trong demo_index.json):
  1. video Drone co canh bao R1 loai `vao_vung` dai nhat;
  2. video KHONG phai Drone co tong thoi gian canh bao sai R0 dai nhat (R1 khong canh bao);
  3. video Drone co nhieu ID switch nhat trong run 14 (kiem tra gop track trung).

Stage: env -> inputs -> select -> render -> bundle.

    python w6_alert_demo.py --data-root <raw> --evidence <.../w6_run14> --roi roi_w6.yaml --alert alert_e1.yaml \
        --out /kaggle/working --commit <sha>
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import platform
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "alert"))     # chay tu repo; tren Kaggle cac file nam chung thu muc
from alert_engine import r0_alerts, r1_alerts  # noqa: E402
from w3_export_yolo import find_video_dir, sha256  # noqa: E402

LOG = logging.getLogger("w6_alert_demo")
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]


def rcsv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def wcsv(p: Path, rows: list[dict], fields: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


def compute(v: dict, poly, cfg: dict) -> dict:
    W, H, n, fps = v["width"], v["height"], v["frames"], v["fps"]
    r1, pw = r1_alerts(v["tracks"], n, fps, poly, W, H, cfg)
    return {"R0": r0_alerts(v["dets"], n, fps, poly, W, H, cfg), "R1": r1, "prewarn": pw}


def select(vids: list[dict], alerts: dict, per_video: dict) -> list[dict]:
    pick = []
    cand = [(a["end"] - a["start"], v["video_id"]) for v in vids if v["class_name"] == "Drone"
            for a in alerts[v["video_id"]]["R1"] if a["kind"] == "vao_vung"]
    if cand:
        pick.append({"video_id": max(cand, key=lambda x: (x[0], x[1]))[1], "rule": "Drone, canh bao R1 vao_vung dai nhat"})
    fa = [(sum(a["end"] - a["start"] + 1 for a in alerts[v["video_id"]]["R0"]), v["video_id"]) for v in vids
          if v["class_name"] != "Drone" and alerts[v["video_id"]]["R0"] and not alerts[v["video_id"]]["R1"]]
    if fa:
        pick.append({"video_id": max(fa)[1], "rule": "khong phai Drone, canh bao sai R0 dai nhat, R1 khong canh bao"})
    sw = [(int(per_video[v["video_id"]]["id_switches"]), v["video_id"]) for v in vids
          if v["class_name"] == "Drone" and v["video_id"] not in {p["video_id"] for p in pick}]
    if sw:
        pick.append({"video_id": max(sw)[1], "rule": "Drone, nhieu ID switch nhat (run 14)"})
    return pick


def render(mp4: Path, v: dict, al: dict, poly, out: Path) -> int:
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(str(mp4))
    if not cap.isOpened():
        raise RuntimeError(f"khong mo duoc {mp4}")
    W, H = v["width"], v["height"]
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), v["fps"], (W, H))
    pts = np.array([[int(x * W), int(y * H)] for x, y in poly], np.int32)
    by_t, gt = {}, {int(g["frame"]): g for g in v["gt"]}
    for t in v["tracks"]:
        by_t.setdefault(int(t["frame"]), []).append(t)
    pre = {p["frame"] for p in al["prewarn"]}
    pal = [(214, 120, 42), (52, 104, 235), (122, 175, 27), (0, 161, 237), (214, 92, 122), (120, 75, 214)]
    f = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        cv2.polylines(im, [pts], True, (0, 215, 255), 2)
        if f in gt:
            g = gt[f]; x, y, w, h = (int(float(g[k])) for k in "xywh")
            cv2.rectangle(im, (x, y), (x + w, y + h), (255, 255, 255), 1)
        for t in by_t.get(f, []):
            c = pal[int(t["id"]) % len(pal)]
            x, y, w, h = (int(float(t[k])) for k in "xywh")
            cv2.rectangle(im, (x, y), (x + w, y + h), c, 2)
            cv2.putText(im, f"ID {t['id']} {CLASSES[int(t['cls'])]} {float(t['conf']):.2f}", (x, max(12, y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1, cv2.LINE_AA)
        r1 = [i for i, a in enumerate(al["R1"]) if a["start"] <= f <= a["end"]]
        r0 = any(a["start"] <= f <= a["end"] for a in al["R0"])
        if r1:
            a = al["R1"][r1[0]]
            cv2.rectangle(im, (0, 0), (W, 26), (0, 0, 220), -1)
            cv2.putText(im, f"CANH BAO R1 #{r1[0]} ({a['kind']}) track {','.join(map(str, a['tracks']))}", (6, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        if r0:
            cv2.putText(im, "R0 detector-only: dang canh bao", (6, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 140, 255), 1, cv2.LINE_AA)
        if f in pre:
            cv2.putText(im, "canh bao som (ngoai suy quy dao)", (6, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 0), 1, cv2.LINE_AA)
        cv2.putText(im, f"{v['video_id']} | frame {f} | vang: ROI center_hex | trang: nhan goc", (6, H - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        vw.write(im); f += 1
    cap.release(); vw.release()
    if f != v["frames"]:
        raise RuntimeError(f"{v['video_id']}: doc {f} frame, meta {v['frames']}")
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--evidence", type=Path, required=True, help="thu muc w6_run14 cua run 14")
    ap.add_argument("--roi", type=Path, required=True)
    ap.add_argument("--alert", type=Path, required=True)
    ap.add_argument("--tracker", default="tracker_bytetrack_e1")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--overwrite", action="store_true", help="cho phep xoa thu muc bang chung cung tag (mac dinh: dung lai)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import yaml
    ev = a.out / "w6_alert_demo"
    if ev.exists() and any(ev.iterdir()):
        if not a.overwrite:
            raise SystemExit(f"{ev} da co bang chung; dung --tag khac hoac them --overwrite neu chac chan muon xoa (review #80)")
        LOG.warning("--overwrite: xoa %s", ev)
        shutil.rmtree(ev)
    ev.mkdir(parents=True, exist_ok=True)
    status, ctx = {}, {}

    def run(name, fn):
        try:
            r = fn(); status[name] = {"status": "OK", **(r if isinstance(r, dict) else {})}; return r
        except Exception as exc:  # noqa: BLE001
            LOG.error("%s FAILED: %s", name, exc)
            status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
            return None
        finally:
            (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def env():
        info = {"python": sys.version.split()[0], "platform": platform.platform(), "commit": a.commit}
        for mod in ("cv2", "numpy", "yaml"):
            try:
                m = __import__(mod); info[mod] = getattr(m, "__version__", "present")
            except Exception as exc:  # noqa: BLE001
                info[mod] = f"MISSING ({exc.__class__.__name__})"
        (ev / "env.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        return {"cv2": info["cv2"]}

    def inputs():
        st = json.loads((a.evidence / "stage_status.json").read_text(encoding="utf-8"))
        if any(v.get("status") != "OK" for v in st.values()) or "dump" not in st:
            raise ValueError("bang chung run 14 khong day du (can stage dump OK)")
        inp = json.loads((a.evidence / "inputs.json").read_text(encoding="utf-8"))
        if inp.get("split") != "val" or inp.get("test_used") is not False:
            raise ValueError("chi dung bang chung val")
        rc, cfg = yaml.safe_load(a.roi.read_text(encoding="utf-8")), yaml.safe_load(a.alert.read_text(encoding="utf-8"))
        poly = next(r["polygon"] for r in rc["rois"] if r["name"] == rc["primary"])
        data = find_video_dir(a.data_root)
        vids = []
        for m in rcsv(a.evidence / "meta.csv"):
            vid = m["video_id"]
            vids.append({"video_id": vid, "class_name": m["class_name"], "frames": int(m["frames"]), "fps": float(m["fps"]),
                         "width": int(m["width"]), "height": int(m["height"]), "mp4": data / "Video_V" / f"{vid}.mp4",
                         "gt": rcsv(a.evidence / "gt" / f"{vid}.csv"), "dets": rcsv(a.evidence / "dets" / f"{vid}.csv"),
                         "tracks": rcsv(a.evidence / "tracks" / a.tracker / f"{vid}.csv")})
        per = {r["video_id"]: r for r in rcsv(a.evidence / "per_video_metrics.csv") if r["iou_thr"] == "0.5"}
        ctx.update(vids=vids, poly=poly, cfg={**cfg, "point": "center"}, per=per)
        return {"videos": len(vids), "roi": rc["primary"], "roi_sha256": sha256(a.roi), "alert_sha256": sha256(a.alert),
                "weights_sha256": inp["weights_sha256"]}

    def sel():
        al = {v["video_id"]: compute(v, ctx["poly"], ctx["cfg"]) for v in ctx["vids"]}
        rows = [{"video_id": vid, "rule": rule, "alert": i, "start_f": x["start"], "end_f": x["end"], "tracks": " ".join(map(str, x["tracks"])),
                 "kind": x["kind"]} for vid, d in al.items() for rule in ("R0", "R1") for i, x in enumerate(d[rule])]
        wcsv(ev / "demo_alerts.csv", rows, ["video_id", "rule", "alert", "start_f", "end_f", "tracks", "kind"])
        ctx["al"], ctx["pick"] = al, select(ctx["vids"], al, ctx["per"])
        return {"picked": [p["video_id"] for p in ctx["pick"]], "alerts": len(rows)}

    def rend():
        by = {v["video_id"]: v for v in ctx["vids"]}
        done = []
        for p in ctx["pick"]:
            v = by[p["video_id"]]; out = ev / f"{v['video_id']}_alert.mp4"
            n = render(v["mp4"], v, ctx["al"][v["video_id"]], ctx["poly"], out)
            done.append({**p, "frames": n, "file": out.name, "sha256": sha256(out)})
        (ev / "demo_index.json").write_text(json.dumps(done, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"videos": len(done)}

    def bundle():
        z1, z2 = a.out / "w6_alert_demo_evidence.zip", a.out / "w6_alert_demo_videos.zip"
        with zipfile.ZipFile(z1, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(ev.glob("*")):
                if p.suffix != ".mp4":
                    zf.write(p, p.relative_to(ev.parent))
        with zipfile.ZipFile(z2, "w", zipfile.ZIP_STORED) as zf:
            for p in sorted(ev.glob("*.mp4")):
                zf.write(p, p.relative_to(ev.parent))
        return {"evidence_sha256": sha256(z1), "videos_sha256": sha256(z2)}

    run("env", env)
    if run("inputs", inputs) is not None and run("select", sel) is not None:
        run("render", rend)
    run("bundle", bundle)
    print(json.dumps({k: v.get("status") for k, v in status.items()}, indent=2))
    return 0 if all(v.get("status") == "OK" for v in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
