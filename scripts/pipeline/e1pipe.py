#!/usr/bin/env python3
"""e1pipe: pipeline dau-cuoi chay TUNG FRAME (W9-01, #129; docs/w9/W9_PLAN.md muc B; ADR-0015 che do truc tiep).

    decode (cv2) -> detect (Ultralytics predict, NMS cung lop IoU 0,5) -> track (BYTETracker, ByteTrack-e1)
    -> alert (R1Engine, truc tuyen) -> persist (FrameResult JSONL + su kien da chot vao SQLite)

Do tre (perf_counter, ms), hai noi ghi, hai pham vi (review cua An tren PR #136):
- latency_out (latency.csv cua benchmark, dung cho luat C va NFR1): persist va total tinh SAU khi ghi xong dong FrameResult,
  dung dinh nghia W9_PLAN muc B ("tu truoc luc doc frame toi sau luc ghi xong").
- stage_latency_ms trong chinh FrameResult: persist va total chi tinh toi khi ban ghi duoc serialize (mot dong khong the
  chua thoi gian ghi chinh no); dong co "latency_scope": "pre_write". Chenh lech = lenh ghi mot dong vao bo dem gzip.
Chuyen trang thai "close" o cuoi video: neu biet truoc so frame, R1 duoc chot ngay o frame cuoi va "close" nam trong
FrameResult cuoi; neu video het som hon (hoac khong biet truoc), them mot dong {"type": "eos", ...} chua cac "close". Su kien chi ghi vao kho bat bien khi da dong va het cua so mo lai
(R1Engine.finalized), nen kho khong bao gio phai sua ban ghi.

Thiet ke de kiem thu: detector la mot ham frame -> mang [x1, y1, x2, y2, conf, cls]; pytest dung detector gia va video
tong hop, khong can GPU hay du lieu that. Tren Kaggle dung UltralyticsDetector.
"""
from __future__ import annotations

import csv
import gzip
import json
import time
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
import sys  # noqa: E402

for _p in (ROOT / "scripts" / "alert", Path(__file__).resolve().parent):
    sys.path.insert(0, str(_p))
import alert_engine as ae  # noqa: E402
import e1store  # noqa: E402

CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]
STAGES = ("decode", "detect", "track", "alert", "persist")
TRACK_FIELDS = ["frame", "id", "cls", "conf", "x", "y", "w", "h"]


class UltralyticsDetector:
    """predict tren mot frame BGR. quantize: None (fp32) hoac 16 (fp16). weights co the la .pt hoac .engine (TensorRT)."""

    def __init__(self, weights: str, conf: float = 0.1, iou: float = 0.5, imgsz: int = 640, device: str = "0", quantize=None):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.kw = dict(conf=conf, iou=iou, imgsz=imgsz, device=device, verbose=False)
        if quantize:
            self.kw["quantize"] = quantize

    def __call__(self, frame) -> np.ndarray:
        r = self.model.predict(frame, **self.kw)[0]
        b = r.boxes.cpu().numpy()
        return np.concatenate([b.xyxy, b.conf[:, None], b.cls[:, None]], axis=1).astype(np.float32) if len(b) else np.zeros((0, 6), np.float32)


def make_tracker(cfg):
    from ultralytics.trackers.byte_tracker import BYTETracker
    return BYTETracker(args=cfg)


def track_step(tracker, det: np.ndarray, w: int, h: int) -> list[dict]:
    """Giong offline_track.track_video va model.track cua Ultralytics: cap hop vao khung anh, lam tron nhu run 14/17."""
    from ultralytics.engine.results import Boxes
    out = tracker.update(Boxes(det.reshape(-1, 6), (h, w)))
    rows = []
    for x1, y1, x2, y2, tid, score, cls, _ in out:
        x1, x2 = min(max(x1, 0.0), w), min(max(x2, 0.0), w)
        y1, y2 = min(max(y1, 0.0), h), min(max(y2, 0.0), h)
        rows.append({"id": int(tid), "cls": int(cls), "conf": round(float(score), 4),
                     "x": round(float(x1), 2), "y": round(float(y1), 2), "w": round(float(x2 - x1), 2), "h": round(float(y2 - y1), 2)})
    return rows


def read_frames(path: Path) -> Iterable:
    import cv2
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"khong mo duoc {path}")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                return
            yield frame
    finally:
        cap.release()


