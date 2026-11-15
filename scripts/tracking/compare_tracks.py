#!/usr/bin/env python3
"""So sanh hai thu muc track log (vd. run 14 tren Kaggle va ban chay lai offline) theo tung dong (frame, id, lop, hop).

    python scripts/tracking/compare_tracks.py --a results/W06/kaggle_run_14/w6_run14/tracks/tracker_bytetrack_e1 \
        --b <offline> --out results/W07/offline_repro/track_repro.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def rows(p: Path) -> dict:
    with p.open(encoding="utf-8") as fh:
        return {(r["frame"], r["id"], r["cls"]): tuple(float(r[k]) for k in "xywh") for r in csv.DictReader(fh)}


def compare(a_dir: Path, b_dir: Path, tol: float = 0.02) -> dict:
    out = {"tolerance_px": tol, "videos": 0, "videos_identical": 0, "rows_a": 0, "rows_matched": 0, "differing_videos": {}}
    for fa in sorted(a_dir.glob("*.csv")):
        fb = b_dir / fa.name
        if not fb.is_file():
            raise FileNotFoundError(f"thieu {fb}")
        ra, rb = rows(fa), rows(fb)
        ok = sum(1 for k in ra.keys() & rb.keys() if all(abs(x - y) < tol for x, y in zip(ra[k], rb[k])))
        out["videos"] += 1; out["rows_a"] += len(ra); out["rows_matched"] += ok
        if ra.keys() == rb.keys() and ok == len(ra):
            out["videos_identical"] += 1
        else:
            out["differing_videos"][fa.stem] = {"rows_a": len(ra), "rows_b": len(rb), "rows_matched": ok}
    out["row_match_rate"] = round(out["rows_matched"] / out["rows_a"], 5) if out["rows_a"] else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--tol", type=float, default=0.02)
    ap.add_argument("--out", type=Path, required=True)
    x = ap.parse_args()
    res = {"a": x.a.as_posix(), "b": x.b.as_posix(), **compare(x.a, x.b, x.tol)}
    x.out.parent.mkdir(parents=True, exist_ok=True)
    x.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "differing_videos"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
