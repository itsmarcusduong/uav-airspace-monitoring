#!/usr/bin/env python3
"""Dung bundle phat lai (ADR-0015 muc 5) tu bang chung Kaggle cua mot hay nhieu run tracking (run 14, run 17).

Chi doc CSV/JSON (track log, meta) va video da ma hoa H.264 tren Kaggle (neu co); KHONG giai ma video, KHONG suy luan.
Cac buoc sau tracker cua pipeline chay o day, giong het pipeline lien tuc:
  track log -> AlertEngine R1 (ADR-0009, configs/alert_e1.yaml, ROI chinh trong configs/roi_w6.yaml)
            -> EventStore SQLite (e1store) + FrameResult JSONL.gz theo (run, nguon).

    python scripts/pipeline/build_bundle.py --evidence results/W06/kaggle_run_14/w6_run14 --run-id run14 \
        --commit <sha> --out bundles/w8 [--media-dir <thu muc mp4 H.264>] [--videos V_DRONE_025 V_BIRD_041]
    python scripts/pipeline/build_bundle.py --evidence results/W08/kaggle_run_17/w8_run17 --run-id run17 \
        --commit <sha> --out bundles/w8 --append --reason "ADR-0012 muc 5: ap dung V2"

Che do ghi:
  mac dinh     --out chua ton tai (hoac thu muc rong)
  --append     them run vao bundle co san; cau hinh khac run truoc -> ghi config_audit (bat buoc --reason)
  --overwrite  dung lai bundle co san; chi xoa cac tep cua bundle, tu choi neu --out khong phai bundle,
               la thu muc goc/repo/thu muc cha cua repo hoac thu muc hien tai, co tep la, hoac da co review/audit

bundle/
  bundle.json                    manifest: cac run, nguon, SHA-256 moi tep (format 2)
  events.sqlite                  runs, sources, events, event_reviews, config_audit
  frames/<run>/<source>.jsonl.gz
  media/<source>.mp4             (tuy chon; dung chung cho moi run, SHA phai trung)
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
FORMAT = 2
BUNDLE_ITEMS = {"bundle.json", "events.sqlite", "events.sqlite-journal", "events.sqlite-wal", "events.sqlite-shm", "frames", "media"}


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


def _protected(p: Path) -> bool:
    """Duong dan khong bao gio duoc xoa: thu muc goc, home, repo, thu muc hien tai va moi thu muc cha cua chung."""
    keep = {Path(p.anchor), Path.home().resolve(), ROOT.resolve(), Path.cwd().resolve()}
    return any(p == k or p in k.parents for k in keep)


def reset_bundle(out: Path) -> None:
    """Xoa bundle cu truoc khi dung lai. Chi xoa cac muc cua bundle; tu choi moi truong hop co the xoa nham du lieu."""
    out = out.resolve()
    if _protected(out):
        raise SystemExit(f"tu choi --overwrite: {out} la thu muc goc/home/repo/thu muc hien tai hoac thu muc cha cua chung")
    if not out.is_dir() or not (out / "bundle.json").is_file():
        raise SystemExit(f"tu choi --overwrite: {out} khong phai bundle (thieu bundle.json)")
    extra = sorted(p.name for p in out.iterdir() if p.name not in BUNDLE_ITEMS)
    if extra:
        raise SystemExit(f"tu choi --overwrite: {out} co tep khong thuoc bundle: {extra[:5]}")
    if (out / "events.sqlite").is_file():
        c = e1store.connect(out / "events.sqlite")
        try:
            n = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("event_reviews", "config_audit")}
        finally:
            c.close()
        if any(n.values()):
            raise SystemExit(f"tu choi --overwrite: bundle da co {n} (lich su chi them); sao luu hoac dung --out moi")
    for name in BUNDLE_ITEMS:
        p = out / name
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        elif p.exists() or p.is_symlink():
            p.unlink()


def config_targets(config: dict, model_version: str) -> dict[str, str]:
    """SHA-256 tung doi tuong cau hinh de so voi run truoc (config_audit)."""
    h = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()  # noqa: E731
    return {"roi": h(config["roi"]), "alert": h(config["alert"]), "tracker": h(config["tracker"]),
            "detector": h(config["detector"]), "weights": model_version}


def build(evidence: Path, out: Path, run_id: str, commit: str, roi_cfg: Path, alert_cfg: Path,
          media_dir: Path | None = None, videos: list[str] | None = None, tracker: str = TRACKER,
          overwrite: bool = False, append: bool = False, actor: str = "build_bundle", reason: str | None = None) -> dict:
    if overwrite and append:
        raise SystemExit("chon --overwrite hoac --append, khong ca hai")
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
    if append:
        if not (out / "bundle.json").is_file() or json.loads((out / "bundle.json").read_text(encoding="utf-8")).get("format") != FORMAT:
            raise SystemExit(f"--append: {out} khong phai bundle format {FORMAT}")
    elif out.exists() and (not out.is_dir() or any(out.iterdir())):
        if not overwrite:
            raise SystemExit(f"{out} da ton tai; dung --overwrite hoac --append")
        reset_bundle(out)
    (out / "frames" / run_id).mkdir(parents=True, exist_ok=append)
    config = {"roi": {"name": primary, "polygon": poly, "point": point, "file": roi_cfg.name, "sha256": lf_sha(roi_cfg)},
              "alert": {"version": cfg.get("version"), "rule": "R1", "file": alert_cfg.name, "sha256": lf_sha(alert_cfg)},
              "tracker": {"name": tracker, "cfg": inp["trackers"][tracker]},
              "detector": inp.get("detector", {})}
    config_sha = hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    model_version = inp["weights_sha256"]
    c = e1store.connect(out / "events.sqlite"); e1store.init(c)
    if c.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone():
        c.close()
        raise SystemExit(f"run {run_id} da co trong bundle")
    prev = e1store.last_run(c)
    changed = {}
    if prev is not None:
        old, new = config_targets(prev["config"], prev["model_version"]), config_targets(config, model_version)
        changed = {t: (old[t], new[t]) for t in new if old[t] != new[t]}
        if changed and not (reason and reason.strip()):
            c.close()
            raise SystemExit(f"cau hinh khac run {prev['run_id']} o {sorted(changed)}: can --reason de ghi config_audit")
    with c:
        e1store.add_run(c, run_id, commit, model_version, config, config_sha, inp.get("device", "UNKNOWN"),
                        f"{evidence.as_posix()} (commit {inp.get('commit', 'UNKNOWN')})")
        for t, (o, n) in sorted(changed.items()):
            e1store.add_config_audit(c, actor, t, prev["run_id"], run_id, o, n, reason)
    summary = {}
    for v in vids:
        vid, fps, n = v["video_id"], v["fps"], v["frames"]
        alerts, _ = ae.r1_alerts(v["tracks"], n, fps, poly, v["width"], v["height"], cfg)
        media_rel = media_sha = None
        if media_dir is not None and (media_dir / f"{vid}.mp4").is_file():
            (out / "media").mkdir(exist_ok=True)
            dst, src_sha = out / "media" / f"{vid}.mp4", sha256(media_dir / f"{vid}.mp4")
            if dst.is_file() and sha256(dst) != src_sha:
                raise SystemExit(f"media/{vid}.mp4 trong bundle khac tep moi (SHA khac)")
            if not dst.is_file():
                shutil.copy2(media_dir / f"{vid}.mp4", dst)
            media_rel, media_sha = f"media/{vid}.mp4", src_sha
        events = [{"event_id": f"{run_id}:{vid}:{i}", "start_frame": a["start"], "end_frame": a["end"],
                   "tracks": a["tracks"], "kind": a["kind"]} for i, a in enumerate(alerts)]
        with c:
            e1store.add_source(c, run_id, vid, v["class_name"], fps, v["width"], v["height"], n, media_rel, media_sha)
            for e in events:
                e1store.add_event(c, e["event_id"], run_id, vid, "R1", primary, e["kind"], e["start_frame"], e["end_frame"], fps, e["tracks"])
        fr = frame_results(run_id, vid, model_version, n, fps, v["tracks"], events)
        with gzip.open(out / "frames" / run_id / f"{vid}.jsonl.gz", "wt", encoding="utf-8") as fh:
            for r in fr:
                fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
        summary[vid] = {"frames": n, "events": len(events), "media": media_rel is not None}
    c.close()
    runs = json.loads((out / "bundle.json").read_text(encoding="utf-8"))["runs"] if append else {}
    runs[run_id] = {"commit": commit, "model_version": model_version, "config_sha256": config_sha,
                    "evidence": evidence.as_posix(), "config_changed_vs": prev["run_id"] if changed else None,
                    "sources": summary}
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "bundle.json")
    man = {"format": FORMAT, "runs": runs,
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
    ap.add_argument("--overwrite", action="store_true", help="dung lai bundle co san (chi xoa tep cua bundle, xem docstring)")
    ap.add_argument("--append", action="store_true", help="them run vao bundle co san")
    ap.add_argument("--actor", default="build_bundle", help="actor_id ghi vao config_audit")
    ap.add_argument("--reason", help="ly do doi cau hinh so voi run truoc (bat buoc khi --append va cau hinh khac)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    man = build(a.evidence, a.out, a.run_id, a.commit, a.roi_config, a.alert_config, a.media_dir, a.videos,
                overwrite=a.overwrite, append=a.append, actor=a.actor, reason=a.reason)
    r = man["runs"][a.run_id]
    LOG.info("bundle %s: run %s, %d nguon, %d su kien, doi cau hinh so voi %s", a.out, a.run_id, len(r["sources"]),
             sum(s["events"] for s in r["sources"].values()), r["config_changed_vs"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
