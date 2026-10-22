#!/usr/bin/env python3
"""E1 W3 Kaggle job: bang review nhan v2 (ky hon v1) cho cac video trong review_assignment_w2.csv.

v1 (W2): 3 frame/video, anh thu nho. v2: 8 frame/video trai deu tren pham vi nhan + frame co buoc nhay
tam lon nhat; moi frame gom anh toan canh (co hop) + anh phong to quanh hop. Nhan dung theo offset 0
(frame i <-> nhan i), dung chinh sach ADR-0004.

    python w3_review_sheets.py --data-root /kaggle/input/e1-svanstrom-raw \
        --review review_assignment_w2.csv --out /kaggle/working --commit <sha>

Dau ra: w3_review_v2/sheets/*.jpg (2 video/bang), review_v2_index.csv, stage_status.json, w3_review_v2.zip.
Chi doc du lieu goc. Seed khong can (chon frame tat dinh).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import math
import shutil
import traceback
import zipfile
from pathlib import Path

LOG = logging.getLogger("w3_review")
TILE_W, FULL_H, ZOOM_H, CAP_H = 160, 128, 160, 16
PER_VIDEO, PER_SHEET = 8, 2


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_data(root: Path) -> Path:
    if (root / "Data" / "Video_V").is_dir():
        return root / "Data"
    for cand in sorted(root.rglob("Video_V")):
        if cand.is_dir() and cand.parent.name == "Data" and (cand.parent / "Video_IR").is_dir():
            return cand.parent
    raise SystemExit(f"Khong tim thay Data/Video_V, Data/Video_IR duoi {root}")


MALFORMED = "MALFORMED"


def to_box(b):
    """(x, y, w, h) neu hop le; None neu frame vang nhan (b None/rong); MALFORMED neu nhan loi.

    Nhan loi (khong du 4 so, NaN/inf, w/h <= 0) KHONG duoc coi la frame khong co nhan (review An, PR #23)."""
    if b is None:
        return None
    vals = list(b)
    if len(vals) == 0:
        return None
    try:
        x, y, w, h = (float(v) for v in vals[:4])
    except Exception:
        return MALFORMED
    if any(math.isnan(v) or math.isinf(v) for v in (x, y, w, h)) or w <= 0 or h <= 0:
        return MALFORMED
    return (x, y, w, h)


def is_box(b) -> bool:
    return isinstance(b, tuple)


def pick_frames(boxes: list, n_frames: int) -> list[int]:
    """8 frame: trai deu tren [0, min(n_frames, len(boxes))) + frame co buoc nhay tam lon nhat."""
    n = min(n_frames, len(boxes))
    if n <= 0:
        return []
    base = sorted({round(k * (n - 1) / (PER_VIDEO - 2)) for k in range(PER_VIDEO - 1)}) if n > 1 else [0]
    best, jump = None, -1.0
    for i in range(n - 1):
        a, b = boxes[i], boxes[i + 1]
        if is_box(a) and is_box(b):
            j = math.hypot(a[0] + a[2] / 2 - b[0] - b[2] / 2, a[1] + a[3] / 2 - b[1] - b[3] / 2)
            if j > jump:
                best, jump = i, j
    if best is not None and best not in base:
        base.append(best)
    return sorted(base)[:PER_VIDEO]


def render_tile(frame, box, idx: int):
    import cv2
    import numpy as np
    H, W = frame.shape[:2]
    tile = np.full((FULL_H + ZOOM_H + CAP_H, TILE_W, 3), 255, np.uint8)
    s = min(TILE_W / W, FULL_H / H)
    full = cv2.resize(frame, (int(W * s), int(H * s)), interpolation=cv2.INTER_AREA)
    if is_box(box):
        x, y, w, h = box
        cv2.rectangle(full, (int(x * s), int(y * s)), (int((x + w) * s) + 1, int((y + h) * s) + 1), (0, 0, 255), 1)
    tile[:full.shape[0], :full.shape[1]] = full
    if is_box(box):
        x, y, w, h = box
        side = max(48.0, 3.0 * max(w, h))
        cx, cy = x + w / 2, y + h / 2
        x0, y0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
        x1, y1 = int(min(W, cx + side / 2)), int(min(H, cy + side / 2))
        crop = frame[y0:y1, x0:x1].copy()
        z = min(TILE_W / max(1, crop.shape[1]), ZOOM_H / max(1, crop.shape[0]))
        crop = cv2.resize(crop, (max(1, int(crop.shape[1] * z)), max(1, int(crop.shape[0] * z))), interpolation=cv2.INTER_NEAREST)
        cv2.rectangle(crop, (int((x - x0) * z), int((y - y0) * z)), (int((x + w - x0) * z), int((y + h - y0) * z)), (0, 0, 255), 1)
        tile[FULL_H:FULL_H + crop.shape[0], :crop.shape[1]] = crop
        txt = f"f{idx} {int(w)}x{int(h)}px"
    elif box == MALFORMED:
        cv2.putText(tile, "NHAN LOI (malformed)", (8, FULL_H + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        txt = f"f{idx} (MALFORMED)"
    else:
        cv2.putText(tile, "khong co nhan", (8, FULL_H + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        txt = f"f{idx} (absent)"
    cv2.putText(tile, txt, (2, FULL_H + ZOOM_H + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    return tile


def video_row(data: Path, vid: str):
    import cv2
    import numpy as np
    from mcos_decoder import load_groundtruth  # type: ignore
    mod = vid.split("_")[0]
    mp4, mat = data / f"Video_{mod}" / f"{vid}.mp4", data / f"Video_{mod}" / f"{vid}_LABELS.mat"
    boxes = [to_box(b) for b in load_groundtruth(mat)]
    if not mp4.is_file():
        raise FileNotFoundError(mp4)
    cap = cv2.VideoCapture(str(mp4))
    if not cap.isOpened():
        raise RuntimeError(f"VideoCapture khong mo duoc {mp4}")
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    picks = pick_frames(boxes, n_frames)
    need, tiles, i = set(picks), {}, 0
    while need:
        ok, frame = cap.read()
        if not ok:
            break
        if i in need:
            need.discard(i)
            tiles[i] = render_tile(frame, boxes[i] if i < len(boxes) else None, i)
        i += 1
    cap.release()
    missing = sorted(set(picks) - set(tiles))
    if missing:
        raise RuntimeError(f"{vid}: khong doc duoc frame {missing} (doc duoc {i} frame)")
    row = [tiles[k] for k in sorted(tiles)]
    while len(row) < PER_VIDEO:
        row.append(np.full((FULL_H + ZOOM_H + CAP_H, TILE_W, 3), 255, np.uint8))
    head = np.full((22, TILE_W * PER_VIDEO, 3), 235, np.uint8)
    cv2.putText(head, f"{vid}  labels={len(boxes)} frames={n_frames}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    n_bad = sum(1 for b in boxes if b == MALFORMED)
    return np.vstack([head, np.hstack(row)]), sorted(tiles), len(boxes), n_frames, n_bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--review", type=Path, required=True, help="review_assignment_w2.csv (danh sach video can xem)")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import cv2
    import numpy as np

    ev = args.out / "w3_review_v2"
    if ev.exists():
        shutil.rmtree(ev)
    (ev / "sheets").mkdir(parents=True)
    status = {"inputs": {"review_sha256": sha256(args.review), "commit": args.commit}}
    with args.review.open(encoding="utf-8-sig") as fh:
        vids = [r["video_id"] for r in csv.DictReader(fh)]
    data = find_data(args.data_root)
    index, failed, rows, sheet_no = [], [], [], 0

    def flush():
        nonlocal rows, sheet_no
        if not rows:
            return
        sheet_no += 1
        name = f"review_v2_{sheet_no:03d}.jpg"
        dst = ev / "sheets" / name
        if not cv2.imwrite(str(dst), np.vstack([r[0] for r in rows]), [cv2.IMWRITE_JPEG_QUALITY, 90]) or not dst.is_file():
            raise RuntimeError(f"cv2.imwrite that bai: {dst}")
        for _, rec in rows:
            rec["sheet"] = name
            index.append(rec)
        rows = []

    for n, vid in enumerate(vids, 1):
        try:
            img, frames, n_labels, n_frames, n_bad = video_row(data, vid)
            rows.append((img, {"video_id": vid, "frames_shown": " ".join(map(str, frames)), "label_entries": n_labels,
                               "malformed_labels": n_bad, "frames_prop": n_frames, "sheet": ""}))
        except Exception as exc:  # noqa: BLE001
            failed.append({"video_id": vid, "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-400:]})
        if len(rows) == PER_SHEET:
            flush()
        if n % 50 == 0:
            LOG.info("%d/%d", n, len(vids))
    flush()
    with (ev / "review_v2_index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["sheet", "video_id", "frames_shown", "label_entries", "malformed_labels", "frames_prop"])
        w.writeheader(); w.writerows(index)
    status["sheets"] = {"status": "OK" if not failed else "PARTIAL", "videos_requested": len(vids),
                        "videos_rendered": len(index), "sheets": sheet_no, "failed": failed,
                        "videos_with_malformed_labels": [r["video_id"] for r in index if r["malformed_labels"]],
                        "malformed_label_entries": sum(r["malformed_labels"] for r in index)}
    (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    z = args.out / "w3_review_v2.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(ev.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(ev.parent))
    print(json.dumps({"videos": len(index), "sheets": sheet_no, "failed": len(failed), "zip_sha256": sha256(z)}))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
