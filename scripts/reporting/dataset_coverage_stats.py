#!/usr/bin/env python3
"""Do phu cua Svanstrom (anh kha kien) so voi chi tieu cua de tai (issue #88).

Tra loi bang so lieu, khong bang cam tinh:
  - moi split co bao nhieu video / frame / phut theo lop;
  - tong thoi luong video KHONG co Drone (de do canh bao sai/gio, Thuyet minh muc 13: >= 2 gio);
  - so video Drone trong val (luc thong ke cua moi so sanh);
  - nham lop va FP tren frame am tinh cua detector dang dung (run 13, val).

    python scripts/reporting/dataset_coverage_stats.py \
        --split data/splits/video_split_v1.csv \
        --meta results/W06/kaggle_run_14/w6_run14/meta.csv \
        --analysis results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030 \
        --out results/W06/dataset_coverage.json
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("dataset_coverage")
TARGET_NEG_MIN = 120.0


def coverage(rows: list[dict], fps: float, modality: str = "V") -> dict:
    """Thong ke video/frame/phut theo split va lop cho mot modality."""
    vids, frames = Counter(), Counter()
    for r in rows:
        if r["modality"] != modality:
            continue
        vids[(r["split"], r["class_name"])] += 1
        frames[(r["split"], r["class_name"])] += int(r["frames"])
    by_split = defaultdict(dict)
    for (s, c), n in sorted(vids.items()):
        by_split[s][c] = {"videos": n, "frames": frames[(s, c)], "minutes": round(frames[(s, c)] / fps / 60, 2)}
    neg = {s: round(sum(v["frames"] for c, v in d.items() if c != "Drone") / fps / 60, 2) for s, d in by_split.items()}
    total_neg = round(sum(neg.values()), 2)
    return {
        "modality": modality, "fps": fps, "by_split": dict(by_split),
        "non_drone_minutes": neg, "non_drone_minutes_all_splits": total_neg,
        "target_negative_minutes": TARGET_NEG_MIN,
        "target_reachable_with_svanstrom_only": total_neg >= TARGET_NEG_MIN,
        "drone_videos_val": by_split.get("val", {}).get("Drone", {}).get("videos", 0),
    }


def confusion(path: Path) -> dict:
    """Doc class_confusion.csv (gt,pred,count) -> ma tran va ty le GT bi doan thanh Drone."""
    m = defaultdict(dict)
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            m[r["gt"]][r["pred"]] = int(r["count"])
    to_drone = {g: {"gt_boxes": sum(p.values()), "pred_drone": p.get("Drone", 0)} for g, p in m.items() if g != "Drone"}
    return {"matrix": dict(m), "non_drone_gt_predicted_as_drone": to_drone}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", type=Path, required=True)
    ap.add_argument("--meta", type=Path, required=True, help="meta.csv cua run 14 (fps, kich thuoc, video val)")
    ap.add_argument("--analysis", type=Path, required=True, help="thu muc analysis_* cua run 13")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with a.meta.open(encoding="utf-8") as fh:
        meta = list(csv.DictReader(fh))
    fps = {float(m["fps"]) for m in meta}
    if len(fps) != 1:
        raise ValueError(f"{a.meta}: fps khong dong nhat {sorted(fps)}")
    with a.split.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = {"note": "so lieu tu split v1 + run 13 (val) + run 14 (val); test khoa, chi dem video/frame cua test, khong mo nhan",
           "inputs": {"split": a.split.as_posix(), "meta": a.meta.as_posix(), "analysis": a.analysis.as_posix()},
           "visible": coverage(rows, fps.pop())}
    nd = [m for m in meta if m["class_name"] != "Drone"]
    out["run14_val_non_drone"] = {"videos": len(nd), "frames": sum(int(m["frames"]) for m in nd),
                                  "minutes": round(sum(int(m["frames"]) / float(m["fps"]) for m in nd) / 60, 2),
                                  "resolution": sorted({f"{m['width']}x{m['height']}" for m in meta})}
    out["detector_val_confusion"] = confusion(a.analysis / "class_confusion.csv")
    out["detector_val_negative_images"] = json.loads((a.analysis / "negatives_fp.json").read_text(encoding="utf-8"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    v = out["visible"]
    LOG.info("video khong Drone (kha kien, moi split): %.1f phut / muc tieu %.0f phut", v["non_drone_minutes_all_splits"], TARGET_NEG_MIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
