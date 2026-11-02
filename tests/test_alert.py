"""Kiem thu mo-dun canh bao W6 (ADR-0009) bang du lieu tong hop: hinh hoc ROI, GT su kien, R0, R1, ghep su kien."""
import csv
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "alert"))
import alert_engine as ae  # noqa: E402
import evaluate_alerts as ea  # noqa: E402

W, H, FPS = 640, 512, 30.0
CFG = yaml.safe_load((ROOT / "configs" / "alert_e1.yaml").read_text(encoding="utf-8"))
ROIS = yaml.safe_load((ROOT / "configs" / "roi_w6.yaml").read_text(encoding="utf-8"))
HEX = next(r["polygon"] for r in ROIS["rois"] if r["name"] == "center_hex")
IN, OUT = (310, 246), (10, 10)             # goc tren-trai cua hop 20x20: tam trong / ngoai luc giac


def tr(f, tid, at, cls=2, conf=0.8):
    return {"frame": f, "id": tid, "cls": cls, "conf": conf, "x": at[0], "y": at[1], "w": 20, "h": 20}


def det(f, at, cls=2, conf=0.8):
    return {"frame": f, "cls": cls, "conf": conf, "x": at[0], "y": at[1], "w": 20, "h": 20}


def test_polygon_geometry():
    assert ae.point_in_polygon(0.5, 0.5, HEX) and not ae.point_in_polygon(0.05, 0.05, HEX)
    assert ae.point_in_polygon(0.5, 0.10, HEX)                       # nam dung tren canh -> trong
    assert not ae.point_in_polygon(0.12, 0.15, HEX)                  # goc cat xien cua luc giac
    edge = (40, 240, 40, 40)                                         # tam x = 60 px = 0,094 < 0,10: ngoai; hop cat canh trai
    assert not ae.box_in_roi(edge, HEX, W, H, "center") and ae.box_in_roi(edge, HEX, W, H, "box")
    with pytest.raises(ValueError):
        ae.box_in_roi(edge, HEX, W, H, "corner")


def test_gt_events_dwell_and_merge():
    short = [{"frame": f, "x": IN[0], "y": IN[1], "w": 20, "h": 20} for f in range(5)]
    assert ae.gt_events(short, 100, FPS, HEX, W, H, CFG) == []      # 5 frame < 0,3 s (9 frame)
    two = [{"frame": f, "x": IN[0], "y": IN[1], "w": 20, "h": 20} for f in list(range(10, 30)) + list(range(40, 60))]
    assert ae.gt_events(two, 100, FPS, HEX, W, H, CFG) == [(10, 59)]  # cach 10 frame <= 1 s -> gop


def test_r0_detector_only():
    d = [det(f, IN) for f in range(0, 20)] + [det(f, IN, cls=1) for f in range(30, 60)] + [det(f, IN, conf=0.2) for f in range(70, 90)]
    al = ae.r0_alerts(d, 100, FPS, HEX, W, H, CFG)
    assert [(a["start"], a["end"]) for a in al] == [(0, 19)]           # chim va conf thap khong canh bao
    flick = [det(f, IN) for f in range(0, 60) if f % 6]               # nhap nhay, khe 1 frame -> mot canh bao
    assert len(ae.r0_alerts(flick, 100, FPS, HEX, W, H, CFG)) == 1


def test_r1_enter_roi_after_dwell():
    t = [tr(f, 1, OUT) for f in range(20)] + [tr(f, 1, IN) for f in range(20, 60)]
    d = [det(f, OUT) for f in range(20)] + [det(f, IN) for f in range(20, 60)]
    al, _ = ae.r1_alerts(t, 100, FPS, HEX, W, H, CFG)
    assert [(a["start"], a["end"]) for a in ae.r0_alerts(d, 100, FPS, HEX, W, H, CFG)] == [(20, 59)]
    assert len(al) == 1 and al[0]["start"] == 28 and al[0]["end"] == 59 and al[0]["kind"] == "vao_vung"


def test_r1_track_appears_inside_roi():
    tracks = [tr(f, 1, IN) for f in range(20)]
    al, _ = ae.r1_alerts(tracks, 30, FPS, HEX, W, H, CFG)
    assert [(a["start"], a["end"]) for a in ae.r0_alerts([det(f, IN) for f in range(20)], 30, FPS, HEX, W, H, CFG)] == [(0, 19)]
    assert len(al) == 1 and al[0]["start"] == 8 and al[0]["kind"] == "xuat_hien_trong_vung"


