#!/usr/bin/env python3
"""So do lien ket cua CUNG mot tracker voi HAI detector (W6: baseline A run 12b vs YOLO11n run 14; issue #74).

Khong phai luat chon (tracker da chon theo ADR-0008, detector theo ADR-0007): day la bang mo ta tac dong cua viec
doi detector len do on dinh ID, kem so frame co hai track chong nhau (track_gap_stats.py).

    python scripts/reporting/compare_detector_tracking.py \
        --a results/W05/kaggle_run_12b/w5_track --a-label baseline_A \
        --b results/W06/kaggle_run_14/w6_run14 --b-label yolo11n_s20261030 \
        --tracker tracker_bytetrack_e1 --gaps results/W06/track_gaps_A_vs_yolo11n.json --out results/W06/detector_swap_tracking
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

LOG = logging.getLogger("detector_swap")
COLS = ["idsw_per_1000_gt_frames", "id_switches", "track_recall_pooled", "median_dominant_id_coverage", "videos_single_id",
        "fragments", "false_tracks"]


def load(ev: Path, tracker: str) -> tuple[dict, dict, dict]:
    st = json.loads((ev / "stage_status.json").read_text(encoding="utf-8"))
    if any(v.get("status") != "OK" for v in st.values()):
        raise ValueError(f"{ev}: stage khong OK")
    inp = json.loads((ev / "inputs.json").read_text(encoding="utf-8"))
    if inp.get("split") != "val" or inp.get("test_used") is not False:
        raise ValueError(f"{ev}: chi chap nhan val, test_used=False")
    summ = json.loads((ev / "track_summary.json").read_text(encoding="utf-8"))["summary"][f"{tracker}@0.5"]
    with (ev / "per_video_metrics.csv").open(encoding="utf-8") as fh:
        pv = {r["video_id"]: r for r in csv.DictReader(fh) if r["tracker"] == tracker and r["iou_thr"] == "0.5"}
    return summ, pv, inp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", type=Path, required=True); ap.add_argument("--a-label", required=True)
    ap.add_argument("--b", type=Path, required=True); ap.add_argument("--b-label", required=True)
    ap.add_argument("--tracker", default="tracker_bytetrack_e1")
    ap.add_argument("--gaps", type=Path, required=True, help="track_gap_stats.py --pair <a tracks> <b tracks>")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sa, pa, ia = load(a.a, a.tracker); sb, pb, ib = load(a.b, a.tracker)
    if set(pa) != set(pb) or ia["gt_frames"] != ib["gt_frames"]:
        raise ValueError("hai run khong cung tap video / frame GT")
    gp = json.loads(a.gaps.read_text(encoding="utf-8"))["pairs"][0]
    ova, ovb = gp["a"]["overlapping_by_video"], gp["b"]["overlapping_by_video"]
    summary = []
    for cls in ["all", "Airplane", "Bird", "Drone", "Helicopter"]:
        for lab, s in ((a.a_label, sa), (a.b_label, sb)):
            if cls in s:
                summary.append({"detector": lab, "class": cls, **{c: s[cls][c] for c in COLS}, "videos": s[cls]["videos"]})
    per = []
    for v in sorted(pa):
        x, y = pa[v], pb[v]
        per.append({"video_id": v, "class_name": x["class_name"], f"idsw_{a.a_label}": int(x["id_switches"]), f"idsw_{a.b_label}": int(y["id_switches"]),
                    "delta_idsw": int(y["id_switches"]) - int(x["id_switches"]),
                    f"overlap_frames_{a.a_label}": ova.get(v, {}).get("frames", 0), f"overlap_frames_{a.b_label}": ovb.get(v, {}).get("frames", 0),
                    f"recall_{a.a_label}": x["track_recall"], f"recall_{a.b_label}": y["track_recall"]})
    per.sort(key=lambda r: (-r["delta_idsw"], r["video_id"]))
    worse = sum(r["delta_idsw"] > 0 for r in per); better = sum(r["delta_idsw"] < 0 for r in per)
    dup_videos = [r for r in per if r[f"overlap_frames_{a.b_label}"] >= 30]
    res = {"tracker": a.tracker, "a": {"label": a.a_label, "weights_sha256": ia["weights_sha256"], "evidence": a.a.as_posix()},
           "b": {"label": a.b_label, "weights_sha256": ib["weights_sha256"], "evidence": a.b.as_posix()},
           "videos": len(per), "gt_frames": ia["gt_frames"],
           "per_video": {"b_worse": worse, "b_better": better, "equal": len(per) - worse - better},
           "overlap": {lab: {"videos": gp[k]["videos_with_overlapping_tracks"], "frames": gp[k]["overlapping_track_frames"]}
                       for lab, k in ((a.a_label, "a"), (a.b_label, "b"))},
           "b_idsw_in_videos_with_ge30_overlap_frames": {"videos": len(dup_videos), "idsw": sum(r[f"idsw_{a.b_label}"] for r in dup_videos),
                                                       "idsw_total": sum(r[f"idsw_{a.b_label}"] for r in per)},
           "note": "GT dan xuat 1 track/video (ADR-0008), val; mo ta, khong phai luat chon"}
    a.out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("summary.csv", summary), ("per_video.csv", per)):
        with (a.out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (a.out / "detector_swap.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = ["| Detector | Lớp | ID switch / 1000 frame GT | ID switch | Track recall | Trung vị độ phủ ID chính | Video 1 ID | Đứt track |",
          "|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['detector']} | {r['class']} | {r['idsw_per_1000_gt_frames']} | {r['id_switches']} | {r['track_recall_pooled']} | "
           f"{r['median_dominant_id_coverage']} | {r['videos_single_id']}/{r['videos']} | {r['fragments']} |" for r in summary]
    md += ["", f"Theo video: {a.b_label} nhiều ID switch hơn ở {worse} video, ít hơn ở {better}, bằng ở {len(per) - worse - better}. "
               f"Frame có hai track chồng nhau (IoU ≥ 0,3): {res['overlap']}."]
    (a.out / "detector_swap.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    LOG.info("%s", res["per_video"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
