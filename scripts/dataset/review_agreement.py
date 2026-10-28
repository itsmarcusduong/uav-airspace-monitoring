#!/usr/bin/env python3
"""Do dong y giua hai nguoi review nhan theo video (issue #24): verdict cua An va review_quang_v2.

    python scripts/dataset/review_agreement.py --csv results/W03/review/review_assignment_w3.csv \
        --out results/W04/review_v2_agreement.json

Chi tinh tren cac video co ca hai verdict. Don vi la video. In ty le dong y, Cohen's kappa va danh sach video lech.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter
from pathlib import Path

log = logging.getLogger("review_agreement")


def cohen_kappa(a: list, b: list) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return None if pe == 1 else (po - pe) / (1 - pe)


def agreement(rows: list, col_a: str, col_b: str) -> dict:
    pairs = [(r["video_id"], r[col_a].strip(), r[col_b].strip()) for r in rows if r.get(col_a, "").strip() and r.get(col_b, "").strip()]
    a, b = [p[1] for p in pairs], [p[2] for p in pairs]
    k = cohen_kappa(a, b)
    return {"rater_a": col_a, "rater_b": col_b, "videos": len(pairs),
            "agree": sum(x == y for x, y in zip(a, b)),
            "percent_agree": round(100 * sum(x == y for x, y in zip(a, b)) / len(pairs), 2) if pairs else None,
            "cohen_kappa": round(k, 4) if k is not None else None,
            "confusion": {f"{x}|{y}": c for (x, y), c in sorted(Counter(zip(a, b)).items())},
            "disagreements": [{"video_id": v, col_a: x, col_b: y} for v, x, y in pairs if x != y]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--rater-a", default="verdict", help="cot verdict cua An")
    ap.add_argument("--rater-b", default="review_quang_v2")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not a.csv.is_file():
        raise SystemExit(f"khong thay {a.csv}")
    rows = list(csv.DictReader(a.csv.open(encoding="utf-8-sig")))
    for c in ("video_id", a.rater_a, a.rater_b):
        if rows and c not in rows[0]:
            raise SystemExit(f"thieu cot {c}")
    res = agreement(rows, a.rater_a, a.rater_b)
    res["source"] = str(a.csv).replace("\\", "/")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("%d video, dong y %s%%, kappa %s", res["videos"], res["percent_agree"], res["cohen_kappa"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
