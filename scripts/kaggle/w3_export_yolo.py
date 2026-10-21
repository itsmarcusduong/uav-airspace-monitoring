#!/usr/bin/env python3
"""E1 W3 Kaggle job 03: do anh huong lech nhan 1 frame + xuat du lieu YOLO tu split video v1.

Chay tren Kaggle (CPU du). Huong dan: docs/w3/W3_PLAN.md muc C.

    python w3_export_yolo.py --data-root /kaggle/input/e1-svanstrom-raw \
        --split-csv video_split_v1.csv --audit annotation_audit.csv \
        --review review_assignment_w2.csv --out /kaggle/working --commit <sha>

Stage (doc lap, ghi vao stage_status.json):
  env -> inputs -> sensitivity -> offset_sheets -> decide -> export -> verify -> bundle
Quy tac (ADR-0004, Proposed):
  * Chi split train/val; test KHONG duoc xuat (khoa den danh gia cuoi).
  * Video so nhan = so frame: frame i <-> nhan i.
  * Video du dung 1 muc (plus1): theo --plus1-policy (offset0: frame i <-> nhan i, bo muc cuoi;
    offset1: frame i <-> nhan i+1; exclude: loai). Voi offset0/offset1 nhom (modality, lop) chi
    duoc dua vao neu ty le cap frame lien tiep co IoU >= --iou-min dat >= --iou-frac
    (lech 1 frame it lam doi ket qua khop o nguong IoU 0.5).
  * Video thieu nhan / du > 1 muc: loai (khong biet canh nhan).
  * Video co ket qua review = SAI_NHAN: loai. Cot dung theo thu tu uu tien verdict > review_quang_v2
    > review_quang (cot nao co gia tri dau tien); cot da dung ghi vao inclusion_decisions.csv.
  * Video khong co bbox nao: giu lam am tinh.
  * Frame co nhan None trong pham vi nhan = am tinh (file .txt rong).
Seed co dinh. Chi doc du lieu goc.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import math
import platform
import random
import re
import shutil
import subprocess
import sys
import traceback
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("w3_export")
NAME = re.compile(r"^(IR|V)_(AIRPLANE|BIRD|DRONE|HELICOPTER)_(\d+)$")
CLASS_ID = {"Airplane": 0, "Bird": 1, "Drone": 2, "Helicopter": 3}
CLASS_NAMES = ["Airplane", "Bird", "Drone", "Helicopter"]
SMALL, MEDIUM = 32 * 32, 96 * 96
REVIEW_COLUMNS = ("verdict", "review_quang_v2", "review_quang")


# ----------------------------------------------------------------------------- helpers
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def find_video_dir(root: Path) -> Path:
    """Tra ve thu muc Data (chua Video_IR, Video_V)."""
    if (root / "Data" / "Video_V").is_dir():
        return root / "Data"
    for cand in sorted(root.rglob("Video_V")):
        if cand.is_dir() and cand.parent.name == "Data":
            return cand.parent
    raise SystemExit(f"Khong tim thay Data/Video_V duoi {root}")


def to_box(b):
    """(x, y, w, h) float, None neu vang, 'MALFORMED' neu loi kieu/NaN."""
    if b is None:
        return None
    try:
        x, y, w, h = (float(v) for v in list(b)[:4])
    except Exception:
        return "MALFORMED"
    if any(math.isnan(v) or math.isinf(v) for v in (x, y, w, h)):
        return "MALFORMED"
    return (x, y, w, h)


def iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0.0, min(ax2, bx2) - max(ax1, bx1)), max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def label_kind(label_entries: int, frames: int) -> str:
    d = label_entries - frames
    return "equal" if d == 0 else "plus1" if d == 1 else "minus" if d < 0 else "plusN"


def size_bucket(area: float) -> str:
    return "small" if area < SMALL else "medium" if area < MEDIUM else "large"


def load_labels(mat: Path) -> list:
    from mcos_decoder import load_groundtruth  # type: ignore
    return [to_box(b) for b in load_groundtruth(mat)]


# ----------------------------------------------------------------------------- stages
def stage_env(out: Path, commit: str) -> dict:
    info = {"python": sys.version, "platform": platform.platform(), "commit": commit}
    for mod in ("cv2", "numpy", "mcos_decoder"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "present")
        except Exception as exc:  # noqa: BLE001
            info[mod] = f"MISSING ({exc.__class__.__name__})"
    try:
        info["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=20).stdout.strip() or "none"
    except Exception:
        info["nvidia_smi"] = "none/unavailable"
    (out / "env.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    return info


def stage_inputs(args, ev: Path) -> dict:
    split = {r["video_id"]: r for r in read_csv(args.split_csv)}
    audit = {r["video_id"]: r for r in read_csv(args.audit)}
    review = {}
    if args.review and args.review.is_file():
        review = {r["video_id"]: r for r in read_csv(args.review)}
    missing = sorted(set(split) - set(audit))
    if missing:
        raise RuntimeError(f"{len(missing)} video trong split khong co trong audit, vd {missing[:3]}")
    info = {
        "split_csv_sha256": sha256(args.split_csv), "audit_sha256": sha256(args.audit),
        "review_sha256": sha256(args.review) if review else "", "videos_in_split": len(split),
        "split_counts": dict(Counter(r["split"] for r in split.values())),
    }
    (ev / "inputs.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return {"split": split, "audit": audit, "review": review, "info": info}


def select_videos(ctx, args) -> list[str]:
    mods, splits = set(args.modalities), set(args.splits)
    return sorted(v for v, r in ctx["split"].items() if r["modality"] in mods and r["split"] in splits)


def stage_sensitivity(ctx, args, data: Path, ev: Path, labels: dict) -> dict:
    """IoU giua nhan cua 2 frame lien tiep: neu cao, lech 1 frame it anh huong khop o IoU 0.5."""
    rows, groups = [], defaultdict(lambda: {"pairs": 0, "ge": 0, "videos": 0})
    for vid in select_videos(ctx, args):
        a = ctx["audit"][vid]
        kind = label_kind(int(a["label_entries"]), int(a["frames_decoded"]))
        mod, cls = ctx["split"][vid]["modality"], ctx["split"][vid]["class_name"]
        mat = next((data / f"Video_{mod}").glob(f"{vid}_LABELS.mat"), None)
        if mat is None:
            continue
        boxes = labels.setdefault(vid, load_labels(mat))
        vals = [iou(boxes[i], boxes[i + 1]) for i in range(len(boxes) - 1)
                if isinstance(boxes[i], tuple) and isinstance(boxes[i + 1], tuple)
                and boxes[i][2] > 0 and boxes[i][3] > 0 and boxes[i + 1][2] > 0 and boxes[i + 1][3] > 0]
        if not vals:
            continue
        s = sorted(vals)
        ge = sum(v >= args.iou_min for v in vals)
        rows.append({"video_id": vid, "modality": mod, "class_name": cls, "kind": kind, "split": ctx["split"][vid]["split"],
                     "pairs": len(vals), "iou_median": round(s[len(s) // 2], 4), "iou_p10": round(s[int(0.1 * (len(s) - 1))], 4),
                     "frac_iou_ge_min": round(ge / len(vals), 4)})
        g = groups[f"{mod}|{cls}|{kind}"]
        g["pairs"] += len(vals); g["ge"] += ge; g["videos"] += 1
    write_csv(ev / "offset_sensitivity_per_video.csv", rows)
    summary = {k: {**g, "frac_iou_ge_min": round(g["ge"] / g["pairs"], 4) if g["pairs"] else None,
                   "passes": bool(g["pairs"] and g["ge"] / g["pairs"] >= args.iou_frac)}
               for k, g in sorted(groups.items())}
    (ev / "offset_sensitivity_summary.json").write_text(json.dumps(
        {"iou_min": args.iou_min, "iou_frac_required": args.iou_frac, "groups": summary}, indent=2), encoding="utf-8")
    return summary


def stage_offset_sheets(ctx, args, data: Path, ev: Path, labels: dict) -> dict:
    """Bang xem mu: tren frame i ve 2 hop A/B = nhan i va nhan i+1 (gan mau ngau nhien, khoa dap an rieng).
    Nhom doi chung (equal) phai chon nhan i; neu khong, nguoi xem/khung hinh khong dang tin."""
    import cv2
    import numpy as np
    rng = random.Random(args.seed)
    pool = defaultdict(list)
    for vid in select_videos(ctx, args):
        if ctx["split"][vid]["split"] != "train":
            continue
        a = ctx["audit"][vid]
        kind = label_kind(int(a["label_entries"]), int(a["frames_decoded"]))
        if kind in ("plus1", "equal"):
            pool[(ctx["split"][vid]["modality"], ctx["split"][vid]["class_name"], kind)].append(vid)
    picks = []
    for key in sorted(pool):
        vids = sorted(pool[key]); rng.shuffle(vids)
        picks += [(key, v) for v in vids[:(args.sheet_plus1 if key[2] == "plus1" else args.sheet_control)]]
    tiles, key_rows, review_rows = [], [], []
    for (mod, cls, kind), vid in picks:
        boxes = labels.get(vid) or load_labels(data / f"Video_{mod}" / f"{vid}_LABELS.mat")
        cand = []
        for i in range(len(boxes) - 1):
            b0, b1 = boxes[i], boxes[i + 1]
            if isinstance(b0, tuple) and isinstance(b1, tuple):
                jump = math.hypot((b0[0] + b0[2] / 2) - (b1[0] + b1[2] / 2), (b0[1] + b0[3] / 2) - (b1[1] + b1[3] / 2))
                cand.append((jump, i))
        cand.sort(reverse=True)
        chosen = sorted(i for _, i in cand[:2] if _ > 0)
        if not chosen:
            continue
        cap = cv2.VideoCapture(str(data / f"Video_{mod}" / f"{vid}.mp4"))
        i, need = 0, set(chosen)
        while need:
            ok, frame = cap.read()
            if not ok:
                break
            if i in need:
                need.discard(i)
                h0, h1 = boxes[i], boxes[i + 1]
                x0 = min(h0[0], h1[0]); y0 = min(h0[1], h1[1])
                x1 = max(h0[0] + h0[2], h1[0] + h1[2]); y1 = max(h0[1] + h0[3], h1[1] + h1[3])
                pad = max(24.0, 1.0 * max(x1 - x0, y1 - y0))
                H, W = frame.shape[:2]
                cx0, cy0 = int(max(0, x0 - pad)), int(max(0, y0 - pad))
                cx1, cy1 = int(min(W, x1 + pad)), int(min(H, y1 + pad))
                crop = frame[cy0:cy1, cx0:cx1].copy()
                scale = 220.0 / max(crop.shape[:2])
                crop = cv2.resize(crop, (max(1, int(crop.shape[1] * scale)), max(1, int(crop.shape[0] * scale))),
                                  interpolation=cv2.INTER_NEAREST)
                a_is_offset0 = rng.random() < 0.5
                for box, color, tag in ((h0 if a_is_offset0 else h1, (0, 220, 0), "A"),
                                        (h1 if a_is_offset0 else h0, (255, 0, 255), "B")):
                    p1 = (int((box[0] - cx0) * scale), int((box[1] - cy0) * scale))
                    p2 = (int((box[0] + box[2] - cx0) * scale), int((box[1] + box[3] - cy0) * scale))
                    cv2.rectangle(crop, p1, p2, color, 1)
                tile = np.full((250, 230, 3), 255, np.uint8)
                tile[:crop.shape[0], :crop.shape[1]] = crop
                tid = f"T{len(tiles) + 1:03d}"
                cv2.putText(tile, f"{tid} A=xanh B=hong", (2, 244), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
                tiles.append(tile)
                key_rows.append({"tile": tid, "video_id": vid, "frame_index": i, "group": kind, "modality": mod,
                                 "class_name": cls, "A_is": "label_i (offset0)" if a_is_offset0 else "label_i+1 (offset1)"})
                review_rows.append({"tile": tid, "sheet": "", "choice_A_B_UNCLEAR": "", "reviewer": "", "notes": ""})
            i += 1
        cap.release()
    order = list(range(len(tiles))); rng.shuffle(order)          # tron thu tu de nguoi xem khong doan nhom
    sheets_dir = ev / "offset_review_sheets"; sheets_dir.mkdir(parents=True, exist_ok=True)
    per = 12
    for s in range(0, len(order), per):
        idx = order[s:s + per]
        rows = []
        for r in range(0, len(idx), 4):
            row = [tiles[j] for j in idx[r:r + 4]]
            while len(row) < 4:
                row.append(np.full((250, 230, 3), 255, np.uint8))
            rows.append(np.hstack(row))
        name = f"offset_sheet_{s // per + 1:02d}.jpg"
        cv2.imwrite(str(sheets_dir / name), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
        for j in idx:
            review_rows[j]["sheet"] = name
    review_rows = [review_rows[j] for j in order]
    write_csv(ev / "offset_review.csv", review_rows)
    write_csv(ev / "offset_review_KEY_do_not_open_before_review.csv", key_rows)
    return {"tiles": len(tiles), "sheets": math.ceil(len(tiles) / per)}


def stage_decide(ctx, args, sens: dict, ev: Path) -> list[dict]:
    rows = []
    for vid in select_videos(ctx, args):
        s, a = ctx["split"][vid], ctx["audit"][vid]
        kind = label_kind(int(a["label_entries"]), int(a["frames_decoded"]))
        gkey = f"{s['modality']}|{s['class_name']}|{kind}"
        rv = ctx["review"].get(vid, {})
        # Uu tien: verdict (xac nhan cuoi) > review_quang_v2 (review ky, W3) > review_quang (so bo, W2)
        rcol = next((c for c in REVIEW_COLUMNS if rv.get(c, "").strip()), "")
        rval = rv.get(rcol, "").strip().upper() if rcol else ""
        include, offset, reason = True, 0, ""
        if rval == "SAI_NHAN" and args.exclude_review_flag:
            include, reason = False, f"{rcol}=SAI_NHAN"
        elif kind in ("minus", "plusN"):
            include, reason = False, f"label_entries-frames={int(a['label_entries']) - int(a['frames_decoded'])}: khong biet canh nhan"
        elif kind == "plus1":
            if args.plus1_policy == "exclude":
                include, reason = False, "plus1 bi loai theo --plus1-policy exclude"
            elif not sens.get(gkey, {}).get("passes", False) and s["all_absent"] != "True":
                include, reason = False, f"plus1: nhom {gkey} khong dat nguong nhay cam IoU"
            else:
                offset = 1 if args.plus1_policy == "offset1" else 0
                reason = f"plus1, {args.plus1_policy}"
        rows.append({"video_id": vid, "split": s["split"], "modality": s["modality"], "class_name": s["class_name"],
                     "kind": kind, "all_absent": s["all_absent"], "include": include, "label_offset": offset,
                     "reason": reason, "review_column": rcol, "review_value": rval})
    write_csv(ev / "inclusion_decisions.csv", rows)
    return rows


def stage_export(ctx, args, data: Path, ds: Path, decisions: list[dict], labels: dict) -> list[dict]:
    import cv2
    for sp in args.splits:
        (ds / "images" / sp).mkdir(parents=True, exist_ok=True)
        (ds / "labels" / sp).mkdir(parents=True, exist_ok=True)
    manifest, skipped = [], Counter()
    todo = [d for d in decisions if d["include"]]
    for n, d in enumerate(todo, 1):
        vid, mod, sp, off = d["video_id"], d["modality"], d["split"], int(d["label_offset"])
        boxes = labels.get(vid) or load_labels(data / f"Video_{mod}" / f"{vid}_LABELS.mat")
        cap = cv2.VideoCapture(str(data / f"Video_{mod}" / f"{vid}.mp4"))
        i = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if i % args.stride == 0:
                j = i + off
                if j >= len(boxes):
                    skipped["beyond_labels"] += 1
                else:
                    b = boxes[j]
                    H, W = frame.shape[:2]
                    line, rec = "", {"bbox_area_px": "", "size_bucket": ""}
                    if b == "MALFORMED":
                        skipped["malformed"] += 1; i += 1; continue
                    if isinstance(b, tuple):
                        x0, y0 = max(0.0, b[0]), max(0.0, b[1])
                        x1, y1 = min(float(W), b[0] + b[2]), min(float(H), b[1] + b[3])
                        if x1 - x0 < 1 or y1 - y0 < 1:
                            skipped["degenerate_after_clip"] += 1; i += 1; continue
                        cid = CLASS_ID[d["class_name"]]
                        line = f"{cid} {(x0 + x1) / 2 / W:.6f} {(y0 + y1) / 2 / H:.6f} {(x1 - x0) / W:.6f} {(y1 - y0) / H:.6f}\n"
                        area = (x1 - x0) * (y1 - y0)
                        rec = {"bbox_area_px": round(area, 1), "size_bucket": size_bucket(area)}
                    stem = f"{vid}_f{i:05d}"
                    img = ds / "images" / sp / f"{stem}.jpg"
                    cv2.imwrite(str(img), frame, [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])
                    (ds / "labels" / sp / f"{stem}.txt").write_text(line, encoding="utf-8")
                    manifest.append({"image": f"images/{sp}/{stem}.jpg", "split": sp, "video_id": vid, "frame_index": i,
                                     "label_index": j, "class_name": d["class_name"], "has_bbox": int(bool(line)),
                                     "width": W, "height": H, **rec, "sha256": sha256(img)})
            i += 1
        cap.release()
        if n % 25 == 0:
            LOG.info("export %d/%d video", n, len(todo))
    (ds / "data.yaml").write_text(
        "# Duong dan 'path' duoc w3_train_baseline.py ghi de khi chay\npath: .\ntrain: images/train\nval: images/val\n"
        f"nc: {len(CLASS_NAMES)}\nnames: {json.dumps(CLASS_NAMES)}\n", encoding="utf-8")
    ctx["skipped"] = dict(skipped)
    return manifest


def stage_verify(ctx, args, ds: Path, ev: Path, manifest: list[dict], decisions: list[dict]) -> dict:
    problems = []
    vid_split = defaultdict(set)
    for m in manifest:
        vid_split[m["video_id"]].add(m["split"])
    multi = [v for v, s in vid_split.items() if len(s) > 1]
    if multi:
        problems.append(f"video o nhieu split: {multi[:5]}")
    if any(m["split"] == "test" for m in manifest):
        problems.append("co anh test trong du lieu xuat")
    for sp in args.splits:
        imgs = {p.stem for p in (ds / "images" / sp).glob("*.jpg")}
        txts = {p.stem for p in (ds / "labels" / sp).glob("*.txt")}
        if imgs != txts:
            problems.append(f"{sp}: anh/nhan khong khop ({len(imgs ^ txts)} file)")
        for t in (ds / "labels" / sp).glob("*.txt"):
            for line in t.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                ok = len(parts) == 5 and parts[0].isdigit() and int(parts[0]) < len(CLASS_NAMES) \
                    and all(0.0 <= float(v) <= 1.0 for v in parts[1:]) and float(parts[3]) > 0 and float(parts[4]) > 0
                if not ok:
                    problems.append(f"nhan sai dinh dang: {t.name}: {line}")
                    break
    stats = defaultdict(Counter)
    for m in manifest:
        k = (m["split"], m["class_name"])
        stats[k]["images"] += 1
        stats[k]["with_bbox"] += m["has_bbox"]
        if m["size_bucket"]:
            stats[k][m["size_bucket"]] += 1
    stat_rows = [{"split": k[0], "class_name": k[1], "images": c["images"], "with_bbox": c["with_bbox"],
                  "negatives": c["images"] - c["with_bbox"], "small": c["small"], "medium": c["medium"], "large": c["large"]}
                 for k, c in sorted(stats.items())]
    write_csv(ev / "dataset_stats.csv", stat_rows,
              ["split", "class_name", "images", "with_bbox", "negatives", "small", "medium", "large"])
    with gzip.open(ev / "yolo_manifest.csv.gz", "wt", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(manifest[0]) if manifest else ["empty"])
        w.writeheader(); w.writerows(manifest)
    fingerprint = hashlib.sha256("\n".join(f"{m['image']} {m['sha256']}" for m in sorted(manifest, key=lambda r: r["image"]))
                                 .encode()).hexdigest()
    inc = Counter((d["split"], d["include"]) for d in decisions)
    card = {
        "dataset_version": args.dataset_version, "source": "Svanstrom Drone-detection-dataset (CC0-1.0 theo repo)",
        "split_version": "v1", "modalities": args.modalities, "splits_exported": args.splits, "stride": args.stride,
        "plus1_policy": args.plus1_policy, "iou_min": args.iou_min, "iou_frac": args.iou_frac,
        "exclude_review_flag": args.exclude_review_flag, "jpeg_quality": args.jpeg_quality, "seed": args.seed,
        "inputs": ctx["info"], "videos_included": {f"{k[0]}|{'in' if k[1] else 'out'}": v for k, v in sorted(inc.items())},
        "images": len(manifest), "frames_skipped": ctx.get("skipped", {}), "content_fingerprint_sha256": fingerprint,
        "classes": CLASS_NAMES, "problems": problems, "commit": args.commit,
    }
    (ev / "dataset_card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(ev / "dataset_card.json", ds / "dataset_card.json")
    if problems:
        raise RuntimeError("; ".join(problems[:5]))
    return {"images": len(manifest), "fingerprint": fingerprint}


def stage_pack(args, ds: Path, ev: Path) -> dict:
    """Zip thu muc du lieu (khong nen lai JPEG), kiem tra lai zip, roi xoa thu muc goc."""
    files = sorted(p for p in ds.rglob("*") if p.is_file())
    z = args.out / f"{args.dataset_version}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        for p in files:
            zf.write(p, p.relative_to(ds.parent))
    with zipfile.ZipFile(z) as zf:
        names, bad = zf.namelist(), zf.testzip()
    if bad is not None or len(names) != len(files):
        raise RuntimeError(f"zip loi: bad={bad}, {len(names)} entry / {len(files)} file")
    info = {"zip": z.name, "sha256": sha256(z), "bytes": z.stat().st_size, "entries": len(names),
            "root": args.dataset_version, "compression": "ZIP_STORED"}
    (ev / "dataset_zip.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    shutil.rmtree(ds)
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--split-csv", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True, help="annotation_audit.csv (Kaggle run 01)")
    ap.add_argument("--review", type=Path, default=None, help="review_assignment_w2.csv (cot review_quang)")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--modalities", nargs="+", default=["V"], choices=["V", "IR"])
    ap.add_argument("--splits", nargs="+", default=["train", "val"], choices=["train", "val"])
    ap.add_argument("--stride", type=int, default=10)
    ap.add_argument("--plus1-policy", choices=["offset0", "offset1", "exclude"], default="offset0")
    ap.add_argument("--iou-min", type=float, default=0.5)
    ap.add_argument("--iou-frac", type=float, default=0.90)
    ap.add_argument("--no-exclude-review-flag", dest="exclude_review_flag", action="store_false")
    ap.add_argument("--sheet-plus1", type=int, default=12, help="so video plus1 moi nhom cho bang xem mu")
    ap.add_argument("--sheet-control", type=int, default=6, help="so video doi chung moi nhom")
    ap.add_argument("--jpeg-quality", type=int, default=95)
    ap.add_argument("--seed", type=int, default=20261013)
    ap.add_argument("--dataset-version", default="e1-yolo-v1")
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--skip-export", action="store_true", help="chi chay sensitivity + bang xem (nhanh)")
    ap.add_argument("--pack-zip", action="store_true",
                    help="dong goi thu muc du lieu thanh <dataset-version>.zip (ZIP_STORED) roi xoa thu muc: output it file, "
                         "Kaggle gan input on dinh hon ~14k file nho")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ev = args.out / "w3_export_evidence"; ds = args.out / args.dataset_version
    for p in (ev, ds):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    status, ctx, sens, labels, decisions, manifest = {}, {}, {}, {}, [], []

    def run(name, fn):
        try:
            res = fn()
            status[name] = {"status": "OK", **(res if isinstance(res, dict) and len(json.dumps(res, default=str)) < 4000 else {})}
            return res
        except Exception as exc:  # noqa: BLE001
            LOG.error("stage %s FAILED: %s", name, exc)
            status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
            return None
        finally:
            (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    run("env", lambda: stage_env(ev, args.commit))
    ctx = run("inputs", lambda: stage_inputs(args, ev)) or {}
    if not ctx:
        return 1
    data = find_video_dir(args.data_root)
    sens = run("sensitivity", lambda: stage_sensitivity(ctx, args, data, ev, labels)) or {}
    run("offset_sheets", lambda: stage_offset_sheets(ctx, args, data, ev, labels))
    decisions = run("decide", lambda: stage_decide(ctx, args, sens, ev)) or []
    if args.skip_export:
        status["export"] = {"status": "SKIPPED"}
    elif decisions:
        manifest = run("export", lambda: stage_export(ctx, args, data, ds, decisions, labels)) or []
        if manifest:
            ok = run("verify", lambda: stage_verify(ctx, args, ds, ev, manifest, decisions))
            if ok and args.pack_zip:
                run("pack", lambda: stage_pack(args, ds, ev))

    def bundle():
        z = args.out / "w3_export_evidence.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(ev.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(ev.parent))
        return {"zip": z.name, "sha256": sha256(z)}
    run("bundle", bundle)
    print(json.dumps({k: v.get("status") for k, v in status.items()}, indent=2))
    return 0 if all(v.get("status") in ("OK", "SKIPPED") for v in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
