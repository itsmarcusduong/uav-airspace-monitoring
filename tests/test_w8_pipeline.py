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


def make_evidence(root: Path, name: str = "w8_fake", nms: float = 0.5, drone_frames: int = 80) -> Path:
    """Evidence gia dang run 14/17: V_DRONE_001 co drone bay tu ngoai vao center_hex; V_BIRD_001 chi co chim trong ROI."""
    ev = root / name
    (ev / "tracks/tracker_bytetrack_e1").mkdir(parents=True)
    (ev / "stage_status.json").write_text(json.dumps({k: {"status": "OK"} for k in ("env", "inputs", "track", "detect", "dump")}))
    (ev / "inputs.json").write_text(json.dumps({"split": "val", "test_used": False, "weights_sha256": "ab" * 32, "commit": "c" * 40,
                                                "trackers": {"tracker_bytetrack_e1": {"sha256": "x"}}, "detector": {"conf": 0.1, "nms_iou": nms}}))
    write_csv(ev / "meta.csv", [{"video_id": "V_DRONE_001", "class_name": "Drone", "frames": 90, "fps": FPS, "width": W, "height": H},
                                {"video_id": "V_BIRD_001", "class_name": "Bird", "frames": 60, "fps": FPS, "width": W, "height": H}],
              ["video_id", "class_name", "frames", "fps", "width", "height"])
    tf = ["frame", "id", "cls", "conf", "x", "y", "w", "h"]
    drone = [{"frame": f, "id": 1, "cls": 2, "conf": 0.8, "x": 10 + 4 * f, "y": 240, "w": 20, "h": 20} for f in range(drone_frames)]
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
                "DELETE FROM event_reviews", "INSERT INTO config_audit (actor_id, changed_at, target, new_run_id, new_sha256, reason) VALUES ('q','t','roi','r','x','y')"):
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
    with gzip.open(bundle / "frames/runX/V_DRONE_001.jsonl.gz", "rt") as fh:
        fr = [json.loads(x) for x in fh]
    assert len(fr) == 90 and fr[0]["tracks"][0]["box"] == [10.0, 240.0, 30.0, 260.0] and fr[85]["tracks"] == []
    opened = [f["frame_index"] for f in fr for e in f["events"] if e["transition"] == "open"]
    assert opened == [ev[0]["start_frame"]] and all(f["model_version"] == "ab" * 32 for f in fr)
    assert bb.verify(bundle) == []
    (bundle / "frames/runX/V_BIRD_001.jsonl.gz").write_bytes(b"x")
    assert bb.verify(bundle) == ["frames/runX/V_BIRD_001.jsonl.gz"]


def test_overwrite_refuses_paths_outside_bundle(tmp_path, bundle, monkeypatch):
    """Review An (PR #124) muc 1: --overwrite khong duoc xoa de quy ngoai pham vi bundle."""
    ev, cfg = make_evidence(tmp_path, "ev2"), (ROOT / "configs/roi_w6.yaml", ROOT / "configs/alert_e1.yaml")
    def go(out):
        return bb.build(ev, out, "runY", "d" * 40, *cfg, overwrite=True)
    for bad, why in ((ROOT, "repo"), (ROOT.parent, "repo"), (Path(ROOT.anchor), "goc")):
        with pytest.raises(SystemExit, match="tu choi --overwrite"):
            bb.reset_bundle(bad)
    data = tmp_path / "data"; (data / "keep").mkdir(parents=True); (data / "keep" / "x.txt").write_text("du lieu")
    with pytest.raises(SystemExit, match="khong phai bundle"):
        go(data)
    assert (data / "keep" / "x.txt").read_text() == "du lieu"
    (bundle / "ghi_chu.txt").write_text("cua nguoi dung")
    with pytest.raises(SystemExit, match="khong thuoc bundle"):
        go(bundle)
    (bundle / "ghi_chu.txt").unlink()
    c = e1store.connect(bundle / "events.sqlite")
    e1store.add_review(c, e1store.list_events(c, "runX")[0]["event_id"], "an", "confirmed"); c.close()
    with pytest.raises(SystemExit, match="lich su chi them"):
        go(bundle)
    assert (bundle / "events.sqlite").is_file()
    monkeypatch.chdir(bundle)                                 # thu muc hien tai cung khong duoc xoa
    with pytest.raises(SystemExit, match="thu muc hien tai"):
        bb.reset_bundle(bundle)
    monkeypatch.chdir(tmp_path)
    fresh = tmp_path / "fresh"
    bb.build(ev, fresh, "runY", "d" * 40, *cfg)
    go(fresh)                                                 # bundle sach, chua review -> dung lai duoc
    assert bb.verify(fresh) == [] and sorted(p.name for p in fresh.iterdir()) == ["bundle.json", "events.sqlite", "frames"]


