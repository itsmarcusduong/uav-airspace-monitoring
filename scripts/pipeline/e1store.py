#!/usr/bin/env python3
"""Kho su kien SQLite cua MVP (ADR-0015 muc 2). Khong I/O mang; chi sqlite3 cua thu vien chuan.

Quy tac (ADR-0015, review cua An tren PR #121):
  - `events` la ban ghi bat bien do pipeline sinh, KHONG co cot trang thai;
  - `event_reviews`, `config_audit` chi them;
  - trigger chan moi UPDATE/DELETE tren ba bang tren o muc CSDL (khong chi dua vao code API);
  - trang thai hien tai = action cua review co review_id lon nhat, 'new' khi chua co review (view `event_status`);
  - reviewer_id o W8 la dinh danh cuc bo, CHUA xac thuc.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ACTIONS = ("confirmed", "false_alarm")
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    commit_sha TEXT NOT NULL,
    model_version TEXT NOT NULL,           -- SHA-256 cua weights
    config_json TEXT NOT NULL,             -- ROI + luat canh bao + tracker da dung (JSON)
    config_sha256 TEXT NOT NULL,
    device TEXT NOT NULL,
    source_evidence TEXT NOT NULL,         -- vd. kaggle run 17 (w8_run17)
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    source_id TEXT NOT NULL,
    class_name TEXT NOT NULL,
    media_path TEXT,                       -- duong dan tuong doi trong bundle, NULL neu khong co video
    media_sha256 TEXT,
    fps REAL NOT NULL CHECK (fps > 0),
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    frame_count INTEGER NOT NULL CHECK (frame_count > 0),
    PRIMARY KEY (run_id, source_id)
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    roi TEXT NOT NULL,
    kind TEXT NOT NULL,
    start_frame INTEGER NOT NULL,
    end_frame INTEGER NOT NULL CHECK (end_frame >= start_frame),
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    track_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id, source_id) REFERENCES sources(run_id, source_id)
);
CREATE TABLE IF NOT EXISTS event_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    reviewer_id TEXT NOT NULL CHECK (length(trim(reviewer_id)) > 0),
    action TEXT NOT NULL CHECK (action IN ('confirmed', 'false_alarm')),
    created_at TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS config_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    target TEXT NOT NULL,                  -- roi | alert | tracker | weights
    old_sha256 TEXT,
    new_sha256 TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE VIEW IF NOT EXISTS event_status AS
SELECT e.*,
       COALESCE((SELECT r.action FROM event_reviews r WHERE r.event_id = e.event_id ORDER BY r.review_id DESC LIMIT 1), 'new') AS status,
       (SELECT COUNT(*) FROM event_reviews r WHERE r.event_id = e.event_id) AS n_reviews
FROM events e;
"""
_GUARDED = ("events", "event_reviews", "config_audit")
TRIGGERS = "\n".join(
    f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
    f"BEGIN SELECT RAISE(ABORT, '{t} chi them (append-only), khong {op}'); END;"
    for t in _GUARDED for op in ("UPDATE", "DELETE"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def connect(path: Path | str) -> sqlite3.Connection:
    c = sqlite3.connect(str(path), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init(c: sqlite3.Connection) -> None:
    c.executescript(SCHEMA + TRIGGERS)
    c.commit()


def add_run(c, run_id, commit_sha, model_version, config: dict, config_sha256, device, source_evidence) -> None:
    c.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
              (run_id, commit_sha, model_version, json.dumps(config, ensure_ascii=False, sort_keys=True), config_sha256,
               device, source_evidence, now()))


def add_source(c, run_id, source_id, class_name, fps, width, height, frame_count, media_path=None, media_sha256=None) -> None:
    c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?)",
              (run_id, source_id, class_name, media_path, media_sha256, fps, width, height, frame_count))


def add_event(c, event_id, run_id, source_id, rule, roi, kind, start_frame, end_frame, fps, track_ids) -> None:
    c.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (event_id, run_id, source_id, rule, roi, kind, int(start_frame), int(end_frame),
               frame_ms(start_frame, fps), frame_ms(end_frame, fps), json.dumps(sorted(int(t) for t in track_ids)), now()))


def add_review(c, event_id: str, reviewer_id: str, action: str, note: str = "") -> int:
    if action not in ACTIONS:
        raise ValueError(f"action phai thuoc {ACTIONS}")
    if not reviewer_id or not reviewer_id.strip():
        raise ValueError("reviewer_id rong")
    if c.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,)).fetchone() is None:
        raise KeyError(event_id)
    with c:
        cur = c.execute("INSERT INTO event_reviews (event_id, reviewer_id, action, created_at, note) VALUES (?,?,?,?,?)",
                        (event_id, reviewer_id.strip(), action, now(), note or ""))
    return int(cur.lastrowid)


def frame_ms(frame: int, fps: float) -> int:
    return int(round(int(frame) * 1000.0 / float(fps)))


def rows(c, sql, args=()) -> list[dict]:
    return [dict(r) for r in c.execute(sql, args).fetchall()]


def list_runs(c) -> list[dict]:
    out = rows(c, "SELECT run_id, commit_sha, model_version, config_sha256, config_json, device, source_evidence, created_at FROM runs ORDER BY run_id")
    for r in out:
        r["config"] = json.loads(r.pop("config_json"))
    return out


def list_sources(c, run_id: str) -> list[dict]:
    out = rows(c, "SELECT * FROM sources WHERE run_id = ? ORDER BY source_id", (run_id,))
    for r in out:
        r["has_media"] = bool(r.pop("media_path"))
        r["duration_s"] = round(r["frame_count"] / r["fps"], 3)
    return out


def list_events(c, run_id: str, source_id: str | None = None) -> list[dict]:
    q, a = "SELECT * FROM event_status WHERE run_id = ?", [run_id]
    if source_id:
        q += " AND source_id = ?"; a.append(source_id)
    out = rows(c, q + " ORDER BY source_id, start_frame", a)
    for r in out:
        r["track_ids"] = json.loads(r.pop("track_ids_json"))
    return out


def get_event(c, event_id: str) -> dict | None:
    r = rows(c, "SELECT * FROM event_status WHERE event_id = ?", (event_id,))
    if not r:
        return None
    e = r[0]; e["track_ids"] = json.loads(e.pop("track_ids_json"))
    e["reviews"] = rows(c, "SELECT review_id, reviewer_id, action, created_at, note FROM event_reviews WHERE event_id = ? ORDER BY review_id", (event_id,))
    return e
