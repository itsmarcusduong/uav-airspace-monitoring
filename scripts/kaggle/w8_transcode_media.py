#!/usr/bin/env python3
"""E1 W8 Kaggle (CPU, buoc cua run 17): ma hoa lai video kha kien tap val sang H.264 de trinh duyet phat duoc trong dashboard.

Video goc cua Svanstrom khong chac phat duoc tren trinh duyet; giai ma va ma hoa video la viec chay tren Kaggle (quy tac du an).
Giu nguyen so frame, fps va kich thuoc; chi doi codec. Moi tep ghi SHA-256 va so frame doc lai bang ffprobe.

    python w8_transcode_media.py --data-root /kaggle/input --manifest yolo_manifest.csv.gz --out /kaggle/working/w8_media
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

LOG = logging.getLogger("w8_transcode_media")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ffmpeg_major() -> int:
    out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split()
    try:
        return int(out[2].split(".")[0].lstrip("n"))
    except (IndexError, ValueError):
        return 0


def ffmpeg_cmd(src: Path, dst: Path, crf: int = 23, major: int = 6) -> list[str]:
    """H.264 yuv420p, giu nguyen tung frame (khong nhan doi/bo frame), khong am thanh, faststart de phat qua HTTP.
    ffmpeg >= 5.1 dung -fps_mode passthrough; ban cu (Kaggle co the la 4.x) dung -vsync passthrough."""
    sync = ["-fps_mode", "passthrough"] if major >= 6 else ["-vsync", "passthrough"]
    return ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-map", "0:v:0", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
            *sync, "-movflags", "+faststart", str(dst)]


def probe(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=codec_name,width,height,r_frame_rate,nb_read_frames", "-of", "json", str(p)],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    return {"codec": s["codec_name"], "width": int(s["width"]), "height": int(s["height"]),
            "fps": round(num / den, 3), "frames": int(s["nb_read_frames"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--split", default="val")
    ap.add_argument("--crf", type=int, default=23)
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working/w8_media"))
    ap.add_argument("--max-videos", type=int, default=0, help="chi de kiem thu")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if a.split == "test":
        raise SystemExit("test khoa toi W10")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("can ffmpeg/ffprobe")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from w3_export_yolo import find_video_dir  # noqa: E402
    vdir = find_video_dir(a.data_root) / "Video_V"
    with gzip.open(a.manifest, "rt", encoding="utf-8") as fh:
        vids = sorted({m["video_id"] for m in csv.DictReader(fh) if m["split"] == a.split})
    if a.max_videos:
        vids = vids[: a.max_videos]
    if a.out.exists():
        shutil.rmtree(a.out)
    a.out.mkdir(parents=True)
    rows, bad, major = [], [], ffmpeg_major()
    LOG.info("ffmpeg %s", major)
    for v in vids:
        src, dst = vdir / f"{v}.mp4", a.out / f"{v}.mp4"
        subprocess.run(ffmpeg_cmd(src, dst, a.crf, major), check=True)
        ps, pd = probe(src), probe(dst)
        same = (ps["frames"], ps["width"], ps["height"]) == (pd["frames"], pd["width"], pd["height"]) and abs(ps["fps"] - pd["fps"]) < 0.01
        if not same:
            bad.append(v)
        rows.append({"video_id": v, "src_sha256": sha256(src), "sha256": sha256(dst), "bytes": dst.stat().st_size,
                     "src": ps, "out": pd, "same_frames_fps_size": same})
    man = {"split": a.split, "crf": a.crf, "videos": len(rows), "mismatch": bad, "files": rows}
    (a.out / "media_manifest.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    z = a.out.parent / f"{a.out.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        for p in sorted(a.out.iterdir()):
            zf.write(p, p.relative_to(a.out.parent))
    LOG.info("%d video, %d lech so frame/fps/kich thuoc, zip %s", len(rows), len(bad), z)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