def test_r1_needs_confirmation_and_drone_majority():
    brief = [tr(f, 1, IN) for f in range(2)]
    assert ae.r1_alerts(brief, 100, FPS, HEX, W, H, CFG)[0] == []
    bird = [tr(f, 1, IN, cls=1) for f in range(60)]
    assert ae.r1_alerts(bird, 100, FPS, HEX, W, H, CFG)[0] == []
    mostly_bird = [tr(f, 1, IN, cls=1) for f in range(40)] + [tr(f, 1, IN) for f in range(40, 60)]
    assert ae.r1_alerts(mostly_bird, 100, FPS, HEX, W, H, CFG)[0] == []   # lop da so khong phai Drone


def test_r1_class_tie_does_not_count_as_drone_majority():
    tracks = [tr(f, 1, IN, cls=2 if f % 2 == 0 else 0) for f in range(60)]
    dets = [det(f, IN) for f in range(0, 60, 2)]
    assert len(ae.r0_alerts(dets, 60, FPS, HEX, W, H, CFG)) == 1
    assert ae.r1_alerts(tracks, 60, FPS, HEX, W, H, CFG)[0] == []


def test_r1_short_detection_gaps_restart_dwell():
    one_frame_gap = [tr(f, 1, IN) for f in range(8)] + [tr(f, 1, IN) for f in range(9, 18)]
    two_frame_gap = [tr(f, 1, IN) for f in range(8)] + [tr(f, 1, IN) for f in range(10, 19)]

    one_frame_dets = [det(f, IN) for f in range(8)] + [det(f, IN) for f in range(9, 18)]
    two_frame_dets = [det(f, IN) for f in range(8)] + [det(f, IN) for f in range(10, 19)]
    assert [(a["start"], a["end"]) for a in ae.r0_alerts(one_frame_dets, 30, FPS, HEX, W, H, CFG)] == [(0, 17)]
    assert [(a["start"], a["end"]) for a in ae.r0_alerts(two_frame_dets, 30, FPS, HEX, W, H, CFG)] == [(0, 18)]

    one_alert, _ = ae.r1_alerts(one_frame_gap, 30, FPS, HEX, W, H, CFG)
    two_alerts, _ = ae.r1_alerts(two_frame_gap, 30, FPS, HEX, W, H, CFG)
    assert len(one_alert) == 1 and one_alert[0]["start"] == 17
    assert len(two_alerts) == 1 and two_alerts[0]["start"] == 18


def test_r1_duplicate_tracks_and_id_change_one_event():
    dup = [tr(f, 1, IN) for f in range(40)] + [tr(f, 2, (IN[0] + 3, IN[1])) for f in range(5, 40)]
    al, _ = ae.r1_alerts(dup, 100, FPS, HEX, W, H, CFG)
    assert len(ae.r0_alerts([det(f, IN) for f in range(40)], 100, FPS, HEX, W, H, CFG)) == 1
    assert len(al) == 1 and al[0]["tracks"] == [1, 2]
    swap = [tr(f, 1, IN) for f in range(30)] + [tr(f, 7, IN) for f in range(45, 80)]
    al, _ = ae.r1_alerts(swap, 100, FPS, HEX, W, H, CFG)
    swap_dets = [det(f, IN) for f in range(30)] + [det(f, IN) for f in range(45, 80)]
    assert len(ae.r0_alerts(swap_dets, 100, FPS, HEX, W, H, CFG)) == 1
    assert len(al) == 1 and al[0]["tracks"] == [1, 7] and al[0]["end"] == 79


def test_r1_short_loss_keeps_event_long_absence_splits():
    gap10 = [tr(f, 1, IN) for f in range(30)] + [tr(f, 1, IN) for f in range(41, 60)]
    assert len(ae.r1_alerts(gap10, 100, FPS, HEX, W, H, CFG)[0]) == 1
    leave = [tr(f, 1, IN) for f in range(30)] + [tr(f, 1, OUT) for f in range(30, 110)] + [tr(f, 1, IN) for f in range(110, 140)]
    leave_dets = [det(f, IN) for f in range(30)] + [det(f, OUT) for f in range(30, 110)] + [det(f, IN) for f in range(110, 140)]
    al, _ = ae.r1_alerts(leave, 150, FPS, HEX, W, H, CFG)
    assert [(a["start"], a["end"]) for a in ae.r0_alerts(leave_dets, 150, FPS, HEX, W, H, CFG)] == [(0, 29), (110, 139)]
    assert [(a["start"], a["end"]) for a in al] == [(8, 29), (118, 139)]


