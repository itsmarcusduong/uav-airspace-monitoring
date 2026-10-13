#!/usr/bin/env python3
"""Chan doan lech chi so nhan/frame (label_entries = frames + 1 o 231 video Svanstrom).

Voi moi video mau, thu 3 gia thuyet: frame i ung voi label[i+o], o in {-1, 0, +1}.
Diem = do tuong phan |mean(trong bbox) - mean(vanh bao quanh)| / (std(vanh)+1) tren anh xam,
trung binh tren <= 80 frame co bbox. Nhom doi chung (so label = so frame) phai chon o=0; neu khong,
phuong phap khong dang tin va ket qua phai bi bo qua.

    python w2b_label_alignment.py --data-root /kaggle/input \
        --audit <annotation_audit.csv> --out /kaggle/working/w2b_outputs
Chi doc du lieu. Seed co dinh.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("align")
OFFSETS = (-1, 0, 1)


def find_root(root: Path) -> Path:
    for cand in sorted(root.rglob("Video_IR")):
        if cand.parent.name == "Data":
            return cand.parent
    raise SystemExit(f"Khong thay Data/Video_IR duoi {root}")


def to_box(x):
    if x is None:
        return None
    try:
        b = tuple(float(v) for v in list(x)[:4])
    except Exception:
        return None
    return None if any(v != v for v in b) else b


def contrast(gray, box, margin=6) -> float | None:
    import numpy as np
    h, w = gray.shape
    x, y, bw, bh = box
    x0, y0, x1, y1 = int(round(x)), int(round(y)), int(round(x + bw)), int(round(y + bh))
    if x1 - x0 < 2 or y1 - y0 < 2 or x0 < 0 or y0 < 0 or x1 > w or y1 > h:
        return None
    X0, Y0, X1, Y1 = max(0, x0 - margin), max(0, y0 - margin), min(w, x1 + margin), min(h, y1 + margin)
    inside = gray[y0:y1, x0:x1].astype("float32")
    ring_mask = np.ones((Y1 - Y0, X1 - X0), bool)
    ring_mask[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = False
    ring = gray[Y0:Y1, X0:X1].astype("float32")[ring_mask]
    if ring.size < 8:
        return None
    return float(abs(inside.mean() - ring.mean()) / (ring.std() + 1.0))


def evaluate(video: Path, boxes: list, rng: random.Random, max_frames=80):
    import cv2
    pos = [i for i, b in enumerate(boxes) if isinstance(b, tuple)]
    if len(pos) < 10:
        return None
    picks = sorted(rng.sample(pos, min(max_frames, len(pos))))
    need = set(picks)
    cap = cv2.VideoCapture(str(video))
    scores = defaultdict(list)
    i = 0
    while need:
        ok, frame = cap.read()
        if not ok:
            break
        if i in need:
            need.discard(i)
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            for o in OFFSETS:
                j = i + o
                if 0 <= j < len(boxes) and isinstance(boxes[j], tuple):
                    c = contrast(g, boxes[j])
                    if c is not None:
                        scores[o].append(c)
        i += 1
    cap.release()
    return {o: (sum(v) / len(v), len(v)) for o, v in scores.items() if len(v) >= 5}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True, help="annotation_audit.csv tu job W2")
    ap.add_argument("--out", type=Path, default=Path("w2b_outputs"))
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--per-group", type=int, default=25, help="so video moi nhom (modality,class,diff)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from mcos_decoder import load_groundtruth  # type: ignore

    root = find_root(args.data_root)
    rng = random.Random(args.seed)
    with args.audit.open(encoding="utf-8") as fh:
        audit = list(csv.DictReader(fh))
    groups = defaultdict(list)
    for r in audit:
        d = int(r["label_entries"]) - int(r["frames_decoded"])
        if int(r["frames_with_bbox"]) < 10:
            continue
        kind = "plus1" if d == 1 else "equal" if d == 0 else None
        if kind:
            groups[(r["modality"], r["class_name"], kind)].append(r["video_id"])
    rows = []
    for key in sorted(groups):
        vids = sorted(groups[key])
        rng.shuffle(vids)
        for vid in vids[:args.per_group]:
            mp4 = next(root.glob(f"Video_*/{vid}.mp4"))
            boxes = [to_box(x) for x in load_groundtruth(mp4.with_name(vid + "_LABELS.mat"))]
            res = evaluate(mp4, boxes, rng)
            if not res or 0 not in res:
                continue
            best = max(res, key=lambda o: res[o][0])
            rows.append({"video_id": vid, "modality": key[0], "class_name": key[1], "group": key[2],
                         **{f"contrast_o{o:+d}": round(res[o][0], 4) if o in res else "" for o in OFFSETS}, "best_offset": best})
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "label_alignment.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summ = {}
    for key in sorted({(r["modality"], r["class_name"], r["group"]) for r in rows}):
        sel = [r for r in rows if (r["modality"], r["class_name"], r["group"]) == key]
        summ["|".join(key)] = {"videos": len(sel), "best_offset_counts": dict(Counter(r["best_offset"] for r in sel))}
    (args.out / "label_alignment_summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    LOG.info("summary %s", json.dumps(summ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
