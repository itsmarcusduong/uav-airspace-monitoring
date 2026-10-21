#!/usr/bin/env python3
"""E1 W3 Kaggle job 05: phan tich ket qua baseline A tren VAL (issue #19). CPU du.

    python w3_analyze_baseline.py --data-dir <e1-yolo-v1> --manifest <yolo_manifest.csv.gz> \
        --train-evidence <w3_train_evidence> --out /kaggle/working --commit <sha>

Dau vao: nhan YOLO val (data-dir/labels/val), yolo_manifest.csv.gz (run 03b),
w3_train_evidence/ (run 04: train/results.csv, val/predictions.json, baseline_A_val_metrics.json).
Dau ra (w3_analysis/): learning_curves.png/.csv, operating_points.csv (P/R/F1 theo nguong conf),
recall_by_size.csv, recall_by_video.csv, class_confusion.csv, negatives_fp.json, analysis_summary.json,
fig_*.png. Khop du doan - nhan: cung lop, IoU >= 0,5, tham lam theo score. Nguong van hanh chon tren VAL
(F1 lop Drone lon nhat, theo training_protocol.md muc 7) nen so lieu lac quan; test bi khoa.
Dong nhan sai dinh dang -> stage inputs FAILED kem duong dan:so dong (khong bo qua am tham).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import math
import shutil
import traceback
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("w3_analyze")
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]
SMALL, MEDIUM = 32 * 32, 96 * 96
IOU_T = 0.5


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def bucket(area: float) -> str:
    return "small" if area < SMALL else "medium" if area < MEDIUM else "large"


def iou(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        if not rows:
            fh.write("empty\n")
            return
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class LabelError(ValueError):
    """Dong nhan YOLO sai dinh dang: dung phan tich thay vi bo qua am tham (review An, PR #26)."""


def parse_label_line(line: str, path: Path, lineno: int, nc: int) -> tuple[int, float, float, float, float]:
    p = line.split()
    if len(p) != 5:
        raise LabelError(f"{path}:{lineno}: can 5 truong, co {len(p)}: {line!r}")
    try:
        c = int(p[0])
        cx, cy, bw, bh = (float(v) for v in p[1:])
    except ValueError as exc:
        raise LabelError(f"{path}:{lineno}: gia tri khong phai so: {line!r}") from exc
    if not 0 <= c < nc or p[0] != str(c):
        raise LabelError(f"{path}:{lineno}: class id {p[0]!r} ngoai [0, {nc - 1}]")
    if not all(math.isfinite(v) for v in (cx, cy, bw, bh)):
        raise LabelError(f"{path}:{lineno}: NaN/inf: {line!r}")
    if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0 and 0.0 < bw <= 1.0 and 0.0 < bh <= 1.0):
        raise LabelError(f"{path}:{lineno}: toa do chuan hoa ngoai mien (cx,cy in [0,1]; w,h in (0,1]): {line!r}")
    return c, cx, cy, bw, bh


