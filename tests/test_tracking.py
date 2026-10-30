"""Kiem tra do do lien ket (ADR-0008) va job tracking run 12 tren du lieu tong hop (khong dung du lieu that)."""
import csv
import gzip
import json
import sys
import zipfile

import numpy as np
import pytest

import w5_track_metrics as tm
import w5_track_videos as tv


def box(f):
    return (100 + 3 * f, 80, 20, 16)


def trk(f, i, cls=2, dx=0):
    x, y, w, h = box(f)
    return {"frame": f, "id": i, "cls": cls, "conf": 0.8, "x": x + dx, "y": y, "w": w, "h": h}


def test_id_switch_fragment_and_coverage():
    gt = [box(f) for f in range(20)]
    tracks = [trk(f, 1) for f in range(10)] + [trk(f, 2) for f in range(12, 20)]
    tracks += [{"frame": f, "id": 9, "cls": 1, "conf": 0.3, "x": 400, "y": 300, "w": 10, "h": 10} for f in range(6)]
    m = tm.video_metrics(gt, tracks, gt_cls=2)
    assert m["gt_frames"] == 20 and m["matched_frames"] == 18
    assert m["id_switches"] == 1 and m["fragments"] == 1 and m["n_ids_on_target"] == 2
    assert m["dominant_id"] == 1 and m["dominant_id_coverage"] == 0.5
    assert m["false_tracks"] == 1 and m["false_track_frames"] == 6
    assert m["class_consistency"] == 1.0


def test_switch_back_counts_twice_and_missing_gt_frames():
    gt = [box(f) for f in range(6)] + [None, None]
    ids = [1, 1, 2, 2, 1, 1]
    tracks = [trk(f, i) for f, i in enumerate(ids)] + [trk(6, 1)]
    m = tm.video_metrics(gt, tracks, gt_cls=2)
    assert m["id_switches"] == 2 and m["fragments"] == 0
    assert m["gt_frames"] == 6 and m["frames_no_gt_with_tracks"] == 1


def test_iou_threshold_and_class_consistency():
    gt = [box(f) for f in range(4)]
    tracks = [trk(f, 1, cls=1, dx=8) for f in range(4)]          # lech 8 px tren hop rong 20 -> IoU ~0.43
    assert tm.video_metrics(gt, tracks, 2, iou_thr=0.5)["matched_frames"] == 0
    m = tm.video_metrics(gt, tracks, 2, iou_thr=0.3)
    assert m["matched_frames"] == 4 and m["class_consistency"] == 0.0


