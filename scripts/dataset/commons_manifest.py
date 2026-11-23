#!/usr/bin/env python3
"""Lap manifest ung vien video am tinh tu Wikimedia Commons (W9-03 #131; ADR-0013; docs/w9/W9_PLAN.md muc D).

Doc truc tiep Commons API (nguon goc, khong qua ban sao): danh sach tep trong cac category, roi imageinfo cua tung tep
(URL, kich thuoc, thoi luong, SHA-1, giay phep, tac gia). Chi giu tep video co giay phep trong danh sach cho phep.
Khong tai video. Ket qua la bang ung vien de An sang loc doc lap bang cach mo trang Commons (cot `page`).

    python scripts/dataset/commons_manifest.py --out data/manifests/neg_commons_candidates.csv
    python scripts/dataset/commons_manifest.py --categories "Videos of flocks of birds in flight" --out <csv>
    python scripts/dataset/commons_manifest.py --finalize data/manifests/neg_commons_candidates.csv \
        --out data/manifests/neg_commons_v1.csv      # sau khi Quang va An dien screen_quang, screen_an
Luat sang loc va gan split: docs/w9/neg_screening_protocol.md (viet truoc).

Chay tren may co Internet (may cua Quang). Moi request co User-Agent theo chinh sach Wikimedia, nghi giua cac lo.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

LOG = logging.getLogger("commons_manifest")
API = "https://commons.wikimedia.org/w/api.php"
UA = "E1-UAV-thesis-manifest/1.0 (PTIT student project; contact via GitHub itsmarcusduong/uav-airspace-monitoring)"
CATEGORIES = [                                          # canh nen troi, chim bay, may bay, may - KHONG co drone
    "Videos of flocks of birds in flight",
    "Videos of birds in flight",
    "Videos of aircraft landings",
    "Videos of aircraft takeoffs",
    "Time-lapse videos of clouds",
    "Videos of clouds",
]
ALLOWED = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? [0-9.]+|CC BY(-SA)?)$", re.I)
MIN_SECONDS, MIN_WIDTH = 10.0, 640
EXCLUDE_WORDS = re.compile(r"drone|uav|quadcopter|multicopter|dji|unmanned|aerial video|from the air|cockpit|onboard", re.I)
FIELDS = ["source", "title", "page", "url", "mime", "width", "height", "duration_s", "bytes", "sha1", "license", "license_url",
          "artist", "category", "split", "screen_quang", "screen_an", "screen_note"]


def get(params: dict, opener=urllib.request.urlopen) -> dict:
    q = urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    with opener(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def category_files(cat: str, fetch=get) -> list[str]:
    out, cont = [], {}
    while True:
        d = fetch({"action": "query", "list": "categorymembers", "cmtitle": f"Category:{cat}", "cmtype": "file", "cmlimit": "500", **cont})
        out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        if "continue" not in d:
            return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}


def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def file_info(titles: list[str], fetch=get) -> list[dict]:
    rows = []
    for i in range(0, len(titles), 50):
        d = fetch({"action": "query", "prop": "imageinfo", "titles": "|".join(titles[i:i + 50]),
                   "iiprop": "url|size|sha1|mime|extmetadata|mediatype", "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist"})
        for p in d.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            rows.append({"title": p["title"], "page": ii.get("descriptionurl", ""), "url": ii.get("url", ""), "mime": ii.get("mime", ""),
                         "width": ii.get("width"), "height": ii.get("height"), "duration_s": ii.get("duration"), "bytes": ii.get("size"),
                         "sha1": ii.get("sha1", ""), "license": strip_html(md.get("LicenseShortName", {}).get("value", "")),
                         "license_url": strip_html(md.get("LicenseUrl", {}).get("value", "")), "artist": strip_html(md.get("Artist", {}).get("value", ""))[:200]})
        time.sleep(0.5)
    return rows


def keep(r: dict) -> tuple[bool, str]:
    if not r["mime"].startswith("video/"):
        return False, "khong phai video"
    if not ALLOWED.match(r["license"] or ""):
        return False, f"giay phep {r['license']!r} ngoai danh sach"
    if (r["duration_s"] or 0) < MIN_SECONDS:
        return False, "ngan hon 10 s"
    if (r["width"] or 0) < MIN_WIDTH:
        return False, "rong < 640 px"
    if EXCLUDE_WORDS.search(r["title"]):
        return False, "ten goi y drone/quay tu tren khong"
    return True, ""


def split_of(artist: str) -> str:
    """Luat muc 3 cua protocol: chu so hex cuoi cua SHA-256(artist) chan -> neg_eval, le -> neg_train."""
    import hashlib
    return "neg_eval" if int(hashlib.sha256(artist.strip().encode("utf-8")).hexdigest()[-1], 16) % 2 == 0 else "neg_train"


def finalize(cand: Path, out: Path) -> dict:
    """Giu clip khi CA HAI nguoi deu 'keep' (luat muc 2); gan split theo tac gia (muc 3). Tu choi neu con o trong."""
    rows = list(csv.DictReader(cand.open(encoding="utf-8")))
    empty = [r["title"] for r in rows if not r["screen_quang"].strip() or not r["screen_an"].strip()]
    if empty:
        raise SystemExit(f"{len(empty)} clip chua sang loc du hai cot, vd. {empty[:3]}")
    bad = {r["screen_quang"].strip().lower() for r in rows} | {r["screen_an"].strip().lower() for r in rows}
    if not bad <= {"keep", "reject"}:
        raise SystemExit(f"gia tri sang loc khong hop le: {bad - {'keep', 'reject'}}")
    kept = [{**r, "split": split_of(r["artist"])} for r in rows
            if r["screen_quang"].strip().lower() == "keep" and r["screen_an"].strip().lower() == "keep"]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(kept)
    agree = sum(1 for r in rows if r["screen_quang"].strip().lower() == r["screen_an"].strip().lower())
    st = {"candidates": len(rows), "kept": len(kept), "agreement": round(agree / len(rows), 4) if rows else None,
          "minutes": {s: round(sum(float(r["duration_s"] or 0) for r in kept if r["split"] == s) / 60, 2) for s in ("neg_eval", "neg_train")}}
    LOG.info("%s", st)
    return st


def main(argv=None, fetch=get) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--categories", nargs="+", default=CATEGORIES)
    ap.add_argument("--finalize", type=Path, help="bang ung vien da sang loc -> manifest chinh thuc")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if a.finalize:
        finalize(a.finalize, a.out)
        return 0
    seen, rows, rejected = set(), [], {}
    for cat in a.categories:
        titles = [t for t in category_files(cat, fetch) if t not in seen]
        seen |= set(titles)
        for r in file_info(titles, fetch):
            ok, why = keep(r)
            if ok:
                rows.append({"source": "wikimedia_commons", **r, "category": cat, "split": "", "screen_quang": "", "screen_an": "", "screen_note": ""})
            else:
                rejected[why.split(" ")[0]] = rejected.get(why.split(" ")[0], 0) + 1
        LOG.info("%s: %d tep, giu tong %d", cat, len(titles), len(rows))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(sorted(rows, key=lambda r: r["title"]))
    mins = sum(float(r["duration_s"] or 0) for r in rows) / 60
    LOG.info("ung vien: %d tep, %.1f phut; loai: %s", len(rows), mins, rejected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