def test_roi_boundary_center_vs_box_rules():
    boundary_box = {"x": 40, "y": 240, "w": 40, "h": 40}
    boxes = [{"frame": f, "cls": 2, "conf": 0.8, **boundary_box} for f in range(20)]
    tracks = [{"frame": f, "id": 1, "cls": 2, "conf": 0.8, **boundary_box} for f in range(20)]
    box_cfg = {**CFG, "point": "box"}

    assert ae.r0_alerts(boxes, 30, FPS, HEX, W, H, CFG) == []
    assert len(ae.r0_alerts(boxes, 30, FPS, HEX, W, H, box_cfg)) == 1
    assert ae.r1_alerts(tracks, 30, FPS, HEX, W, H, CFG)[0] == []
    box_alerts, _ = ae.r1_alerts(tracks, 30, FPS, HEX, W, H, box_cfg)
    assert len(box_alerts) == 1 and box_alerts[0]["start"] == 8


def test_r1_prewarning_from_trajectory():
    t = [tr(f, 1, (10 + 8 * f, 246)) for f in range(40)]              # bay ngang vao luc giac tu ben trai
    al, pw = ae.r1_alerts(t, 60, FPS, HEX, W, H, CFG)
    assert pw and al and pw[0]["frame"] < al[0]["start"]


def test_match_events_counts():
    alerts = [{"start": 5, "end": 20}, {"start": 22, "end": 30}, {"start": 80, "end": 90}]
    m = ae.match_events(alerts, [(10, 40)], tol=30)                   # canh bao 80-90 nam ngoai [10-30, 40+30]
    assert m["detected"] == 1 and m["duplicates"] == 1 and m["false_alerts"] == 1 and m["false_alert_ids"] == [2]
    assert m["latency_frames"] == [-5]
    m = ae.match_events(alerts, [(10, 40)], tol=50)
    assert m["false_alerts"] == 0 and m["duplicates"] == 2
    assert ae.match_events(alerts, [], tol=30)["false_alerts"] == 3


def _write_evidence(ev: Path):
    vids = {"V_DRONE_001": "Drone", "V_BIRD_001": "Bird"}
    rows = {"V_DRONE_001": {"gt": [{"frame": f, "x": IN[0], "y": IN[1], "w": 20, "h": 20} for f in range(20, 80)],
                            "dets": [det(f, IN) for f in range(20, 80)], "tracks": [tr(f, 1, IN) for f in range(20, 80)]},
            "V_BIRD_001": {"gt": [{"frame": f, "x": IN[0], "y": IN[1], "w": 20, "h": 20} for f in range(0, 90)],
                           "dets": [det(f, IN) for f in range(10, 14)] + [det(f, IN) for f in range(50, 52)],   # R0: 2 canh bao sai
                           "tracks": [tr(f, 3, IN, cls=1) for f in range(90)]}}                                 # R1: chim -> khong
    for v, r in rows.items():
        for sub, fields in (("gt", ["frame", "x", "y", "w", "h"]), ("dets", ["frame", "cls", "conf", "x", "y", "w", "h"]),
                            ("tracks/tracker_bytetrack_e1", ["frame", "id", "cls", "conf", "x", "y", "w", "h"])):
            key = sub.split("/")[0]
            ea.wcsv(ev / sub / f"{v}.csv", r[key], fields)
    ea.wcsv(ev / "meta.csv", [{"video_id": v, "class_name": c, "frames": 90, "gt_frames": 60, "fps": FPS, "width": W, "height": H}
                              for v, c in vids.items()], ["video_id", "class_name", "frames", "gt_frames", "fps", "width", "height"])
    (ev / "stage_status.json").write_text(json.dumps({s: {"status": "OK"} for s in ("env", "inputs", "track", "metrics", "detect", "dump")}))
    (ev / "inputs.json").write_text(json.dumps({"split": "val", "test_used": False, "weights_sha256": "a" * 64,
                                                "trackers": {"tracker_bytetrack_e1": {}}}))


