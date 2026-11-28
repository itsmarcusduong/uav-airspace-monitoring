#!/usr/bin/env python3
"""Lap manifest ung vien video am tinh tu Wikimedia Commons (W9-03 #131; ADR-0013; docs/w9/W9_PLAN.md muc D).

Doc truc tiep Commons API (nguon goc, khong qua ban sao): danh sach tep trong cac category, roi imageinfo cua tung tep
(URL, kich thuoc, thoi luong, SHA-1, giay phep, tac gia, nguoi tai len). Chi giu tep video co giay phep trong danh sach
cho phep. Khong tai video. Luat sang loc va gan split: docs/w9/neg_screening_protocol.md (viet truoc).

Buoc 1 - lap ung vien va hai ban sang loc rieng (Quang, may co Internet):
    python scripts/dataset/commons_manifest.py --out data/manifests/neg_commons_candidates.csv
  -> neg_commons_candidates.csv, neg_commons_screen_quang.csv, neg_commons_screen_an.csv (cung thu muc)
Buoc 2 - moi nguoi dien ban cua minh, khong xem ban cua nguoi kia (protocol muc 2).
Buoc 3 - gop sau khi CA HAI ban da xong:
    python scripts/dataset/commons_manifest.py --finalize data/manifests/neg_commons_candidates.csv \
        --screen-quang <ban Quang> --screen-an <ban An> --out data/manifests/neg_commons_v1.csv

Moi request co User-Agent theo chinh sach Wikimedia, nghi giua cac lo.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

LOG = logging.getLogger("commons_manifest")
API = "https://commons.wikimedia.org/w/api.php"
UA = "E1-UAV-thesis-manifest/1.0 (PTIT student project; contact via GitHub itsmarcusduong/uav-airspace-monitoring)"
CATEGORIES = [                                          # canh nen troi, chim bay, may bay, may - KHONG co drone, KHONG time-lapse
    "Videos of flocks of birds in flight",
    "Videos of birds in flight",
    "Videos of aircraft landings",
    "Videos of aircraft takeoffs",
    "Videos of clouds",
]
ALLOWED = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? [0-9.]+|CC BY(-SA)?)$", re.I)
MIN_SECONDS, MIN_WIDTH = 10.0, 640
EXCLUDE_WORDS = re.compile(r"drone|uav|quadcopter|multicopter|dji|unmanned|aerial video|from the air|cockpit|onboard", re.I)
EDITED_WORDS = re.compile(r"time[\s_-]?lapse|hyper[\s_-]?lapse|slow[\s_-]?mo(tion)?|slo[\s_-]?mo|montage|compilation", re.I)
UNKNOWN_AUTHORS = {"", "unknown", "unknown author", "anonymous", "anon", "not provided", "see below", "see description",
                   "various", "various authors", "n a", "na", "none"}
TRAIN_FRACTION = 0.25                                   # ADR-0013: khoang 1/4 thoi luong vao neg_train
CAND_FIELDS = ["source", "title", "page", "url", "mime", "width", "height", "duration_s", "bytes", "sha1", "license",
               "license_url", "artist", "uploader", "author_key", "author_status", "category"]
SCREEN_FIELDS = ["title", "page", "screen", "screen_note"]
FINAL_FIELDS = CAND_FIELDS + ["group_key", "split", "screen_quang", "note_quang", "screen_an", "note_an"]
VALUES = {"keep", "reject"}


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


def norm(s: str) -> str:
    """Chuan hoa ten: NFKC, chu thuong, bo dau cau, gop khoang trang, '_' = ' '."""
    s = unicodedata.normalize("NFKC", s or "").casefold().replace("_", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def author_key(artist_html: str) -> tuple[str, str]:
    """Khoa tac gia on dinh (protocol muc 3). Uu tien tai khoan Commons trong lien ket User:, sau do ten da chuan hoa.

    Tra (key, status): status 'ok' hoac 'needs_review' (trong, khong ro, hoac nhieu tai khoan khac nhau)."""
    # chi doc tai khoan trong href (thuoc tinh title co the them "(page does not exist)" lam mot tai khoan thanh hai)
    users = {norm(urllib.parse.unquote(u)) for u in re.findall(r"href=[\"'][^\"']*?User:([^\"'#?&<>/|]+)", artist_html or "")}
    users.discard("")
    if len(users) > 1:
        return "", "needs_review"
    if users:
        return "user:" + users.pop(), "ok"
    text = norm(re.sub(r"\bown work\b", " ", strip_html(artist_html), flags=re.I))
    if text in UNKNOWN_AUTHORS:
        return "", "needs_review"
    return "name:" + text, "ok"


def file_info(titles: list[str], fetch=get) -> list[dict]:
    rows = []
    for i in range(0, len(titles), 50):
        d = fetch({"action": "query", "prop": "imageinfo", "titles": "|".join(titles[i:i + 50]),
                   "iiprop": "url|size|sha1|mime|extmetadata|mediatype|user", "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist"})
        for p in d.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            raw_artist = md.get("Artist", {}).get("value", "")
            key, status = author_key(raw_artist)
            rows.append({"title": p["title"], "page": ii.get("descriptionurl", ""), "url": ii.get("url", ""), "mime": ii.get("mime", ""),
                         "width": ii.get("width"), "height": ii.get("height"), "duration_s": ii.get("duration"), "bytes": ii.get("size"),
                         "sha1": ii.get("sha1", ""), "license": strip_html(md.get("LicenseShortName", {}).get("value", "")),
                         "license_url": strip_html(md.get("LicenseUrl", {}).get("value", "")), "artist": strip_html(raw_artist)[:200],
                         "uploader": ii.get("user", ""), "author_key": key, "author_status": status})
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
    if EDITED_WORDS.search(r["title"]):
        return False, "ten goi y canh chinh sua (time-lapse, slow-motion, ghep)"
    return True, ""


def author_groups(rows: list[dict]) -> dict[str, str]:
    """Gop clip thanh nhom tac gia: hai clip chung nhom neu chung author_key HOAC chung nguoi tai len (bat alias).

    Tra {title: group_key}; group_key = khoa nho nhat (theo thu tu chuoi) trong nhom. Chi nhan dong author_status == 'ok'."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for r in rows:
        keys = [r["author_key"]] + (["uploader:" + norm(r["uploader"])] if norm(r.get("uploader", "")) else [])
        for k in keys[1:]:
            union(keys[0], k)
        find(keys[0])
    members: dict[str, set[str]] = {}
    for k in list(parent):
        members.setdefault(find(k), set()).add(k)
    label = {root: min(ks) for root, ks in members.items()}
    return {r["title"]: label[find(r["author_key"])] for r in rows}


