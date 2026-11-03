#!/usr/bin/env python3
"""Xuat 40 anh val "am tinh" cua e1-yolo-v1 de An xem tan mat (W6, review cua An tren #89; phan tich nham lan W7).

Danh sach anh, du doan run 13 va hop GT gan nhat da tinh offline trong repo:
`results/W06/val_negative_frames/val_negative_frames.csv` (scripts/reporting/val_negative_frames.py).
Job nay chi lay dung cac anh JPEG ma metric run 13 da dung (kiem SHA-256 voi yolo_manifest.csv.gz), kiem file nhan
rong, roi ghi:
  originals/<stem>.jpg            anh goc, chep nguyen byte (640x512);
  annotated/<stem>_review.jpg     ve du doan run 13 conf >= 0,25 (lop, conf) va hop GT gan nhat (net dut vang, "GT f<k>");
  overview.jpg                    luoi 8x5 de xem nhanh;
  review_index.csv                index + SHA-256 tung anh goc;
  stage_status.json, env.json.
Khong can GPU, khong chay model (du doan lay tu predictions.json cua run 13).

    python w6_negative_frames_export.py --data-dir /tmp/e1data/e1-yolo-v1 --manifest yolo_manifest.csv.gz \
        --index val_negative_frames.csv --out /kaggle/working --commit <SHA>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import platform
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

LOG = logging.getLogger("w6_negframes")
TAG = "w6_negframes"
PAD = 3   # px; hop ve noi rong ra ngoai hop that de khong che pixel cua vat nho (anh goc nam rieng trong originals/)
COLORS = {"Airplane": (255, 128, 0), "Bird": (0, 200, 0), "Drone": (255, 0, 255), "Helicopter": (0, 165, 255)}   # BGR


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def parse_boxes(classes: str, confs: str, boxes: str) -> list[tuple[str, float, tuple]]:
    """Doc cac cot run13_* cua index (cach nhau boi khoang trang / ' | ')."""
    if not boxes.strip():
        return []
    cl, cf = classes.split(), [float(x) for x in confs.split()]
    bx = [tuple(float(v) for v in b.split(",")) for b in boxes.split(" | ")]
    if not (len(cl) == len(cf) == len(bx)):
        raise ValueError(f"so lop/conf/hop khong khop: {classes!r} {confs!r} {boxes!r}")
    return list(zip(cl, cf, bx))


def dashed_rect(img, x, y, w, h, color, step=6):
    import cv2
    x0, y0, x1, y1 = int(round(x)), int(round(y)), int(round(x + w)), int(round(y + h))
    for a, b, fixed, horiz in ((x0, x1, y0, True), (x0, x1, y1, True), (y0, y1, x0, False), (y0, y1, x1, False)):
        for s in range(a, b, 2 * step):
            e = min(s + step, b)
            p, q = ((s, fixed), (e, fixed)) if horiz else ((fixed, s), (fixed, e))
            cv2.line(img, p, q, (0, 0, 0), 2)       # vien den de thay tren nen troi sang
            cv2.line(img, p, q, color, 1)


def text(img, s, org, color):
    import cv2
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)


def annotate(src: Path, dst: Path, row: dict) -> tuple[int, int]:
    import cv2
    img = cv2.imread(str(src))
    if img is None:
        raise ValueError(f"khong doc duoc anh {src}")
    h, w = img.shape[:2]
    if row["nearest_gt_xywh"]:
        gx, gy, gw, gh = (float(v) for v in row["nearest_gt_xywh"].split(","))
        dashed_rect(img, gx - 2 * PAD, gy - 2 * PAD, gw + 4 * PAD, gh + 4 * PAD, (0, 255, 255))
        text(img, f"GT f{row['nearest_gt_frame']}", (int(gx), max(26, int(gy) - 4)), (0, 255, 255))
    for cls, conf, (x, y, bw, bh) in parse_boxes(row["run13_classes"], row["run13_conf"], row["run13_boxes_xywh"]):
        c = COLORS.get(cls, (0, 0, 255))
        p0, p1 = (int(x) - PAD, int(y) - PAD), (int(x + bw) + PAD, int(y + bh) + PAD)   # noi rong de khong che vat
        cv2.rectangle(img, p0, p1, (0, 0, 0), 2)
        cv2.rectangle(img, p0, p1, c, 1)
        text(img, f"{cls} {conf:.2f}", (int(x), min(h - 4, int(y + bh) + 12)), c)
    head = f"#{row['sample_no']} {row['video_id']} f{row['frame']} | {row['cause']} | {row['role']} | nhan: rong"
    cv2.rectangle(img, (0, 0), (w, 16), (0, 0, 0), -1)
    cv2.putText(img, head, (4, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    if not cv2.imwrite(str(dst), img, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise OSError(f"cv2.imwrite that bai: {dst}")
    return w, h


def overview(paths: list[Path], dst: Path, cols: int = 8, tile=(320, 256)) -> None:
    import cv2
    import numpy as np
    rows = (len(paths) + cols - 1) // cols
    sheet = np.zeros((rows * tile[1], cols * tile[0], 3), dtype=np.uint8)
    for i, p in enumerate(paths):
        im = cv2.resize(cv2.imread(str(p)), tile)
        r, c = divmod(i, cols)
        sheet[r * tile[1]:(r + 1) * tile[1], c * tile[0]:(c + 1) * tile[0]] = im
    if not cv2.imwrite(str(dst), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise OSError(f"cv2.imwrite that bai: {dst}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, required=True, help="thu muc e1-yolo-v1 da giai nen (images/val, labels/val)")
    ap.add_argument("--manifest", type=Path, required=True, help="yolo_manifest.csv.gz (SHA-256 tung anh)")
    ap.add_argument("--index", type=Path, required=True, help="val_negative_frames.csv tu repo")
    ap.add_argument("--expect", type=int, default=40, help="so anh mong doi")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--overwrite", action="store_true", help="cho phep xoa thu muc bang chung cung tag")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ev = a.out / TAG
    if ev.exists() and any(ev.iterdir()):
        if not a.overwrite:
            raise SystemExit(f"{ev} da co bang chung; dung --overwrite neu chac chan muon xoa")
        shutil.rmtree(ev)
    ev.mkdir(parents=True, exist_ok=True)
    status, ctx = {}, {}

    def run(name, fn):
        if any(v["status"] != "OK" for v in status.values()):
            status[name] = {"status": "SKIPPED"}
        else:
            try:
                status[name] = {"status": "OK", **(fn() or {})}
            except Exception as exc:  # noqa: BLE001
                LOG.error("%s FAILED: %s", name, exc)
                status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
        (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    def env():
        info = {"python": sys.version.split()[0], "platform": platform.platform(), "commit": a.commit,
                "args": {k: str(v) for k, v in vars(a).items()}}
        import cv2
        info["cv2"] = cv2.__version__
        (ev / "env.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    def inputs():
        with a.index.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if len(rows) != a.expect:
            raise ValueError(f"{a.index}: {len(rows)} dong, mong doi {a.expect}")
        with gzip.open(a.manifest, "rt", encoding="utf-8") as fh:
            man = {m["image"]: m for m in csv.DictReader(fh)}
        bad = []
        for r in rows:
            img = a.data_dir / r["image"]
            lab = a.data_dir / r["image"].replace("images/", "labels/").replace(".jpg", ".txt")
            m = man.get(r["image"])
            if m is None or m.get("split") != "val":
                bad.append(f"{r['image']}: khong co trong manifest val")
            elif not img.is_file() or sha256(img) != m["sha256"]:
                bad.append(f"{r['image']}: thieu anh hoac SHA-256 khac manifest")
            elif not lab.is_file() or lab.read_text(encoding="utf-8").strip():
                bad.append(f"{lab.name}: file nhan khong ton tai hoac khong rong")
            else:
                r["image_sha256"] = m["sha256"]
        if bad:
            raise ValueError(f"{len(bad)} loi, vd: {bad[:3]}")
        ctx["rows"] = rows
        return {"images": len(rows), "index_sha256": sha256(a.index), "manifest_sha256": sha256(a.manifest)}

    def export():
        (ev / "originals").mkdir(); (ev / "annotated").mkdir()
        ann, sizes = [], set()
        for r in ctx["rows"]:
            src = a.data_dir / r["image"]
            stem = Path(r["image"]).stem
            shutil.copy2(src, ev / "originals" / f"{stem}.jpg")
            dst = ev / "annotated" / f"{stem}_review.jpg"
            sizes.add(annotate(src, dst, r)); ann.append(dst)
        overview(ann, ev / "overview.jpg")
        with (ev / "review_index.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(ctx["rows"][0])); w.writeheader(); w.writerows(ctx["rows"])
        return {"originals": len(ann), "sizes": sorted(f"{x}x{y}" for x, y in sizes),
                "with_pred": sum(r["role"] == "FP" for r in ctx["rows"])}

    def bundle():
        z = a.out / f"{TAG}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
            for p in sorted(ev.rglob("*")):
                if p.is_file() and p.name != "stage_status.json":
                    zf.write(p, p.relative_to(a.out).as_posix())
        return {"zip": z.name}

    for name, fn in (("env", env), ("inputs", inputs), ("export", export), ("bundle", bundle)):
        run(name, fn)
    z = a.out / f"{TAG}.zip"
    if status.get("bundle", {}).get("status") == "OK":
        with zipfile.ZipFile(z, "a", zipfile.ZIP_STORED) as zf:
            zf.write(ev / "stage_status.json", f"{TAG}/stage_status.json")
    return 0 if all(v["status"] == "OK" for v in status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
