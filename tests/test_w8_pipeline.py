"""W8-03 (#116): kho su kien, dung bundle, API va dashboard phat lai tren du lieu tong hop (ADR-0015)."""
import csv
import gzip
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import build_bundle as bb  # noqa: E402
import e1store  # noqa: E402

FPS, W, H = 30.0, 640, 512


def write_csv(p: Path, rows: list[dict], fields: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


def make_evidence(root: Path) -> Path:
    """Evidence gia dang run 14/17: V_DRONE_001 co drone bay tu ngoai vao center_hex; V_BIRD_001 chi co chim trong ROI."""
    ev = root / "w8_fake"
    (ev / "tracks/tracker_bytetrack_e1").mkdir(parents=True)
    (ev / "stage_status.json").write_text(json.dumps({k: {"status": "OK"} for k in ("env", "inputs", "track", "detect", "dump")}))
    (ev / "inputs.json").write_text(json.dumps({"split": "val", "test_used": False, "weights_sha256": "ab" * 32, "commit": "c" * 40,
                                                "trackers": {"tracker_bytetrack_e1": {"sha256": "x"}}, "detector": {"conf": 0.1, "nms_iou": 0.5}}))
    write_csv(ev / "meta.csv", [{"video_id": "V_DRONE_001", "class_name": "Drone", "frames": 90, "fps": FPS, "width": W, "height": H},
                                {"video_id": "V_BIRD_001", "class_name": "Bird", "frames": 60, "fps": FPS, "width": W, "height": H}],
              ["video_id", "class_name", "frames", "fps", "width", "height"])
    tf = ["frame", "id", "cls", "conf", "x", "y", "w", "h"]
    drone = [{"frame": f, "id": 1, "cls": 2, "conf": 0.8, "x": 10 + 4 * f, "y": 240, "w": 20, "h": 20} for f in range(80)]
    bird = [{"frame": f, "id": 7, "cls": 1, "conf": 0.9, "x": 300, "y": 240, "w": 20, "h": 20} for f in range(60)]
    write_csv(ev / "tracks/tracker_bytetrack_e1/V_DRONE_001.csv", drone, tf)
    write_csv(ev / "tracks/tracker_bytetrack_e1/V_BIRD_001.csv", bird, tf)
    for v in ("V_DRONE_001", "V_BIRD_001"):
        write_csv(ev / "gt" / f"{v}.csv", [], ["frame", "x", "y", "w", "h"])
        write_csv(ev / "dets" / f"{v}.csv", [], ["frame", "cls", "conf", "x", "y", "w", "h"])
    return ev


@pytest.fixture()
def bundle(tmp_path):
    ev = make_evidence(tmp_path)
    media = tmp_path / "media"; media.mkdir()
    (media / "V_DRONE_001.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42fake")
    out = tmp_path / "bundle"
    bb.build(ev, out, "runX", "d" * 40, ROOT / "configs/roi_w6.yaml", ROOT / "configs/alert_e1.yaml", media_dir=media)
    return out


# ----------------------------------------------------------------------------- kho su kien
def test_store_append_only_and_derived_status(tmp_path):
    c = e1store.connect(tmp_path / "e.sqlite"); e1store.init(c)
    e1store.add_run(c, "r", "c", "m", {"a": 1}, "s", "cpu", "ev")
    e1store.add_source(c, "r", "V1", "Drone", 30.0, 640, 512, 90)
    e1store.add_event(c, "r:V1:0", "r", "V1", "R1", "center_hex", "vao_vung", 10, 40, 30.0, [3, 1])
    c.commit()
    assert e1store.get_event(c, "r:V1:0")["status"] == "new"
    e1store.add_review(c, "r:V1:0", "an", "confirmed")
    e1store.add_review(c, "r:V1:0", "quang", "false_alarm")
    e = e1store.get_event(c, "r:V1:0")
    assert e["status"] == "false_alarm" and e["n_reviews"] == 2 and e["track_ids"] == [1, 3] and e["end_ms"] == 1333
    for sql in ("UPDATE events SET end_frame = 50", "DELETE FROM events", "UPDATE event_reviews SET action = 'confirmed'",
                "DELETE FROM event_reviews", "INSERT INTO config_audit (actor_id, changed_at, target, new_sha256, reason) VALUES ('q','t','roi','x','y')"):
        if sql.startswith("INSERT"):
            c.execute(sql); c.commit()
            sql = "UPDATE config_audit SET reason = 'z'"
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            c.execute(sql)
    with pytest.raises(sqlite3.IntegrityError):            # su kien phai thuoc nguon cua dung run
        e1store.add_event(c, "r:V9:0", "r", "V9", "R1", "center_hex", "vao_vung", 0, 1, 30.0, [1])
    with pytest.raises(ValueError):
        e1store.add_review(c, "r:V1:0", "  ", "confirmed")
    with pytest.raises(KeyError):
        e1store.add_review(c, "khong-co", "an", "confirmed")


# ----------------------------------------------------------------------------- dung bundle
def test_bundle_events_frames_and_manifest(bundle):
    c = e1store.connect(bundle / "events.sqlite")
    ev = e1store.list_events(c, "runX")
    assert [(e["source_id"], e["kind"], e["status"]) for e in ev] == [("V_DRONE_001", "vao_vung", "new")]   # chim: khong canh bao
    src = {s["source_id"]: s for s in e1store.list_sources(c, "runX")}
    assert src["V_DRONE_001"]["has_media"] and not src["V_BIRD_001"]["has_media"]
    with gzip.open(bundle / "frames/V_DRONE_001.jsonl.gz", "rt") as fh:
        fr = [json.loads(x) for x in fh]
    assert len(fr) == 90 and fr[0]["tracks"][0]["box"] == [10.0, 240.0, 30.0, 260.0] and fr[85]["tracks"] == []
    opened = [f["frame_index"] for f in fr for e in f["events"] if e["transition"] == "open"]
    assert opened == [ev[0]["start_frame"]] and all(f["model_version"] == "ab" * 32 for f in fr)
    assert bb.verify(bundle) == []
    (bundle / "frames/V_BIRD_001.jsonl.gz").write_bytes(b"x")
    assert bb.verify(bundle) == ["frames/V_BIRD_001.jsonl.gz"]


def test_bundle_from_run14_matches_w6_alert_log(tmp_path):
    """Doi chieu cheo: su kien R1 trong bundle dung tu run 14 phai trung tung dong alert_log.csv cua W6."""
    ev, log = ROOT / "results/W06/kaggle_run_14/w6_run14", ROOT / "results/W06/alert_eval/alert_log.csv"
    if not (ev / "meta.csv").exists() or not log.exists():
        pytest.skip("thieu bang chung W6")
    out = tmp_path / "b14"
    bb.build(ev, out, "run14", "t", ROOT / "configs/roi_w6.yaml", ROOT / "configs/alert_e1.yaml")
    got = {(e["source_id"], e["start_frame"], e["end_frame"]) for e in e1store.list_events(e1store.connect(out / "events.sqlite"), "run14")}
    with log.open(encoding="utf-8") as fh:
        want = {(r["video_id"], int(r["start_f"]), int(r["end_f"])) for r in csv.DictReader(fh)
                if r["roi"] == "center_hex" and r["point"] == "center" and r["rule"] == "R1"}
    assert got == want and len(got) == 25


# ----------------------------------------------------------------------------- API
def test_api_rest_review_media_and_stream(bundle):
    from fastapi.testclient import TestClient
    import api
    cl = TestClient(api.create_app(bundle))
    assert cl.get("/health").json()["mode"] == "replay"
    run = cl.get("/runs").json()[0]
    assert run["run_id"] == "runX" and run["config"]["roi"]["name"] == "center_hex"
    assert cl.get("/sources", params={"run_id": "nope"}).status_code == 404
    ev = cl.get("/events", params={"run_id": "runX", "source_id": "V_DRONE_001"}).json()
    eid = ev[0]["event_id"]
    assert cl.post(f"/events/{eid}/review", json={"action": "maybe", "reviewer_id": "an"}).status_code == 422
    assert cl.post(f"/events/{eid}/review", json={"action": "confirmed", "reviewer_id": ""}).status_code == 422
    assert cl.post("/events/khong-co/review", json={"action": "confirmed", "reviewer_id": "an"}).status_code == 404
    r = cl.post(f"/events/{eid}/review", json={"action": "confirmed", "reviewer_id": "an", "note": "thay drone"})
    assert r.status_code == 201 and r.json()["status"] == "confirmed" and len(r.json()["reviews"]) == 1
    assert cl.get("/media/runX/V_DRONE_001").status_code == 200
    assert cl.get("/media/runX/V_BIRD_001").status_code == 404
    assert cl.get("/media/runX/..%2Fevents.sqlite").status_code == 404
    with cl.websocket_connect("/ws/stream?run_id=runX&source_id=V_BIRD_001&speed=16") as ws:
        msgs = []
        while True:
            m = ws.receive_json(); msgs.append(m)
            if m["type"] != "frame":
                break
    frames = [m for m in msgs if m["type"] == "frame"]
    assert len(frames) == 60 and msgs[-1] == {"type": "eos", "frames": 60}
    assert [f["frame_index"] for f in frames] == list(range(60))
    with cl.websocket_connect("/ws/stream?run_id=runX&source_id=KHONG") as ws:
        assert ws.receive_json()["type"] == "error"


def test_openapi_lists_contract(bundle):
    import api
    paths = set(api.create_app(bundle).openapi()["paths"])
    assert {"/health", "/runs", "/sources", "/events", "/events/{event_id}", "/events/{event_id}/review", "/media/{run_id}/{source_id}"} <= paths


# ----------------------------------------------------------------------------- dashboard (Playwright, headless)
def test_dashboard_replay_and_review(bundle, tmp_path):
    """Ca tu dong cho kich ban E2E (An, #118): phat toi EOS, danh sach su kien, review chi them, khong su kien o nguon Bird."""
    pw = pytest.importorskip("playwright.sync_api")
    import socket
    import threading
    import time
    import uvicorn
    import api
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = uvicorn.Server(uvicorn.Config(api.create_app(bundle), host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True); th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#source option", state="attached")
            pg.select_option("#source", "V_DRONE_001"); pg.select_option("#speed", "8")
            pg.wait_for_selector(".ev[data-event-id]")
            pg.click("#play")
            pg.wait_for_function("document.getElementById('conn').dataset.state === 'eos'", timeout=10000)
            assert pg.inner_text("#frame") == "89"
            st = pg.locator(".ev .status")
            assert st.get_attribute("data-status") == "new"
            pg.click(".ev button.confirm")                       # chua nhap reviewer -> khong ghi
            pg.wait_for_selector("#msg")
            pg.fill("#reviewer", "an")
            pg.click(".ev button.confirm")
            pg.wait_for_function("document.querySelector('.ev .status').dataset.status === 'confirmed'")
            pg.reload(); pg.wait_for_selector("#source option", state="attached"); pg.select_option("#source", "V_DRONE_001")
            pg.wait_for_function("document.querySelector('.ev .status') && document.querySelector('.ev .status').dataset.status === 'confirmed'")
            pg.select_option("#source", "V_BIRD_001")
            pg.wait_for_selector("#noevents")
            b.close()
    finally:
        server.should_exit = True; th.join(timeout=5)
    c = e1store.connect(bundle / "events.sqlite")
    assert [r["reviewer_id"] for r in e1store.rows(c, "SELECT reviewer_id FROM event_reviews")] == ["an"]

