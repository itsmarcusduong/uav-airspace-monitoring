"""Luat B, C cua W9_PLAN (scripts/experiments/w9_bench_select.py): du lieu gia va detection da luu cua run 17."""
import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in ("scripts/experiments", "scripts/pipeline", "scripts/alert", "scripts/tracking", "tests"):
    sys.path.insert(0, str(ROOT / sub))
import w9_bench_select as bs  # noqa: E402

EV17 = ROOT / "results/W08/kaggle_run_17/w8_run17"


def offline_c0(tmp: Path) -> Path:
    """Gia lap C0 rep1: e1pipe tren detection da luu cua run 17 (detector gia), du tep nhu job Kaggle --save-outputs."""
    import e1pipe
    import offline_track as ot
    import test_w9_e1pipe as t
    ev = tmp / "w9_C0_rep1"
    tr, poly, acfg = t.cfgs()
    sink = e1pipe.Sink(ev, "w9_C0_rep1", "c", "a3de", {}, "cpu", "x")
    meta = list(csv.DictReader((EV17 / "meta.csv").open(encoding="utf-8")))
    for m in meta:
        v, n = m["video_id"], int(m["frames"])
        e1pipe.run_source(range(n), v, m["class_name"], float(m["fps"]), int(m["width"]), int(m["height"]), n,
                          t.SavedDets(ot.load_dets(EV17 / "dets" / f"{v}.csv")), e1pipe.make_tracker(tr), sink, poly, acfg, "center_hex", "a3de")
    sink.close()
    shutil.copy2(EV17 / "meta.csv", ev / "meta.csv"); shutil.copy2(EV17 / "timing.csv", ev / "timing.csv")
    inp = json.loads((EV17 / "inputs.json").read_text(encoding="utf-8"))
    (ev / "inputs.json").write_text(json.dumps(inp))
    (ev / "stage_status.json").write_text(json.dumps({k: {"status": "OK"} for k in ("env", "inputs", "run", "detect", "dump", "summary")}))
    (ev / "summary.json").write_text(json.dumps({"tag": "w9_C0_rep1", "frames": 11821, "fps_excl_warmup": 80.0, "gpu_peak_mb": 100,
                                                 "latency_ms": {k: {"p50": 5.0, "p95": 9.0} for k in ("decode", "detect", "track", "alert", "persist", "total")}}))
    return ev


def test_gate_b_and_accuracy_on_saved_run17(tmp_path):
    ev = offline_c0(tmp_path)
    g = bs.gate_b(ev)
    assert g["pass"] and g["rate"] == 1.0 and g["events_e1pipe"] == g["events_run17"] == 25
    import yaml
    import w7_postproc as w7
    rois = [r for r in yaml.safe_load((ROOT / "configs/roi_w6.yaml").read_text())["rois"] if r["name"] == "center_hex"]
    acfg = yaml.safe_load((ROOT / "configs/alert_e1.yaml").read_text())
    with w7.NEG.open(encoding="utf-8-sig") as fh:
        ign = {f"{r['video_id']}_f{int(r['frame']):05d}" for r in csv.DictReader(fh)}
    acc = bs.accuracy(ev, rois, acfg, ign)
    v2 = json.loads((ROOT / "results/W08/v2_verify/v2_verify.json").read_text())["runs"]["run17"]
    assert acc["idsw_per_1000"] == v2["tracking"]["all"]["idsw_per_1000_gt_frames"] and acc["r1_detected"] == 23
    (ev / "tracks/tracker_bytetrack_e1/V_DRONE_060.csv").write_text("frame,id,cls,conf,x,y,w,h\n")    # mat track -> cong truot
    assert not bs.gate_b(ev)["pass"]


def T(fps, p95):
    return {"fps_median": fps, "p95_total_median": p95}


def A(r=0.87, det=23, fa=0, tr=0.84, idsw=2.0):
    return {"drone_recall": r, "r1_detected": det, "r1_false_nondrone": fa, "track_recall_pooled": tr, "idsw_per_1000": idsw}


def test_rule_c_branches():
    c = bs.rule_c({"C0": T(80, 30), "C1": T(110, 20), "C2": T(200, 10)}, {"C0": A(), "C1": A(), "C2": A()}, {})
    assert c["choice"] == "C2"
    c = bs.rule_c({"C0": T(80, 30), "C1": T(110, 20), "C2": T(113, 10)}, {"C0": A(), "C1": A(), "C2": A()}, {})
    assert c["choice"] == "C1"                                     # C2 hon C1 < 5% -> hoa -> don gian hon
    c = bs.rule_c({"C0": T(80, 30), "C1": T(110, 20), "C2": T(200, 10)}, {"C0": A(), "C1": A(r=0.85), "C2": A(det=22)}, {})
    assert c["choice"] == "C0" and not c["candidates"]["C1"]["accuracy_guard"]["drone_recall_drop_le_0.01"]
    c = bs.rule_c({"C0": T(10, 30), "C1": T(14, 20)}, {"C0": A(), "C1": A()}, {"C2": {"status": "FAILED", "error": "x"}})
    assert c["choice"] == "C0" and c["nfr1_met"] is False and "KHONG DAT" in c["reason"] and not c["candidates"]["C2"]["available"]
    c = bs.rule_c({"C0": T(80, 600), "C1": T(90, 400)}, {"C0": A(), "C1": A(idsw=2.3)}, {})
    assert c["choice"] == "C0" and c["candidates"]["C1"]["accuracy_guard"]["idsw_increase_le_10pct"] is False