def test_append_run_writes_config_audit(tmp_path, bundle):
    """Review An (PR #124) muc 4 / ADR-0015: config_audit ghi khi them run co cau hinh khac run truoc."""
    cfg = (ROOT / "configs/roi_w6.yaml", ROOT / "configs/alert_e1.yaml")
    ev7 = make_evidence(tmp_path, "ev7", nms=0.7)
    with pytest.raises(SystemExit, match="can --reason"):
        bb.build(ev7, bundle, "run07", "e" * 40, *cfg, append=True)
    c = e1store.connect(bundle / "events.sqlite")
    assert [r["run_id"] for r in e1store.list_runs(c)] == ["runX"]          # tu choi -> khong them run
    c.close()
    man = bb.build(ev7, bundle, "run07", "e" * 40, *cfg, append=True, actor="quang", reason="thu NMS 0,7")
    with pytest.raises(SystemExit, match="da co trong bundle"):
        bb.build(ev7, bundle, "run07", "e" * 40, *cfg, append=True, reason="x")
    c = e1store.connect(bundle / "events.sqlite")
    au = e1store.list_config_audit(c)
    assert [(a["target"], a["old_run_id"], a["new_run_id"], a["actor_id"]) for a in au] == [("detector", "runX", "run07", "quang")]
    assert au[0]["old_sha256"] != au[0]["new_sha256"] and man["runs"]["run07"]["config_changed_vs"] == "runX"
    assert set(man["runs"]) == {"runX", "run07"} and bb.verify(bundle) == []
    assert [e["source_id"] for e in e1store.list_events(c, "run07")] == ["V_DRONE_001"]
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        c.execute("DELETE FROM config_audit")
    c.rollback()
    same = make_evidence(tmp_path, "ev7b", nms=0.7)
    bb.build(same, bundle, "run07b", "e" * 40, *cfg, append=True)          # cung cau hinh run truoc -> khong can ly do, khong ghi
    assert len(e1store.list_config_audit(c)) == 1


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
    h = cl.get("/health").json()
    assert h["mode"] == "replay" and h["runs"]["runX"]["sources"] == 2
    assert cl.get("/config_audit").json() == []
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



def _serve(bundle):
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
    return server, th, port


def test_dashboard_renders_bundle_text_without_html_injection(bundle):
    """Review An (PR #124) muc 2: gia tri tu bundle hien dang chu, khong thanh HTML/script."""
    pw = pytest.importorskip("playwright.sync_api")
    evil = '<img src=x onerror="window.__xss=1">'
    c = e1store.connect(bundle / "events.sqlite")
    with c:
        e1store.add_event(c, "runX:V_DRONE_001:9", "runX", "V_DRONE_001", "R1", "center_hex", evil, 1, 2, FPS, [1])
    c.close()
    server, th, port = _serve(bundle)
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#source option", state="attached")
            pg.select_option("#source", "V_DRONE_001")
            pg.wait_for_selector('.ev[data-event-id="runX:V_DRONE_001:9"]')
            assert pg.locator("#events img").count() == 0
            assert pg.locator('.ev[data-event-id="runX:V_DRONE_001:9"] b').inner_text() == evil
            pg.wait_for_timeout(300)
            assert pg.evaluate("window.__xss") is None
            b.close()
    finally:
        server.should_exit = True; th.join(timeout=5)


def test_dashboard_pauses_video_when_stream_stalls(tmp_path):
    """Review An (PR #124) muc 3: WebSocket ngung giua chung -> 'qua han', video dung; frame den lai -> phat tiep."""
    pw = pytest.importorskip("playwright.sync_api")
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        pytest.skip("can ffmpeg de tao video thu")
    ev = make_evidence(tmp_path, "evs", drone_frames=90)
    media = tmp_path / "m"; media.mkdir()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size={W}x{H}:rate=30:duration=3",
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(media / "V_DRONE_001.mp4")], check=True)
    out = tmp_path / "b"
    bb.build(ev, out, "runS", "d" * 40, ROOT / "configs/roi_w6.yaml", ROOT / "configs/alert_e1.yaml", media_dir=media)
    server, th, port = _serve(out)
    gate = {"open": True, "sent": 0}
    def route(ws):
        srv = ws.connect_to_server()
        def from_server(m):
            if gate["open"]:
                gate["sent"] += 1; ws.send(m)
        srv.on_message(from_server)
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page()
            pg.route_web_socket("**/ws/stream*", route)
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#source option", state="attached")
            pg.select_option("#source", "V_DRONE_001")
            pg.wait_for_function("document.getElementById('video').readyState >= 2", timeout=10000)
            pg.click("#play")
            pg.wait_for_function("document.getElementById('conn').dataset.state === 'playing'", timeout=10000)
            pg.wait_for_function("!document.getElementById('video').paused && document.getElementById('video').currentTime > 0.2", timeout=10000)
            gate["open"] = False                                  # luong bi ngat giua chung
            pg.wait_for_function("document.getElementById('conn').dataset.state === 'stale'", timeout=5000)
            assert pg.evaluate("document.getElementById('video').paused")
            t_stale = pg.evaluate("document.getElementById('video').currentTime")
            pg.wait_for_timeout(700)
            assert pg.evaluate("document.getElementById('video').currentTime") == t_stale       # hinh khong chay tiep
            gate["open"] = True                                   # frame den lai
            pg.wait_for_function("document.getElementById('conn').dataset.state === 'playing' || document.getElementById('conn').dataset.state === 'eos'", timeout=5000)
            assert gate["sent"] > 0
            b.close()
    finally:
        server.should_exit = True; th.join(timeout=5)


def test_e2e_fixture_cases_pass(tmp_path, monkeypatch):
    """Kich ban E2E cua An (#118) tren fixture tong hop: E2E-01..07, 09 chay tu dong tren dashboard that."""
    pytest.importorskip("playwright.sync_api")
    import shutil
    if not shutil.which("ffmpeg"):
        pytest.skip("can ffmpeg")
    import e2e_fixtures as ef
    monkeypatch.setattr(sys, "argv", ["x", "--out", str(tmp_path), "--commit", "test"])
    assert ef.main() == 0
    res = json.loads((tmp_path / "e2e_fixture_results.json").read_text(encoding="utf-8"))
    assert res["summary"]["pass"] == ["E2E-01", "E2E-02", "E2E-03", "E2E-04", "E2E-05", "E2E-06", "E2E-07", "E2E-09"]
    saved = json.loads((ROOT / "results/W08/e2e/e2e_fixture_results.json").read_text(encoding="utf-8"))
    assert res["fixture_bundle_sha256"]["files"].keys() == saved["fixture_bundle_sha256"]["files"].keys()
