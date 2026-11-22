#!/usr/bin/env python3
"""E1 W9 Kaggle (#129, #130): chay e1pipe tung frame tren bo video benchmark co dinh, MOT lan chay (mot cau hinh, mot lan lap).

docs/w9/W9_PLAN.md muc B, C. Notebook goi script nay nhieu lan (moi lan mot tien trinh moi):
    C0 rep1 (--save-outputs, cong tai tao), C0 rep2, C0 rep3, C1 x3, C2 x3, CPU x1 (5 video dau), on dinh 60 phut.

Cau hinh (moi cau hinh chi doi mot yeu to so voi C0):
    C0  PyTorch fp32          C1  PyTorch fp16 (quantize=16)
    C2  TensorRT fp16 engine (xuat tu cung weights; that bai -> stage export FAILED, ma thoat 2)
    CPU PyTorch fp32 tren CPU

    python w9_e1pipe_bench.py --data-root /kaggle/input --tools <thu muc tools> --weights best.pt --weights-sha <sha> \
        --config C0 --rep 1 --save-outputs --out /kaggle/working --commit <sha> --runner manual

Kiem SHA-256 tung video theo media_manifest.json cua run 17 (src_sha256). Khong dung tap test.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path

LOG = logging.getLogger("w9_e1pipe_bench")
CONFIGS = {"C0": {"device": "0", "quantize": None, "engine": False}, "C1": {"device": "0", "quantize": 16, "engine": False},
           "C2": {"device": "0", "quantize": 16, "engine": True}, "CPU": {"device": "cpu", "quantize": None, "engine": False}}
WARMUP = 30


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def pct(xs: list[float], q: float) -> float | None:
    """Phan vi theo noi suy tuyen tinh (giong numpy 'linear')."""
    if not xs:
        return None
    s = sorted(xs); k = (len(s) - 1) * q; lo = int(k); hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 3)


def rss_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    return -1.0


def summarize_latency(rows: list[tuple], stages: tuple) -> dict:
    """rows: (video, frame, *stages, total). Bo WARMUP frame dau cua video dau tien."""
    keep = rows[WARMUP:]
    out = {"frames_measured": len(keep)}
    for i, k in enumerate((*stages, "total")):
        v = [r[2 + i] for r in keep]
        out[k] = {"p50": pct(v, 0.5), "p95": pct(v, 0.95), "mean": round(statistics.fmean(v), 3) if v else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True, help="du lieu tho Svanstrom (co Data/Video_V)")
    ap.add_argument("--tools", type=Path, required=True, help="thu muc tools: scripts/, configs/, results/W08/... (dataset e1-w3-tools)")
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--weights-sha", required=True)
    ap.add_argument("--config", choices=list(CONFIGS), required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--max-videos", type=int, default=0)
    ap.add_argument("--duration-min", type=float, default=0.0, help="che do on dinh: lap bo video toi khi du so phut")
    ap.add_argument("--save-outputs", action="store_true", help="luu track/det/su kien/FrameResult de danh gia do chinh xac va cong tai tao")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--runner", choices=["manual", "github-actions"], default="manual")
    ap.add_argument("--tag", default="")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tag = a.tag or (f"w9_{a.config}_rep{a.rep}" + ("_stab" if a.duration_min else ""))
    ev = a.out / tag
    if ev.exists():
        if not a.overwrite:
            raise SystemExit(f"{ev} da ton tai; dung --overwrite neu chac chan")
        shutil.rmtree(ev)
    ev.mkdir(parents=True)
    status: dict[str, dict] = {}

    def save_status():
        (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for sub in ("scripts/pipeline", "scripts/alert", "scripts/kaggle"):
        sys.path.insert(0, str(a.tools / sub))
    import e1pipe  # noqa: E402
    import yaml  # noqa: E402
    from w3_export_yolo import find_video_dir  # noqa: E402

    # ------------------------------------------------------------------ inputs
    if sha256(a.weights) != a.weights_sha:
        raise SystemExit("SHA-256 weights khac ky vong")
    r17 = a.tools / "results/W08/kaggle_run_17"
    meta = list(csv.DictReader((r17 / "w8_run17/meta.csv").open(encoding="utf-8")))
    meta.sort(key=lambda m: m["video_id"])
    if a.max_videos:
        meta = meta[: a.max_videos]
    src_sha = {f["video_id"]: f["src_sha256"] for f in json.loads((r17 / "media_manifest.json").read_text(encoding="utf-8"))["files"]}
    vdir = find_video_dir(a.data_root) / "Video_V"
    for m in meta:
        p = vdir / f"{m['video_id']}.mp4"
        if sha256(p) != src_sha[m["video_id"]]:
            raise SystemExit(f"{p.name}: SHA-256 khac media_manifest run 17")
    cfg_tr = yaml.safe_load((a.tools / "configs/tracker_bytetrack_e1.yaml").read_text(encoding="utf-8"))
    rois = yaml.safe_load((a.tools / "configs/roi_w6.yaml").read_text(encoding="utf-8"))
    poly = next(r["polygon"] for r in rois["rois"] if r["name"] == rois["primary"])
    acfg = yaml.safe_load((a.tools / "configs/alert_e1.yaml").read_text(encoding="utf-8"))
    C = CONFIGS[a.config]
    detector_cfg = {"conf": 0.1, "nms_iou": 0.5, "imgsz": 640, "batch": 1, "device": C["device"], "quantize": C["quantize"],
                    "runtime": "tensorrt" if C["engine"] else "pytorch"}
    inputs = {"split": "val", "test_used": False, "videos": len(meta), "frames_expected": sum(int(m["frames"]) for m in meta),
              "weights_sha256": a.weights_sha, "detector": detector_cfg, "config": a.config, "rep": a.rep,
              "trackers": {"tracker_bytetrack_e1": {"cfg": cfg_tr}}, "roi": rois["primary"], "alert": acfg.get("version"),
              "duration_min": a.duration_min, "commit": a.commit, "runner": a.runner,
              "actions_run_id": os.environ.get("GITHUB_RUN_ID", "")}
    (ev / "inputs.json").write_text(json.dumps(inputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    status["inputs"] = {"status": "OK", "videos": len(meta), "video_sha256_checked": len(meta)}

    # ------------------------------------------------------------------ env
    import torch
    import ultralytics
    from ultralytics.utils import IterableSimpleNamespace
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else ""
    if C["device"] != "cpu" and not gpu:
        raise SystemExit("cau hinh GPU nhung khong co CUDA")
    smi = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip() if gpu else ""
    env = {"python": platform.python_version(), "platform": platform.platform(), "torch": torch.__version__, "ultralytics": ultralytics.__version__,
           "cuda": torch.cuda.is_available(), "gpu": gpu, "nvidia_smi": smi, "cpu": platform.processor() or "UNKNOWN",
           "cpu_count": os.cpu_count(), "mem_total_mb": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**20),
           "commit": a.commit, "runner": a.runner, "args": {k: str(v) for k, v in vars(a).items()}}
    try:
        import cv2
        env["cv2"] = cv2.__version__
    except ImportError:
        pass
    (ev / "env.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    status["env"] = {"status": "OK", "gpu": gpu, "ultralytics": ultralytics.__version__}
    save_status()

    # ------------------------------------------------------------------ model (C2: xuat TensorRT)
    weights = str(a.weights)
    if C["engine"]:
        eng = a.out / "_engine_cache" / "best.engine"
        t0 = time.time()
        try:
            if not eng.is_file():
                eng.parent.mkdir(parents=True, exist_ok=True)
                from ultralytics import YOLO
                exported = YOLO(str(a.weights)).export(format="engine", half=True, imgsz=640, batch=1, device=0)
                shutil.copy2(exported, eng)
            weights = str(eng)
            status["export"] = {"status": "OK", "engine_sha256": sha256(eng), "seconds": round(time.time() - t0, 1)}
        except Exception as ex:  # noqa: BLE001 - ghi lai moi loi xuat engine, theo luat: khong thu cau hinh khac
            status["export"] = {"status": "FAILED", "error": f"{type(ex).__name__}: {str(ex)[:800]}"}
            save_status()
            return 2
    det = e1pipe.UltralyticsDetector(weights, conf=0.1, iou=0.5, imgsz=640, device=C["device"], quantize=None if C["engine"] else C["quantize"])
    trcfg = IterableSimpleNamespace(**cfg_tr)

    # ------------------------------------------------------------------ chay
    work = ev if a.save_outputs else Path("/tmp") / f"{tag}_sink"
    if work.exists() and work != ev:
        shutil.rmtree(work)
    sink = e1pipe.Sink(work, tag, a.commit, a.weights_sha, {"detector": detector_cfg, "tracker": cfg_tr, "roi": rois["primary"],
                                                             "alert": acfg.get("version")},
                       C["device"], f"w9 bench {tag}", save_csv=a.save_outputs)
    lat: list[tuple] = []
    per_video, mem = [], []
    t_start = time.perf_counter(); last_mem = -1e9; loop = 0
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    try:
        while True:
            for m in meta:
                vid = m["video_id"]; sid = vid if not a.duration_min else f"{vid}#{loop}"
                n0 = len(lat)
                s = e1pipe.run_source(e1pipe.read_frames(vdir / f"{vid}.mp4"), sid, m["class_name"], float(m["fps"]), int(m["width"]),
                                      int(m["height"]), int(m["frames"]), det, e1pipe.make_tracker(trcfg), sink, poly, acfg,
                                      rois["primary"], a.weights_sha, latency_out=lat)
                if not a.duration_min and s["frames"] != int(m["frames"]):
                    raise RuntimeError(f"{vid}: doc {s['frames']} frame, ky vong {m['frames']}")
                per_video.append({"video_id": sid, "frames": s["frames"], "events": s["events"], "seconds": s["seconds"],
                                  "fps": round(s["frames"] / s["seconds"], 2) if s["seconds"] else None, "lat_rows": len(lat) - n0})
                el = time.perf_counter() - t_start
                if el - last_mem >= 60 or not a.duration_min:
                    mem.append({"minute": round(el / 60, 2), "rss_mb": rss_mb(),
                                "gpu_alloc_mb": round(torch.cuda.memory_allocated() / 2**20, 1) if torch.cuda.is_available() else None})
                    last_mem = el
                if a.duration_min and el >= a.duration_min * 60:
                    break
            loop += 1
            if not a.duration_min or (time.perf_counter() - t_start) >= a.duration_min * 60:
                break
        status["run"] = {"status": "OK", "videos": len(per_video), "frames": len(lat)}
    except Exception as ex:  # noqa: BLE001 - che do on dinh phai ghi lai loi
        status["run"] = {"status": "FAILED", "error": f"{type(ex).__name__}: {str(ex)[:800]}", "frames_done": len(lat)}
    wall = time.perf_counter() - t_start
    sink.close()

    # ------------------------------------------------------------------ tong hop
    stages = e1pipe.STAGES
    t_after_warm = sum(r[-1] for r in lat[:WARMUP]) / 1000.0
    summ = {"tag": tag, "config": a.config, "rep": a.rep, "frames": len(lat), "wall_seconds": round(wall, 3),
            "fps_wall": round(len(lat) / wall, 3) if wall else None,
            "fps_excl_warmup": round((len(lat) - WARMUP) / max(1e-9, wall - t_after_warm), 3) if len(lat) > WARMUP else None,
            "latency_ms": summarize_latency(lat, stages),
            "gpu_peak_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1) if torch.cuda.is_available() else None,
            "memory_samples": mem, "per_video": per_video}
    if a.duration_min and len(mem) >= 2:
        m10 = min(mem, key=lambda x: abs(x["minute"] - 10)); mlast = mem[-1]
        summ["stability"] = {"minutes": round(wall / 60, 2), "rss_min10": m10["rss_mb"], "rss_last": mlast["rss_mb"],
                             "rss_ratio": round(mlast["rss_mb"] / m10["rss_mb"], 4) if m10["rss_mb"] > 0 else None,
                             "errors": status["run"].get("error")}
    (ev / "summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with gzip.open(ev / "latency.csv.gz", "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["source_id", "frame", *stages, "total"]); w.writerows(lat)
    if a.save_outputs:
        with (ev / "meta.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(meta[0])); w.writeheader(); w.writerows(meta)
        with (ev / "timing.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["tracker", "video_id", "frames", "seconds", "fps"])
            for p in per_video:
                w.writerow(["tracker_bytetrack_e1", p["video_id"], p["frames"], p["seconds"], p["fps"]])
        status["detect"] = {"status": "OK"}; status["dump"] = {"status": "OK"}
    status["summary"] = {"status": "OK", "fps_excl_warmup": summ["fps_excl_warmup"], "p95_total_ms": summ["latency_ms"]["total"]["p95"]}
    save_status()
    z = a.out / f"{tag}_evidence.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(ev.rglob("*")):
            zf.write(p, p.relative_to(a.out))
    LOG.info("%s: %d frame, FPS %s, p95 total %s ms", tag, len(lat), summ["fps_excl_warmup"], summ["latency_ms"]["total"]["p95"])
    return 0 if status["run"]["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