def assign_splits(rows: list[dict], train_fraction: float = TRAIN_FRACTION) -> dict[str, str]:
    """Luat muc 3: sap nhom theo SHA-256(group_key); lan luot dua nhom vao neg_train toi khi dat train_fraction tong thoi
    luong, phan con lai vao neg_eval. Tat dinh, chi dung khoa tac gia va thoi luong (khong dung ket qua detector)."""
    groups = author_groups(rows)
    dur: dict[str, float] = {}
    for r in rows:
        dur[groups[r["title"]]] = dur.get(groups[r["title"]], 0.0) + float(r["duration_s"] or 0)
    total, acc, split = sum(dur.values()), 0.0, {}
    for g in sorted(dur, key=lambda g: hashlib.sha256(g.encode("utf-8")).hexdigest()):
        split[g] = "neg_train" if acc < train_fraction * total else "neg_eval"
        acc += dur[g] if split[g] == "neg_train" else 0.0
    return {t: (g, split[g]) for t, g in groups.items()}


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def screen_paths(cand: Path) -> tuple[Path, Path]:
    stem = cand.stem.replace("_candidates", "")
    return cand.with_name(f"{stem}_screen_quang.csv"), cand.with_name(f"{stem}_screen_an.csv")


def read_screen(path: Path, who: str, expected: set[str]) -> dict[str, dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    by = {r["title"]: r for r in rows}
    if len(by) != len(rows):
        raise SystemExit(f"ban sang loc cua {who} co title trung lap")
    if set(by) != expected:
        raise SystemExit(f"ban sang loc cua {who} khong khop danh sach ung vien: thieu {sorted(expected - set(by))[:3]}, "
                         f"thua {sorted(set(by) - expected)[:3]}")
    empty = [t for t, r in by.items() if not r["screen"].strip()]
    if empty:
        raise SystemExit(f"{who}: {len(empty)} clip chua sang loc, vd. {empty[:3]}")
    bad = {r["screen"].strip().lower() for r in by.values()} - VALUES
    if bad:
        raise SystemExit(f"{who}: gia tri sang loc khong hop le {bad}")
    no_note = [t for t, r in by.items() if r["screen"].strip().lower() == "reject" and not r["screen_note"].strip()]
    if no_note:
        raise SystemExit(f"{who}: {len(no_note)} clip reject thieu ly do (screen_note), vd. {no_note[:3]}")
    return by


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(v) / n) * (b.count(v) / n) for v in VALUES)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def finalize(cand: Path, screen_quang: Path, screen_an: Path, out: Path) -> dict:
    """Gop hai ban sang loc doc lap (muc 2): giu clip khi CA HAI nguoi deu 'keep'; gan split theo nhom tac gia (muc 3).

    Tu choi neu: ban sang loc thieu/thua/trong; reject khong co ly do; mot trong hai split rong."""
    rows = list(csv.DictReader(cand.open(encoding="utf-8")))
    screened = [r for r in rows if r["author_status"] == "ok"]
    titles = {r["title"] for r in screened}
    q, n = read_screen(screen_quang, "Quang", titles), read_screen(screen_an, "An", titles)
    kept = [r for r in screened if q[r["title"]]["screen"].strip().lower() == "keep" and n[r["title"]]["screen"].strip().lower() == "keep"]
    sp = assign_splits(kept)
    final = [{**r, "group_key": sp[r["title"]][0], "split": sp[r["title"]][1],
              "screen_quang": "keep", "note_quang": q[r["title"]]["screen_note"], "screen_an": "keep", "note_an": n[r["title"]]["screen_note"]}
             for r in kept]
    splits = {s: [r for r in final if r["split"] == s] for s in ("neg_train", "neg_eval")}
    if not splits["neg_train"] or not splits["neg_eval"]:
        raise SystemExit(f"khong tao duoc ca hai split: neg_train {len(splits['neg_train'])}, neg_eval {len(splits['neg_eval'])} clip")
    leak = {r["group_key"] for r in splits["neg_train"]} & {r["group_key"] for r in splits["neg_eval"]}
    if leak:                                            # khong the xay ra theo cach gan; kiem lai cho chac
        raise SystemExit(f"nhom tac gia nam o ca hai split: {sorted(leak)[:3]}")
    write_csv(out, FINAL_FIELDS, sorted(final, key=lambda r: (r["split"], r["title"])))
    vq = [q[r["title"]]["screen"].strip().lower() for r in screened]
    va = [n[r["title"]]["screen"].strip().lower() for r in screened]
    st = {"candidates": len(rows), "needs_review_author": len(rows) - len(screened), "screened": len(screened), "kept": len(final),
          "agreement": round(sum(x == y for x, y in zip(vq, va)) / len(vq), 4) if vq else None, "cohen_kappa": cohen_kappa(vq, va),
          "groups": {s: len({r["group_key"] for r in v}) for s, v in splits.items()},
          "clips": {s: len(v) for s, v in splits.items()},
          "minutes": {s: round(sum(float(r["duration_s"] or 0) for r in v) / 60, 2) for s, v in splits.items()},
          "train_fraction_target": TRAIN_FRACTION,
          "inputs_sha256": {p.name: sha256_file(p) for p in (cand, screen_quang, screen_an)}}
    out.with_suffix(".json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.info("%s", st)
    return st


def main(argv=None, fetch=get) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--categories", nargs="+", default=CATEGORIES)
    ap.add_argument("--finalize", type=Path, help="bang ung vien -> manifest chinh thuc (can --screen-quang, --screen-an)")
    ap.add_argument("--screen-quang", type=Path)
    ap.add_argument("--screen-an", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if a.finalize:
        if not (a.screen_quang and a.screen_an):
            ap.error("--finalize can ca --screen-quang va --screen-an")
        finalize(a.finalize, a.screen_quang, a.screen_an, a.out)
        return 0
    seen, rows, rejected = set(), [], {}
    for cat in a.categories:
        if EDITED_WORDS.search(cat):
            raise SystemExit(f"category {cat!r} la canh chinh sua (ADR-0013), khong dung")
        titles = [t for t in category_files(cat, fetch) if t not in seen]
        seen |= set(titles)
        for r in file_info(titles, fetch):
            ok, why = keep(r)
            if ok:
                rows.append({"source": "wikimedia_commons", **r, "category": cat})
            else:
                rejected[why] = rejected.get(why, 0) + 1
        LOG.info("%s: %d tep, giu tong %d", cat, len(titles), len(rows))
    rows.sort(key=lambda r: r["title"])
    write_csv(a.out, CAND_FIELDS, rows)
    to_screen = [{"title": r["title"], "page": r["page"], "screen": "", "screen_note": ""} for r in rows if r["author_status"] == "ok"]
    for p in screen_paths(a.out):
        write_csv(p, SCREEN_FIELDS, to_screen)
    mins = sum(float(r["duration_s"] or 0) for r in rows) / 60
    LOG.info("ung vien: %d tep, %.1f phut; can sang loc %d; tac gia can xem lai %d; loai: %s",
             len(rows), mins, len(to_screen), len(rows) - len(to_screen), rejected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
