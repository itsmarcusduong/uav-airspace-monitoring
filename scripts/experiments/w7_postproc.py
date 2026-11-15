#!/usr/bin/env python3
"""W7 (ADR-0012): bien the hau xu ly detection -> tracking offline -> canh bao, va kiem chung muc anh.

Moi bien the chi doi MOT yeu to so voi V0 (run 14 nguyen ban):
  V0 none          detection run 14 giu nguyen (cong tai tao)
  V1 agnostic_nms  NMS khong phan lop IoU 0,5 tren detection da luu
  V2 nms_iou       NMS cung lop IoU 0,5 (run 14 dung 0,7)
Voi moi bien the:
  - tracking: ByteTrack-e1 chay offline (scripts/tracking/offline_track.py) tren detection da hau xu ly;
    do do lien ket GT dan xuat (ADR-0008, IoU 0,5) bang w5_track_metrics;
  - canh bao: luat ADR-0009 khong doi (ROI center_hex, diem tam), R0 dung detection da hau xu ly, R1 dung track moi;
  - muc anh: cung hau xu ly ap len du doan run 13 (val/predictions.json.gz, anh JPEG), P/R/F1 theo lop o conf 0,25 va
    ma tran nham (co nen), BO 40 anh val khong nhan (ca 40 co vat that, PR #94).
Bien the V1, V2 chi chay khi ADR-0012 da Accepted (kiem van ban ADR). V0 chay luc nao cung duoc (cong tai tao).

    python scripts/experiments/w7_postproc.py --variants none --out results/W07/postproc
    python scripts/experiments/w7_postproc.py --variants none agnostic_nms nms_iou --out results/W07/postproc
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

ROOT = Path(__file__).resolve().parents[2]
for sub in ("scripts/tracking", "scripts/alert", "scripts/kaggle"):
    sys.path.insert(0, str(ROOT / sub))
import offline_track as ot  # noqa: E402

LOG = logging.getLogger("w7_postproc")
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]
VARIANTS = {"none": ("V0", None), "agnostic_nms": ("V1", 0.5), "nms_iou": ("V2", 0.5)}
EV = ROOT / "results/W06/kaggle_run_14/w6_run14"
PRED = ROOT / "results/W05/kaggle_run_13/train_yolo11n_640_s20261030/val/predictions.json.gz"
NEG = ROOT / "results/W06/val_negative_frames/manual_review_classification.csv"
ADR = ROOT / "docs/decisions/ADR-0012-w7-postprocessing-experiments.md"
WEIGHTS = "a3de1e0195e4380aac497612296ed57f67e41ceb5ae3314e82a5ad66b125ef8a"


def adr_accepted(p: Path = ADR) -> bool:
    head = p.read_text(encoding="utf-8").split("\n## ")[0] if p.is_file() else ""
    return "**Accepted**" in head


# ----------------------------------------------------------------------------- muc anh
def load_preds(p: Path = PRED) -> dict[str, list[tuple]]:
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    off = 1 if min(d["category_id"] for d in data) >= 1 else 0
    out = defaultdict(list)
    for d in data:
        out[str(d["image_id"])].append((int(d["category_id"]) - off, float(d["score"]), tuple(float(v) for v in d["bbox"])))
    return out


def image_gt(meta: list[dict], ev: Path = EV, stride: int = 10) -> dict[str, list[tuple]]:
    """stem -> [(lop, hop)] cho anh val stride 10 (offset0, giong e1-yolo-v1); anh khong co hop -> []."""
    out = {}
    for m in meta:
        v, k = m["video_id"], CLASSES.index(m["class_name"])
        with (ev / "gt" / f"{v}.csv").open(encoding="utf-8") as fh:
            g = {int(r["frame"]): tuple(float(r[c]) for c in "xywh") for r in csv.DictReader(fh)}
        for f in range(0, int(m["frames"]), stride):
            out[f"{v}_f{f:05d}"] = [(k, g[f])] if f in g else []
    return out


def det_metrics(gt: dict, preds: dict, conf: float, ignore: set[str]) -> dict:
    """Ghep tham lam theo conf, IoU >= 0,5. P/R/F1 theo lop (ghep cung lop) va ma tran nham khong xet lop (co 'nen')."""
    tp, fp, n = Counter(), Counter(), Counter()
    conf_m = Counter()
    for stem, g in gt.items():
        if stem in ignore:
            continue
        ps = sorted((p for p in preds.get(stem, []) if p[1] >= conf), key=lambda p: -p[1])
        for c, _ in g:
            n[c] += 1
        for cls_aware in (True, False):
            used, matched_gt = set(), set()
            for i, (pc, _, pb) in enumerate(ps):
                best, bj = 0.0, None
                for j, (gc, gb) in enumerate(g):
                    if j in matched_gt or (cls_aware and gc != pc):
                        continue
                    u = ot.iou_xywh(pb, gb)
                    if u >= 0.5 and u > best:
                        best, bj = u, j
                if bj is not None:
                    matched_gt.add(bj); used.add(i)
                    if cls_aware:
                        tp[pc] += 1
                    else:
                        conf_m[(CLASSES[g[bj][0]], CLASSES[pc])] += 1
                elif cls_aware:
                    fp[pc] += 1
                else:
                    conf_m[("nen", CLASSES[pc])] += 1
            if not cls_aware:
                for j, (gc, _) in enumerate(g):
                    if j not in matched_gt:
                        conf_m[(CLASSES[gc], "bo_sot")] += 1
    per = {}
    for k, name in enumerate(CLASSES):
        p = tp[k] / (tp[k] + fp[k]) if tp[k] + fp[k] else 0.0
        r = tp[k] / n[k] if n[k] else 0.0
        per[name] = {"gt": n[k], "tp": tp[k], "fp": fp[k], "P": round(p, 4), "R": round(r, 4),
                     "F1": round(2 * p * r / (p + r), 4) if p + r else 0.0}
    return {"conf": conf, "images": len(gt) - len(ignore & gt.keys()), "ignored_images": len(ignore & gt.keys()),
            "per_class": per, "confusion": {f"{a}->{b}": v for (a, b), v in sorted(conf_m.items())}}


def postproc_preds(preds: dict, variant: str, thr) -> dict:
    return {s: ot.apply_variant(sorted(ps, key=lambda p: -p[1]), variant, thr) for s, ps in preds.items()} if thr else preds


# ----------------------------------------------------------------------------- tracking + canh bao
def run_variant(variant: str, out: Path, cfg, rois, acfg, vids0: list[dict], gt_img, preds, ignore) -> dict:
    import evaluate_alerts as ea
    import w5_track_metrics as tm
    tag, thr = VARIANTS[variant]
    vdir = out / f"{tag}_{variant}"
    tdir = vdir / "tracks"; tdir.mkdir(parents=True, exist_ok=True)
    vids, per, kept, total = [], [], 0, 0
    for v in vids0:
        dets = ot.load_dets(EV / "dets" / f"{v['video_id']}.csv")
        total += sum(len(x) for x in dets.values())
        pdets = {f: ot.apply_variant(x, variant, thr) for f, x in dets.items()}
        kept += sum(len(x) for x in pdets.values())
        rows = ot.track_video(dets, v["frames"], v["width"], v["height"], cfg, variant, thr)
        with (tdir / f"{v['video_id']}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["frame", "id", "cls", "conf", "x", "y", "w", "h"]); w.writeheader(); w.writerows(rows)
        trk = [{k: (float(x) if k in "xywh" or k == "conf" else int(x)) for k, x in r.items()} for r in rows]
        dl = [{"frame": f, "cls": c, "conf": s, "x": b[0], "y": b[1], "w": b[2], "h": b[3]} for f, x in sorted(pdets.items()) for c, s, b in x]
        g = [None] * v["frames"]
        for r in v["gt"]:
            g[int(r["frame"])] = tuple(float(r[c]) for c in "xywh")
        per.append({"video_id": v["video_id"], "class_name": v["class_name"],
                    **tm.video_metrics(g, trk, CLASSES.index(v["class_name"]), iou_thr=0.5)})
        vids.append({**v, "dets": [{k: str(x) for k, x in d.items()} for d in dl], "tracks": [{k: str(x) for k, x in r.items()} for r in rows]})
    _, pv, summ, _, _ = ea.evaluate(vids, rois, acfg, points=("center",))
    track = {"all": tm.summarize(per), **{c: tm.summarize([r for r in per if r["class_name"] == c]) for c in CLASSES}}
    det = det_metrics(gt_img, postproc_preds(preds, variant, thr), 0.25, ignore)
    res = {"variant": variant, "tag": tag, "nms_iou": thr, "dets_in": total, "dets_kept": kept,
           "tracking": track, "alerts": {k: v for k, v in summ.items() if k.startswith("center_hex|center|")}, "detection": det}
    with (vdir / "per_video_tracking.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per[0])); w.writeheader(); w.writerows(per)
    (vdir / "summary.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return res


def decide(v0: dict, cands: dict) -> dict:
    """Luat ADR-0012 muc 4 (dat truoc)."""
    def k(r):
        return (r["tracking"]["all"]["idsw_per_1000_gt_frames"], r["alerts"]["center_hex|center|R0"]["false_alerts_nondrone"],
                r["alerts"]["center_hex|center|R1"])
    i0, fa0, r1_0 = k(v0)
    out = {}
    for name, r in cands.items():
        i1, fa1, r1 = k(r)
        g = {"drone_recall_drop_le_0.02": v0["detection"]["per_class"]["Drone"]["R"] - r["detection"]["per_class"]["Drone"]["R"] <= 0.02 + 1e-9,
             "r1_event_recall_not_lower": r1["detected"] >= r1_0["detected"],
             "r1_false_nondrone_not_higher": r1["false_alerts_nondrone"] <= r1_0["false_alerts_nondrone"]}
        gain_idsw = (i0 - i1) / i0 if i0 else 0.0
        gain_fa = (fa0 - fa1) / fa0 if fa0 else 0.0
        g["improves"] = gain_idsw >= 0.20 or gain_fa >= 0.30
        out[name] = {"guards": g, "pass": all(g.values()), "idsw_reduction": round(gain_idsw, 4), "r0_fa_reduction": round(gain_fa, 4),
                     "dets_removed_frac": round(1 - r["dets_kept"] / r["dets_in"], 4)}
    ok = [n for n, x in out.items() if x["pass"]]
    if not ok:
        choice, why = "none", "khong bien the nao dat du dieu kien -> giu V0"
    elif len(ok) == 1:
        choice, why = ok[0], "chi mot bien the dat"
    else:
        a, b = sorted(ok, key=lambda n: -out[n]["idsw_reduction"])[:2]
        if out[a]["idsw_reduction"] - out[b]["idsw_reduction"] >= 0.05:
            choice, why = a, "ca hai dat; chon muc giam ID switch lon hon (chenh >= 5 diem)"
        else:
            choice = min(ok, key=lambda n: out[n]["dets_removed_frac"]); why = "ca hai dat, giam ID switch chenh < 5 diem -> chon bien the bo it detection hon"
    return {"rule": "ADR-0012 muc 4", "candidates": out, "choice": choice, "reason": why}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="+", default=["none"], choices=list(VARIANTS))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if any(v != "none" for v in a.variants) and not adr_accepted():
        raise SystemExit("ADR-0012 chua Accepted: chi duoc chay --variants none (cong tai tao)")
    import evaluate_alerts as ea
    import yaml
    from ultralytics.utils import IterableSimpleNamespace
    cfg = IterableSimpleNamespace(**yaml.safe_load((ROOT / "configs/tracker_bytetrack_e1.yaml").read_text(encoding="utf-8")))
    rois = [r for r in yaml.safe_load((ROOT / "configs/roi_w6.yaml").read_text(encoding="utf-8"))["rois"] if r["name"] == "center_hex"]
    acfg = yaml.safe_load((ROOT / "configs/alert_e1.yaml").read_text(encoding="utf-8"))
    vids0, _ = ea.load_evidence(EV, "tracker_bytetrack_e1", WEIGHTS)
    with (EV / "meta.csv").open(encoding="utf-8") as fh:
        meta = list(csv.DictReader(fh))
    gt_img, preds = image_gt(meta), load_preds()
    with NEG.open(encoding="utf-8-sig") as fh:
        ignore = {f"{r['video_id']}_f{int(r['frame']):05d}" for r in csv.DictReader(fh)}
    a.out.mkdir(parents=True, exist_ok=True)
    res = {v: run_variant(v, a.out, cfg, rois, acfg, vids0, gt_img, preds, ignore) for v in a.variants}
    if "none" in res:                              # cong tai tao: V0 offline so voi run 14 va run 13
        import compare_tracks as ct
        ref = json.loads((ROOT / "results/W06/alert_eval/alert_summary.json").read_text(encoding="utf-8"))["summary"]
        keys = ("events", "detected", "alerts", "false_alerts", "false_alerts_nondrone", "duplicates")
        al = {r: {k: (ref[f"center_hex|center|{r}"][k], res["none"]["alerts"][f"center_hex|center|{r}"][k]) for k in keys} for r in ("R0", "R1")}
        nn = det_metrics(gt_img, preds, 0.25, set())["per_class"]
        op = next(r for r in csv.DictReader((ROOT / "results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030/operating_points.csv").open(encoding="utf-8"))
                  if r["conf"] == "0.25")
        det = {c: {"P": (float(op[f"{c}_P"]), nn[c]["P"]), "R": (float(op[f"{c}_R"]), nn[c]["R"])} for c in CLASSES}
        tr = ct.compare(EV / "tracks" / "tracker_bytetrack_e1", a.out / "V0_none" / "tracks")
        ts = json.loads((EV / "track_summary.json").read_text(encoding="utf-8"))["summary"]["tracker_bytetrack_e1@0.5"]["all"]
        repro = {"note": "(gia tri run 14/run 13, gia tri tinh lai offline)",
                 "track_logs": {k: v for k, v in tr.items() if k != "differing_videos"}, "track_logs_differing": tr["differing_videos"],
                 "idsw_per_1000": (ts["idsw_per_1000_gt_frames"], res["none"]["tracking"]["all"]["idsw_per_1000_gt_frames"]),
                 "alerts_center_hex_center": al, "alerts_identical": all(x == y for r in al.values() for x, y in r.values()),
                 "detection_conf025_all_images": det,
                 "detection_identical": all(abs(x - y) < 1e-4 for c in det.values() for x, y in c.values())}
        (a.out / "repro_check.json").write_text(json.dumps(repro, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        LOG.info("tai tao: track %s/%s video giong, canh bao giong=%s, muc anh giong=%s", tr["videos_identical"], tr["videos"],
                 repro["alerts_identical"], repro["detection_identical"])
    summary = {"adr": "ADR-0012", "evidence": EV.relative_to(ROOT).as_posix(), "predictions": PRED.relative_to(ROOT).as_posix(),
               "variants": {v: {"tag": r["tag"], "dets_kept": r["dets_kept"], "dets_in": r["dets_in"],
                                "idsw_per_1000": r["tracking"]["all"]["idsw_per_1000_gt_frames"],
                                "R0_false_nondrone": r["alerts"]["center_hex|center|R0"]["false_alerts_nondrone"],
                                "R1_events": f"{r['alerts']['center_hex|center|R1']['detected']}/{r['alerts']['center_hex|center|R1']['events']}",
                                "R1_false_nondrone": r["alerts"]["center_hex|center|R1"]["false_alerts_nondrone"],
                                "Drone_P": r["detection"]["per_class"]["Drone"]["P"], "Drone_R": r["detection"]["per_class"]["Drone"]["R"]}
                            for v, r in res.items()}}
    if "none" in res and len(res) > 1:
        summary["decision"] = decide(res["none"], {v: r for v, r in res.items() if v != "none"})
    (a.out / "postproc_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("%s", json.dumps(summary["variants"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