def load_gt(data_dir: Path, manifest: Path, nc: int = len(CLASSES)) -> dict:
    """stem -> {video, w, h, boxes:[(cls, x, y, w, h, area)]} cho split val. Dong sai dinh dang -> LabelError."""
    meta = {}
    with gzip.open(manifest, "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["split"] == "val":
                meta[Path(r["image"]).stem] = r
    if not meta:
        raise LabelError(f"{manifest}: khong co anh split val")
    gt = {}
    for stem, r in meta.items():
        W, H = float(r["width"]), float(r["height"])
        boxes = []
        lab = data_dir / "labels" / "val" / f"{stem}.txt"
        if not lab.is_file():
            raise FileNotFoundError(lab)
        for lineno, line in enumerate(lab.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            c, cx, cy, bw, bh = parse_label_line(line, lab, lineno, nc)
            w, h = bw * W, bh * H
            boxes.append((c, cx * W - w / 2, cy * H - h / 2, w, h, w * h))
        if str(r.get("has_bbox", "")) in ("0", "1") and int(r["has_bbox"]) != int(bool(boxes)):
            raise LabelError(f"{lab}: has_bbox={r['has_bbox']} trong manifest nhung file nhan co {len(boxes)} hop")
        gt[stem] = {"video": r["video_id"], "class_name": r["class_name"], "W": W, "H": H, "boxes": boxes}
    return gt


def load_preds(path: Path, nc: int) -> tuple[dict, int]:
    """stem -> [(cls, x, y, w, h, score)]; tu nhan dang category_id 0- hay 1-based."""
    data = json.loads(path.read_text(encoding="utf-8"))
    cats = {d["category_id"] for d in data}
    off = 1 if cats and min(cats) >= 1 and max(cats) <= nc else 0
    preds = defaultdict(list)
    for d in data:
        x, y, w, h = d["bbox"]
        preds[str(d["image_id"])].append((int(d["category_id"]) - off, x, y, w, h, float(d["score"])))
    return preds, off


def match(gt: dict, preds: dict, thr: float, class_agnostic=False):
    """Tra ve list GT (stem, cls, area, matched, pred_cls) va so FP theo anh."""
    gts, fps = [], Counter()
    for stem, g in gt.items():
        ps = sorted((p for p in preds.get(stem, []) if p[5] >= thr), key=lambda p: -p[5])
        used = set()
        for gb in g["boxes"]:
            best, bi = 0.0, None
            for i, p in enumerate(ps):
                if i in used or (not class_agnostic and p[0] != gb[0]):
                    continue
                v = iou(gb[1:5], p[1:5])
                if v > best:
                    best, bi = v, i
            ok = bi is not None and best >= IOU_T
            if ok:
                used.add(bi)
            gts.append({"stem": stem, "video": g["video"], "cls": gb[0], "area": gb[5], "matched": ok,
                        "pred_cls": ps[bi][0] if ok else -1})
        fps[stem] = len(ps) - len(used)
    return gts, fps


def prf(gts, fps, cls=None):
    tp = sum(1 for g in gts if g["matched"] and (cls is None or g["cls"] == cls))
    n = sum(1 for g in gts if cls is None or g["cls"] == cls)
    return tp, n, sum(fps.values())


def stage_curves(ev: Path, out: Path) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = list(csv.DictReader((ev / "train" / "results.csv").open(encoding="utf-8")))
    rows = [{k.strip(): v for k, v in r.items()} for r in rows]
    shutil.copy2(ev / "train" / "results.csv", out / "learning_curves.csv")
    ep = [int(float(r["epoch"])) for r in rows]
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for k, lab in (("train/box_loss", "train box"), ("val/box_loss", "val box"), ("train/cls_loss", "train cls"), ("val/cls_loss", "val cls")):
        if k in rows[0]:
            ax[0].plot(ep, [float(r[k]) for r in rows], label=lab)
    ax[0].set_title("Loss"); ax[0].set_xlabel("epoch"); ax[0].legend(fontsize=8)
    for k, lab in (("metrics/mAP50(B)", "mAP@0.5"), ("metrics/mAP50-95(B)", "mAP@0.5:0.95")):
        if k in rows[0]:
            ax[1].plot(ep, [float(r[k]) for r in rows], label=lab)
    ax[1].set_title("mAP (val)"); ax[1].set_xlabel("epoch"); ax[1].legend(fontsize=8)
    for k, lab in (("metrics/precision(B)", "precision"), ("metrics/recall(B)", "recall")):
        if k in rows[0]:
            ax[2].plot(ep, [float(r[k]) for r in rows], label=lab)
    ax[2].set_title("P / R (val)"); ax[2].set_xlabel("epoch"); ax[2].legend(fontsize=8)
    for a in ax:
        a.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(out / "learning_curves.png", dpi=150); plt.close(fig)
    m = [float(r.get("metrics/mAP50-95(B)", 0)) for r in rows]
    best = max(range(len(m)), key=lambda i: m[i])
    return {"epochs_run": len(rows), "best_epoch_by_map50_95": ep[best], "map50_95_at_best": round(m[best], 4)}


def stage_ops(gt, preds, out: Path) -> dict:
    rows, best, best_macro = [], None, None
    drone = CLASSES.index("Drone")
    for t in [round(0.05 * i, 2) for i in range(1, 19)]:
        gts, fps = match(gt, preds, t)
        f1s = []
        rec = {"conf": t}
        tp_all, n_all, fp_all = prf(gts, fps)
        for c, name in enumerate(CLASSES):
            tp, n, _ = prf(gts, fps, c)
            fp_c = sum(1 for stem, ps in preds.items() if stem in gt for p in ps if p[5] >= t and p[0] == c) - tp
            p = tp / (tp + fp_c) if tp + fp_c else 0.0
            r = tp / n if n else 0.0
            f = 2 * p * r / (p + r) if p + r else 0.0
            f1s.append(f)
            rec.update({f"{name}_P": round(p, 4), f"{name}_R": round(r, 4), f"{name}_F1": round(f, 4)})
        P = tp_all / (tp_all + fp_all) if tp_all + fp_all else 0.0
        R = tp_all / n_all if n_all else 0.0
        rec.update({"all_P": round(P, 4), "all_R": round(R, 4), "macro_F1": round(sum(f1s) / len(f1s), 4)})
        rows.append(rec)
        # Giao thuc #17: chon nguong toi da F1 lop Drone tren val; dong hang -> nguong cao hon (duyet tang dan nen dung >=)
        if best is None or rec["Drone_F1"] >= best["Drone_F1"]:
            best = rec
        if best_macro is None or rec["macro_F1"] >= best_macro["macro_F1"]:
            best_macro = rec
    write_csv(out / "operating_points.csv", rows)
    return {"selection_rule": "max Drone F1 on val; tie -> higher conf (training_protocol.md muc 7)",
            "conf_selected_on_val": best["conf"], "Drone_P": best["Drone_P"], "Drone_R": best["Drone_R"], "Drone_F1": best["Drone_F1"],
            "macro_F1": best["macro_F1"], "all_P": best["all_P"], "all_R": best["all_R"],
            "reference_conf_max_macro_F1": best_macro["conf"], "reference_macro_F1": best_macro["macro_F1"], "drone_class_id": drone}


def stage_breakdown(gt, preds, thr: float, out: Path) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gts, fps = match(gt, preds, thr)
    size = defaultdict(Counter)
    for g in gts:
        b = bucket(g["area"])
        size[(CLASSES[g["cls"]], b)]["n"] += 1
        size[(CLASSES[g["cls"]], b)]["tp"] += g["matched"]
        size[("ALL", b)]["n"] += 1
        size[("ALL", b)]["tp"] += g["matched"]
    srows = [{"class": k[0], "size": k[1], "gt": v["n"], "tp": v["tp"], "recall": round(v["tp"] / v["n"], 4) if v["n"] else ""}
             for k, v in sorted(size.items())]
    write_csv(out / "recall_by_size.csv", srows)
    vid = defaultdict(Counter)
    for g in gts:
        vid[g["video"]]["n"] += 1
        vid[g["video"]]["tp"] += g["matched"]
    for stem, n in fps.items():
        vid[gt[stem]["video"]]["fp"] += n
        vid[gt[stem]["video"]]["images"] += 1
    vrows = [{"video_id": v, "class_name": next(g["class_name"] for g in gt.values() if g["video"] == v),
              "images": c["images"], "gt": c["n"], "tp": c["tp"], "fp": c["fp"],
              "recall": round(c["tp"] / c["n"], 4) if c["n"] else ""} for v, c in sorted(vid.items())]
    write_csv(out / "recall_by_video.csv", vrows)
    ag, _ = match(gt, preds, thr, class_agnostic=True)
    conf = Counter((CLASSES[g["cls"]], CLASSES[g["pred_cls"]] if g["matched"] else "missed") for g in ag)
    write_csv(out / "class_confusion.csv", [{"gt": a, "pred": b, "count": n} for (a, b), n in sorted(conf.items())])
    neg = [s for s, g in gt.items() if not g["boxes"]]
    neg_fp = sum(1 for s in neg if fps.get(s, 0) > 0)
    negj = {"negative_images": len(neg), "images_with_fp": neg_fp, "conf": thr}
    (out / "negatives_fp.json").write_text(json.dumps(negj, indent=2), encoding="utf-8")
    labels = ["small", "medium", "large"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    wbar = 0.18
    for i, c in enumerate(CLASSES + ["ALL"]):
        vals = [size[(c, b)]["tp"] / size[(c, b)]["n"] if size[(c, b)]["n"] else 0 for b in labels]
        ax.bar([j + (i - 2) * wbar for j in range(3)], vals, wbar, label=c)
    ax.set_xticks(range(3)); ax.set_xticklabels(["nho (<32²)", "vua (32²–96²)", "lon (≥96²)"])
    ax.set_ylim(0, 1); ax.set_ylabel(f"recall @conf {thr}"); ax.legend(fontsize=7, ncol=5); ax.grid(axis="y", alpha=.3)
    fig.tight_layout(); fig.savefig(out / "fig_recall_by_size.png", dpi=150); plt.close(fig)
    return {"conf": thr, "recall_small_all": srows and next((r["recall"] for r in srows if r["class"] == "ALL" and r["size"] == "small"), ""),
            "negatives": negj, "videos": len(vrows)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--train-evidence", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = a.out / "w3_analysis"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    status, ctx = {}, {}

    def run(name, fn):
        try:
            r = fn()
            status[name] = {"status": "OK", **(r if isinstance(r, dict) else {})}
            return r
        except Exception as exc:  # noqa: BLE001
            LOG.error("%s FAILED: %s", name, exc)
            status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1200:]}
        finally:
            (out / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def inputs():
        ctx["gt"] = load_gt(a.data_dir, a.manifest)
        pj = a.train_evidence / "val" / "predictions.json"
        ctx["preds"], off = load_preds(pj, len(CLASSES))
        return {"val_images": len(ctx["gt"]), "pred_images": len(ctx["preds"]), "category_offset": off,
                "predictions_sha256": sha256(pj), "manifest_sha256": sha256(a.manifest), "commit": a.commit}
    run("inputs", inputs)
    run("curves", lambda: stage_curves(a.train_evidence, out))
    if "gt" in ctx:
        ops = run("operating_points", lambda: stage_ops(ctx["gt"], ctx["preds"], out)) or {}
        thr = ops.get("conf_selected_on_val", 0.25)
        run("breakdown_selected", lambda: stage_breakdown(ctx["gt"], ctx["preds"], thr, out))
    mj = a.train_evidence / "baseline_A_val_metrics.json"
    summary = {"status": {k: v["status"] for k, v in status.items()}, "stages": status,
               "ultralytics_metrics": json.loads(mj.read_text(encoding="utf-8")) if mj.is_file() else None,
               "note": "Danh gia tren VAL; nguong chon tren VAL nen so lieu lac quan. Test bi khoa. Nhan val da duoc kiem tra dinh dang (5 truong, class id, toa do chuan hoa) va khop has_bbox voi manifest truoc khi tinh metric."}
    (out / "analysis_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    z = a.out / "w3_analysis.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out.rglob("*")):
            zf.write(p, p.relative_to(out.parent))
    print(json.dumps(summary["status"], indent=1))
    return 0 if all(v["status"] == "OK" for v in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