def test_summarize_pools_counts():
    a = tm.video_metrics([box(f) for f in range(10)], [trk(f, 1) for f in range(10)], 2)
    b = tm.video_metrics([box(f) for f in range(10)], [trk(f, f // 5) for f in range(10)], 2)
    s = tm.summarize([a, b])
    assert s["videos"] == 2 and s["gt_frames"] == 20 and s["id_switches"] == 1
    assert s["idsw_per_1000_gt_frames"] == 50.0 and s["videos_single_id"] == 1


class _Boxes:
    def __init__(self, rows):
        self.xyxy = np.array([[r[0], r[1], r[0] + r[2], r[1] + r[3]] for r in rows], dtype=float)
        self.id = np.array([r[4] for r in rows], dtype=float) if rows else None
        self.cls = np.array([2.0] * len(rows)); self.conf = np.array([0.9] * len(rows))

    def __len__(self):
        return len(self.xyxy)


class _FakeModel:
    """Gia lap model.track: tra ve dung hop GT, doi ID o frame 6 cua video dau tien."""
    def track(self, source, **kw):
        assert kw["persist"] is False and kw["stream"] is True
        first = "V_DRONE_001" in source
        for f in range(10):
            x, y, w, h = box(f)
            yield type("R", (), {"boxes": _Boxes([(x, y, w, h, 2 if (first and f >= 6) else 1)])})()


def _make_inputs(tmp_path):
    import cv2
    data = tmp_path / "raw" / "Data" / "Video_V"; data.mkdir(parents=True)
    vids = [("V_DRONE_001", "Drone"), ("V_DRONE_002", "Drone"), ("V_BIRD_001", "Bird")]
    for v, _ in vids:
        vw = cv2.VideoWriter(str(data / f"{v}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 256))
        for f in range(10):
            vw.write(np.full((256, 320, 3), 40 + 10 * f, np.uint8))
        vw.release()
        (data / f"{v}_LABELS.mat").write_bytes(b"x")
    man = tmp_path / "yolo_manifest.csv.gz"
    with gzip.open(man, "wt", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["image", "split", "video_id", "class_name"]); w.writeheader()
        for v, c in vids:
            w.writerow({"image": f"images/val/{v}_f00000.jpg", "split": "val", "video_id": v, "class_name": c})
        w.writerow({"image": "images/train/V_X_f0.jpg", "split": "train", "video_id": "V_AIRPLANE_009", "class_name": "Airplane"})
    audit = tmp_path / "annotation_audit.csv"
    with audit.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["video_id", "frames_decoded"]); w.writeheader()
        for v, _ in vids:
            w.writerow({"video_id": v, "frames_decoded": 10})
    cfgs = []
    for name in ("bytetrack", "botsort"):
        p = tmp_path / f"tracker_{name}_default.yaml"; p.write_text(f"tracker_type: {name}\ntrack_buffer: 30\n"); cfgs.append(p)
    weights = tmp_path / "best.pt"; weights.write_bytes(b"weights")
    return tmp_path / "raw", man, audit, cfgs, weights


def test_track_job_end_to_end(tmp_path, monkeypatch):
    raw, man, audit, cfgs, weights = _make_inputs(tmp_path)
    monkeypatch.setattr(tv, "load_labels", lambda p: [box(f) for f in range(11)])     # du 1 muc -> offset0 cat ve 10
    monkeypatch.setattr(tv, "load_model", lambda w: _FakeModel())
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["x", "--data-root", str(raw), "--manifest", str(man), "--audit", str(audit),
                                      "--weights", str(weights), "--weights-sha", tv.sha256(weights), "--trackers", *map(str, cfgs),
                                      "--out", str(out), "--commit", "a" * 40, "--device", "cpu"])
    assert tv.main() == 0
    ev = out / "w5_track"
    st = json.loads((ev / "stage_status.json").read_text())
    assert all(v["status"] == "OK" for v in st.values()), st
    inp = json.loads((ev / "inputs.json").read_text())
    assert inp["videos"] == 3 and inp["test_used"] is False and inp["gt_frames"] == 30
    rows = list(csv.DictReader((ev / "per_video_metrics.csv").open()))
    d1 = [r for r in rows if r["video_id"] == "V_DRONE_001" and r["tracker"] == "tracker_bytetrack_default" and r["iou_thr"] == "0.5"][0]
    assert d1["id_switches"] == "1" and d1["dominant_id_coverage"] == "0.6"
    s = json.loads((ev / "track_summary.json").read_text())["summary"]
    assert s["tracker_bytetrack_default@0.5"]["all"]["id_switches"] == 1
    assert len(list((ev / "tracks" / "tracker_botsort_default").glob("*.csv"))) == 3
    demo = json.loads((ev / "demo" / "demo_index.json").read_text())
    assert [d["video_id"] for d in demo] == ["V_DRONE_001", "V_BIRD_001", "V_DRONE_002"]
    with zipfile.ZipFile(out / "w5_track_evidence.zip") as z:
        names = z.namelist()
    assert not any(n.endswith(".mp4") for n in names) and "w5_track/per_video_metrics.csv" in names


def test_track_job_rejects_wrong_weights(tmp_path, monkeypatch):
    raw, man, audit, cfgs, weights = _make_inputs(tmp_path)
    monkeypatch.setattr(tv, "load_labels", lambda p: [box(f) for f in range(10)])
    monkeypatch.setattr(sys, "argv", ["x", "--data-root", str(raw), "--manifest", str(man), "--audit", str(audit),
                                      "--weights", str(weights), "--weights-sha", "0" * 64, "--trackers", *map(str, cfgs),
                                      "--out", str(tmp_path / "o"), "--device", "cpu"])
    assert tv.main() == 1
    st = json.loads((tmp_path / "o" / "w5_track" / "stage_status.json").read_text())
    assert st["inputs"]["status"] == "FAILED" and "SHA-256" in st["inputs"]["error"]


def test_track_comparison_tie_rule():
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts" / "reporting"))
    import build_track_comparison as bc
    d = bc.decide("tracker_bytetrack_e1", "tracker_botsort_e1", 8.962, 7.756)       # 13,5% -> hoa
    assert d["tie"] and d["choice"] == "tracker_bytetrack_e1" and "tuyet doi" not in d["reason"]
    d = bc.decide("tracker_bytetrack_e1", "tracker_botsort_e1", 10.0, 7.0)          # 30% va 3/1000 -> BoT-SORT
    assert not d["tie"] and d["choice"] == "tracker_botsort_e1"
    d = bc.decide("tracker_bytetrack_e1", "tracker_botsort_e1", 2.0, 1.2)           # 40% nhung < 1/1000 -> hoa
    assert d["tie"] and d["choice"] == "tracker_bytetrack_e1"
    assert bc.decide("a_bytetrack", "b", 0.0, 0.0)["tie"]
