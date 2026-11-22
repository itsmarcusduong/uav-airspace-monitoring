#!/usr/bin/env python3
"""W9 (#129, #130): ap luat muc B (cong tai tao e1pipe) va muc C (chon cau hinh van hanh) cua docs/w9/W9_PLAN.md
len bang chung Kaggle da giai nen. Chay ngoai Kaggle, chi doc CSV/JSON.

    python scripts/experiments/w9_bench_select.py --runs results/W09/kaggle_run_18 results/W09/kaggle_run_20 \
        [--stability results/W09/kaggle_run_21/w9_C1_rep1_stab] --out results/W09/benchmark

Moi thu muc trong --runs chua cac thu muc con w9_<CFG>_rep<k>/ (summary.json, stage_status.json, ...); rep1 cua C0, C1,
C2 co --save-outputs (track, det, su kien) de danh gia do chinh xac bang cung ham w8_v2_verify.evaluate_run.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import sqlite3
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("scripts/experiments", "scripts/alert", "scripts/pipeline", "scripts/tracking"):
    sys.path.insert(0, str(ROOT / sub))
import w8_v2_verify as vv  # noqa: E402

LOG = logging.getLogger("w9_bench_select")
RUN17 = ROOT / "results/W08/kaggle_run_17/w8_run17"
ORDER = ["C0", "C1", "C2"]                     # thu tu "don gian hon" khi hoa (luat C.3)


def load_runs(dirs: list[Path]) -> dict[str, dict[int, Path]]:
    out: dict[str, dict[int, Path]] = {}
    for d in dirs:
        for p in sorted(d.glob("w9_*_rep*")):
            if p.is_dir() and (p / "summary.json").is_file() and not p.name.endswith("_stab"):
                cfg, rep = p.name[3:].rsplit("_rep", 1)
                out.setdefault(cfg, {})[int(rep)] = p
    return out


def gate_b(c0: Path, run17: Path = RUN17) -> dict:
    """Cong tai tao (W9_PLAN muc B): track log khop run 17 >= 99% dong (cung frame, ID, lop; toa do lech <= 0,05 px)
    va su kien R1 trung tung khung frame voi R1 tinh tren track log run 17 (= bundle run 17)."""
    import alert_engine as ae
    import e1pipe
    import yaml
    rois = yaml.safe_load((ROOT / "configs/roi_w6.yaml").read_text(encoding="utf-8"))
    poly = next(r["polygon"] for r in rois["rois"] if r["name"] == rois["primary"])
    acfg = yaml.safe_load((ROOT / "configs/alert_e1.yaml").read_text(encoding="utf-8"))
    hit = n = 0; want_ev = set()
    meta = list(csv.DictReader((run17 / "meta.csv").open(encoding="utf-8")))
    for m in meta:
        v = m["video_id"]
        ref = list(csv.DictReader((run17 / "tracks/tracker_bytetrack_e1" / f"{v}.csv").open(encoding="utf-8")))
        got = list(csv.DictReader((c0 / "tracks/tracker_bytetrack_e1" / f"{v}.csv").open(encoding="utf-8")))
        h, k = e1pipe.match_tracks(ref, got, tol=0.05); hit += h; n += k
        al, _ = ae.r1_alerts(ref, int(m["frames"]), float(m["fps"]), poly, int(m["width"]), int(m["height"]), acfg)
        want_ev |= {(v, x["start"], x["end"]) for x in al}
    c = sqlite3.connect(str(c0 / "events.sqlite"))
    got_ev = {(s, a, b) for s, a, b in c.execute("SELECT source_id, start_frame, end_frame FROM events")}
    c.close()
    rate = hit / n if n else 0.0
    return {"track_rows_run17": n, "matched": hit, "rate": round(rate, 5), "events_run17": len(want_ev), "events_e1pipe": len(got_ev),
            "events_identical": got_ev == want_ev, "pass": rate >= 0.99 and got_ev == want_ev}


def accuracy(rep1: Path, rois, acfg, ignore) -> dict:
    """Danh gia mot cau hinh bang cung ham voi W8 (duong predict), GT lay tu run 17."""
    with tempfile.TemporaryDirectory() as td:
        ev = Path(td) / rep1.name
        shutil.copytree(rep1, ev, ignore=shutil.ignore_patterns("frames", "latency.csv.gz", "events.sqlite"))
        shutil.copytree(RUN17 / "gt", ev / "gt")
        r = vv.evaluate_run(ev, 0.5, rois, acfg, ignore)
    t = r["tracking"]["all"]; a1 = r["alerts"]["center_hex|center|R1"]
    return {"drone_recall": r["image_level"]["per_class"]["Drone"]["R"], "drone_precision": r["image_level"]["per_class"]["Drone"]["P"],
            "r1_detected": a1["detected"], "r1_events": a1["events"], "r1_false_nondrone": a1["false_alerts_nondrone"],
            "track_recall_pooled": t["track_recall_pooled"], "idsw_per_1000": t["idsw_per_1000_gt_frames"]}


def timing(reps: dict[int, Path]) -> dict:
    s = {k: json.loads((p / "summary.json").read_text(encoding="utf-8")) for k, p in reps.items()}
    fps = [x["fps_excl_warmup"] for x in s.values()]; p95 = [x["latency_ms"]["total"]["p95"] for x in s.values()]
    stages = {st: statistics.median(x["latency_ms"][st]["p50"] for x in s.values()) for st in ("decode", "detect", "track", "alert", "persist", "total")}
    return {"reps": sorted(s), "fps_median": statistics.median(fps), "fps_min": min(fps), "fps_max": max(fps),
            "p95_total_median": statistics.median(p95), "p95_total_min": min(p95), "p95_total_max": max(p95),
            "p50_total_median": stages["total"], "stage_p50_median_ms": stages,
            "gpu_peak_mb_max": max((x.get("gpu_peak_mb") or 0) for x in s.values())}


def rule_c(tm: dict[str, dict], acc: dict[str, dict], export: dict[str, dict]) -> dict:
    """Luat C, W9_PLAN (dat truoc). tm, acc: theo cau hinh. export: stage export cua C2 (neu co)."""
    base = acc.get("C0")
    out = {}
    for cfg in ORDER:
        if cfg == "C2" and export.get("C2", {}).get("status") == "FAILED":
            out[cfg] = {"available": False, "reason": "xuat TensorRT that bai: " + export["C2"].get("error", "")[:200]}
            continue
        if cfg not in tm or cfg not in acc:
            out[cfg] = {"available": False, "reason": "khong co ket qua"}
            continue
        t, x = tm[cfg], acc[cfg]
        nfr1 = t["fps_median"] >= 15 and t["p95_total_median"] <= 500
        g = {"drone_recall_drop_le_0.01": base["drone_recall"] - x["drone_recall"] <= 0.01 + 1e-9,
             "r1_event_recall_not_lower": x["r1_detected"] >= base["r1_detected"],
             "r1_false_nondrone_not_higher": x["r1_false_nondrone"] <= base["r1_false_nondrone"],
             "track_recall_drop_le_0.01": base["track_recall_pooled"] - x["track_recall_pooled"] <= 0.01 + 1e-9,
             "idsw_increase_le_10pct": x["idsw_per_1000"] <= base["idsw_per_1000"] * 1.10 + 1e-9}
        out[cfg] = {"available": True, "nfr1": nfr1, "accuracy_guard": g, "accuracy_ok": all(g.values()),
                    "fps_median": t["fps_median"], "p95_total_median": t["p95_total_median"]}
    ok = [c for c in ORDER if out[c].get("available") and out[c]["nfr1"] and out[c]["accuracy_ok"]]
    if not ok:
        nf = out.get("C0", {}).get("nfr1")
        return {"candidates": out, "choice": "C0", "nfr1_met": bool(nf),
                "reason": "khong cau hinh nao dat (1) va (2) -> giu C0" + ("" if nf else "; C0 khong dat NFR1 -> NFR1 KHONG DAT")}
    best = max(ok, key=lambda c: out[c]["fps_median"])
    tie = [c for c in ok if out[c]["fps_median"] >= out[best]["fps_median"] * 0.95]
    choice = min(tie, key=ORDER.index)
    return {"candidates": out, "choice": choice, "nfr1_met": True,
            "reason": f"dat (1)+(2): {ok}; FPS cao nhat {best}; trong 5%: {tie} -> chon don gian nhat {choice}"}


def stability(p: Path | None) -> dict | None:
    if p is None:
        return None
    s = json.loads((p / "summary.json").read_text(encoding="utf-8")); st = json.loads((p / "stage_status.json").read_text(encoding="utf-8"))
    sb = s.get("stability") or {}
    ok = st.get("run", {}).get("status") == "OK" and sb.get("minutes", 0) >= 60 and (sb.get("rss_ratio") or 9) <= 1.10
    return {"tag": s["tag"], **sb, "pass": ok}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--stability", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import yaml
    import w7_postproc as w7
    rois = [r for r in yaml.safe_load((ROOT / "configs/roi_w6.yaml").read_text(encoding="utf-8"))["rois"] if r["name"] == "center_hex"]
    acfg = yaml.safe_load((ROOT / "configs/alert_e1.yaml").read_text(encoding="utf-8"))
    with w7.NEG.open(encoding="utf-8-sig") as fh:
        ignore = {f"{r['video_id']}_f{int(r['frame']):05d}" for r in csv.DictReader(fh)}
    runs = load_runs(a.runs)
    if "C0" not in runs or 1 not in runs["C0"]:
        raise SystemExit("thieu C0 rep1")
    gate = gate_b(runs["C0"][1])
    tm = {c: timing(r) for c, r in runs.items()}
    acc = {c: accuracy(r[1], rois, acfg, ignore) for c, r in runs.items() if c in ORDER and 1 in r and (r[1] / "tracks").is_dir()}
    export = {c: json.loads((r[min(r)] / "stage_status.json").read_text(encoding="utf-8")).get("export", {}) for c, r in runs.items()}
    res = {"plan": "docs/w9/W9_PLAN.md", "gate_b": gate, "timing": tm, "accuracy": acc,
           "rule_c": rule_c(tm, acc, export) if gate["pass"] else {"choice": None, "reason": "cong tai tao muc B khong dat -> khong ap luat C"},
           "stability": stability(a.stability)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "benchmark_summary.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (a.out / "benchmark.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["config", "rep", "frames", "fps_excl_warmup", "p50_total_ms", "p95_total_ms", "gpu_peak_mb", "source"])
        for c, r in sorted(runs.items()):
            for k, p in sorted(r.items()):
                s = json.loads((p / "summary.json").read_text(encoding="utf-8"))
                w.writerow([c, k, s["frames"], s["fps_excl_warmup"], s["latency_ms"]["total"]["p50"], s["latency_ms"]["total"]["p95"],
                            s.get("gpu_peak_mb"), p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.as_posix()])
    LOG.info("cong B: %s | chon: %s", gate["pass"], res["rule_c"].get("choice"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
