#!/usr/bin/env python3
"""E1 W8 Kaggle job (GPU, phan cua run 17): vi sao detection tren video co nhieu hop trung cung lop hon du doan anh val?

Phat hien tham do W7 (results/W07/postproc/exploratory.json): tren cung 1.194 frame val, conf >= 0,25,
hop trung cung lop IoU 0,5-0,7 la 11,7% o detection video (run 14, model.predict tren frame giai ma tu mp4)
so voi 0,6% o du doan anh val (run 13, model.val tren anh JPG). Job nay tach nguyen nhan bang 4 dieu kien,
cung weights, conf 0,1, NMS IoU 0,7, imgsz 640, chi doi MOT yeu to moi lan:

  jpg_fp32    model.predict(anh JPG cua e1-yolo-v1, half=False)
  frame_fp32  model.predict(frame giai ma tu mp4,  half=False)   <- giong run 14
  jpg_fp16    model.predict(anh JPG,               half=True)
  frame_fp16  model.predict(frame giai ma,         half=True)

Cong tai tao: frame_fp32 phai trung detection luu cua run 14 tren cung frame (>= 99% hop, sai so 0,02 px)
neu co --run14-dets. Luat dien giai dat truoc trong docs/w8/W8_PLAN.md muc C.

    python w8_dup_diagnostic.py --data-dir /tmp/e1data/e1-yolo-v1 --manifest yolo_manifest.csv.gz \
        --data-root /kaggle/input --weights best.pt --weights-sha <sha> --out /kaggle/working --commit <sha>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import shutil
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path

LOG = logging.getLogger("w8_dup_diagnostic")
CONDITIONS = [("jpg_fp32", "jpg", False), ("frame_fp32", "frame", False), ("jpg_fp16", "jpg", True), ("frame_fp16", "frame", True)]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def iou_xywh(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def dup_count(dets: list[tuple], conf: float = 0.25, lo: float = 0.5) -> tuple[int, int]:
    """(so hop conf >= conf, so hop bi NMS cung lop IoU lo loai). dets: [(cls, conf, (x, y, w, h))].
    Giong cach dem cua scripts/experiments/w7_postproc_explore.py (len(d) - len(nms(d, 0.5, cung lop)))."""
    d = sorted((x for x in dets if x[1] >= conf), key=lambda x: -x[1])
    keep: list[tuple] = []
    for x in d:
        if all(not (k[0] == x[0] and iou_xywh(k[2], x[2]) >= lo) for k in keep):
            keep.append(x)
    return len(d), len(d) - len(keep)


def to_dets(result) -> list[tuple]:
    b = result.boxes
    out = []
    for (x1, y1, x2, y2), c, s in zip(b.xyxy.tolist(), b.cls.tolist(), b.conf.tolist()):
        out.append((int(c), round(float(s), 4), (round(x1, 2), round(y1, 2), round(x2 - x1, 2), round(y2 - y1, 2))))
    return out


def summarize(per_image: dict[str, dict[str, list]], conf: float = 0.25) -> dict:
    out = {}
    for cond in sorted({c for v in per_image.values() for c in v}):
        n = d = 0
        by_vid: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for img, conds in per_image.items():
            a, b = dup_count(conds[cond], conf)
            n += a; d += b
            vid = img.rsplit("_f", 1)[0]; by_vid[vid][0] += a; by_vid[vid][1] += b
        out[cond] = {"boxes": n, "dup_same_class_iou_0.5_0.7": d, "dup_rate": round(d / n, 4) if n else None,
                     "videos_with_dup": sum(1 for v in by_vid.values() if v[1] > 0)}
    return out


def match_rate(a: list[tuple], b: list[tuple], tol: float = 0.02) -> tuple[int, int]:
    """So hop cua a co hop cung lop trong b lech moi toa do <= tol (sau khi lam tron 2 chu so nhu run 14)."""
    used, hit = set(), 0
    for x in a:
        for j, y in enumerate(b):
            if j not in used and x[0] == y[0] and all(abs(p - q) <= tol + 1e-9 for p, q in zip(x[2], y[2])):
                used.add(j); hit += 1; break
    return hit, len(a)


def read_run14(path: Path) -> dict[int, list[tuple]]:
    d: dict[int, list[tuple]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d[int(r["frame"])].append((int(r["cls"]), float(r["conf"]), tuple(float(r[k]) for k in "xywh")))
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, required=True, help="thu muc e1-yolo-v1 da giai nen (co images/val)")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True, help="du lieu tho Svanstrom (co Data/Video_V)")
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--weights-sha", required=True)
    ap.add_argument("--run14-dets", type=Path, help="thu muc dets/ cua run 14 (cong tai tao), tuy chon")
    ap.add_argument("--conf", type=float, default=0.1)
    ap.add_argument("--iou", type=float, default=0.7)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="0")
    ap.add_argument("--max-videos", type=int, default=0, help="chi de kiem thu")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--tag", default="w8_dupdiag")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ev = a.out / a.tag
    if ev.exists():
        if not a.overwrite:
            raise SystemExit(f"{ev} da ton tai; dung --overwrite neu chac chan")
        shutil.rmtree(ev)
    ev.mkdir(parents=True)
    status: dict[str, dict] = {}

    if sha256(a.weights) != a.weights_sha:
        raise SystemExit("SHA-256 weights khac ky vong")
    with gzip.open(a.manifest, "rt", encoding="utf-8") as fh:
        man = [m for m in csv.DictReader(fh) if m["split"] == "val"]
    by_vid: dict[str, list[dict]] = defaultdict(list)
    for m in man:
        by_vid[m["video_id"]].append(m)
    vids = sorted(by_vid)[: a.max_videos] if a.max_videos else sorted(by_vid)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from w3_export_yolo import find_video_dir  # noqa: E402  (cung thu muc tren dataset e1-w3-tools)
    vdir = find_video_dir(a.data_root) / "Video_V"
    status["inputs"] = {"status": "OK", "videos": len(vids), "images": sum(len(by_vid[v]) for v in vids),
                        "weights_sha256": a.weights_sha, "conf": a.conf, "nms_iou": a.iou, "imgsz": a.imgsz, "commit": a.commit}

    import cv2
    import numpy as np
    import torch
    import ultralytics
    from ultralytics import YOLO
    model = YOLO(str(a.weights))
    status["env"] = {"status": "OK", "ultralytics": ultralytics.__version__, "torch": torch.__version__,
                     "cuda": torch.cuda.is_available(), "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else ""}
    per_image: dict[str, dict[str, list]] = {}
    pix, t0 = [], time.time()
    repro = [0, 0]
    for vid in vids:
        want = {int(m["frame_index"]): m for m in by_vid[vid]}
        cap = cv2.VideoCapture(str(vdir / f"{vid}.mp4"))
        if not cap.isOpened():
            raise RuntimeError(f"khong mo duoc {vid}.mp4")
        r14 = read_run14(a.run14_dets / f"{vid}.csv") if a.run14_dets else None
        f = 0
        while want:
            ok, frame = cap.read()
            if not ok:
                break
            if f in want:
                m = want.pop(f)
                jpg = a.data_dir / m["image"]
                if sha256(jpg) != m["sha256"]:
                    raise ValueError(f"{jpg} khac SHA-256 manifest")
                img = cv2.imread(str(jpg))
                pix.append(float(np.abs(img.astype(np.int16) - frame.astype(np.int16)).mean()))
                key = Path(m["image"]).stem
                per_image[key] = {}
                for name, src, half in CONDITIONS:
                    r = model.predict(str(jpg) if src == "jpg" else frame, conf=a.conf, iou=a.iou, imgsz=a.imgsz,
                                      device=a.device, half=half, verbose=False)[0]
                    per_image[key][name] = to_dets(r)
                if r14 is not None:
                    h, n = match_rate(per_image[key]["frame_fp32"], r14.get(f, []))
                    repro[0] += h; repro[1] += n
            f += 1
        cap.release()
        if want:
            raise RuntimeError(f"{vid}: khong doc duoc frame {sorted(want)[:5]}")
    status["predict"] = {"status": "OK", "images": len(per_image), "seconds": round(time.time() - t0, 1)}
    res = {"note": "dem hop trung cung lop IoU 0,5-0,7 o conf >= 0,25, giong w7_postproc_explore.py",
           "conditions": summarize(per_image),
           "mean_abs_pixel_diff_jpg_vs_frame": round(float(np.mean(pix)), 4) if pix else None,
           "max_mean_abs_pixel_diff": round(float(np.max(pix)), 4) if pix else None,
           "repro_frame_fp32_vs_run14": {"matched": repro[0], "boxes": repro[1],
                                         "rate": round(repro[0] / repro[1], 4) if repro[1] else None}}
    (ev / "dup_diagnostic.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with gzip.open(ev / "per_image_dets.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(per_image, fh)
    status["summary"] = {"status": "OK"}
    (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    z = a.out / f"{a.tag}_evidence.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(ev.rglob("*")):
            zf.write(p, p.relative_to(a.out))
    LOG.info("%s", json.dumps(res["conditions"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
