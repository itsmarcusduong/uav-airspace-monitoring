"""W7 (ADR-0012): hau xu ly detection, tracker offline, luat chon bien the - du lieu tong hop."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in ("scripts/tracking", "scripts/experiments"):
    sys.path.insert(0, str(ROOT / sub))
import offline_track as ot  # noqa: E402


def test_nms_agnostic_vs_class_aware():
    d = [(2, 0.6, (10, 10, 20, 20)), (0, 0.5, (11, 10, 20, 20)), (2, 0.4, (12, 11, 20, 20)), (1, 0.9, (100, 100, 5, 5))]
    assert ot.nms(d, 0.5, agnostic=True) == [(2, 0.6, (10, 10, 20, 20)), (1, 0.9, (100, 100, 5, 5))]
    # cung lop: hop Airplane giu lai, hop Drone thu hai bi bo
    assert ot.nms(d, 0.5, agnostic=False) == [(2, 0.6, (10, 10, 20, 20)), (0, 0.5, (11, 10, 20, 20)), (1, 0.9, (100, 100, 5, 5))]
    assert ot.apply_variant(d, "none", None) is d
    with pytest.raises(ValueError):
        ot.apply_variant(d, "khac", 0.5)


def test_offline_tracker_keeps_one_id_for_moving_box():
    pytest.importorskip("ultralytics")
    import yaml
    from ultralytics.utils import IterableSimpleNamespace
    cfg = IterableSimpleNamespace(**yaml.safe_load((ROOT / "configs/tracker_bytetrack_e1.yaml").read_text()))
    dets = {f: [(2, 0.8, (100 + 2 * f, 50, 20, 16))] for f in range(30)}
    rows = ot.track_video(dets, 30, 640, 512, cfg, "none", None)
    assert {r["id"] for r in rows} == {1} and len(rows) >= 28
    # hop trung khac lop: agnostic NMS bo hop Airplane nen khong sinh track thu hai
    dup = {f: [(2, 0.8, (100 + 2 * f, 50, 20, 16)), (0, 0.7, (101 + 2 * f, 50, 20, 16))] for f in range(30)}
    assert len({r["id"] for r in ot.track_video(dup, 30, 640, 512, cfg, "none", None)}) == 2
    assert len({r["id"] for r in ot.track_video(dup, 30, 640, 512, cfg, "agnostic_nms", 0.5)}) == 1


def _res(idsw, fa0, r1_det, r1_fa, drone_r, kept=100):
    return {"tracking": {"all": {"idsw_per_1000_gt_frames": idsw}}, "dets_in": 100, "dets_kept": kept,
            "alerts": {"center_hex|center|R0": {"false_alerts_nondrone": fa0},
                       "center_hex|center|R1": {"detected": r1_det, "events": 23, "false_alerts_nondrone": r1_fa}},
            "detection": {"per_class": {"Drone": {"R": drone_r}}}}


def test_decide_rule_adr0012():
    pytest.importorskip("ultralytics")
    import w7_postproc as w
    v0 = _res(18.0, 7, 23, 0, 0.83)
    d = w.decide(v0, {"agnostic_nms": _res(17.0, 2, 23, 0, 0.82, 95), "nms_iou": _res(12.0, 7, 23, 0, 0.80, 90)})
    assert d["candidates"]["agnostic_nms"]["pass"] and not d["candidates"]["nms_iou"]["pass"]   # recall Drone giam 0,03
    assert d["choice"] == "agnostic_nms"
    d = w.decide(v0, {"agnostic_nms": _res(17.0, 6, 23, 0, 0.83), "nms_iou": _res(14.0, 7, 22, 0, 0.83)})
    assert d["choice"] == "none"                                                               # mot khong cai thien, mot mat su kien
    d = w.decide(v0, {"agnostic_nms": _res(14.0, 7, 23, 0, 0.83, 97), "nms_iou": _res(13.5, 7, 23, 0, 0.83, 90)})
    assert d["choice"] == "agnostic_nms"                                                       # chenh < 5 diem -> bo it detection hon


def test_variants_gated_by_adr(tmp_path):
    pytest.importorskip("ultralytics")
    import w7_postproc as w
    p = tmp_path / "adr.md"
    p.write_text("# ADR\n- Trạng thái: **Proposed**\n## Bối cảnh\n**Accepted** o day khong tinh\n", encoding="utf-8")
    assert not w.adr_accepted(p)
    p.write_text("# ADR\n- Trạng thái: **Accepted**\n## Bối cảnh\n", encoding="utf-8")
    assert w.adr_accepted(p)


def test_explore_sign_counts_and_drop_top():
    sys.path.insert(0, str(ROOT / "scripts" / "experiments"))
    import w7_postproc_explore as ex
    v0 = {"a": {"id_switches": "10"}, "b": {"id_switches": "2"}, "c": {"id_switches": "0"}}
    vx = {"a": {"id_switches": "0"}, "b": {"id_switches": "3"}, "c": {"id_switches": "0"}}
    assert ex.sign_counts(v0, vx, "id_switches") == {"better": 1, "worse": 1, "same": 1}
    d = ex.drop_top(v0, vx, 1)
    assert d["dropped"] == ["a"] and (d["v0"], d["variant"]) == (2, 3) and d["reduction"] == -0.5
