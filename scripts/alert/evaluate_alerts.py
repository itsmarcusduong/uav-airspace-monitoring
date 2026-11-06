#!/usr/bin/env python3
"""Danh gia canh bao theo vung tren bang chung run 14 (W6, issue #76, ADR-0009).

Doc thu muc bang chung cua job tracking (`--tag w6_run14 --save-detections --save-gt`):
  meta.csv, gt/<video>.csv, dets/<video>.csv, tracks/<tracker>/<video>.csv, inputs.json, stage_status.json
Ap luat R0 (detector-only) va R1 (theo track) cho moi ROI trong configs/roi_w6.yaml, voi diem dai dien `center` (chinh)
va `box` (do nhay), roi ghep voi su kien GT.

Dau ra (--out):
  gt_events.csv, alert_log.csv, prewarn.csv, per_video_alerts.csv
  alert_summary.json, alert_summary.md  (bang theo ROI x luat x diem dai dien + quyet dinh theo luat dat truoc)

    python scripts/alert/evaluate_alerts.py --evidence results/W06/kaggle_run_14/w6_run14 \
        --tracker tracker_bytetrack_e1 --roi configs/roi_w6.yaml --alert configs/alert_e1.yaml --out results/W06/alert_eval

Chi doc CSV/JSON ket qua (khong doc video, khong doc du lieu tho).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import math
import statistics
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alert_engine import frames, gt_events, match_events, r0_alerts, r1_alerts  # noqa: E402

LOG = logging.getLogger("evaluate_alerts")
DRONE = "Drone"
FA_REDUCTION, RECALL_DROP = 0.30, 0.05          # Thuyet minh muc 12; ADR-0009 muc 6


def rcsv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def wcsv(p: Path, rows: list[dict], fields: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_evidence(ev: Path, tracker: str, expect_sha: str = "") -> tuple[list[dict], dict]:
    st = json.loads((ev / "stage_status.json").read_text(encoding="utf-8"))
    bad = {k: v.get("status") for k, v in st.items() if v.get("status") != "OK"}
    if bad:
        raise ValueError(f"stage khong OK: {bad}")
    for need in ("detect", "dump"):
        if need not in st:
            raise ValueError(f"thieu stage {need}: chay job voi --save-detections --save-gt")
    inp = json.loads((ev / "inputs.json").read_text(encoding="utf-8"))
    if inp.get("split") != "val":
        raise ValueError(f"chi chap nhan evidence split=val, nhan duoc {inp.get('split')!r}")
    if inp.get("test_used") is not False:
        raise ValueError("inputs.json khong xac nhan test_used=False")
    if expect_sha and inp["weights_sha256"] != expect_sha:
        raise ValueError(f"weights {inp['weights_sha256'][:16]} != ky vong {expect_sha[:16]}")
    if tracker not in inp["trackers"]:
        raise ValueError(f"khong co tracker {tracker} trong {list(inp['trackers'])}")
    vids = []
    for m in rcsv(ev / "meta.csv"):
        v = m["video_id"]
        vids.append({"video_id": v, "class_name": m["class_name"], "frames": int(m["frames"]), "fps": float(m["fps"]),
                     "width": int(m["width"]), "height": int(m["height"]),
                     "gt": rcsv(ev / "gt" / f"{v}.csv"), "dets": rcsv(ev / "dets" / f"{v}.csv"),
                     "tracks": rcsv(ev / "tracks" / tracker / f"{v}.csv")})
    return vids, inp


def evaluate(vids: list[dict], rois: list[dict], cfg: dict, points=("center", "box")):
    """Tra ve (dong log, dong theo video, tong hop, su kien GT, canh bao som)."""
    log, per, gtrows, pre = [], [], [], []
    agg: dict[str, dict] = {}
    for roi in rois:
        poly = roi["polygon"]
        for v in vids:
            fps, n = v["fps"], v["frames"]
            ev = gt_events(v["gt"], n, fps, poly, v["width"], v["height"], cfg) if v["class_name"] == DRONE else []
            for k, (s, e) in enumerate(ev):
                gtrows.append({"roi": roi["name"], "video_id": v["video_id"], "event": k, "start_f": s, "end_f": e,
                               "start_s": round(s / fps, 3), "end_s": round(e / fps, 3)})
            for pt in points:
                c = {**cfg, "point": pt}
                r1, pw = r1_alerts(v["tracks"], n, fps, poly, v["width"], v["height"], c)
                rules = {"R0": r0_alerts(v["dets"], n, fps, poly, v["width"], v["height"], c), "R1": r1}
                if pt == "center":
                    pre += [{"roi": roi["name"], "video_id": v["video_id"], **p, "time_s": round(p["frame"] / fps, 3)} for p in pw]
                for rule, al in rules.items():
                    m = match_events(al, ev, frames(cfg["match_tolerance_s"], fps))
                    fa = set(m["false_alert_ids"])
                    for i, x in enumerate(al):
                        log.append({"roi": roi["name"], "point": pt, "rule": rule, "video_id": v["video_id"], "class_name": v["class_name"],
                                    "alert": i, "start_f": x["start"], "end_f": x["end"], "start_s": round(x["start"] / fps, 3),
                                    "end_s": round(x["end"] / fps, 3), "tracks": " ".join(map(str, x["tracks"])), "kind": x["kind"],
                                    "matched": i not in fa})
                    per.append({"roi": roi["name"], "point": pt, "rule": rule, "video_id": v["video_id"], "class_name": v["class_name"],
                                **{k: m[k] for k in ("events", "detected", "alerts", "matched_alerts", "false_alerts", "duplicates")}})
                    key = f"{roi['name']}|{pt}|{rule}"
                    g = agg.setdefault(key, {"roi": roi["name"], "point": pt, "rule": rule, "events": 0, "detected": 0, "alerts": 0,
                                             "matched_alerts": 0, "matched_1to1": 0, "false_alerts": 0, "false_alerts_nondrone": 0, "duplicates": 0,
                                             "latency_s": [], "hours_nondrone": 0.0, "hours_all": 0.0, "videos_with_false_alert": 0})
                    for k in ("events", "detected", "alerts", "matched_alerts", "matched_1to1", "false_alerts", "duplicates"):
                        g[k] += m[k]
                    g["latency_s"] += [x / fps for x in m["latency_frames"]]
                    g["hours_all"] += n / fps / 3600
                    g["videos_with_false_alert"] += m["false_alerts"] > 0
                    if v["class_name"] != DRONE:
                        g["false_alerts_nondrone"] += m["false_alerts"]; g["hours_nondrone"] += n / fps / 3600
    summary = {}
    for k, g in agg.items():
        lat = g.pop("latency_s")
        summary[k] = {**g, "event_recall": round(g["detected"] / g["events"], 4) if g["events"] else None,
                      "event_precision": round(g["matched_alerts"] / g["alerts"], 4) if g["alerts"] else None,
                      "event_precision_1to1": round(g["matched_1to1"] / g["alerts"], 4) if g["alerts"] else None,
                      "false_alerts_drone_videos": g["false_alerts"] - g["false_alerts_nondrone"],
                      "false_alerts_per_hour_nondrone_upper95": round(poisson_upper(g["false_alerts_nondrone"]) / g["hours_nondrone"], 1)
                      if g["hours_nondrone"] else None,
                      "false_alerts_per_hour_nondrone": round(g["false_alerts_nondrone"] / g["hours_nondrone"], 2) if g["hours_nondrone"] else None,
                      "latency_median_s": round(statistics.median(lat), 3) if lat else None,
                      "hours_nondrone": round(g["hours_nondrone"], 4), "hours_all": round(g["hours_all"], 4)}
    return log, per, summary, gtrows, pre


def poisson_upper(k: int, conf: float = 0.95) -> float:
    """Can tren mot phia cua trung binh Poisson khi quan sat k su kien (P(X <= k; mu) = 1 - conf), tim bang chia doi.
    k = 0 -> -ln(0,05) = 2,996. Gia dinh cac su kien doc lap va dong nhat, nen chi la chi bao (review #83)."""
    cdf = lambda mu: sum(math.exp(-mu) * mu ** i / math.factorial(i) for i in range(k + 1))
    lo, hi = 0.0, 10.0 + 10 * k
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > 1 - conf else (lo, mid)
    return hi


def decide(summary: dict, roi: str, point: str = "center") -> dict:
    """Luat dat truoc (ADR-0009 muc 6): R1 dat neu giam >= 30% canh bao sai tren video khong co Drone so voi R0
    va event recall giam khong qua 5 diem %. R0 khong co canh bao sai -> khong do duoc muc giam."""
    r0, r1 = summary[f"{roi}|{point}|R0"], summary[f"{roi}|{point}|R1"]
    fa0, fa1 = r0["false_alerts_nondrone"], r1["false_alerts_nondrone"]
    rc0, rc1 = r0["event_recall"], r1["event_recall"]
    out = {"roi": roi, "point": point, "fa_nondrone": {"R0": fa0, "R1": fa1}, "event_recall": {"R0": rc0, "R1": rc1}}
    if rc0 is None or rc1 is None:
        return {**out, "verdict": "UNDETERMINED", "reason": "khong co su kien GT trong ROI"}
    drop_ok = rc1 >= rc0 - RECALL_DROP
    if fa0 == 0:
        return {**out, "verdict": "UNDETERMINED", "reason": "R0 khong co canh bao sai tren video khong co Drone; khong do duoc muc giam",
                "recall_ok": drop_ok}
    red = 1 - fa1 / fa0
    out.update(fa_reduction=round(red, 4), recall_drop=round(rc0 - rc1, 4))
    ok = red >= FA_REDUCTION and drop_ok
    return {**out, "verdict": "PASS" if ok else "FAIL",
            "reason": f"giam canh bao sai {red:.1%} (can >= {FA_REDUCTION:.0%}); recall giam {rc0 - rc1:+.3f} (cho phep <= {RECALL_DROP})"}


def to_md(summary: dict, dec: dict) -> str:
    L = ["| ROI | Diem | Luat | Su kien GT | Event recall | Canh bao | Event precision | Event precision 1-1 | Canh bao sai (video khong Drone) | "
         "Canh bao sai / gio (khong Drone) | Can tren 95% / gio | Canh bao sai (video Drone) | Lap | Do tre trung vi (s) |", "|" + "---|" * 14]
    for k, s in summary.items():
        L.append(f"| {s['roi']} | {s['point']} | {s['rule']} | {s['events']} | {s['event_recall']} | {s['alerts']} | {s['event_precision']} | {s['event_precision_1to1']} | "
                 f"{s['false_alerts_nondrone']} | {s['false_alerts_per_hour_nondrone']} | {s['false_alerts_per_hour_nondrone_upper95']} | {s['false_alerts_drone_videos']} | {s['duplicates']} | "
                 f"{s['latency_median_s']} |")
    L += ["", f"**Quyet dinh theo luat (ROI {dec['roi']}, diem {dec['point']}):** {dec['verdict']} - {dec['reason']}"]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", type=Path, required=True)
    ap.add_argument("--tracker", default="tracker_bytetrack_e1")
    ap.add_argument("--roi", type=Path, required=True)
    ap.add_argument("--alert", type=Path, required=True)
    ap.add_argument("--weights-sha", default="", help="SHA-256 weights ky vong (kiem trong inputs.json)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rc, cfg = yaml.safe_load(a.roi.read_text(encoding="utf-8")), yaml.safe_load(a.alert.read_text(encoding="utf-8"))
    vids, inp = load_evidence(a.evidence, a.tracker, a.weights_sha)
    log, per, summary, gtrows, pre = evaluate(vids, rc["rois"], cfg)
    dec = decide(summary, rc["primary"])
    a.out.mkdir(parents=True, exist_ok=True)
    wcsv(a.out / "gt_events.csv", gtrows, ["roi", "video_id", "event", "start_f", "end_f", "start_s", "end_s"])
    wcsv(a.out / "alert_log.csv", log, ["roi", "point", "rule", "video_id", "class_name", "alert", "start_f", "end_f", "start_s",
                                        "end_s", "tracks", "kind", "matched"])
    wcsv(a.out / "prewarn.csv", pre, ["roi", "video_id", "track", "frame", "time_s"])
    wcsv(a.out / "per_video_alerts.csv", per, list(per[0]))
    res = {"protocol": "ADR-0009", "roi_config": {"path": a.roi.as_posix(), "sha256": sha(a.roi), "version": rc["version"]},
           "alert_config": {"path": a.alert.as_posix(), "sha256": sha(a.alert), "version": cfg["version"]},
           "evidence": a.evidence.as_posix(), "tracker": a.tracker, "weights_sha256": inp["weights_sha256"],
           "videos": len(vids), "by_class": {c: sum(v["class_name"] == c for v in vids) for c in sorted({v["class_name"] for v in vids})},
           "test_used": False, "summary": summary, "decision": dec,
           "note": "Chi tren val; video khong co Drone chi vai phut, xa muc >= 2 gio cua Thuyet minh: ket qua chi mang tinh chi bao."}
    (a.out / "alert_summary.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (a.out / "alert_summary.md").write_text(to_md(summary, dec), encoding="utf-8")
    LOG.info("%s: %s", dec["verdict"], dec["reason"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
