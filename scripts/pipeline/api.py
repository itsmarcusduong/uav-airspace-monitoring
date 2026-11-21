#!/usr/bin/env python3
"""API FastAPI + WebSocket va dashboard phat lai (ADR-0015 muc 3-6). Khong suy luan, khong giai ma video.

    python scripts/pipeline/api.py --bundle bundles/run17            # http://127.0.0.1:8000/
    python scripts/pipeline/api.py --bundle bundles/run17 --openapi docs/w8/openapi_w8.json   # chi ghi OpenAPI

- Chi nghe 127.0.0.1 (ranh gioi tin cay ADR-0015 muc 6).
- Media chi theo (run_id, source_id) co trong bundle; khong nhan duong dan/URL tu client.
- POST review chi INSERT (trigger SQLite chan UPDATE/DELETE); reviewer_id la dinh danh cuc bo, CHUA xac thuc.
- WebSocket phat FrameResult theo thoi gian nguon: cho den source_time_ms / speed truoc khi gui frame tiep theo.
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e1store  # noqa: E402

LOG = logging.getLogger("e1api")
STATIC = Path(__file__).resolve().parent / "static"
API_VERSION = "w8-0.1"


class ReviewIn(BaseModel):
    action: str = Field(pattern="^(confirmed|false_alarm)$")
    reviewer_id: str = Field(min_length=1, max_length=64, description="dinh danh cuc bo, chua xac thuc (W8)")
    note: str = Field(default="", max_length=500)


def read_frames(bundle: Path, source_id: str) -> list[dict]:
    p = bundle / "frames" / f"{source_id}.jsonl.gz"
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        out = [json.loads(line) for line in fh if line.strip()]
    for a, b in zip(out, out[1:]):
        if not (b["frame_index"] > a["frame_index"] and b["source_time_ms"] >= a["source_time_ms"]):
            raise ValueError(f"{p}: FrameResult khong tang don dieu o frame {b['frame_index']}")
    return out


def create_app(bundle: Path) -> FastAPI:
    bundle = bundle.resolve()
    if not (bundle / "events.sqlite").is_file() or not (bundle / "bundle.json").is_file():
        raise FileNotFoundError(f"{bundle}: khong phai bundle (thieu events.sqlite/bundle.json)")
    manifest = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
    db = e1store.connect(bundle / "events.sqlite")
    app = FastAPI(title="E1 UAV airspace monitoring — replay API", version=API_VERSION,
                  description="Phat lai ket qua pipeline sinh tren Kaggle (ADR-0015). reviewer_id chua xac thuc.")

    def source_or_404(run_id: str, source_id: str) -> dict:
        s = [x for x in e1store.list_sources(db, run_id) if x["source_id"] == source_id]
        if not s:
            raise HTTPException(404, f"khong co nguon {run_id}/{source_id}")
        return s[0]

    @app.get("/health")
    def health():
        return {"status": "ok", "api_version": API_VERSION, "bundle_run": manifest["run_id"], "model_version": manifest["model_version"],
                "sources": len(manifest["sources"]), "mode": "replay"}

    @app.get("/runs")
    def runs():
        return e1store.list_runs(db)

    @app.get("/sources")
    def sources(run_id: str):
        if not any(r["run_id"] == run_id for r in e1store.list_runs(db)):
            raise HTTPException(404, f"khong co run {run_id}")
        return e1store.list_sources(db, run_id)

    @app.get("/events")
    def events(run_id: str, source_id: str | None = None):
        return e1store.list_events(db, run_id, source_id)

    @app.get("/events/{event_id}")
    def event(event_id: str):
        e = e1store.get_event(db, event_id)
        if e is None:
            raise HTTPException(404, f"khong co su kien {event_id}")
        return e

    @app.post("/events/{event_id}/review", status_code=201)
    def review(event_id: str, body: ReviewIn):
        try:
            rid = e1store.add_review(db, event_id, body.reviewer_id, body.action, body.note)
        except KeyError:
            raise HTTPException(404, f"khong co su kien {event_id}")
        except ValueError as ex:
            raise HTTPException(422, str(ex))
        LOG.info("review %s %s %s by %s (chua xac thuc)", rid, event_id, body.action, body.reviewer_id)
        return {"review_id": rid, **e1store.get_event(db, event_id)}

    @app.get("/media/{run_id}/{source_id}")
    def media(run_id: str, source_id: str):
        source_or_404(run_id, source_id)
        row = db.execute("SELECT media_path FROM sources WHERE run_id = ? AND source_id = ?", (run_id, source_id)).fetchone()
        if not row or not row["media_path"]:
            raise HTTPException(404, "nguon nay khong co video trong bundle")
        p = (bundle / row["media_path"]).resolve()
        if bundle not in p.parents or not p.is_file():
            raise HTTPException(404, "duong dan media khong hop le")
        return FileResponse(p, media_type="video/mp4")

    @app.websocket("/ws/stream")
    async def stream(ws: WebSocket, run_id: str = Query(...), source_id: str = Query(...),
                     speed: float = Query(1.0, gt=0, le=16), start_frame: int = Query(0, ge=0)):
        await ws.accept()
        try:
            source_or_404(run_id, source_id)
            frames = [f for f in read_frames(bundle, source_id) if f["frame_index"] >= start_frame]
        except (HTTPException, FileNotFoundError, ValueError) as ex:
            await ws.send_json({"type": "error", "detail": getattr(ex, "detail", str(ex))}); await ws.close(); return
        t0, base = time.monotonic(), (frames[0]["source_time_ms"] if frames else 0)
        try:
            for fr in frames:
                due = (fr["source_time_ms"] - base) / 1000.0 / speed
                wait = due - (time.monotonic() - t0)
                if wait > 0:
                    await asyncio.sleep(wait)
                await ws.send_json({"type": "frame", **fr})
            await ws.send_json({"type": "eos", "frames": len(frames)})
            await ws.close()
        except WebSocketDisconnect:
            LOG.info("client ngat %s/%s", run_id, source_id)

    app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="dashboard")
    return app


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--openapi", type=Path, help="chi ghi OpenAPI JSON ra tep roi thoat")
    ap.add_argument("--log", type=Path, help="ghi nhat ky API ra tep (mac dinh: stderr)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        filename=str(a.log) if a.log else None)
    app = create_app(a.bundle)
    if a.openapi:
        a.openapi.parent.mkdir(parents=True, exist_ok=True)
        a.openapi.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return 0
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=a.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
