"""Kiem luat muc B, C (docs/w8/W8_PLAN.md) trong scripts/experiments/w8_v2_verify.py tren du lieu gia va bang chung that."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))
import w8_v2_verify as vv  # noqa: E402


def _run(idsw, rec, drone_r, det, fa, per=None):
    return {"tracking": {"all": {"idsw_per_1000_gt_frames": idsw, "track_recall_pooled": rec, "fragments": 1}},
            "alerts": {"center_hex|center|R1": {"detected": det, "events": 23, "false_alerts_nondrone": fa},
                       "center_hex|center|R0": {"false_alerts_nondrone": 7}},
            "image_level": {"per_class": {"Drone": {"R": drone_r}}}, "median_fps": 80.0,
            "per_video": per or [{"video_id": "V", "track_recall": rec}]}


def test_rule_b_passes_and_each_condition_can_fail():
    base = _run(18.0, 0.84, 0.87, 23, 0)
    assert vv.rule_b(base, _run(2.0, 0.83, 0.86, 23, 0))["apply_v2"]
    fails = {"1_drone_image_recall_drop_le_0.02": _run(2.0, 0.84, 0.84, 23, 0),
             "2_r1_event_recall_not_lower": _run(2.0, 0.84, 0.87, 22, 0),
             "3_r1_false_nondrone_not_higher": _run(2.0, 0.84, 0.87, 23, 1),
             "4_idsw_reduction_ge_20pct": _run(15.0, 0.84, 0.87, 23, 0),
             "5_pooled_track_recall_drop_le_0.02": _run(2.0, 0.81, 0.87, 23, 0)}
    for name, r in fails.items():
        out = vv.rule_b(base, r)
        assert not out["apply_v2"] and [k for k, c in out["conditions"].items() if not c["pass"]] == [name]


def _dup(fj, ff, hj, hf, rate=1.0):
    c = {"jpg_fp32": fj, "frame_fp32": ff, "jpg_fp16": hj, "frame_fp16": hf}
    return {"conditions": {k: {"dup_rate": v} for k, v in c.items()}, "repro_frame_fp32_vs_run14": {"rate": rate}}


def test_rule_c_branches():
    assert vv.rule_c(_dup(0.11, 0.117, 0.11, 0.11, rate=0.9))["interpretation"].startswith("khong qua")
    assert vv.rule_c(_dup(0.11, 0.14, 0.11, 0.11))["gate_pass"] is False          # ngoai 11,7 +- 1
    assert vv.rule_c(_dup(0.01, 0.117, 0.01, 0.11))["c1_input_is_factor"]
    assert vv.rule_c(_dup(0.11, 0.117, 0.11, 0.11))["c3_all_ge_8pct"]
    assert vv.rule_c(_dup(0.05, 0.117, 0.05, 0.10))["interpretation"].startswith("yeu to")
    assert vv.rule_c(_dup(0.10, 0.117, 0.07, 0.10))["interpretation"] == "chua xac dinh"


def test_saved_result_matches_rerun_and_kaggle(tmp_path, monkeypatch):
    """Chay lai tren bang chung that phai ra dung v2_verify.json da luu, va khop track_summary cua Kaggle."""
    monkeypatch.setattr(sys, "argv", ["x", "--out", str(tmp_path)])
    assert vv.main() == 0
    new = json.loads((tmp_path / "v2_verify.json").read_text(encoding="utf-8"))
    old = json.loads((ROOT / "results/W08/v2_verify/v2_verify.json").read_text(encoding="utf-8"))
    assert new == old
    k = new["checks"]["consistency_with_kaggle_summary"]
    assert all(a == b for a, b in k.values())
