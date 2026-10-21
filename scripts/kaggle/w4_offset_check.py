#!/usr/bin/env python3
"""E1 W4 Kaggle job 06 (CPU): kiem chung chieu lech nhan bang du doan cua baseline A (issue #36, ADR-0006).

Y tuong: detector chi nhin 1 frame nen du doan cua no bam vi tri that cua vat the trong frame do.
Voi moi anh val (chua dung de train) cua video kha kien, lay du doan tot nhat dung lop (score >= --conf),
tinh IoU voi nhan goc muc i (offset0) va muc i+1 (offset1). Gom theo video:
  delta_video = trung binh(IoU_{i+1} - IoU_i) tren cac anh co ca hai nhan va |delta| >= --tie.
Luat quyet dinh (dat truoc, ADR-0006): xem stage "decide".

    python w4_offset_check.py --data-root <Svanstrom raw> --manifest yolo_manifest.csv.gz \
        --predictions predictions.json --audit annotation_audit.csv --out /kaggle/working --commit <sha>
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
import sys
import traceback
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from w3_analyze_baseline import load_preds  # noqa: E402
from w3_export_yolo import find_video_dir, iou, label_kind, load_labels  # noqa: E402

LOG = logging.getLogger("w4_offset")
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def sign_test_p(k: int, n: int) -> float:
    """p hai phia cua sign test (binomial p=0.5)."""
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, j) for j in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["empty"])
        w.writeheader(); w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--predictions", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--split", default="val")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--min-iou", type=float, default=0.1, help="du doan phai cham it nhat mot trong hai nhan")
    ap.add_argument("--tie", type=float, default=0.01)
    ap.add_argument("--video-frac", type=float, default=0.80)
    ap.add_argument("--alpha", type=float, default=0.01)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = a.out / "w4_offset_check"
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
            status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
            return None
        finally:
            (out / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def inputs():
        audit = {r["video_id"]: r for r in csv.DictReader(a.audit.open(encoding="utf-8-sig"))}
        with gzip.open(a.manifest, "rt", encoding="utf-8") as fh:
            man = [r for r in csv.DictReader(fh) if r["split"] == a.split]
        if not man:
            raise RuntimeError(f"manifest khong co anh split {a.split}")
        preds, off = load_preds(a.predictions, len(CLASSES))
        missing = [Path(r["image"]).stem for r in man if Path(r["image"]).stem not in preds]
        ctx.update(audit=audit, man=man, preds=preds, data=find_video_dir(a.data_root))
        return {"images": len(man), "videos": len({r["video_id"] for r in man}), "images_without_pred": len(missing),
                "category_offset": off, "manifest_sha256": sha256(a.manifest), "predictions_sha256": sha256(a.predictions),
                "audit_sha256": sha256(a.audit), "commit": a.commit, "conf": a.conf, "tie": a.tie}

    def pairs():
        rows, labels = [], {}
        for r in ctx["man"]:
            vid, cls = r["video_id"], r["class_name"]
            if vid not in labels:
                labels[vid] = load_labels(ctx["data"] / f"Video_{vid.split('_')[0]}" / f"{vid}_LABELS.mat")
            lab = labels[vid]
            i = int(r["frame_index"])
            au = ctx["audit"][vid]
            kind = label_kind(int(au["label_entries"]), int(au["frames_decoded"]))
            li = lab[i] if i < len(lab) else None
            lj = lab[i + 1] if i + 1 < len(lab) else None
            cand = [p for p in ctx["preds"].get(Path(r["image"]).stem, []) if p[0] == CLASSES.index(cls) and p[5] >= a.conf]
            rec = {"video_id": vid, "class_name": cls, "kind": kind, "frame_index": i, "label_i": "box" if isinstance(li, tuple) else str(li),
                   "label_i1": "box" if isinstance(lj, tuple) else str(lj), "pred_score": "", "iou_i": "", "iou_i1": "", "used": 0}
            if cand and isinstance(li, tuple) and isinstance(lj, tuple):
                p = max(cand, key=lambda q: q[5])
                u0, u1 = iou(p[1:5], li), iou(p[1:5], lj)
                rec.update(pred_score=round(p[5], 4), iou_i=round(u0, 4), iou_i1=round(u1, 4),
                           used=int(max(u0, u1) >= a.min_iou and abs(u1 - u0) >= a.tie))
            rows.append(rec)
        write_csv(out / "offset_pairs.csv", rows)
        ctx["rows"] = rows
        return {"rows": len(rows), "used": sum(r["used"] for r in rows)}

    def per_video():
        by = defaultdict(list)
        for r in ctx["rows"]:
            if r["used"]:
                by[(r["video_id"], r["class_name"], r["kind"])].append(r["iou_i1"] - r["iou_i"])
        vrows = [{"video_id": v, "class_name": c, "kind": k, "pairs": len(d), "mean_delta_i1_minus_i": round(sum(d) / len(d), 4),
                  "frac_pairs_i1_better": round(sum(x > 0 for x in d) / len(d), 4)} for (v, c, k), d in sorted(by.items())]
        write_csv(out / "offset_per_video.csv", vrows)
        ctx["vrows"] = vrows
        return {"videos": len(vrows)}

    def decide():
        groups = defaultdict(list)
        for v in ctx["vrows"]:
            g = "control_equal" if v["kind"] == "equal" else f"{v['class_name']}|{v['kind']}"
            groups[g].append(v["mean_delta_i1_minus_i"])
        res = {}
        for g, ds in sorted(groups.items()):
            n = len(ds); k_pos = sum(d > 0 for d in ds)
            res[g] = {"videos": n, "videos_i1_better": k_pos, "frac_i1_better": round(k_pos / n, 4) if n else None,
                      "median_delta": round(sorted(ds)[n // 2], 4) if n else None, "sign_test_p": sign_test_p(k_pos, n)}
        ctl = res.get("control_equal")
        control_ok = bool(ctl and ctl["videos"] >= 5 and (1 - ctl["frac_i1_better"]) >= a.video_frac and ctl["sign_test_p"] < a.alpha)
        verdict = {}
        for g, r in res.items():
            if g == "control_equal":
                continue
            if not control_ok:
                verdict[g] = "UNDETERMINED (doi chung khong dat)"
            elif r["frac_i1_better"] >= a.video_frac and r["sign_test_p"] < a.alpha:
                verdict[g] = "offset1"
            elif (1 - r["frac_i1_better"]) >= a.video_frac and r["sign_test_p"] < a.alpha:
                verdict[g] = "offset0"
            else:
                verdict[g] = "UNDETERMINED"
        summary = {"rule": {"control": f"video equal: >= {a.video_frac:.0%} video co delta < 0 va sign test p < {a.alpha}",
                            "plus1": f">= {a.video_frac:.0%} video cung chieu va sign test p < {a.alpha}",
                            "delta": "trung binh IoU(du doan, nhan i+1) - IoU(du doan, nhan i) tren anh dung duoc"},
                   "groups": res, "control_ok": control_ok, "verdict": verdict}
        (out / "offset_check_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"control_ok": control_ok, "verdict": verdict}

    if run("inputs", inputs):
        if run("pairs", pairs):
            if run("per_video", per_video):
                run("decide", decide)
    z = a.out / "w4_offset_check.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out.rglob("*")):
            zf.write(p, p.relative_to(out.parent))
    print(json.dumps({k: v["status"] for k, v in status.items()}, indent=1))
    return 0 if all(v["status"] == "OK" for v in status.values()) and len(status) == 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