class Sink:
    """Noi ghi ket qua cua mot run: FrameResult JSONL.gz theo nguon, kho su kien SQLite, track/det CSV de danh gia."""

    def __init__(self, out: Path, run_id: str, commit: str, model_version: str, config: dict, device: str, evidence: str,
                 save_csv: bool = True):
        import hashlib
        self.out, self.run_id, self.model_version, self.save_csv = out, run_id, model_version, save_csv
        (out / "frames" / run_id).mkdir(parents=True, exist_ok=True)
        if save_csv:
            (out / "tracks" / "tracker_bytetrack_e1").mkdir(parents=True, exist_ok=True)
            (out / "dets").mkdir(parents=True, exist_ok=True)
        self.db = e1store.connect(out / "events.sqlite"); e1store.init(self.db)
        sha = hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.db:
            e1store.add_run(self.db, run_id, commit, model_version, config, sha, device, evidence)

    def open_source(self, source_id: str, class_name: str, fps: float, w: int, h: int, n_frames: int):
        with self.db:
            e1store.add_source(self.db, self.run_id, source_id, class_name, fps, w, h, max(1, n_frames))
        self.fh = gzip.open(self.out / "frames" / self.run_id / f"{source_id}.jsonl.gz", "wt", encoding="utf-8")
        self.tracks, self.dets = [], []

    def write_line(self, line: str) -> None:
        self.fh.write(line + "\n")

    def event(self, source_id: str, idx: int, ev: dict, fps: float, roi: str) -> None:
        with self.db:
            e1store.add_event(self.db, f"{self.run_id}:{source_id}:{idx}", self.run_id, source_id, "R1", roi, ev["kind"],
                              ev["start"], ev["end"], fps, ev["tracks"])

    def close_source(self, source_id: str) -> None:
        self.fh.close()
        if self.save_csv:
            for sub, rows, fields in (("tracks/tracker_bytetrack_e1", self.tracks, TRACK_FIELDS), ("dets", self.dets, ["frame", "cls", "conf", "x", "y", "w", "h"])):
                with (self.out / sub / f"{source_id}.csv").open("w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)

    def close(self) -> None:
        self.db.close()


def run_source(frames: Iterable, source_id: str, class_name: str, fps: float, w: int, h: int, n_frames: int,
               detector: Callable, tracker, sink: Sink, poly, alert_cfg: dict, roi_name: str,
               model_version: str, clock=time.perf_counter, latency_out: list | None = None) -> dict:
    """Xu ly mot nguon video tung frame. Tra ve tom tat: so frame, so su kien, thoi gian tuong."""
    eng = ae.R1Engine(fps, poly, w, h, alert_cfg)
    sink.open_source(source_id, class_name, fps, w, h, n_frames)
    written: set[int] = set()
    it = iter(frames)
    f, t_start = 0, clock()
    while True:
        t0 = clock()
        frame = next(it, None)
        if frame is None:
            break
        t1 = clock()
        det = detector(frame)
        t2 = clock()
        rows = track_step(tracker, det, w, h)
        t3 = clock()
        trans = eng.step(f, rows)
        if n_frames and f == n_frames - 1:       # frame cuoi da biet truoc: chot moi canh bao ngay trong FrameResult cuoi
            trans += eng.close()
        t4 = clock()
        rec = {"run_id": sink.run_id, "source_id": source_id, "model_version": model_version, "frame_index": f,
               "source_time_ms": e1store.frame_ms(f, fps),
               "tracks": [{"id": r["id"], "cls": r["cls"], "cls_name": CLASSES[r["cls"]], "conf": r["conf"],
                           "box": [r["x"], r["y"], round(r["x"] + r["w"], 2), round(r["y"] + r["h"], 2)]} for r in rows],
               "events": [{"event_id": f"{sink.run_id}:{source_id}:{t['event']}", "transition": t["transition"]} for t in trans]}
        for idx in eng.finalized(f):
            if idx not in written:
                sink.event(source_id, idx, eng.event(idx), fps, roi_name); written.add(idx)
        if sink.save_csv:
            sink.tracks.extend({"frame": f, **r} for r in rows)
            sink.dets.extend({"frame": f, "cls": int(c), "conf": round(float(s), 4), "x": round(float(x1), 2), "y": round(float(y1), 2),
                              "w": round(float(x2 - x1), 2), "h": round(float(y2 - y1), 2)} for x1, y1, x2, y2, s, c in det)
        body = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        t5 = clock()
        lat = {"decode": t1 - t0, "detect": t2 - t1, "track": t3 - t2, "alert": t4 - t3, "persist": t5 - t4, "total": t5 - t0}
        rec["stage_latency_ms"] = {k: round(1000 * v, 3) for k, v in lat.items()}
        sink.write_line(body[:-1] + ',"stage_latency_ms":' + json.dumps(rec["stage_latency_ms"], separators=(",", ":"))
                        + ',"latency_scope":"pre_write"}')
        t6 = clock()
        if latency_out is not None:              # so do benchmark (W9_PLAN muc B, C): persist va total tinh SAU khi ghi xong dong
            ms = {k: round(1000 * v, 3) for k, v in lat.items()}
            ms["persist"] = round(1000 * (t6 - t4), 3); ms["total"] = round(1000 * (t6 - t0), 3)
            latency_out.append((source_id, f, *(ms[k] for k in (*STAGES, "total"))))
        f += 1
    trans = eng.close()
    if trans:                                    # het video som hon so frame ky vong (hoac khong biet truoc): ban ghi ket thuc
        sink.write_line(json.dumps({"type": "eos", "run_id": sink.run_id, "source_id": source_id, "frame_index": f,
                                    "events": [{"event_id": f"{sink.run_id}:{source_id}:{t['event']}", "transition": t["transition"]}
                                               for t in trans]}, ensure_ascii=False, separators=(",", ":")))
    for idx in range(len(eng.alerts)):
        if idx not in written:
            sink.event(source_id, idx, eng.event(idx), fps, roi_name)
    sink.close_source(source_id)
    return {"source_id": source_id, "frames": f, "frames_expected": n_frames, "events": len(eng.alerts),
            "closed_at_end": len(trans), "seconds": round(clock() - t_start, 4)}


def match_tracks(a: list[dict], b: list[dict], tol: float = 0.05) -> tuple[int, int]:
    """So dong cua a co dong cung (frame, id, cls) trong b voi moi toa do lech <= tol. Tra ve (khop, tong a)."""
    idx = {(int(r["frame"]), int(r["id"]), int(r["cls"])): r for r in b}
    hit = 0
    for r in a:
        q = idx.get((int(r["frame"]), int(r["id"]), int(r["cls"])))
        if q is not None and all(abs(float(r[k]) - float(q[k])) <= tol + 1e-9 for k in "xywh"):
            hit += 1
    return hit, len(a)
