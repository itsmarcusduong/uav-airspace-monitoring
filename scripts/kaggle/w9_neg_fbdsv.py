#!/usr/bin/env python3
"""E1 W9 Kaggle (#131): chuan hoa FBD-SV-2024 va do canh bao sai tren neg_eval bang e1pipe cau hinh C0.

docs/w9/W9_PLAN.md muc D; ADR-0013 muc 2 (tien xu ly), ADR-0014 (FBD-SV chi danh gia, khong phan phoi lai).
- Kiem SHA-256 tung mp4 theo data/manifests/fbd_sv_2024_zip_contents_sha256.csv (483 clip).
- Chuan hoa: cat giua ti le 5:4, resize 640x512, dua ve 30 fps (ffmpeg fps=30), H.264; ghi ffprobe nguon va dich.
  Video chuan hoa chi nam trong /tmp cua phien Kaggle, KHONG dua vao bang chung.
- e1pipe C0 (PyTorch fp32, NMS cung lop 0,5, ByteTrack-e1, R1) tung clip; R0 tu detection.
- Moi canh bao tren clip am tinh la canh bao sai. Bang chung chi gom so do tong hop va ID clip.

    python w9_neg_fbdsv.py --fbd-root /kaggle/input/e1-fbd-sv-2024 --tools <tools> --weights best.pt --weights-sha <sha> \
        --out /kaggle/working --commit <sha>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

LOG = logging.getLogger("w9_neg_fbdsv")
CMD_TIMEOUT_S = 300          # mot clip FBD-SV <= 30 MB; ffmpeg/ffprobe lau hon 5 phut la treo, dung lai va bao loi
PROGRESS_EVERY = 25          # in tien do moi 25 clip (W9: run 19 lan dau im lang 3,3 gio, khong biet ket o dau)
VF = "crop='min(iw,ih*5/4)':'min(ih,iw*4/5)',scale=640:512,fps=30"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def probe(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", str(p)], capture_output=True, text=True, check=True,
                       timeout=CMD_TIMEOUT_S)
    s = json.loads(r.stdout)["streams"][0]
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    return {"width": int(s["width"]), "height": int(s["height"]), "fps": round(num / den, 3), "frames": int(s["nb_read_frames"])}


def normalize_cmd(src: Path, dst: Path) -> list[str]:
    return ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-map", "0:v:0", "-an", "-vf", VF,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(dst)]


def progress(stage: str, i: int, n: int, t0: float, frames: int) -> None:
    """Dong tien do: so clip, thoi gian da chay, toc do frame/s, uoc tinh thoi gian con lai."""
    el = time.time() - t0
    eta = el / i * (n - i) if i else 0.0
    LOG.info("[%s] %d/%d clip | %d frame | %.0f s | %.1f frame/s | con ~%.0f s", stage, i, n, frames, el, frames / el if el else 0.0, eta)


def clip_index(root: Path) -> dict[str, list[Path]]:
    """Mot lan rglob: ten tep -> cac duong dan (tranh 483 lan quet thu muc tren /kaggle/input)."""
    idx: dict[str, list[Path]] = {}
    for p in root.rglob("*.mp4"):
        idx.setdefault(p.name, []).append(p)
    return idx


def find_in_index(idx: dict[str, list[Path]], rel: str) -> Path:
    tail = Path(*Path(rel).parts[1:])
    hits = [p for p in idx.get(Path(rel).name, []) if p.as_posix().endswith(tail.as_posix())]
    if len(hits) != 1:
        raise FileNotFoundError(f"{rel}: tim thay {len(hits)} tep")
    return hits[0]


def find_clip(root: Path, rel: str) -> Path:
    """rel kieu 'FBD-SV-2024/videos/train/bird_1.mp4'; Kaggle co the giai nen them mot tang thu muc."""
    tail = Path(*Path(rel).parts[1:])
    hits = [p for p in root.rglob(Path(rel).name) if p.as_posix().endswith(tail.as_posix())]
    if len(hits) != 1:
        raise FileNotFoundError(f"{rel}: tim thay {len(hits)} tep")
    return hits[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fbd-root", type=Path, required=True)
    ap.add_argument("--tools", type=Path, required=True)
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--weights-sha", required=True)
    ap.add_argument("--device", default="0")
    ap.add_argument("--max-clips", type=int, default=0, help="chi de kiem thu")
    ap.add_argument("--jobs", type=int, default=4, help="so clip chuan hoa song song (doc /kaggle/input cham, run 19: ~11 s/clip)")
    ap.add_argument("--work", type=Path, default=Path("/tmp/e1_fbd_norm"))
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--runner", choices=["manual", "github-actions"], default="manual")
    ap.add_argument("--tag", default="w9_neg_fbdsv")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S", stream=sys.stdout, force=True)
    ev = a.out / a.tag
    if ev.exists():
        if not a.overwrite:
            raise SystemExit(f"{ev} da ton tai; dung --overwrite neu chac chan")
        shutil.rmtree(ev)
    ev.mkdir(parents=True)
    for sub in ("scripts/pipeline", "scripts/alert"):
        sys.path.insert(0, str(a.tools / sub))
    import alert_engine as ae  # noqa: E402
    import e1pipe  # noqa: E402
    import evaluate_alerts as ea  # noqa: E402
    import yaml  # noqa: E402
    status: dict[str, dict] = {}

    def save_status():
        (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("can ffmpeg/ffprobe")
    if sha256(a.weights) != a.weights_sha:
        raise SystemExit("SHA-256 weights khac ky vong")
    with (a.tools / "data/manifests/fbd_sv_2024_zip_contents_sha256.csv").open(encoding="utf-8") as fh:
        man = [r for r in csv.DictReader(fh) if r["path"].endswith(".mp4")]
    man.sort(key=lambda r: r["path"])
    if len(man) != 483:
        raise SystemExit(f"manifest co {len(man)} mp4, ky vong 483")
    if a.max_clips:
        man = man[: a.max_clips]
    # ------------------------------------------------------------------ kiem SHA + chuan hoa
    if a.work.exists():
        shutil.rmtree(a.work)
    a.work.mkdir(parents=True)
    clips = []
    t0 = time.time()
    LOG.info("[normalize] bat dau %d clip, %d luong", len(man), a.jobs)
    tt = time.time()
    index = clip_index(a.fbd_root)                                    # mot lan rglob thay vi 483 lan
    tsum = {"index": time.time() - tt, "copy": 0.0, "sha": 0.0, "ffmpeg": 0.0, "probe": 0.0}
    (a.work / "_src").mkdir()

    def one(r: dict) -> dict:
        """Chep clip tu /kaggle/input (doc mang, cham) sang dia cuc bo MOT lan, roi kiem SHA, chuan hoa, probe tren ban chep."""
        cid = f"{Path(r['path']).parent.name}/{Path(r['path']).stem}"
        key = "__".join(Path(r["path"]).parts[-2:])
        loc = a.work / "_src" / key
        dst = a.work / f"{Path(r['path']).parent.name}__{Path(r['path']).stem}.mp4"
        tm = {}
        t = time.time(); shutil.copyfile(find_in_index(index, r["path"]), loc); tm["copy"] = time.time() - t
        t = time.time(); ok = sha256(loc) == r["sha256"]; tm["sha"] = time.time() - t
        if not ok:
            raise ValueError(f"{r['path']}: SHA-256 khac manifest (ADR-0014: dung lai)")
        t = time.time(); subprocess.run(normalize_cmd(loc, dst), check=True, timeout=CMD_TIMEOUT_S); tm["ffmpeg"] = time.time() - t
        t = time.time(); ps, pd = probe(loc), probe(dst); tm["probe"] = time.time() - t
        loc.unlink()
        if (pd["width"], pd["height"]) != (640, 512) or abs(pd["fps"] - 30.0) > 0.01:
            raise ValueError(f"{cid}: chuan hoa sai {pd}")
        return {"clip": cid, "src": ps, "out": pd, "path": dst, "_tm": tm}

    done = {}
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(one, r): k for k, r in enumerate(man)}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                c = f.result()
            except subprocess.TimeoutExpired as e:
                status["normalize"] = {"status": "FAIL", "clip": man[futs[f]]["path"], "error": f"timeout {CMD_TIMEOUT_S}s: {e.cmd[0]}", "done": len(done)}
                save_status(); ex.shutdown(cancel_futures=True)
                raise SystemExit(f"{man[futs[f]]['path']}: {e.cmd[0]} qua {CMD_TIMEOUT_S}s")
            except ValueError as e:
                status["normalize"] = {"status": "FAIL", "error": str(e), "done": len(done)}
                save_status(); ex.shutdown(cancel_futures=True)
                raise SystemExit(str(e))
            for k, v in c.pop("_tm").items():
                tsum[k] += v
            done[futs[f]] = c
            if n % PROGRESS_EVERY == 0 or n == len(man):
                progress("normalize", n, len(man), t0, sum(x["out"]["frames"] for x in done.values()))
                LOG.info("[normalize] giay cong don (tong cac luong): %s", {k: round(v, 1) for k, v in tsum.items()})
    clips = [done[k] for k in range(len(man))]                       # giu dung thu tu manifest (tat dinh)
    shutil.rmtree(a.work / "_src", ignore_errors=True)
    status["normalize"] = {"status": "OK", "clips": len(clips), "seconds": round(time.time() - t0, 1),
                           "seconds_by_step": {k: round(v, 1) for k, v in tsum.items()},
                           "source_sizes": sorted({f"{c['src']['width']}x{c['src']['height']}@{c['src']['fps']}" for c in clips})}
    save_status()
    # ------------------------------------------------------------------ e1pipe C0
    import torch
    import ultralytics
    from ultralytics.utils import IterableSimpleNamespace
    cfg_tr = yaml.safe_load((a.tools / "configs/tracker_bytetrack_e1.yaml").read_text(encoding="utf-8"))
    rois = yaml.safe_load((a.tools / "configs/roi_w6.yaml").read_text(encoding="utf-8"))
    poly = next(x["polygon"] for x in rois["rois"] if x["name"] == rois["primary"])
    acfg = yaml.safe_load((a.tools / "configs/alert_e1.yaml").read_text(encoding="utf-8"))
    env = {"torch": torch.__version__, "ultralytics": ultralytics.__version__, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
           "commit": a.commit, "runner": a.runner, "actions_run_id": os.environ.get("GITHUB_RUN_ID", ""), "ffmpeg_vf": VF}
    (ev / "env.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    det = e1pipe.UltralyticsDetector(str(a.weights), conf=0.1, iou=0.5, imgsz=640, device=a.device)
    sink_dir = a.work.parent / f"{a.tag}_sink"
    shutil.rmtree(sink_dir, ignore_errors=True)
    sink = e1pipe.Sink(sink_dir, a.tag, a.commit, a.weights_sha, {"config": "C0", "source": "FBD-SV-2024"},
                       a.device, "FBD-SV-2024 neg_eval", save_csv=True)
    rows = []
    t1, nf = time.time(), 0
    LOG.info("[measure] bat dau %d clip, %d frame, thiet bi %s", len(clips), sum(c["out"]["frames"] for c in clips), env["gpu"] or a.device)
    for i, c in enumerate(clips, 1):
        o = c["out"]; tc = time.time()
        s = e1pipe.run_source(e1pipe.read_frames(c["path"]), c["clip"].replace("/", "__"), "Bird", 30.0, 640, 512, o["frames"], det,
                              e1pipe.make_tracker(IterableSimpleNamespace(**cfg_tr)), sink, poly, acfg, rois["primary"], a.weights_sha)
        dets, tracks = sink.dets, sink.tracks
        r0 = ae.r0_alerts(dets, s["frames"], 30.0, poly, 640, 512, acfg)
        drone_frames = len({d["frame"] for d in dets if d["cls"] == acfg["drone_class"] and d["conf"] >= acfg["conf_min"]})
        cls_tracks = {}
        for t in tracks:
            cls_tracks.setdefault(t["id"], []).append(t["cls"])
        rows.append({"clip": c["clip"], "split_in_source": c["clip"].split("/")[0], "frames": s["frames"], "seconds": round(s["frames"] / 30.0, 3),
                     "r1_false_alerts": s["events"], "r0_false_alerts": len(r0), "frames_drone_det_conf025": drone_frames,
                     "tracks": len(cls_tracks), "tracks_majority_drone": sum(1 for v in cls_tracks.values() if max(set(v), key=v.count) == acfg["drone_class"]),
                     "tracks_majority_bird": sum(1 for v in cls_tracks.values() if max(set(v), key=v.count) == 1),
                     "src_w": c["src"]["width"], "src_h": c["src"]["height"], "src_fps": c["src"]["fps"], "src_frames": c["src"]["frames"],
                     "measure_s": round(time.time() - tc, 2)})
        nf += s["frames"]
        if i % PROGRESS_EVERY == 0 or i == len(clips) or i == 1:
            progress("measure", i, len(clips), t1, nf)
    sink.close()
    shutil.rmtree(a.work, ignore_errors=True)                 # video chuan hoa khong roi khoi phien
    shutil.rmtree(sink_dir, ignore_errors=True)
    status["measure"] = {"status": "OK", "clips": len(rows), "seconds": round(time.time() - t1, 1), "frames": nf}
    with (ev / "per_clip.csv").open("w", newline="", encoding="utf-8") as fh:   # ghi truoc khi tong hop, de khong mat ket qua do
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    save_status()
    hours = sum(r["seconds"] for r in rows) / 3600
    k1, k0 = sum(r["r1_false_alerts"] for r in rows), sum(r["r0_false_alerts"] for r in rows)
    nfr = sum(r["frames"] for r in rows); ndf = sum(r["frames_drone_det_conf025"] for r in rows)
    summ = {"source": "FBD-SV-2024", "split": "neg_eval (ADR-0014)", "config": "C0", "clips": len(rows), "frames": nfr, "hours": round(hours, 4),
            "minutes": round(hours * 60, 2),
            "R1": {"false_alerts": k1, "per_hour": round(k1 / hours, 2) if hours else None, "per_hour_upper95": round(ea.poisson_upper(k1) / hours, 2) if hours else None,
                   "clips_with_false_alert": sum(1 for r in rows if r["r1_false_alerts"])},
            "R0": {"false_alerts": k0, "per_hour": round(k0 / hours, 2) if hours else None, "per_hour_upper95": round(ea.poisson_upper(k0) / hours, 2) if hours else None,
                   "clips_with_false_alert": sum(1 for r in rows if r["r0_false_alerts"])},
            "frames_drone_det_conf025": ndf, "frac_frames_drone_det": round(ndf / nfr, 5) if nfr else None,
            "adr0011_trigger": {"r1_false_alert_ge1": k1 >= 1, "drone_det_frames_ge_1pct": (ndf / nfr >= 0.01) if nfr else False},
            "clips_with_r1_false_alert": [r["clip"] for r in rows if r["r1_false_alerts"]],
            "normalization": {"vf": VF, "source_sizes": status["normalize"]["source_sizes"]}}
    (ev / "neg_summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    status["summary"] = {"status": "OK", "minutes": summ["minutes"], "r1_false": k1, "r0_false": k0}
    save_status()
    z = a.out / f"{a.tag}_evidence.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(ev.rglob("*")):
            zf.write(p, p.relative_to(a.out))
    LOG.info("%s", json.dumps({k: summ[k] for k in ("clips", "minutes", "R1", "R0", "frac_frames_drone_det")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
