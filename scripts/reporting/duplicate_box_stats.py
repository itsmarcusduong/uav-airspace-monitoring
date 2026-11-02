#!/usr/bin/env python3
"""Hop trung tren cung vat: cung lop hay khac lop (W6, issue #76; phan tich tham do, dat sau khi xem ket qua).

Hai co che can tach truoc khi chon cach xu ly o W7:
  - track log: cap track trong cung frame co IoU >= --iou, cung lop (NMS theo lop de lot) hay khac lop;
  - detection tho: frame co detection Drone (conf >= --conf) nam chong (IoU >= 0,5) len detection lop khac,
    tren video KHONG phai Drone (nguon canh bao sai cua luat R0).

    python scripts/reporting/duplicate_box_stats.py \
        --tracks baseline_A=results/W05/kaggle_run_12b/w5_track/tracks/tracker_bytetrack_e1 \
        --tracks yolo11n=results/W06/kaggle_run_14/w6_run14/tracks/tracker_bytetrack_e1 \
        --evidence results/W06/kaggle_run_14/w6_run14 --out results/W06/duplicate_boxes.json
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("duplicate_boxes")
DRONE = 2


def iou(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - i
    return i / u if u > 0 else 0.0


def rows_by_frame(p: Path) -> dict[int, list[tuple[int, float, tuple]]]:
    by = defaultdict(list)
    with p.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            by[int(r["frame"])].append((int(r["cls"]), float(r.get("conf") or 0), tuple(float(r[k]) for k in "xywh")))
    return by


def pair_classes(by: dict, thr: float) -> Counter:
    c = Counter()
    for boxes in by.values():
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if iou(boxes[i][2], boxes[j][2]) >= thr:
                    c["same_class" if boxes[i][0] == boxes[j][0] else "cross_class"] += 1
    return c


def drone_on_other(by: dict, conf: float) -> tuple[int, int]:
    """(so frame co Drone >= conf, so frame trong do Drone chong IoU >= 0,5 len detection lop khac)."""
    fr = [f for f, d in by.items() if any(c == DRONE and s >= conf for c, s, _ in d)]
    co = [f for f in fr if any(c != DRONE and iou(b, b2) >= 0.5 for c, _, b in by[f] for c2, s2, b2 in by[f] if c2 == DRONE and s2 >= conf)]
    return len(fr), len(co)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tracks", action="append", required=True, help="nhan=thu_muc_track_log")
    ap.add_argument("--evidence", type=Path, required=True, help="thu muc w6_run14 (dets/, meta.csv)")
    ap.add_argument("--iou", type=float, default=0.3)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out = {"note": "phan tich tham do sau khi xem ket qua W6; khong doi luat nao", "track_pairs_iou": a.iou, "tracks": {}, "raw_drone_on_other_class": {}}
    for spec in a.tracks:
        label, d = spec.split("=", 1)
        c = Counter()
        for f in sorted(Path(d).glob("*.csv")):
            c += pair_classes(rows_by_frame(f), a.iou)
        out["tracks"][label] = {"dir": d, **c}
        LOG.info("%s: %s", label, dict(c))
    with (a.evidence / "meta.csv").open(encoding="utf-8") as fh:
        meta = list(csv.DictReader(fh))
    tot = Counter()
    for m in meta:
        if m["class_name"] == "Drone":
            continue
        n, co = drone_on_other(rows_by_frame(a.evidence / "dets" / f"{m['video_id']}.csv"), a.conf)
        if n:
            out["raw_drone_on_other_class"][m["video_id"]] = {"frames_drone": n, "frames_drone_on_other_class": co}
            tot["frames_drone"] += n; tot["frames_drone_on_other_class"] += co
    out["raw_drone_on_other_class_total"] = dict(tot)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("detection Drone tren video khong Drone: %s", dict(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
