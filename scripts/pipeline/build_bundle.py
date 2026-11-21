#!/usr/bin/env python3
"""Dung bundle phat lai (ADR-0015 muc 5) tu bang chung Kaggle cua mot run tracking (run 14, run 17).

Chi doc CSV/JSON (track log, meta) va video da ma hoa H.264 tren Kaggle (neu co); KHONG giai ma video, KHONG suy luan.
Cac buoc sau tracker cua pipeline chay o day, giong het pipeline lien tuc:
  track log -> AlertEngine R1 (ADR-0009, configs/alert_e1.yaml, ROI chinh trong configs/roi_w6.yaml)
            -> EventStore SQLite (e1store) + FrameResult JSONL.gz theo nguon.

    python scripts/pipeline/build_bundle.py --evidence results/W08/kaggle_run_17/w8_run17 --run-id run17 \
        --commit <sha> --out bundles/run17 [--media-dir <thu muc mp4 H.264>] [--videos V_DRONE_025 V_BIRD_041]

bundle/
  bundle.json            manifest: run, nguon, SHA-256 moi tep
  events.sqlite          runs, sources, events, event_reviews (trong), config_audit (trong)
  frames/<source>.jsonl.gz
  media/<source>.mp4     (tuy chon)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "alert"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import alert_engine as ae  # noqa: E402
import e1store  # noqa: E402
from evaluate_alerts import load_evidence  # noqa: E402

LOG = logging.getLogger("build_bundle")
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]
TRACKER = "tracker_bytetrack_e1"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def lf_sha(p: Path) -> str:
    """SHA-256 bo qua CRLF/LF (giong build_evidence) de cau hinh tren Windows va Linux cho cung SHA."""
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def frame_results(run_id: str, source_id: str, model_version: str, n_frames: int, fps: float,
                  tracks: list[dict], events: list[dict]) -> list[dict]:
    by_f: dict[int, list[dict]] = {}
    for t in tracks:
        by_f.setdefault(int(t["frame"]), []).append(t)
    opens, closes = {}, {}
    for e in events:
        opens.setdefault(e["start_frame"], []).append(e["event_id"])
        closes.setdefault(e["end_frame"], []).append(e["event_id"])
    out = []
    for f in range(n_frames):
        tr = []
        for t in sorted(by_f.get(f, []), key=lambda r: int(r["id"])):
            x, y, w, h = (float(t[k]) for k in "xywh")
            c = int(t["cls"])
            tr.append({"id": int(t["id"]), "cls": c, "cls_name": CLASSES[c], "conf": float(t["conf"]),
                       "box": [round(x, 2), round(y, 2), round(x + w, 2), round(y + h, 2)]})
        ev = [{"event_id": i, "transition": "open"} for i in opens.get(f, [])] + \
             [{"event_id": i, "transition": "close"} for i in closes.get(f, [])]
        out.append({"run_id": run_id, "source_id": source_id, "model_version": model_version, "frame_index": f,
                    "source_time_ms": e1store.frame_ms(f, fps), "tracks": tr, "events": ev,
                    "stage_latency_ms": None})      # phat lai tu track log da luu: do tre do o W9 tren Kaggle
    return out


def build(evidence: Path, out: Path, run_id: str, commit: str, roi_cfg: Path, alert_cfg: Path,
          media_dir: Path | None = None, videos: list[str] | None = None, tracker: str = TRACKER, overwrite: bool = False) -> dict:
    vids, inp = load_evidence(evidence, tracker)
    if videos:
        missing = set(videos) - {v["video_id"] for v in vids}
        if missing:
            raise ValueError(f"khong co trong evidence: {sorted(missing)}")
        vids = [v for v in vids if v["video_id"] in set(videos)]
    rois = yaml.safe_load(roi_cfg.read_text(encoding="utf-8"))
    cfg = yaml.safe_load(alert_cfg.read_text(encoding="utf-8"))
    primary = rois["primary"]
    poly = next(r["polygon"] for r in rois["rois"] if r["name"] == primary)
    point = cfg.get("point", "center")
    if out.exists():
        if not overwrite:
            raise SystemExit(f"{out} da ton tai; dung --overwrite")
        shutil.rmtree(out)
    (out / "frames").mkdir(parents=True)
    config = {"roi": {"name": primary, "polygon": poly, "point": point, "file": roi_cfg.name, "sha256": lf_sha(roi_cfg)},
              "alert": {"version": cfg.get("version"), "rule": "R1", "file": alert_cfg.name, "sha256": lf_sha(alert_cfg)},
              "tracker": {"name": tracker, "cfg": inp["trackers"][tracker]},
              "detector": inp.get("detector", {})}
    config_sha = hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    c = e1store.connect(out / "events.sqlite"); e1store.init(c)
    model_version = inp["weights_sha256"]
    with c:
        e1store.add_run(c, run_id, commit, model_version, config, config_sha, inp.get("device", "UNKNOWN"),
                        f"{evidence.as_posix()} (commit {inp.get('commit', 'UNKNOWN')})")
    summary = {}
    for v in vids:
        vid, fps, n = v["video_id"], v["fps"], v["frames"]
        alerts, _ = ae.r1_alerts(v["tracks"], n, fps, poly, v["width"], v["height"], cfg)
        media_rel = media_sha = None
        if media_dir is not None and (media_dir / f"{vid}.mp4").is_file():
            (out / "media").mkdir(exist_ok=True)
            shutil.copy2(media_dir / f"{vid}.mp4", out / "media" / f"{vid}.mp4")
            media_rel, media_sha = f"media/{vid}.mp4", sha256(out / "media" / f"{vid}.mp4")
        events = [{"event_id": f"{run_id}:{vid}:{i}", "start_frame": a["start"], "end_frame": a["end"],
                   "tracks": a["tracks"], "kind": a["kind"]} for i, a in enumerate(alerts)]
        with c:
            e1store.add_source(c, run_id, vid, v["class_name"], fps, v["width"], v["height"], n, media_rel, media_sha)
            for e in events:
                e1store.add_event(c, e["event_id"], run_id, vid, "R1", primary, e["kind"], e["start_frame"], e["end_frame"], fps, e["tracks"])
        fr = frame_results(run_id, vid, model_version, n, fps, v["tracks"], events)
        with gzip.open(out / "frames" / f"{vid}.jsonl.gz", "wt", encoding="utf-8") as fh:
            for r in fr:
                fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
        summary[vid] = {"frames": n, "events": len(events), "media": media_rel is not None}
    c.close()
    files = sorted(p for p in out.rglob("*") if p.is_file())
    man = {"run_id": run_id, "commit": commit, "model_version": model_version, "config_sha256": config_sha,
           "evidence": evidence.as_posix(), "sources": summary,
           "files": [{"path": p.relative_to(out).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size} for p in files]}
    (out / "bundle.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return man


def verify(out: Path) -> list[str]:
    """Kiem SHA-256 moi tep trong bundle so voi bundle.json. events.sqlite bo qua vi review lam doi tep."""
    man = json.loads((out / "bundle.json").read_text(encoding="utf-8"))
    bad = []
    for f in man["files"]:
        if f["path"] == "events.sqlite":
            continue
        p = out / f["path"]
        if not p.is_file() or sha256(p) != f["sha256"]:
            bad.append(f["path"])
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", type=Path, required=True, help="thu muc bang chung run tracking (co meta.csv, tracks/, inputs.json)")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--commit", required=True, help="SHA commit cua repo khi dung bundle")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--roi-config", type=Path, default=ROOT / "configs/roi_w6.yaml")
    ap.add_argument("--alert-config", type=Path, default=ROOT / "configs/alert_e1.yaml")
    ap.add_argument("--media-dir", type=Path, help="thu muc <video>.mp4 da ma hoa H.264 tren Kaggle")
    ap.add_argument("--videos", nargs="*", help="chi dung cac video nay (mac dinh: moi video trong evidence)")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    man = build(a.evidence, a.out, a.run_id, a.commit, a.roi_config, a.alert_config, a.media_dir, a.videos, overwrite=a.overwrite)
    LOG.info("bundle %s: %d nguon, %d su kien", a.out, len(man["sources"]), sum(s["events"] for s in man["sources"].values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
