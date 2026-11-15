#!/usr/bin/env python3
"""Chay lai tracker Ultralytics (ByteTrack) OFFLINE tren detection tho da luu cua run 14 (khong giai ma video).

Muc dich (W7, ADR-0012): danh gia cac bien the hau xu ly detection (vd. NMS khong phan lop) ma khong can chay lai
Kaggle. Truoc khi dung, phai chung minh ban offline tai tao duoc track log cua run 14 (che do --variant none).

    python scripts/tracking/offline_track.py --evidence results/W06/kaggle_run_14/w6_run14 \
        --tracker configs/tracker_bytetrack_e1.yaml --variant none --out <thu_muc>

Bien the (`--variant`):
  none            giu nguyen detection (tai tao run 14)
  agnostic_nms    NMS khong phan lop tren detection da luu: hop chong IoU >= --nms-iou voi hop conf cao hon (bat ke lop)
                  bi bo
  nms_iou         NMS cung lop lai voi nguong --nms-iou (thap hon 0,7 cua run 14)
Detection run 14 da qua NMS theo lop IoU 0,7 va conf >= 0,1; bien the chi co the BO them hop, khong them hop.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

LOG = logging.getLogger("offline_track")


def iou_xywh(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - i
    return i / u if u > 0 else 0.0


def nms(dets: list[tuple], thr: float, agnostic: bool) -> list[tuple]:
    """dets: [(cls, conf, (x, y, w, h))]. Giu hop conf cao nhat, bo hop chong IoU >= thr (cung lop, hoac moi lop neu agnostic).
    Dong hang conf: giu hop dung truoc trong danh sach (thu tu file), de ket qua tat dinh."""
    order = sorted(range(len(dets)), key=lambda i: -dets[i][1])
    keep = []
    for i in order:
        if all(iou_xywh(dets[i][2], dets[k][2]) < thr or (not agnostic and dets[i][0] != dets[k][0]) for k in keep):
            keep.append(i)
    return [dets[i] for i in sorted(keep)]


def apply_variant(dets, variant: str, nms_iou: float):
    if variant == "none":
        return dets
    if variant == "agnostic_nms":
        return nms(dets, nms_iou, agnostic=True)
    if variant == "nms_iou":
        return nms(dets, nms_iou, agnostic=False)
    raise ValueError(f"bien the khong ho tro: {variant}")


def load_dets(p: Path) -> dict[int, list[tuple]]:
    by = defaultdict(list)
    with p.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            by[int(r["frame"])].append((int(r["cls"]), float(r["conf"]), tuple(float(r[k]) for k in "xywh")))
    return by


def track_video(dets: dict, n_frames: int, w: int, h: int, cfg, variant: str, nms_iou: float) -> list[dict]:
    from ultralytics.engine.results import Boxes
    from ultralytics.trackers.byte_tracker import BYTETracker
    tr = BYTETracker(args=cfg)
    rows = []
    for f in range(n_frames):
        d = apply_variant(dets.get(f, []), variant, nms_iou)
        arr = np.array([[x, y, x + bw, y + bh, c, k] for k, c, (x, y, bw, bh) in d], dtype=np.float32).reshape(-1, 6)
        out = tr.update(Boxes(arr, (h, w)))
        for x1, y1, x2, y2, tid, score, cls, _ in out:
            x1, x2 = min(max(x1, 0.0), w), min(max(x2, 0.0), w)      # Ultralytics cat hop vao khung anh nhu Results
            y1, y2 = min(max(y1, 0.0), h), min(max(y2, 0.0), h)
            rows.append({"frame": f, "id": int(tid), "cls": int(cls), "conf": round(float(score), 4),
                         "x": round(float(x1), 2), "y": round(float(y1), 2), "w": round(float(x2 - x1), 2), "h": round(float(y2 - y1), 2)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", type=Path, required=True, help="thu muc w6_run14 (meta.csv, dets/)")
    ap.add_argument("--tracker", type=Path, required=True)
    ap.add_argument("--variant", choices=["none", "agnostic_nms", "nms_iou"], default="none")
    ap.add_argument("--nms-iou", type=float, default=0.5)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import yaml
    from ultralytics.utils import IterableSimpleNamespace
    cfg = IterableSimpleNamespace(**yaml.safe_load(a.tracker.read_text(encoding="utf-8")))
    if cfg.tracker_type != "bytetrack":
        raise SystemExit("chi ho tro bytetrack (BoT-SORT can anh cho GMC)")
    with (a.evidence / "meta.csv").open(encoding="utf-8") as fh:
        meta = list(csv.DictReader(fh))
    a.out.mkdir(parents=True, exist_ok=True)
    stats = {"variant": a.variant, "nms_iou": a.nms_iou if a.variant != "none" else None, "tracker": a.tracker.as_posix(),
             "evidence": a.evidence.as_posix(), "videos": len(meta), "dets_in": 0, "dets_kept": 0}
    for m in meta:
        v = m["video_id"]
        dets = load_dets(a.evidence / "dets" / f"{v}.csv")
        stats["dets_in"] += sum(len(x) for x in dets.values())
        stats["dets_kept"] += sum(len(apply_variant(x, a.variant, a.nms_iou)) for x in dets.values())
        rows = track_video(dets, int(m["frames"]), int(m["width"]), int(m["height"]), cfg, a.variant, a.nms_iou)
        with (a.out / f"{v}.csv").open("w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=["frame", "id", "cls", "conf", "x", "y", "w", "h"]); wr.writeheader(); wr.writerows(rows)
    (a.out / "offline_track.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    LOG.info("%s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
