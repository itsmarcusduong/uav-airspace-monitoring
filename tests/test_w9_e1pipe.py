"""W9-01 (#129): e1pipe tung frame tren du lieu tong hop va tren detection da luu cua run 17 (khong GPU, khong video)."""
import csv
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
for sub in ("scripts/pipeline", "scripts/alert", "scripts/tracking"):
    sys.path.insert(0, str(ROOT / sub))
import alert_engine as ae  # noqa: E402
import e1pipe  # noqa: E402
import e1store  # noqa: E402

EV17 = ROOT / "results/W08/kaggle_run_17/w8_run17"


def cfgs():
    from ultralytics.utils import IterableSimpleNamespace
    tr = IterableSimpleNamespace(**yaml.safe_load((ROOT / "configs/tracker_bytetrack_e1.yaml").read_text(encoding="utf-8")))
    roi = yaml.safe_load((ROOT / "configs/roi_w6.yaml").read_text(encoding="utf-8"))
    poly = next(r["polygon"] for r in roi["rois"] if r["name"] == "center_hex")
    return tr, poly, yaml.safe_load((ROOT / "configs/alert_e1.yaml").read_text(encoding="utf-8"))


class SavedDets:
    """Detector gia: tra detection da luu theo thu tu frame (frame chi la so thu tu)."""
    def __init__(self, by_f):
        self.by_f = by_f

    def __call__(self, f):
        d = self.by_f.get(f, [])
        return np.array([[x, y, x + w, y + h, s, c] for c, s, (x, y, w, h) in d], dtype=np.float32).reshape(-1, 6)


def run(tmp, vid, by_f, n, cls_name="Drone", fps=30.0, w=640, h=512):
    tr, poly, acfg = cfgs()
    sink = e1pipe.Sink(tmp, "rt", "c", "m" * 4, {"t": 1}, "cpu", "test")
    lat = []
    s = e1pipe.run_source(range(n), vid, cls_name, fps, w, h, n, SavedDets(by_f), e1pipe.make_tracker(tr), sink, poly, acfg,
                          "center_hex", "m" * 4, latency_out=lat)
    rows = sink.tracks
    sink.close()
    return s, rows, lat, poly, acfg


def test_synthetic_drone_enters_roi(tmp_path):
    by_f = {f: [(2, 0.8, (10 + 4 * f, 240, 20, 20))] for f in range(80)}
    s, rows, lat, poly, acfg = run(tmp_path, "V_SYN", by_f, 140)
    assert s["frames"] == 140 and len(lat) == 140
    want, _ = ae.r1_alerts(rows, 140, 30.0, poly, 640, 512, acfg)
    c = e1store.connect(tmp_path / "events.sqlite")
    got = [(e["start_frame"], e["end_frame"], e["track_ids"], e["kind"]) for e in e1store.list_events(c, "rt")]
    assert got == [(a["start"], a["end"], a["tracks"], a["kind"]) for a in want] and len(got) == 1
    with gzip.open(tmp_path / "frames/rt/V_SYN.jsonl.gz", "rt") as fh:
        fr = [json.loads(x) for x in fh]
    assert [x["frame_index"] for x in fr] == list(range(140))
    assert set(fr[0]["stage_latency_ms"]) == {"decode", "detect", "track", "alert", "persist", "total"}
    assert all(x["stage_latency_ms"]["total"] >= x["stage_latency_ms"]["detect"] for x in fr)
    tr = [(x["frame_index"], t["transition"]) for x in fr for t in x["events"]]
    assert tr[0] == (want[0]["start"], "open") and ("close" in [t for _, t in tr])


def test_finalized_event_written_before_end_and_not_changed():
    """Su kien chi ghi vao kho bat bien khi het cua so mo lai: sau finalized() khong con thay doi."""
    tr, poly, acfg = cfgs()
    eng = ae.R1Engine(30.0, poly, 640, 512, acfg)
    rows = {f: [{"id": 1, "cls": 2, "conf": 0.8, "x": 310, "y": 246, "w": 20, "h": 20}] for f in range(40)}
    snap = {}
    for f in range(200):
        eng.step(f, rows.get(f, []))
        for i in eng.finalized(f):
            snap.setdefault(i, (f, eng.event(i)))
    eng.close()
    assert snap and all(eng.event(i) == ev for i, (_, ev) in snap.items())


@pytest.mark.parametrize("vid", ["V_DRONE_060", "V_HELICOPTER_012", "V_AIRPLANE_037"])
def test_saved_run17_dets_reproduce_run17_tracks(tmp_path, vid):
    """Cung detection da luu cua run 17, e1pipe (BYTETracker tung frame) phai cho track log gan nhu trung run 17
    (model.track tren Kaggle). Detection luu da lam tron 2 chu so nen nguong 99% dong."""
    import offline_track as ot
    meta = {m["video_id"]: m for m in csv.DictReader((EV17 / "meta.csv").open(encoding="utf-8"))}[vid]
    by_f = ot.load_dets(EV17 / "dets" / f"{vid}.csv")
    _, rows, _, _, _ = run(tmp_path, vid, by_f, int(meta["frames"]), meta["class_name"], float(meta["fps"]), int(meta["width"]), int(meta["height"]))
    ref = list(csv.DictReader((EV17 / "tracks/tracker_bytetrack_e1" / f"{vid}.csv").open(encoding="utf-8")))
    hit, n = e1pipe.match_tracks(rows, ref, tol=0.05)
    assert n == len(ref) and hit / n >= 0.99, (hit, n)


def test_match_tracks_tolerance():
    a = [{"frame": 0, "id": 1, "cls": 2, "x": 1.0, "y": 1.0, "w": 2.0, "h": 2.0}, {"frame": 1, "id": 1, "cls": 2, "x": 1, "y": 1, "w": 2, "h": 2}]
    b = [{"frame": 0, "id": 1, "cls": 2, "x": 1.04, "y": 1.0, "w": 2.0, "h": 2.0}, {"frame": 1, "id": 2, "cls": 2, "x": 1, "y": 1, "w": 2, "h": 2}]
    assert e1pipe.match_tracks(a, b) == (1, 2)
