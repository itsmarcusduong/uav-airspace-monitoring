#!/usr/bin/env python3
"""Cham tap chuan CVAT (issue #24, ADR-0006): so hop An ve voi nhan goc muc i va i+1.

Chi chay SAU KHI file annotation cua An da duoc commit (khoa dap an mo sau).

    python scripts/dataset/score_cvat_gold.py --annotations <cvat_export_yolo11.zip> --key <gold_KEY.zip> \
        --out results/W04/cvat_gold

Doc: CVAT export "YOLO 1.1" (obj_train_data/gold_XXXX.txt, dong "0 cx cy w h" chuan hoa). Moi anh can dung 1 hop;
anh khong co hop -> ghi "no_box" (An danh dau vat khong thay). Gom theo video, sign test theo video, luat giong ADR-0006.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path


def iou(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def sign_p(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(0, min(k, n - k) + 1)) / 2 ** n)


def read_annotations(path: Path) -> dict:
    ann = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            p = Path(name)
            if p.suffix == ".txt" and p.stem.startswith("gold_"):
                lines = [ln.split() for ln in zf.read(name).decode("utf-8").splitlines() if ln.strip()]
                for k, ln in enumerate(lines, 1):
                    if len(ln) != 5:
                        raise SystemExit(f"{name}:{k}: can 5 truong, co {len(ln)}")
                ann[p.stem] = [tuple(float(v) for v in ln[1:]) for ln in lines]
    if not ann:
        raise SystemExit(f"{path}: khong thay file gold_XXXX.txt (export dung dinh dang YOLO 1.1?)")
    return ann


def _center(b) -> tuple:
    return (b[0] + b[2] / 2, b[1] + b[3] / 2)


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def exploratory_center(key: list, ann: dict, tie: float) -> dict:
    """THAM DO (them sau khi xem ket qua IoU, KHONG thay luat dat truoc): so khoang cach tam hop An ve toi tam nhan i va i+1.

    Ly do: hop An ve sat vat hon nhieu so voi nhan goc (dien tich nho hon), nen IoU bi chi phoi boi do rong hop, khong
    chi boi vi tri. Khoang cach tam khong phu thuoc do rong hop. Don vi kiem dinh van la video; khong dua ra verdict.
    """
    per_vid, dist, ratio = defaultdict(list), [], []
    for k in key:
        boxes = ann.get(k["gold_id"], [])
        if len(boxes) != 1:
            continue
        W, H = float(k["width"]), float(k["height"])
        cx, cy, w, h = boxes[0]
        li, lj = json.loads(k["label_i"]), json.loads(k["label_i1"])
        c = (cx * W, cy * H)
        d0, d1 = math.dist(c, _center(li)), math.dist(c, _center(lj))
        dist.append(min(d0, d1))
        if li[2] * li[3] > 0:
            ratio.append((w * W * h * H) / (li[2] * li[3]))
        if abs(d0 - d1) >= tie:
            g = "control_equal" if k["kind"] == "equal" else f"{k['class_name']}|{k['kind']}"
            per_vid[(g, k["video_id"])].append(d0 - d1)  # > 0: gan nhan i+1 hon
    groups = defaultdict(list)
    for (g, _), ds in per_vid.items():
        groups[g].append(sum(ds) / len(ds))
    return {"note": "THAM DO, them sau khi xem ket qua; khong dung de ra quyet dinh thay luat dat truoc (ADR-0006)",
            "box_vs_label": {"median_center_dist_px": round(_median(dist), 2) if dist else None,
                             "frac_center_dist_le_10px": round(sum(x <= 10 for x in dist) / len(dist), 4) if dist else None,
                             "median_area_ratio_annot_over_label_i": round(_median(ratio), 4) if ratio else None},
            "groups": {g: {"videos": len(d), "videos_closer_to_i1": sum(x > 0 for x in d),
                           "sign_test_p": sign_p(sum(x > 0 for x in d), len(d))} for g, d in groups.items()}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--annotations", type=Path, required=True)
    ap.add_argument("--key", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tie", type=float, default=0.01)
    ap.add_argument("--video-frac", type=float, default=0.80)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--center-tie", type=float, default=0.5, help="px; bo frame co |d(i) - d(i+1)| nho hon (phan tham do)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.key) as zf:
        key = list(csv.DictReader(io.StringIO(zf.read("gold_key.csv").decode("utf-8"))))
    ann = read_annotations(a.annotations)
    rows, per_vid = [], defaultdict(list)
    for k in key:
        W, H = float(k["width"]), float(k["height"])
        li, lj = json.loads(k["label_i"]), json.loads(k["label_i1"])
        boxes = ann.get(k["gold_id"], [])
        rec = {"gold_id": k["gold_id"], "video_id": k["video_id"], "class_name": k["class_name"], "kind": k["kind"],
               "frame_index": k["frame_index"], "boxes": len(boxes), "iou_i": "", "iou_i1": "", "used": 0, "status": ""}
        if len(boxes) == 0:
            rec["status"] = "no_box"
        elif len(boxes) > 1:
            rec["status"] = "multi_box"
        else:
            cx, cy, w, h = boxes[0]
            g = ((cx - w / 2) * W, (cy - h / 2) * H, w * W, h * H)
            u0, u1 = iou(g, li), iou(g, lj)
            rec.update(iou_i=round(u0, 4), iou_i1=round(u1, 4), status="ok",
                       used=int(max(u0, u1) >= 0.1 and abs(u1 - u0) >= a.tie))
            if rec["used"]:
                per_vid[(k["video_id"], k["class_name"], k["kind"])].append(u1 - u0)
        rows.append(rec)
    with (a.out / "gold_pairs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    groups = defaultdict(list)
    for (v, c, kind), ds in per_vid.items():
        groups["control_equal" if kind == "equal" else f"{c}|{kind}"].append(sum(ds) / len(ds))
    res = {g: {"videos": len(d), "videos_i1_better": sum(x > 0 for x in d), "sign_test_p": sign_p(sum(x > 0 for x in d), len(d))}
           for g, d in groups.items()}
    ctl = res.get("control_equal")
    control_ok = bool(ctl and ctl["videos"] >= 5 and (ctl["videos"] - ctl["videos_i1_better"]) / ctl["videos"] >= a.video_frac
                      and ctl["sign_test_p"] < a.alpha)
    verdict = {}
    for g, r in res.items():
        if g == "control_equal":
            continue
        f = r["videos_i1_better"] / r["videos"] if r["videos"] else 0
        verdict[g] = ("UNDETERMINED (doi chung khong dat)" if not control_ok else
                      "offset1" if f >= a.video_frac and r["sign_test_p"] < a.alpha else
                      "offset0" if (1 - f) >= a.video_frac and r["sign_test_p"] < a.alpha else "UNDETERMINED")
    ok = [r for r in rows if r["status"] == "ok"]
    best = [max(r["iou_i"], r["iou_i1"]) for r in ok]
    summary = {"frames": len(rows), "status_counts": {s: sum(r["status"] == s for r in rows) for s in ("ok", "no_box", "multi_box")},
               "label_quality": {"median_best_iou": sorted(best)[len(best) // 2] if best else None,
                                 "frac_best_iou_ge_0_5": round(sum(b >= 0.5 for b in best) / len(best), 4) if best else None},
               "groups": res, "control_ok": control_ok, "verdict": verdict,
               "exploratory_center": exploratory_center(key, ann, a.center_tie)}
    (a.out / "gold_score.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
