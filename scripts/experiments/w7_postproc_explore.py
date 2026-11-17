#!/usr/bin/env python3
"""Phan tich THAM DO sau khi da chay V0/V1/V2 (ADR-0012 muc 6). Khong doi luat chon, chi giai thich co che.

Tra loi bon cau hoi, tu file da co (khong giai ma video):
  1. theo video (don vi phan tich): bao nhieu video ID switch giam / tang / giu nguyen; ket qua co con dung
     khi bo cac video dong gop nhieu ID switch nhat khong;
  2. track recall theo video thay doi the nao (luat ADR-0012 khong co dieu kien nay);
  3. hop bi bo co conf the nao (>= new_track_thresh 0,25 thi co the sinh track moi);
  4. tren CUNG cac frame val (buoc 10), ty le hop trung cung lop IoU 0,5-0,7 o detection video (run 14, model.predict)
     so voi du doan anh val (run 13, model.val).

    python scripts/experiments/w7_postproc_explore.py --postproc results/W07/postproc \
        --out results/W07/postproc/exploratory.json
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tracking"))
import offline_track as ot  # noqa: E402

LOG = logging.getLogger("w7_postproc_explore")
DETS = ROOT / "results/W06/kaggle_run_14/w6_run14/dets"
PRED = ROOT / "results/W05/kaggle_run_13/train_yolo11n_640_s20261030/val/predictions.json.gz"
VARIANTS = {"V1_agnostic_nms": "agnostic_nms", "V2_nms_iou": "nms_iou"}
NEW_TRACK_THRESH = 0.25
STRIDE = 10


def per_video(d: Path) -> dict[str, dict]:
    with (d / "per_video_tracking.csv").open(encoding="utf-8") as fh:
        return {r["video_id"]: r for r in csv.DictReader(fh)}


def sign_counts(v0: dict, vx: dict, key: str) -> dict:
    out = {"better": 0, "worse": 0, "same": 0}
    for k, r in v0.items():
        a, b = int(r[key]), int(vx[k][key])
        out["better" if b < a else "worse" if b > a else "same"] += 1
    return out


def drop_top(v0: dict, vx: dict, n: int) -> dict:
    """ID switch tong khi bo n video co ID switch V0 lon nhat."""
    top = sorted(v0, key=lambda k: -int(v0[k]["id_switches"]))[:n]
    a = sum(int(r["id_switches"]) for k, r in v0.items() if k not in top)
    b = sum(int(vx[k]["id_switches"]) for k in v0 if k not in top)
    return {"dropped": top, "v0": a, "variant": b, "reduction": round(1 - b / a, 4) if a else None}


def recall_changes(v0: dict, vx: dict, tol: float = 0.01) -> list[dict]:
    rows = []
    for k, r in sorted(v0.items()):
        a, b = float(r["track_recall"]), float(vx[k]["track_recall"])
        if abs(b - a) > tol:
            rows.append({"video_id": k, "v0": a, "variant": b, "delta": round(b - a, 4),
                         "mean_iou_v0": float(r["mean_iou_matched"]), "mean_iou_variant": float(vx[k]["mean_iou_matched"])})
    return rows


def removed_conf(variant: str) -> dict:
    tot = hi = rem = rem_hi = 0
    for p in sorted(DETS.glob("*.csv")):
        for d in ot.load_dets(p).values():
            kept = {id(x) for x in ot.apply_variant(d, variant, 0.5)}
            for x in d:
                tot += 1
                hi += x[1] >= NEW_TRACK_THRESH
                if id(x) not in kept:
                    rem += 1
                    rem_hi += x[1] >= NEW_TRACK_THRESH
    return {"dets": tot, "dets_conf_ge_0.25": hi, "removed": rem, "removed_conf_ge_0.25": rem_hi}


def duplicates_same_frames(conf: float = 0.25) -> dict:
    with gzip.open(PRED, "rt", encoding="utf-8") as fh:
        rows = json.load(fh)
    off = 1 if rows and min(int(r["category_id"]) for r in rows) >= 1 else 0
    val = defaultdict(list)
    for r in rows:
        val[str(r["image_id"])].append((int(r["category_id"]) - off, float(r["score"]), tuple(float(v) for v in r["bbox"])))
    out = {"conf": conf, "frames": 0, "video_predict": {"boxes": 0, "dup_same_class_iou_0.5_0.7": 0},
           "image_val": {"boxes": 0, "dup_same_class_iou_0.5_0.7": 0}}
    for p in sorted(DETS.glob("*.csv")):
        dets = ot.load_dets(p)
        frames = [int(k.rsplit("_f", 1)[1]) for k in val if k.rsplit("_f", 1)[0] == p.stem]
        for f in sorted(frames):
            out["frames"] += 1
            for name, d in (("video_predict", dets.get(f, [])), ("image_val", val[f"{p.stem}_f{f:05d}"])):
                d = [x for x in d if x[1] >= conf]
                out[name]["boxes"] += len(d)
                out[name]["dup_same_class_iou_0.5_0.7"] += len(d) - len(ot.nms(d, 0.5, False))
    for name in ("video_predict", "image_val"):
        o = out[name]
        o["dup_rate"] = round(o["dup_same_class_iou_0.5_0.7"] / o["boxes"], 4) if o["boxes"] else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--postproc", type=Path, default=ROOT / "results/W07/postproc")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    v0 = per_video(a.postproc / "V0_none")
    out = {"note": "THAM DO sau khi xem ket qua (ADR-0012 muc 6); khong doi luat chon", "variants": {}}
    for d, var in VARIANTS.items():
        vx = per_video(a.postproc / d)
        if set(vx) != set(v0):
            raise ValueError(f"{d}: tap video khac V0")
        out["variants"][d] = {
            "idsw_by_video": sign_counts(v0, vx, "id_switches"),
            "fragments_by_video": sign_counts(v0, vx, "fragments"),
            "idsw_without_top1": drop_top(v0, vx, 1),
            "idsw_without_top3": drop_top(v0, vx, 3),
            "track_recall_changes_gt_0.01": recall_changes(v0, vx),
            "removed_detections": removed_conf(var),
        }
    out["duplicates_on_same_val_frames"] = duplicates_same_frames()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    dup = out["duplicates_on_same_val_frames"]
    LOG.info("trung cung lop tren cung frame: video %s vs anh val %s", dup["video_predict"]["dup_rate"], dup["image_val"]["dup_rate"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
