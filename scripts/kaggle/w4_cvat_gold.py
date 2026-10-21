#!/usr/bin/env python3
"""E1 W4 Kaggle job 11 (CPU): tao goi anh cho tap chuan CVAT (issue #24, ADR-0006).

Chon ~200 frame anh kha kien tu video train+val (KHONG dung test), gom 2 nhom:
  plus1  : video du 1 muc nhan (Drone, Bird) -> kiem chieu lech nhan
  control: video khop so nhan (Airplane, Helicopter) -> kiem do tin cay cua nguoi ve
Moi frame duoc chon phai co nhan muc i va i+1 deu la hop hop le va tam hai hop cach nhau >= --min-shift px
(neu vat dung yen thi khong phan biet duoc offset). Toi da --per-video frame/video, trai deu trong video.

Dau ra (tach rieng, KHONG dua khoa cho nguoi ve):
  cvat_package.zip : images/gold_0001.jpg..., labels.txt, README_CVAT.txt  -> gui An de ve hop
  gold_KEY.zip     : gold_key.csv (anh -> video, frame, lop, nhan i, nhan i+1) -> Quang giu, chi mo sau khi
                     An da commit file annotation
  gold_selection.json, stage_status.json -> bang chung (khong lo dap an)

    python w4_cvat_gold.py --data-root <raw> --split-csv video_split_v1.csv --audit annotation_audit.csv \
        --review review_assignment_w3.csv --out /kaggle/working --commit <sha>
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import random
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from w3_export_yolo import find_video_dir, label_kind, load_labels, sha256  # noqa: E402

LOG = logging.getLogger("w4_cvat_gold")
QUOTA = {("Drone", "plus1"): 90, ("Bird", "plus1"): 30, ("Airplane", "equal"): 40, ("Helicopter", "equal"): 40}
CVAT_README = """Tap chuan E1 (issue #24). Ve 1 hop sat vat the bay (lop: object) tren MOI anh.
Quy tac: docs/w4/cvat_gold_guide.md. Khong mo bat ky file nhan goc nao cua dataset khi ve.
Xuat ket qua: Export task -> 'YOLO 1.1' -> gui file zip cho Quang (hoac commit vao results/W04/cvat_gold/).
"""


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def center(b):
    return b[0] + b[2] / 2, b[1] + b[3] / 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--split-csv", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--review", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--seed", type=int, default=20261022)
    ap.add_argument("--per-video", type=int, default=4)
    ap.add_argument("--min-shift", type=float, default=2.0)
    ap.add_argument("--jpeg-quality", type=int, default=95)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = a.out / "w4_cvat_gold"
    if out.exists():
        shutil.rmtree(out)
    (out / "package" / "images").mkdir(parents=True)
    status, ctx = {}, {}
    rng = random.Random(a.seed)

    def run(name, fn):
        try:
            r = fn()
            status[name] = {"status": "OK", **(r if isinstance(r, dict) else {})}
            return r
        except Exception as exc:  # noqa: BLE001
            LOG.error("%s FAILED: %s", name, exc)
            status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
            return None
        finally:
            (out / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def inputs():
        split = read_csv(a.split_csv)
        audit = {r["video_id"]: r for r in read_csv(a.audit)}
        review = {r["video_id"]: r for r in read_csv(a.review)}
        pool = {}
        for r in split:
            if r["modality"] != "V" or r["split"] not in ("train", "val"):
                continue
            au = audit[r["video_id"]]
            kind = label_kind(int(au["label_entries"]), int(au["frames_decoded"]))
            rv = (review.get(r["video_id"], {}).get("review_quang_v2") or "").strip()
            if (r["class_name"], kind) in QUOTA and rv != "SAI_NHAN":
                pool.setdefault((r["class_name"], kind), []).append(r["video_id"])
        ctx.update(pool=pool, data=find_video_dir(a.data_root), audit=audit)
        return {"videos_by_group": {f"{k[0]}|{k[1]}": len(v) for k, v in pool.items()},
                "split_sha256": sha256(a.split_csv), "audit_sha256": sha256(a.audit), "review_sha256": sha256(a.review),
                "commit": a.commit, "seed": a.seed, "test_used": False}

    def select():
        chosen = []
        for key, quota in QUOTA.items():
            vids = sorted(ctx["pool"].get(key, [])); rng.shuffle(vids)
            per = max(1, min(a.per_video, math.ceil(quota / max(1, len(vids)))))
            got = []
            for vid in vids:
                if len(got) >= quota:
                    break
                lab = load_labels(ctx["data"] / "Video_V" / f"{vid}_LABELS.mat")
                n = int(ctx["audit"][vid]["frames_decoded"])
                ok = [i for i in range(1, n) if i + 1 < len(lab) and isinstance(lab[i], tuple) and isinstance(lab[i + 1], tuple)
                      and math.dist(center(lab[i]), center(lab[i + 1])) >= a.min_shift]
                if not ok:
                    continue
                step = max(1, len(ok) // per)
                picks = sorted({ok[min(len(ok) - 1, k * step + rng.randrange(step))] for k in range(per)})
                for i in picks[: quota - len(got)]:
                    got.append({"video_id": vid, "class_name": key[0], "kind": key[1], "frame_index": i,
                                "label_i": list(lab[i]), "label_i1": list(lab[i + 1])})
            chosen += got
        rng.shuffle(chosen)
        for k, c in enumerate(chosen, 1):
            c["gold_id"] = f"gold_{k:04d}"
        ctx["chosen"] = chosen
        return {"frames": len(chosen), "by_group": {f"{k[0]}|{k[1]}": sum(1 for c in chosen if (c['class_name'], c['kind']) == k) for k in QUOTA},
                "videos": len({c["video_id"] for c in chosen})}

    def extract():
        import cv2
        by_vid = {}
        for c in ctx["chosen"]:
            by_vid.setdefault(c["video_id"], []).append(c)
        for vid, cs in by_vid.items():
            cap = cv2.VideoCapture(str(ctx["data"] / "Video_V" / f"{vid}.mp4"))
            if not cap.isOpened():
                raise RuntimeError(f"khong mo duoc {vid}.mp4")
            need = {c["frame_index"]: c for c in cs}
            try:
                i = 0
                while need:
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"{vid}: het video truoc frame {sorted(need)}")
                    if i in need:
                        c = need.pop(i)
                        dst = out / "package" / "images" / f"{c['gold_id']}.jpg"
                        if not cv2.imwrite(str(dst), frame, [cv2.IMWRITE_JPEG_QUALITY, a.jpeg_quality]):
                            raise RuntimeError(f"cv2.imwrite that bai: {dst}")
                        c["width"], c["height"] = frame.shape[1], frame.shape[0]
                        c["image_sha256"] = sha256(dst)
                    i += 1
            finally:
                cap.release()
        return {"images": len(list((out / "package" / "images").glob("*.jpg")))}

    def package():
        (out / "package" / "labels.txt").write_text("object\n", encoding="utf-8")
        (out / "package" / "README_CVAT.txt").write_text(CVAT_README, encoding="utf-8")
        pz = a.out / "cvat_package.zip"
        with zipfile.ZipFile(pz, "w", zipfile.ZIP_STORED) as zf:
            for p in sorted((out / "package").rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(out / "package"))
        keyp = out / "gold_key.csv"
        fields = ["gold_id", "video_id", "class_name", "kind", "frame_index", "width", "height", "label_i", "label_i1", "image_sha256"]
        with keyp.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
            for c in sorted(ctx["chosen"], key=lambda c: c["gold_id"]):
                w.writerow({k: json.dumps(c[k]) if isinstance(c[k], list) else c[k] for k in fields})
        kz = a.out / "gold_KEY.zip"
        with zipfile.ZipFile(kz, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(keyp, keyp.name)
        keyp.unlink()
        sel = {"package_zip_sha256": sha256(pz), "key_zip_sha256": sha256(kz),
               "images": {c["gold_id"]: c["image_sha256"] for c in ctx["chosen"]}}
        (out / "gold_selection.json").write_text(json.dumps(sel, indent=2), encoding="utf-8")
        return {"package_zip": pz.name, "package_sha256": sel["package_zip_sha256"], "key_zip": kz.name, "key_sha256": sel["key_zip_sha256"]}

    if run("inputs", inputs) and run("select", select) and run("extract", extract):
        run("package", package)
    print(json.dumps({k: v["status"] for k, v in status.items()}, indent=1))
    return 0 if len(status) == 4 and all(v["status"] == "OK" for v in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