def test_evaluate_end_to_end(tmp_path, monkeypatch):
    ev = tmp_path / "w6_run14"; _write_evidence(ev)
    out = tmp_path / "alert_eval"
    monkeypatch.setattr(sys, "argv", ["x", "--evidence", str(ev), "--roi", str(ROOT / "configs/roi_w6.yaml"),
                                      "--alert", str(ROOT / "configs/alert_e1.yaml"), "--weights-sha", "a" * 64, "--out", str(out)])
    assert ea.main() == 0
    res = json.loads((out / "alert_summary.json").read_text())
    r0, r1 = res["summary"]["center_hex|center|R0"], res["summary"]["center_hex|center|R1"]
    assert r0["events"] == 1 and r0["event_recall"] == 1.0 and r0["false_alerts_nondrone"] == 2
    assert r1["event_recall"] == 1.0 and r1["false_alerts_nondrone"] == 0 and r1["latency_median_s"] == pytest.approx(8 / FPS, abs=1e-3)
    assert res["decision"]["verdict"] == "PASS" and res["test_used"] is False
    log = list(csv.DictReader((out / "alert_log.csv").open()))
    assert {r["rule"] for r in log} == {"R0", "R1"}


def test_evaluate_rejects_wrong_weights_and_missing_stage(tmp_path):
    ev = tmp_path / "e"; _write_evidence(ev)
    with pytest.raises(ValueError, match="weights"):
        ea.load_evidence(ev, "tracker_bytetrack_e1", "b" * 64)
    (ev / "stage_status.json").write_text(json.dumps({"env": {"status": "OK"}}))
    with pytest.raises(ValueError, match="detect"):
        ea.load_evidence(ev, "tracker_bytetrack_e1")


def test_evaluate_rejects_non_val_split_even_if_flag_says_not_test(tmp_path):
    ev = tmp_path / "e"; _write_evidence(ev)
    inputs = json.loads((ev / "inputs.json").read_text())
    inputs["split"] = "test"
    (ev / "inputs.json").write_text(json.dumps(inputs))
    with pytest.raises(ValueError, match="split=val"):
        ea.load_evidence(ev, "tracker_bytetrack_e1")


def test_decide_rules():
    base = {"false_alerts_nondrone": 10, "event_recall": 0.9}
    s = {"r|center|R0": base, "r|center|R1": {"false_alerts_nondrone": 7, "event_recall": 0.86}}
    assert ea.decide(s, "r")["verdict"] == "PASS"                     # giam 30%, recall -0,04
    s["r|center|R1"] = {"false_alerts_nondrone": 8, "event_recall": 0.9}
    assert ea.decide(s, "r")["verdict"] == "FAIL"                     # giam 20%
    s["r|center|R1"] = {"false_alerts_nondrone": 2, "event_recall": 0.80}
    assert ea.decide(s, "r")["verdict"] == "FAIL"                     # recall -0,10
    s["r|center|R0"] = {"false_alerts_nondrone": 0, "event_recall": 0.9}
    assert ea.decide(s, "r")["verdict"] == "UNDETERMINED"


def test_alert_demo_job(tmp_path, monkeypatch):
    """Job 15 tren du lieu tong hop: chon video theo luat dat truoc, ve, dong goi; khong dung du lieu that."""
    import cv2
    import numpy as np
    sys.path.insert(0, str(ROOT / "scripts" / "kaggle"))
    import w6_alert_demo as jd
    ev = tmp_path / "w6_run14"; _write_evidence(ev)
    with (ev / "per_video_metrics.csv").open("w") as fh:
        fh.write("tracker,iou_thr,video_id,id_switches\ntracker_bytetrack_e1,0.5,V_DRONE_001,3\ntracker_bytetrack_e1,0.5,V_BIRD_001,0\n")
    (ev / "stage_status.json").write_text(json.dumps({s: {"status": "OK"} for s in ("env", "inputs", "dump")}))
    vd = tmp_path / "raw" / "Data" / "Video_V"; vd.mkdir(parents=True)
    for v in ("V_DRONE_001", "V_BIRD_001"):
        w = cv2.VideoWriter(str(vd / f"{v}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
        for _ in range(90):
            w.write(np.zeros((H, W, 3), np.uint8))
        w.release()
        (vd / f"{v}_LABELS.mat").write_bytes(b"x")
    monkeypatch.setattr(sys, "argv", ["x", "--data-root", str(tmp_path / "raw"), "--evidence", str(ev), "--roi", str(ROOT / "configs/roi_w6.yaml"),
                                      "--alert", str(ROOT / "configs/alert_e1.yaml"), "--out", str(tmp_path / "o"), "--commit", "c" * 40])
    assert jd.main() == 0
    idx = json.loads((tmp_path / "o" / "w6_alert_demo" / "demo_index.json").read_text())
    assert [d["video_id"] for d in idx] == ["V_BIRD_001", "V_DRONE_001"]   # khong co canh bao vao_vung -> luat 2, 3 and all(d["frames"] == 90 for d in idx)
