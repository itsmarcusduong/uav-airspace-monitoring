#!/usr/bin/env python3
"""W9 (#130), phan tich tham do sau khi xem run 20: RSS tang gan tuyen tinh trong 60 phut co phai do bo do giu
latency trong RAM hay khong.

Bo do w9_e1pipe_bench.py giu moi dong latency (source_id, frame, 5 buoc, total) trong mot list cho toi khi ket thuc
roi moi ghi latency.csv.gz. Script nay dung lai dung so dong va dang tuple do trong mot tien trinh rieng (tracemalloc)
va so voi muc tang RSS cua run 20. Khong doc du lieu that ngoai summary.json va latency.csv.gz da co trong repo.

    python scripts/experiments/w9_rss_growth_check.py --run results/W09/kaggle_run_20/w9_C0_rep1_stab \
        --out results/W09/benchmark/rss_growth_check.json
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import tracemalloc
from pathlib import Path

LOG = logging.getLogger("w9_rss_growth_check")


def list_bytes(rows: list[list[str]]) -> int:
    """Bo nho cua list tuple giong bo do: (str, int, float x6). Chuoi source_id dung chung nhu trong bo do."""
    names: dict[str, str] = {}
    tracemalloc.start()
    lat = []
    for r in rows:
        sid = names.setdefault(r[0], r[0])
        lat.append((sid, int(r[1]), *(float(x) for x in r[2:])))
    cur, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return cur


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    s = json.loads((a.run / "summary.json").read_text(encoding="utf-8"))
    with gzip.open(a.run / "latency.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh); header = next(rd); rows = list(rd)
    if len(rows) != s["frames"]:
        raise SystemExit(f"latency.csv co {len(rows)} dong, summary {s['frames']} frame")
    m = s["memory_samples"]
    first, last = m[0], m[-1]
    est = list_bytes(rows) / 2**20
    rss_growth = last["rss_mb"] - first["rss_mb"]
    out = {"note": "tham do sau khi xem ket qua run 20; khong phai luat dat truoc",
           "frames": len(rows), "columns": header,
           "rss_first": first, "rss_last": last, "rss_growth_mb": round(rss_growth, 1),
           "rss_slope_mb_per_min": round(rss_growth / (last["minute"] - first["minute"]), 3),
           "latency_list_mb_estimate": round(est, 1),
           "share_explained": round(est / rss_growth, 2) if rss_growth > 0 else None,
           "gpu_alloc_mb_first_last": [first.get("gpu_alloc_mb"), last.get("gpu_alloc_mb")]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("RSS tang %.1f MB; list latency uoc %.1f MB (%.0f%%)", rss_growth, est, 100 * est / rss_growth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
