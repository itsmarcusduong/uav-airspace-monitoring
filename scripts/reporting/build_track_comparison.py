#!/usr/bin/env python3
"""Bang so sanh tracker tu bang chung Kaggle run 12 / 12b va luat ADR-0008 muc 7 (issue #57).

Doc `track_summary.json`, `per_video_metrics.csv`, `timing.csv` trong mot hoac nhieu thu muc `w5_track/`.
Ghi ra `track_comparison.csv` (tracker x IoU x lop), `track_comparison.md`, `track_decision.json`.

Luat (ADR-0008 muc 7, docs/w5/tracking_protocol_w5.md):
  chi so chinh = ID switch / 1000 frame GT o IoU 0,5;
  hoa neu |A-B| / max(A,B) < 0,2 (0 neu ca hai bang 0) HOAC |A-B| < 1;
  ngoai vung hoa: tracker co ID switch thap hon thang; hoa -> giu ByteTrack.

Vi du:
    python scripts/reporting/build_track_comparison.py \
        --evidence results/W05/kaggle_run_12/w5_track \
        --pair tracker_bytetrack_default tracker_botsort_default --reference-only \
        --out results/W05/kaggle_run_12
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
import sys
from pathlib import Path

LOG = logging.getLogger("track_comparison")
CLASSES = ["all", "Airplane", "Bird", "Drone", "Helicopter"]
FIELDS = ["videos", "gt_frames", "track_recall_pooled", "id_switches", "idsw_per_1000_gt_frames", "fragments",
          "videos_single_id", "videos_no_match", "median_dominant_id_coverage", "median_track_recall", "false_tracks"]
REL_TIE, ABS_TIE = 0.2, 1.0


def decide(a: str, b: str, ra: float, rb: float) -> dict:
    """Ap luat muc 7 cho hai tracker a, b voi ID switch / 1000 frame GT ra, rb."""
    diff = abs(ra - rb)
    rel = 0.0 if max(ra, rb) == 0 else diff / max(ra, rb)
    tie = rel < REL_TIE or diff < ABS_TIE
    if tie:
        bt = [t for t in (a, b) if "bytetrack" in t]
        choice = bt[0] if bt else a
        why = [f"tuong doi {rel:.3f} < {REL_TIE}"] if rel < REL_TIE else []
        why += [f"tuyet doi {diff:.3f} < {ABS_TIE}"] if diff < ABS_TIE else []
        reason = f"hoa ({'; '.join(why)}) -> giu ByteTrack"
    else:
        choice = a if ra < rb else b
        reason = f"khac biet (tuong doi {rel:.3f}, tuyet doi {diff:.3f}) -> ID switch thap hon"
    return {"a": a, "b": b, "idsw_per_1000": {a: ra, b: rb}, "abs_diff": round(diff, 3), "rel_diff": round(rel, 4),
            "tie": tie, "choice": choice, "reason": reason}


def load(ev: Path) -> tuple[dict, list[dict], list[dict], dict]:
    need = ["track_summary.json", "per_video_metrics.csv", "timing.csv", "stage_status.json", "inputs.json"]
    miss = [n for n in need if not (ev / n).is_file()]
    if miss:
        raise FileNotFoundError(f"{ev}: thieu {miss}")
    st = json.loads((ev / "stage_status.json").read_text(encoding="utf-8"))
    bad = {k: v.get("status") for k, v in st.items() if v.get("status") != "OK"}
    if bad:
        raise ValueError(f"{ev}: stage khong OK {bad} - khong dien giai")
    inp = json.loads((ev / "inputs.json").read_text(encoding="utf-8"))
    if inp.get("test_used") is not False:
        raise ValueError(f"{ev}: inputs.json khong xac nhan test_used=False")
    summ = json.loads((ev / "track_summary.json").read_text(encoding="utf-8"))["summary"]
    with (ev / "per_video_metrics.csv").open(encoding="utf-8") as fh:
        pv = list(csv.DictReader(fh))
    with (ev / "timing.csv").open(encoding="utf-8") as fh:
        tm = list(csv.DictReader(fh))
    return summ, pv, tm, inp


def per_video_wins(pv: list[dict], a: str, b: str, iou: str = "0.5") -> dict:
    sw = {}
    for r in pv:
        if r["iou_thr"] == iou and r["tracker"] in (a, b):
            sw.setdefault(r["video_id"], {})[r["tracker"]] = int(r["id_switches"])
    both = {v: d for v, d in sw.items() if a in d and b in d}
    return {"videos": len(both), f"{a}_better": sum(d[a] < d[b] for d in both.values()),
            f"{b}_better": sum(d[b] < d[a] for d in both.values()), "equal": sum(d[a] == d[b] for d in both.values())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", type=Path, nargs="+", required=True, help="thu muc w5_track/ cua run 12, 12b...")
    ap.add_argument("--pair", nargs=2, metavar=("A", "B"), help="hai tracker ap luat muc 7")
    ap.add_argument("--reference-only", action="store_true", help="cap nay khong phai cap quyet dinh (vd default)")
    ap.add_argument("--top", type=int, default=5, help="so video nhieu ID switch nhat de liet ke")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows, pv_all, fps, weights = [], [], {}, set()
    for ev in args.evidence:
        summ, pv, tm, inp = load(ev)
        weights.add(inp["weights_sha256"])
        for key, by_cls in summ.items():
            tracker, iou = key.rsplit("@", 1)
            for c in CLASSES:
                if c in by_cls:
                    rows.append({"tracker": tracker, "iou_thr": iou, "class": c, **{f: by_cls[c].get(f) for f in FIELDS},
                                 "source": (ev / "track_summary.json").as_posix()})
        pv_all += pv
        for r in tm:
            fps.setdefault(r["tracker"], []).append(float(r["fps"]))
    if len(weights) != 1:
        raise ValueError(f"cac run dung weights khac nhau {weights} - khong so sanh tracker duoc")
    fps_med = {t: round(statistics.median(v), 1) for t, v in fps.items()}

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "track_comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    top = sorted((r for r in pv_all if r["iou_thr"] == "0.5"), key=lambda r: -int(r["id_switches"]))[:args.top]
    md = ["| Tracker | IoU | ID switch / 1000 frame GT | ID switch | track recall (gộp) | trung vị độ phủ ID chính |"
          " video 1 ID | fragment | track giả | FPS trung vị |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in (r for r in rows if r["class"] == "all"):
        md.append(f"| {r['tracker']} | {r['iou_thr']} | {r['idsw_per_1000_gt_frames']} | {r['id_switches']} | "
                  f"{r['track_recall_pooled']} | {r['median_dominant_id_coverage']} | {r['videos_single_id']}/{r['videos']} | "
                  f"{r['fragments']} | {r['false_tracks']} | {fps_med.get(r['tracker'], '')} |")
    md += ["", "Theo lớp (IoU 0,5): ID switch / 1000 frame GT, trung vị độ phủ ID chính", "",
           "| Tracker | " + " | ".join(CLASSES[1:]) + " |", "|---|" + "---|" * (len(CLASSES) - 1)]
    for t in dict.fromkeys(r["tracker"] for r in rows):
        cells = []
        for c in CLASSES[1:]:
            x = next((r for r in rows if r["tracker"] == t and r["iou_thr"] == "0.5" and r["class"] == c), None)
            cells.append(f"{x['idsw_per_1000_gt_frames']} ({x['median_dominant_id_coverage']})" if x else "")
        md.append(f"| {t} | " + " | ".join(cells) + " |")
    md += ["", f"Video nhiều ID switch nhất (IoU 0,5): " + "; ".join(
        f"{r['video_id']} {r['tracker']} {r['id_switches']} IDSW / {r['n_ids_on_target']} ID" for r in top)]

    dec = {"rule": "ADR-0008 muc 7; docs/w5/tracking_protocol_w5.md", "weights_sha256": weights.pop(), "fps_median": fps_med,
           "note": "GT dan xuat 1 track/video; khong phai MOTA/IDF1/HOTA; FPS gom giai ma + detector + tracker"}
    if args.pair:
        a, b = args.pair
        get = lambda t: next(r["idsw_per_1000_gt_frames"] for r in rows if r["tracker"] == t and r["iou_thr"] == "0.5" and r["class"] == "all")
        d = decide(a, b, float(get(a)), float(get(b)))
        d["per_video"] = per_video_wins(pv_all, a, b)
        d["reference_only"] = args.reference_only
        dec["decision"] = d
        tag = "Tham khảo (không phải cặp quyết định)" if args.reference_only else "Quyết định theo luật"
        md += ["", f"**{tag}:** {d['choice']} — {d['reason']}. Theo video (IoU 0,5): {d['per_video']}"]
        LOG.info("%s: %s - %s", tag, d["choice"], d["reason"])
    (args.out / "track_comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (args.out / "track_decision.json").write_text(json.dumps(dec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("ghi %s", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
