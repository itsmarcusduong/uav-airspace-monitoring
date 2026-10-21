#!/usr/bin/env python3
"""Cham bang xem mu offset nhan (Kaggle run 03) theo luat dat truoc trong ADR-0004 muc 6.

    python scripts/dataset/score_offset_review.py \
        --key results/W03/kaggle_run_03/w3_export_evidence/offset_review_KEY_do_not_open_before_review.csv \
        --review results/W03/review/offset_review_quang.csv results/W03/review/offset_review_an.csv \
        --out results/W03/review/offset_review_score.json

Moi file review co cot tile, choice_A_B_UNCLEAR (A/B/UNCLEAR). Ket qua: do chinh xac nhom doi chung,
ty le chon nhan i+1 o nhom plus1, va khuyen nghi plus1-policy.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("score")


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", type=Path, required=True)
    ap.add_argument("--review", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--control-min", type=float, default=0.80)
    ap.add_argument("--offset1-min", type=float, default=0.70)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    key = {r["tile"]: r for r in read(args.key)}
    result = {"rule": "ADR-0004 muc 6", "control_min": args.control_min, "offset1_min": args.offset1_min, "reviewers": {}}
    pooled = defaultdict(Counter)
    for path in args.review:
        per = defaultdict(Counter)
        for r in read(path):
            k = key.get(r["tile"].strip())
            choice = r.get("choice_A_B_UNCLEAR", "").strip().upper()
            if not k or choice not in ("A", "B", "UNCLEAR"):
                per["_invalid_or_blank"]["n"] += 1
                continue
            if choice == "UNCLEAR":
                picked = "unclear"
            else:
                a_is_0 = k["A_is"].startswith("label_i (")
                picked = "offset0" if (choice == "A") == a_is_0 else "offset1"
            group = f"{k['modality']}|{k['class_name']}|{k['group']}"
            per[group][picked] += 1
            pooled[k["group"]][picked] += 1
        result["reviewers"][path.stem] = {g: dict(c) for g, c in sorted(per.items())}

    def frac(c: Counter, what: str):
        n = c["offset0"] + c["offset1"]
        return round(c[what] / n, 4) if n else None

    ctrl = frac(pooled["equal"], "offset0")
    off1 = frac(pooled["plus1"], "offset1")
    if ctrl is None or ctrl < args.control_min:
        rec = "offset0 (doi chung khong dat: phuong phap xem khong dang tin, offset CHUA XAC DINH)"
    elif off1 is not None and off1 >= args.offset1_min:
        rec = "offset1 (xuat lai voi --plus1-policy offset1)"
    else:
        rec = "offset0"
    result.update({"pooled": {g: dict(c) for g, c in pooled.items()}, "control_accuracy_offset0": ctrl,
                   "plus1_frac_offset1": off1, "recommendation": rec})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG.info("control=%s plus1_offset1=%s -> %s", ctrl, off1, rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
