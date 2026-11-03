#!/usr/bin/env python3
"""Tim 40 anh val "am tinh" cua e1-yolo-v1 va detection tren tung anh (W6, tra loi review cua An tren #89).

`negatives_fp.json` cua run 13 chi co so dem (40 anh am tinh, 38 anh co FP o conf 0,25). Script dung lai danh sach tu
bang chung run 14 (cung weights YOLO11n s20261030, cung 38 video val):
  - anh am tinh = frame stride 10 (0, 10, 20, ...) khong co hop GT (gt/<video>.csv, offset0 nhu e1-yolo-v1);
  - detection = dets/<video>.csv (conf >= 0,1, giai ma tu video) loc lai o --conf;
  - nguyen nhan: frame truoc frame GT dau tien (`before_first_label`), sau frame GT cuoi (`after_last_label`),
    hay khoang trong giua cac frame co nhan (`gap_inside_labels`);
  - IoU tot nhat giua detection va hop GT gan nhat (frame GT dau/cuoi) -> goi y vat van con trong khung.

Run 13 du doan tren anh JPEG, run 14 tren frame giai ma tu video: so dem khop nhau la phep kiem cheo, khong phai bang
chung tung hop giong het. Day la phan tich tham do sau khi xem ket qua, khong doi luat nao.

    python scripts/reporting/val_negative_frames.py --evidence results/W06/kaggle_run_14/w6_run14 \
        --check results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030/negatives_fp.json --out results/W06/val_negative_frames
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("val_negatives")
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]


def iou(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - i
    return i / u if u > 0 else 0.0


def cause(frame: int, labeled: list[int]) -> tuple[str, int | None]:
    """Phan loai frame khong co nhan so voi cac frame co nhan; tra ve (nguyen nhan, frame GT gan nhat)."""
    if not labeled:
        return "no_labels_in_video", None
    if frame < labeled[0]:
        return "before_first_label", labeled[0]
    if frame > labeled[-1]:
        return "after_last_label", labeled[-1]
    prev = max(f for f in labeled if f < frame)
    return "gap_inside_labels", prev


def negative_frames(meta: list[dict], gt: dict, dets: dict, stride: int, conf: float) -> list[dict]:
    rows = []
    for m in meta:
        v, n = m["video_id"], int(m["frames"])
        boxes = gt.get(v, {})
        labeled = sorted(boxes)
        for f in range(0, n, stride):
            if f in boxes:
                continue
            why, ref = cause(f, labeled)
            ds = [d for d in dets.get(v, {}).get(f, []) if d[1] >= conf]
            best = max((iou(d[2], boxes[ref]) for d in ds), default=None) if ref is not None else None
            rows.append({"video_id": v, "class_name": m["class_name"], "frame": f,
                         "image": f"images/val/{v}_f{f:05d}.jpg", "cause": why,
                         "labeled_frames": f"{labeled[0]}-{labeled[-1]}" if labeled else "",
                         "nearest_gt_frame": "" if ref is None else ref, "n_det": len(ds),
                         "det_classes": " ".join(CLASSES[d[0]] for d in ds),
                         "det_conf": " ".join(f"{d[1]:.3f}" for d in ds),
                         "det_boxes_xywh": " | ".join(",".join(f"{x:.1f}" for x in d[2]) for d in ds),
                         "best_iou_with_nearest_gt": "" if best is None else round(best, 3)})
    return rows


def load_run13(path: Path, nc: int = 4) -> dict:
    """predictions.json(.gz) cua Ultralytics val (run 13, anh JPEG): stem -> [(cls 0-based, conf, (x, y, w, h))]."""
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    cats = {d["category_id"] for d in data}
    off = 1 if cats and min(cats) >= 1 and max(cats) <= nc else 0
    out = defaultdict(list)
    for d in data:
        out[str(d["image_id"])].append((int(d["category_id"]) - off, float(d["score"]), tuple(float(v) for v in d["bbox"])))
    return out


def add_run13(rows: list[dict], preds: dict, gt: dict, conf: float) -> None:
    """Them du doan run 13 (dung anh JPEG ma metric da tinh) va hop GT gan nhat de An doi chieu."""
    for i, r in enumerate(rows, 1):
        stem = Path(r["image"]).stem
        ps = sorted((p for p in preds.get(stem, []) if p[1] >= conf), key=lambda p: -p[1])
        ref = r["nearest_gt_frame"]
        g = gt[r["video_id"]][ref] if ref != "" else None
        r.update({"sample_no": i, "role": "FP" if ps else "control_no_fp", "label_file": "empty",
                  "nearest_gt_xywh": "" if g is None else ",".join(f"{x:.1f}" for x in g),
                  "run13_n_pred": len(ps), "run13_classes": " ".join(CLASSES[p[0]] for p in ps),
                  "run13_conf": " ".join(f"{p[1]:.3f}" for p in ps),
                  "run13_boxes_xywh": " | ".join(",".join(f"{x:.1f}" for x in p[2]) for p in ps),
                  "run13_best_iou_with_nearest_gt": round(max(iou(p[2], g) for p in ps), 3) if ps and g else ""})


def summarize(rows: list[dict]) -> dict:
    by = defaultdict(Counter)
    for r in rows:
        by[r["cause"]]["frames"] += 1
        by[r["cause"]]["with_det"] += r["n_det"] > 0
        if r["best_iou_with_nearest_gt"] != "" and r["best_iou_with_nearest_gt"] >= 0.3:
            by[r["cause"]]["det_iou_ge_0.3_with_nearest_gt"] += 1
    return {"negative_frames": len(rows), "with_det": sum(r["n_det"] > 0 for r in rows),
            "by_cause": {k: dict(v) for k, v in by.items()},
            "videos": dict(Counter(r["video_id"] for r in rows))}


def load(ev: Path) -> tuple[list[dict], dict, dict]:
    with (ev / "meta.csv").open(encoding="utf-8") as fh:
        meta = list(csv.DictReader(fh))
    gt, dets = {}, {}
    for m in meta:
        v = m["video_id"]
        with (ev / "gt" / f"{v}.csv").open(encoding="utf-8") as fh:
            gt[v] = {int(r["frame"]): tuple(float(r[k]) for k in "xywh") for r in csv.DictReader(fh)}
        by = defaultdict(list)
        with (ev / "dets" / f"{v}.csv").open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                by[int(r["frame"])].append((int(r["cls"]), float(r["conf"]), tuple(float(r[k]) for k in "xywh")))
        dets[v] = by
    return meta, gt, dets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", type=Path, required=True, help="thu muc w6_run14 (meta.csv, gt/, dets/)")
    ap.add_argument("--stride", type=int, default=10, help="stride lay mau cua e1-yolo-v1 (ADR-0004)")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--check", type=Path, help="negatives_fp.json cua run 13 de doi chieu so dem")
    ap.add_argument("--run13-predictions", type=Path, help="val/predictions.json.gz cua run 13 (anh JPEG)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    meta, gt, dets = load(a.evidence)
    rows = negative_frames(meta, gt, dets, a.stride, a.conf)
    if a.run13_predictions:
        add_run13(rows, load_run13(a.run13_predictions), gt, a.conf)
    summ = {"note": "tham do sau khi xem ket qua; anh am tinh tai dung tu run 14 (offset0, stride 10)", "conf": a.conf, **summarize(rows)}
    if a.run13_predictions:
        summ["run13_images_with_pred"] = sum(r["run13_n_pred"] > 0 for r in rows)
        summ["run13_vs_run14_same_has_pred"] = sum((r["run13_n_pred"] > 0) == (r["n_det"] > 0) for r in rows)
    if a.check:
        ref = json.loads(a.check.read_text(encoding="utf-8"))
        summ["check_run13"] = {**ref, "match": ref.get("negative_images") == summ["negative_frames"] and ref.get("images_with_fp") == summ["with_det"]}
        if not summ["check_run13"]["match"]:
            LOG.warning("so dem khong khop run 13: %s vs %s/%s", ref, summ["negative_frames"], summ["with_det"])
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "val_negative_frames.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["video_id"]); w.writeheader(); w.writerows(rows)
    (a.out / "val_negative_summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("%d anh am tinh, %d co detection >= %.2f", summ["negative_frames"], summ["with_det"], a.conf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
