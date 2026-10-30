#!/usr/bin/env python3
"""Thong ke khoang mat cua track va so track log giong nhau giua hai run (issue #57, giai thich ket qua run 12b).

`track_buffer` chi co tac dung khi mot ID bien mat > 30 frame roi xuat hien lai (Ultralytics, frame_rate 30).
Script dem: khoang trong giua hai lan xuat hien cua cung mot ID; khoang khong co track nao trong video;
va so file track log giong het nhau giua hai thu muc tracker.

Vi du:
    python scripts/reporting/track_gap_stats.py \
        --pair results/W05/kaggle_run_12/w5_track/tracks/tracker_bytetrack_default \
               results/W05/kaggle_run_12b/w5_track/tracks/tracker_bytetrack_e1 \
        --pair results/W05/kaggle_run_12/w5_track/tracks/tracker_botsort_default \
               results/W05/kaggle_run_12b/w5_track/tracks/tracker_botsort_e1 \
        --out results/W05/track_gaps.json
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("track_gaps")
BINS = [(1, 5, "1-5"), (6, 30, "6-30"), (31, 45, "31-45"), (46, 10 ** 9, ">45")]


def bin_of(g: int) -> str:
    return next(name for lo, hi, name in BINS if lo <= g <= hi)


def gaps(frames: list[int]) -> list[int]:
    fr = sorted(set(frames))
    return [b - a - 1 for a, b in zip(fr, fr[1:]) if b - a > 1]


def dir_stats(d: Path) -> dict:
    same_id, no_track = Counter(), Counter()
    files = sorted(d.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"{d}: khong co track log")
    for f in files:
        with f.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        by_id = defaultdict(list)
        for r in rows:
            by_id[r["id"]].append(int(r["frame"]))
        for fr in by_id.values():
            same_id.update(bin_of(g) for g in gaps(fr))
        no_track.update(bin_of(g) for g in gaps([int(r["frame"]) for r in rows]))
    return {"dir": d.as_posix(), "videos": len(files), "same_id_gaps": dict(same_id), "no_track_gaps": dict(no_track)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", nargs=2, type=Path, action="append", required=True, metavar=("A", "B"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out = {"note": "khoang = so frame bi thieu giua hai lan xuat hien; bins " + ", ".join(b[2] for b in BINS), "pairs": []}
    for a, b in args.pair:
        sa, sb = dir_stats(a), dir_stats(b)
        names = sorted(p.name for p in a.glob("*.csv"))
        diff = [n for n in names if not (b / n).is_file() or (a / n).read_bytes() != (b / n).read_bytes()]
        out["pairs"].append({"a": sa, "b": sb, "files": len(names), "identical": len(names) - len(diff), "different": diff})
        LOG.info("%s vs %s: %d/%d file giong het", a.name, b.name, len(names) - len(diff), len(names))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
