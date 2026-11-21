#!/usr/bin/env python3
"""W8 (#115): ap luat muc B va C cua docs/w8/W8_PLAN.md (viet truoc run 17) len bang chung Kaggle.

Muc B - xac nhan V2 tren video that: run 17 (NMS cung lop IoU 0,5 trong detector) so voi run 14 (IoU 0,7).
Hai run cung weights, ByteTrack-e1, 38 video val, Ultralytics 8.4.183. Ca hai run duoc danh gia bang CUNG ham:
  - track: w5_track_metrics.video_metrics tren track log Kaggle (GT dan xuat, IoU 0,5, ADR-0008);
  - canh bao: evaluate_alerts.evaluate, ROI center_hex, diem tam, luat ADR-0009;
  - muc anh: frame co anh val (buoc 10), bo 40 anh loi nhan, conf 0,25, ghep tham lam cung lop IoU >= 0,5,
    tu detection luu cua chinh run do (khong dung model.val).
Muc C - chan doan hop trung: doc dup_diagnostic.json cua job w8_dup_diagnostic.py.

Kiem cheo (khong phai dieu kien): detection run 17 so voi NMS 0,5 offline ap len detection run 14.

    python scripts/experiments/w8_v2_verify.py --out results/W08/v2_verify
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("scripts/tracking", "scripts/alert", "scripts/kaggle", "scripts/experiments"):
    sys.path.insert(0, str(ROOT / sub))
import offline_track as ot  # noqa: E402
import w7_postproc as w7  # noqa: E402

LOG = logging.getLogger("w8_v2_verify")
TRACKER = "tracker_bytetrack_e1"
RUN14 = ROOT / "results/W06/kaggle_run_14/w6_run14"
RUN17 = ROOT / "results/W08/kaggle_run_17/w8_run17"
DUP = ROOT / "results/W08/kaggle_run_17/w8_dupdiag/dup_diagnostic.json"
PLAN = ROOT / "docs/w8/W8_PLAN.md"
V2_OFFLINE_IDSW = 1.982   # results/W07/postproc/postproc_summary.json, V2 nms_iou
W7_DUP_VIDEO = 0.117      # W7 exploratory.json: 153/1307


def median_fps(ev: Path) -> float:
    with (ev / "timing.csv").open(encoding="utf-8") as fh:
        return round(statistics.median(float(r["fps"]) for r in csv.DictReader(fh) if r["tracker"] == TRACKER), 2)


def evaluate_run(ev: Path, nms_expected: float, rois, acfg, ignore: set[str]) -> dict:
    import evaluate_alerts as ea
    import w5_track_metrics as tm
    vids, inp = ea.load_evidence(ev, TRACKER, w7.WEIGHTS)
    if abs(inp["detector"]["nms_iou"] - nms_expected) > 1e-9:
        raise ValueError(f"{ev}: NMS IoU {inp['detector']['nms_iou']} != ky vong {nms_expected}")
    per, preds = [], {}
    for v in vids:
        trk = [{k: (float(x) if k in "xywh" or k == "conf" else int(x)) for k, x in r.items()} for r in v["tracks"]]
        g = [None] * v["frames"]
        for r in v["gt"]:
            g[int(r["frame"])] = tuple(float(r[c]) for c in "xywh")
        per.append({"video_id": v["video_id"], "class_name": v["class_name"],
                    **tm.video_metrics(g, trk, w7.CLASSES.index(v["class_name"]), iou_thr=0.5)})
        for f, ds in ot.load_dets(ev / "dets" / f"{v['video_id']}.csv").items():
            preds[f"{v['video_id']}_f{f:05d}"] = ds
    with (ev / "meta.csv").open(encoding="utf-8") as fh:
        meta = list(csv.DictReader(fh))
    gt_img = w7.image_gt(meta, ev)
    _, _, summ, _, _ = ea.evaluate(vids, rois, acfg, points=("center",))
    track = {"all": tm.summarize(per), **{c: tm.summarize([r for r in per if r["class_name"] == c]) for c in w7.CLASSES}}
    return {"evidence": ev.relative_to(ROOT).as_posix(), "nms_iou": inp["detector"]["nms_iou"],
            "detections": sum(len(v["dets"]) for v in vids), "tracking": track, "per_video": per,
            "alerts": {k: v for k, v in summ.items() if k.startswith("center_hex|center|")},
            "image_level": w7.det_metrics(gt_img, preds, 0.25, ignore), "median_fps": median_fps(ev)}


def rule_b(r14: dict, r17: dict) -> dict:
    """Luat muc B, W8_PLAN.md (dat truoc run 17). Dieu kien 4: giam >= 20% so voi run 14."""
    t14, t17 = r14["tracking"]["all"], r17["tracking"]["all"]
    a14, a17 = r14["alerts"]["center_hex|center|R1"], r17["alerts"]["center_hex|center|R1"]
    d14, d17 = r14["image_level"]["per_class"]["Drone"]["R"], r17["image_level"]["per_class"]["Drone"]["R"]
    i14, i17 = t14["idsw_per_1000_gt_frames"], t17["idsw_per_1000_gt_frames"]
    red = (i14 - i17) / i14 if i14 else 0.0
    cond = {
        "1_drone_image_recall_drop_le_0.02": {"run14": d14, "run17": d17, "pass": d14 - d17 <= 0.02 + 1e-9},
        "2_r1_event_recall_not_lower": {"run14": f"{a14['detected']}/{a14['events']}", "run17": f"{a17['detected']}/{a17['events']}",
                                        "pass": a17["detected"] >= a14["detected"] and a17["events"] == a14["events"]},
        "3_r1_false_nondrone_not_higher": {"run14": a14["false_alerts_nondrone"], "run17": a17["false_alerts_nondrone"],
                                           "pass": a17["false_alerts_nondrone"] <= a14["false_alerts_nondrone"]},
        "4_idsw_reduction_ge_20pct": {"run14": i14, "run17": i17, "reduction": round(red, 4), "pass": red >= 0.20},
        "5_pooled_track_recall_drop_le_0.02": {"run14": t14["track_recall_pooled"], "run17": t17["track_recall_pooled"],
                                               "pass": t14["track_recall_pooled"] - t17["track_recall_pooled"] <= 0.02 + 1e-9},
    }
    ok = all(c["pass"] for c in cond.values())
    rv = {v["video_id"]: v["track_recall"] for v in r14["per_video"]}
    drops = sorted(((v["video_id"], round(v["track_recall"] - rv[v["video_id"]], 4)) for v in r17["per_video"]
                    if v["track_recall"] is not None and rv[v["video_id"]] is not None), key=lambda x: x[1])
    return {"rule": "W8_PLAN.md muc B", "conditions": cond, "apply_v2": ok,
            "decision": "ap dung V2 (NMS cung lop 0,5 trong detector) cho pipeline W8" if ok else "giu V0 (NMS 0,7)",
            "reported_not_conditions": {
                "fragments": {"run14": t14["fragments"], "run17": t17["fragments"]},
                "median_fps": {"run14": r14["median_fps"], "run17": r17["median_fps"]},
                "idsw_vs_v2_offline": {"offline": V2_OFFLINE_IDSW, "run17": i17, "diff": round(i17 - V2_OFFLINE_IDSW, 3)},
                "r0_false_nondrone": {"run14": r14["alerts"]["center_hex|center|R0"]["false_alerts_nondrone"],
                                      "run17": r17["alerts"]["center_hex|center|R0"]["false_alerts_nondrone"]},
                "track_recall_per_video_largest_drops": drops[:5],
                "videos_track_recall_lower": sum(1 for _, d in drops if d < -1e-9),
                "videos_track_recall_higher": sum(1 for _, d in drops if d > 1e-9)}}


def rule_c(d: dict) -> dict:
    """Luat muc C, W8_PLAN.md (dat truoc; An sua C ngay 18/11 qua #122, truoc run 17)."""
    D = {k: v["dup_rate"] for k, v in d["conditions"].items()}
    rep = d["repro_frame_fp32_vs_run14"]
    gate = {"repro_match_ge_0.99": rep["rate"] is not None and rep["rate"] >= 0.99,
            "frame_fp32_within_11.7_pm_1": abs(D["frame_fp32"] - W7_DUP_VIDEO) <= 0.01 + 1e-9}
    out = {"rule": "W8_PLAN.md muc C", "dup_rate": D, "gate_0": gate, "gate_pass": all(gate.values())}
    if not out["gate_pass"]:
        out["interpretation"] = "khong qua cong tai tao -> khong dien giai"
        return out
    c1 = abs(D["jpg_fp32"] - D["frame_fp32"]) >= 0.03
    c2 = abs(D["frame_fp16"] - D["frame_fp32"]) >= 0.03
    c3 = all(v >= 0.08 for v in D.values())
    out.update({"c1_input_is_factor": c1, "c1_diff_pp": round(100 * (D["jpg_fp32"] - D["frame_fp32"]), 2),
                "c2_precision_is_factor": c2, "c2_diff_pp": round(100 * (D["frame_fp16"] - D["frame_fp32"]), 2),
                "c3_all_ge_8pct": c3})
    if c3:
        out["interpretation"] = ("muc hop trung cao ton tai qua ca bien the dau vao va do chinh xac (moc model.val 0,6%); "
                                 "khac biet duong model.val va model.predict la diem khac biet co lien quan, khong ket luan la "
                                 "nguyen nhan duy nhat. Tu W9 so do muc anh de chon/bao cao tinh tu dau ra predict.")
    elif c1 or c2:
        out["interpretation"] = "yeu to: " + ", ".join(n for n, f in (("dau vao", c1), ("do chinh xac so", c2)) if f)
    else:
        out["interpretation"] = "chua xac dinh"
    return out


def fp16_effective(p: Path) -> dict:
    """Kiem phep do (khong phai luat): fp16 co that su doi detection khong."""
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        per = json.load(fh)
    diff = {k: sum(1 for c in per.values() if c[a] != c[b]) for k, (a, b) in
            {"jpg": ("jpg_fp32", "jpg_fp16"), "frame": ("frame_fp32", "frame_fp16")}.items()}
    return {"images": len(per), "images_with_different_dets_fp32_vs_fp16": diff}


def crosscheck_offline(r14: Path, r17: Path) -> dict:
    """Detection run 17 so voi NMS cung lop 0,5 offline tren detection run 14 (lam tron 2 chu so)."""
    import w8_dup_diagnostic as dd
    same = frames = hit = n17 = n_off = 0
    for p in sorted((r17 / "dets").glob("*.csv")):
        a, b = ot.load_dets(r14 / "dets" / p.name), ot.load_dets(p)
        for f in set(a) | set(b):
            off = ot.nms(a.get(f, []), 0.5, agnostic=False)
            got = b.get(f, [])
            frames += 1
            h, _ = dd.match_rate(got, off, tol=0.02)
            hit += h; n17 += len(got); n_off += len(off)
            same += int(h == len(got) == len(off))
    return {"frames": frames, "frames_identical": same, "dets_run17": n17, "dets_offline_v2": n_off,
            "run17_dets_matched_in_offline": hit, "match_rate": round(hit / n17, 4) if n17 else None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if "## B. Luật xác nhận V2" not in PLAN.read_text(encoding="utf-8"):
        raise SystemExit("khong tim thay luat muc B trong W8_PLAN.md")
    import yaml
    rois = [r for r in yaml.safe_load((ROOT / "configs/roi_w6.yaml").read_text(encoding="utf-8"))["rois"] if r["name"] == "center_hex"]
    acfg = yaml.safe_load((ROOT / "configs/alert_e1.yaml").read_text(encoding="utf-8"))
    with w7.NEG.open(encoding="utf-8-sig") as fh:
        ignore = {f"{r['video_id']}_f{int(r['frame']):05d}" for r in csv.DictReader(fh)}
    r14 = evaluate_run(RUN14, 0.7, rois, acfg, ignore)
    r17 = evaluate_run(RUN17, 0.5, rois, acfg, ignore)
    kaggle = json.loads((RUN17 / "track_summary.json").read_text(encoding="utf-8"))["summary"][f"{TRACKER}@0.5"]["all"]
    consistency = {"run17_idsw_kaggle_vs_offline_eval": (kaggle["idsw_per_1000_gt_frames"], r17["tracking"]["all"]["idsw_per_1000_gt_frames"]),
                   "run17_track_recall_kaggle_vs_offline_eval": (kaggle["track_recall_pooled"], r17["tracking"]["all"]["track_recall_pooled"])}
    a.out.mkdir(parents=True, exist_ok=True)
    for name, r in (("run14", r14), ("run17", r17)):
        with (a.out / f"per_video_tracking_{name}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(r["per_video"][0])); w.writeheader(); w.writerows(r["per_video"])
    res = {"plan": PLAN.relative_to(ROOT).as_posix(),
           "runs": {n: {k: v for k, v in r.items() if k != "per_video"} for n, r in (("run14", r14), ("run17", r17))},
           "rule_b": rule_b(r14, r17), "rule_c": rule_c(json.loads(DUP.read_text(encoding="utf-8"))),
           "checks": {"consistency_with_kaggle_summary": consistency,
                      "fp16_effective": fp16_effective(DUP.parent / "per_image_dets.json.gz"),
                      "run17_vs_offline_v2_on_run14": crosscheck_offline(RUN14, RUN17)}}
    (a.out / "v2_verify.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("B: %s | C: %s", res["rule_b"]["decision"], res["rule_c"]["interpretation"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
