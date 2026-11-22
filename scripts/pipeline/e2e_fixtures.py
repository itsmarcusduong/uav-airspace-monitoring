#!/usr/bin/env python3
"""Fixture tong hop cho kich ban E2E W8 (docs/w8/e2e_test_cases.md, #118) va chay tu dong tren dashboard.

Kich ban do An viet va chot truoc (PR #122, #126). Cac ca E2E-01..07 va E2E-09 can fixture tong hop; W8 chi chay
tay E2E-02, 03, 05, 06, 09, 13 tren du lieu that (run 17). Script nay:
  1. tao bang chung tracking gia (track log), dung bundle bang CHINH build_bundle.py (alert R1 that);
  2. phat tung nguon tren dashboard that (Chromium headless, Playwright), ghi lai nhung gi dashboard hien thi;
  3. so voi tieu chi cua tung ca va voi JSONL/SQLite cua bundle; ghi PASS/FAIL kem so lieu.

    python scripts/pipeline/e2e_fixtures.py --out results/W08/e2e --commit <sha>

Khong dung video du lieu; video cua fixture la mau thu tong hop cua ffmpeg (testsrc).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_bundle as bb  # noqa: E402
import e1store  # noqa: E402

LOG = logging.getLogger("e2e_fixtures")
FPS, W, H = 30.0, 640, 512
DRONE, BIRD, AIRPLANE = 2, 1, 0
TF = ["frame", "id", "cls", "conf", "x", "y", "w", "h"]


def box(frame, tid, cls, cx, cy, w=20.0, h=20.0, conf=0.8):
    """Hop theo tam chuan hoa (cx, cy) tren khung W x H."""
    return {"frame": frame, "id": tid, "cls": cls, "conf": conf, "x": round(cx * W - w / 2, 2), "y": round(cy * H - h / 2, 2), "w": w, "h": h}


def fixtures() -> dict[str, dict]:
    """source_id -> {class_name, frames, tracks}. Thong so dat truoc theo docs/w8/e2e_test_cases.md."""
    fx = {}
    # E2E-01: mot track Drone di ngang tu ngoai trai vao center_hex, o lai, roi ra ngoai phai va o ngoai.
    fx["FX01_roi_enter_exit"] = {"class_name": "Drone", "frames": 240,
                                 "tracks": [box(f, 1, DRONE, 0.02 + 0.96 * f / 179, 0.5) for f in range(180)] +
                                           [box(f, 1, DRONE, 0.98, 0.5) for f in range(180, 240)]}
    fx["FX02_bird_in_roi"] = {"class_name": "Bird", "frames": 120, "tracks": [box(f, 1, BIRD, 0.5, 0.5) for f in range(120)]}
    fx["FX03_airplane_in_roi"] = {"class_name": "Airplane", "frames": 120,
                                  "tracks": [box(f, 1, AIRPLANE, 0.3 + 0.4 * f / 119, 0.5, 60, 24) for f in range(120)]}
    # E2E-04: hop Drone 6x6 px; JSONL KHONG co event vi track chi o ngoai ROI (goc trai tren), ROI chi de doi chieu.
    fx["FX04_tiny_drone"] = {"class_name": "Drone", "frames": 90,
                             "tracks": [box(f, 1, DRONE, 0.05 + 0.001 * f, 0.05, 6, 6) for f in range(90)]}
    # E2E-05: Drone trong ROI frame 0-59, khoang che 60-89 KHONG co record, xuat hien lai 90-149 cung ID.
    fx["FX05_occlusion_gap"] = {"class_name": "Drone", "frames": 150,
                                "tracks": [box(f, 1, DRONE, 0.5, 0.5) for f in list(range(60)) + list(range(90, 150))]}
    # E2E-06: Drone ID 1 va Bird ID 2 cung frame, ca hai trong ROI.
    fx["FX06_two_tracks"] = {"class_name": "Drone", "frames": 120,
                             "tracks": [box(f, 1, DRONE, 0.4, 0.5) for f in range(120)] + [box(f, 2, BIRD, 0.6, 0.5) for f in range(120)]}
    # E2E-07: tam (0.5, 0.09) / (0.5, 0.10) / (0.5, 0.11), moi vi tri mot ID, 60 frame, cach nhau 90 frame khong co track.
    seg = []
    for k, (tid, cy) in enumerate(((1, 0.09), (2, 0.10), (3, 0.11))):
        s = k * 150
        seg += [box(f, tid, DRONE, 0.5, cy) for f in range(s, s + 60)]
    fx["FX07_roi_boundary"] = {"class_name": "Drone", "frames": 420, "tracks": seg}
    # E2E-09: video ngan 45 frame, record cuoi o frame 44.
    fx["FX09_short_eof"] = {"class_name": "Drone", "frames": 45, "tracks": [box(f, 1, DRONE, 0.5, 0.5) for f in range(45)]}
    return fx


def write_evidence(root: Path, fx: dict) -> Path:
    ev = root / "e2e_fixture_evidence"
    (ev / "tracks/tracker_bytetrack_e1").mkdir(parents=True)
    (ev / "stage_status.json").write_text(json.dumps({k: {"status": "OK"} for k in ("env", "inputs", "track", "detect", "dump")}))
    (ev / "inputs.json").write_text(json.dumps({"split": "val", "test_used": False, "weights_sha256": "f1" * 32, "commit": "fixture",
                                                "trackers": {"tracker_bytetrack_e1": {"note": "fixture tong hop"}},
                                                "detector": {"note": "fixture tong hop, khong co detector"}}))
    with (ev / "meta.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["video_id", "class_name", "frames", "fps", "width", "height"])
        for sid, f in fx.items():
            w.writerow([sid, f["class_name"], f["frames"], FPS, W, H])
    for sid, f in fx.items():
        with (ev / "tracks/tracker_bytetrack_e1" / f"{sid}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=TF); w.writeheader(); w.writerows(sorted(f["tracks"], key=lambda r: (r["frame"], r["id"])))
        for sub, cols in (("gt", ["frame", "x", "y", "w", "h"]), ("dets", ["frame", "cls", "conf", "x", "y", "w", "h"])):
            (ev / sub).mkdir(exist_ok=True)
            (ev / sub / f"{sid}.csv").write_text(",".join(cols) + "\n", encoding="utf-8")
    return ev


def make_media(fx: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for sid, f in fx.items():
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        f"testsrc=size={W}x{H}:rate={int(FPS)}:duration={f['frames'] / FPS:.4f}", "-frames:v", str(f["frames"]),
                        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-bitexact", "-movflags", "+faststart",
                        str(out / f"{sid}.mp4")], check=True)


# ----------------------------------------------------------------------------- dashboard
OBSERVER = """
window.__log = [];
document.addEventListener('DOMContentLoaded', () => {
  const rec = () => {
    const fr = document.getElementById('frame').textContent;
    if (fr === '–') return;
    window.__log.push({frame: Number(fr), ntracks: Number(document.getElementById('ntracks').textContent),
      active: document.querySelectorAll('.ev.active').length, conn: document.getElementById('conn').dataset.state});
  };
  new MutationObserver(rec).observe(document.getElementById('frame'), {childList: true, characterData: true, subtree: true});
});
"""


def serve(bundle: Path):
    import api
    import uvicorn
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = uvicorn.Server(uvicorn.Config(api.create_app(bundle), host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True); th.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    return server, th, port


def play(pg, port: int, sid: str, speed: int = 4) -> dict:
    pg.goto(f"http://127.0.0.1:{port}/")
    pg.wait_for_selector("#source option", state="attached")
    pg.select_option("#source", sid); pg.select_option("#speed", str(speed))
    pg.wait_for_function(f"document.querySelector('#source').value === '{sid}' && document.getElementById('overlay').width === {W}")
    pg.wait_for_timeout(300)
    pg.evaluate("window.__log = []")
    pg.click("#play")
    pg.wait_for_function("document.getElementById('conn').dataset.state === 'eos'", timeout=60000)
    eos_at = pg.evaluate("performance.now()")
    pg.wait_for_timeout(1500)                                         # cho them > 1 s sau EOS (E2E-09)
    cv = pg.evaluate("""(() => { const c = document.getElementById('overlay'), g = c.getContext('2d');
        const d = g.getImageData(0, 0, c.width, c.height).data; let red = 0;
        for (let i = 0; i < d.length; i += 4) if (d[i] > 180 && d[i+1] < 90 && d[i+2] < 90) red++; return red; })()""")
    return {"log": pg.evaluate("window.__log"), "conn": pg.inner_text("#conn"), "state": pg.evaluate("document.getElementById('conn').dataset.state"),
            "video_paused": pg.evaluate("document.getElementById('video').paused"),
            "events_ui": pg.evaluate("[...document.querySelectorAll('.ev')].map(e => e.dataset.eventId)"),
            "red_pixels_after_eos": cv, "eos_ms": eos_at}


def tiny_box_pixels(pg, port: int, sid: str, frame: int, jl: list[dict]) -> dict:
    """Dung phat o frame >= `frame` va doc mau canvas quanh hop 6x6 cua dung frame dang hien.
    Dat S.playing = false truoc khi dong WebSocket: dashboard xoa lop ve khi mat ket noi (hanh vi dung), nen phai
    tranh nhanh do de canvas giu frame cuoi."""
    pg.goto(f"http://127.0.0.1:{port}/")
    pg.wait_for_selector("#source option", state="attached")
    pg.select_option("#source", sid)
    pg.wait_for_function(f"document.getElementById('overlay').width === {W}")
    pg.click("#play")
    pg.wait_for_function(f"Number(document.getElementById('frame').textContent) >= {frame}", timeout=20000)
    pg.evaluate("S.playing = false; S.ws && S.ws.close()")
    pg.wait_for_timeout(200)
    shown = int(pg.inner_text("#frame"))
    x1, y1, x2, y2 = next(t["box"] for t in jl[shown]["tracks"])
    ym = round((y1 + y2) / 2)
    js = f"""(() => {{ const g = document.getElementById('overlay').getContext('2d');
        const px = (x, y) => Array.from(g.getImageData(x, y, 1, 1).data);
        return {{edge_left: px({round(x1)}, {ym}), edge_right: px({round(x2)}, {ym}),
                 outside_left: px({round(x1) - 3}, {ym}), outside_right: px({round(x2) + 3}, {ym})}}; }})()"""
    return {"frame_shown": shown, "box": [x1, y1, x2, y2], **pg.evaluate(js)}


def is_red(p) -> bool:
    return p[0] > 150 and p[1] < 110 and p[2] < 110 and p[3] > 0


def frames_jsonl(bundle: Path, run: str, sid: str) -> list[dict]:
    with gzip.open(bundle / "frames" / run / f"{sid}.jsonl.gz", "rt", encoding="utf-8") as fh:
        return [json.loads(x) for x in fh]


def evaluate(bundle: Path, run: str, fx: dict, obs: dict, tiny: dict) -> dict:
    c = e1store.connect(bundle / "events.sqlite")
    ev = {sid: e1store.list_events(c, run, sid) for sid in fx}
    c.close()
    jl = {sid: frames_jsonl(bundle, run, sid) for sid in fx}

    def shown_matches_jsonl(sid):
        """Moi frame dashboard hien (frame, so track, co su kien dang mo) khop JSONL/SQLite; frame tang don dieu."""
        want = {r["frame_index"]: len(r["tracks"]) for r in jl[sid]}
        act = {f: any(e["start_frame"] <= f <= e["end_frame"] for e in ev[sid]) for f in want}
        log = obs[sid]["log"]
        frames = [r["frame"] for r in log]
        bad = [r for r in log if want.get(r["frame"]) != r["ntracks"] or bool(r["active"]) != act[r["frame"]]]
        return {"frames_seen": len(set(frames)), "frames_total": len(want), "monotonic": frames == sorted(frames), "mismatch": len(bad)}

    res = {}
    m = shown_matches_jsonl("FX01_roi_enter_exit"); e = ev["FX01_roi_enter_exit"]
    res["E2E-01"] = {"source": "FX01_roi_enter_exit", "events": [(x["start_frame"], x["end_frame"]) for x in e], **m,
                     "pass": len(e) == 1 and m["mismatch"] == 0 and m["monotonic"] and obs["FX01_roi_enter_exit"]["state"] == "eos"}
    for case, sid in (("E2E-02", "FX02_bird_in_roi"), ("E2E-03", "FX03_airplane_in_roi")):
        m = shown_matches_jsonl(sid)
        cls = {t["cls_name"] for r in jl[sid] for t in r["tracks"]}
        res[case] = {"source": sid, "events": len(ev[sid]), "classes_in_jsonl": sorted(cls), **m,
                     "pass": not ev[sid] and not obs[sid]["events_ui"] and m["mismatch"] == 0 and "Drone" not in cls}
    m = shown_matches_jsonl("FX04_tiny_drone")
    edge = is_red(tiny["edge_left"]) and is_red(tiny["edge_right"])
    out = not is_red(tiny["outside_left"]) and not is_red(tiny["outside_right"])
    res["E2E-04"] = {"source": "FX04_tiny_drone", "events": len(ev["FX04_tiny_drone"]), "pixels": tiny, **m,
                     "pass": edge and out and not ev["FX04_tiny_drone"] and m["mismatch"] == 0}
    m = shown_matches_jsonl("FX05_occlusion_gap")
    gap = [r for r in obs["FX05_occlusion_gap"]["log"] if 60 <= r["frame"] < 90]
    e = ev["FX05_occlusion_gap"]
    res["E2E-05"] = {"source": "FX05_occlusion_gap", "gap_frames_seen": len(gap), "gap_frames_with_tracks": sum(1 for r in gap if r["ntracks"]),
                     "events": [(x["start_frame"], x["end_frame"]) for x in e], **m,
                     "pass": len(gap) > 0 and all(r["ntracks"] == 0 for r in gap) and m["mismatch"] == 0}
    m = shown_matches_jsonl("FX06_two_tracks"); e = ev["FX06_two_tracks"]
    ids_ok = all({t["id"]: t["cls_name"] for t in r["tracks"]} == {1: "Drone", 2: "Bird"} for r in jl["FX06_two_tracks"])
    res["E2E-06"] = {"source": "FX06_two_tracks", "events": [x["track_ids"] for x in e], "ids_stable_in_jsonl": ids_ok, **m,
                     "pass": [x["track_ids"] for x in e] == [[1]] and ids_ok and m["mismatch"] == 0}
    m = shown_matches_jsonl("FX07_roi_boundary"); e = ev["FX07_roi_boundary"]
    by_id = {tid: [x for x in e if tid in x["track_ids"]] for tid in (1, 2, 3)}
    res["E2E-07"] = {"source": "FX07_roi_boundary", "events_by_track": {str(k): [(x["start_frame"], x["end_frame"]) for x in v] for k, v in by_id.items()},
                     **m, "pass": len(e) == 2 and not by_id[1] and len(by_id[2]) == 1 and len(by_id[3]) == 1
                     and by_id[2][0] is not by_id[3][0] and m["mismatch"] == 0}
    o = obs["FX09_short_eof"]; m = shown_matches_jsonl("FX09_short_eof")
    after = [r for r in o["log"] if r["frame"] > 44]
    res["E2E-09"] = {"source": "FX09_short_eof", "state_after_1_5s": o["state"], "video_paused": o["video_paused"],
                     "red_pixels_after_eos": o["red_pixels_after_eos"], "records_after_last": len(after), **m,
                     "pass": o["state"] == "eos" and o["video_paused"] and o["red_pixels_after_eos"] == 0 and not after and m["mismatch"] == 0}
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--keep-bundle", type=Path, help="giu bundle fixture tai day (mac dinh: thu muc tam)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from playwright.sync_api import sync_playwright
    if not shutil.which("ffmpeg"):
        raise SystemExit("can ffmpeg de tao video mau tong hop")
    fx = fixtures()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ev = write_evidence(td, fx); make_media(fx, td / "media")
        bundle = a.keep_bundle or td / "bundle"
        bb.build(ev, bundle, "fixture_w8", a.commit, ROOT / "configs/roi_w6.yaml", ROOT / "configs/alert_e1.yaml", media_dir=td / "media")
        man = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
        tiny_f = 30
        server, th, port = serve(bundle)
        obs = {}
        try:
            with sync_playwright() as p:
                br = p.chromium.launch()
                ctx = br.new_context(viewport={"width": 1280, "height": 900}); ctx.add_init_script(OBSERVER)
                pg = ctx.new_page()
                for sid in fx:
                    obs[sid] = play(pg, port, sid)
                    LOG.info("%s: %d frame hien, trang thai %s", sid, len(obs[sid]["log"]), obs[sid]["state"])
                tiny = tiny_box_pixels(pg, port, "FX04_tiny_drone", tiny_f, frames_jsonl(bundle, "fixture_w8", "FX04_tiny_drone"))
                br.close()
        finally:
            server.should_exit = True; th.join(timeout=5)
        res = evaluate(bundle, "fixture_w8", fx, obs, tiny)
    a.out.mkdir(parents=True, exist_ok=True)
    out = {"protocol": "docs/w8/e2e_test_cases.md (An, PR #122, #126)", "commit": a.commit, "speed": 4,
           "fixture_bundle_sha256": {"bundle.json": hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest(),
                                     "files": {f["path"]: f["sha256"] for f in man["files"] if not f["path"].startswith("media/")}},
           "note": "fixture tong hop: kiem hop dong du lieu, luu tru, API, hien thi; khong do do chinh xac mo hinh",
           "results": res, "summary": {"pass": sorted(k for k, v in res.items() if v["pass"]),
                                       "fail": sorted(k for k, v in res.items() if not v["pass"])}}
    (a.out / "e2e_fixture_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("PASS %s | FAIL %s", out["summary"]["pass"], out["summary"]["fail"])
    return 0 if not out["summary"]["fail"] else 1


if __name__ == "__main__":
    sys.exit(main())
