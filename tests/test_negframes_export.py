"""Job xuat anh val am tinh (W6, review cua An) tren du lieu tong hop."""
import csv
import gzip
import hashlib
import json
import sys
import zipfile

import pytest

import w6_negative_frames_export as nf

FIELDS = ["sample_no", "video_id", "frame", "image", "cause", "role", "nearest_gt_frame", "nearest_gt_xywh",
          "run13_classes", "run13_conf", "run13_boxes_xywh"]


def _make(tmp_path, label_text=""):
    cv2 = pytest.importorskip("cv2")
    import numpy as np
    d = tmp_path / "e1-yolo-v1"
    (d / "images" / "val").mkdir(parents=True); (d / "labels" / "val").mkdir(parents=True)
    rows, man = [], []
    for i, (stem, preds) in enumerate([("V_DRONE_001_f00000", ("Drone", "0.6", "10.0,10.0,20.0,20.0")),
                                       ("V_DRONE_002_f00000", ("", "", ""))], 1):
        img = d / "images" / "val" / f"{stem}.jpg"
        cv2.imwrite(str(img), np.full((512, 640, 3), 90, dtype=np.uint8))
        (d / "labels" / "val" / f"{stem}.txt").write_text(label_text)
        man.append({"image": f"images/val/{stem}.jpg", "split": "val", "sha256": hashlib.sha256(img.read_bytes()).hexdigest()})
        rows.append(dict(zip(FIELDS, [i, stem[:11], 0, f"images/val/{stem}.jpg", "before_first_label", "FP" if preds[0] else "control_no_fp",
                                      1, "12.0,11.0,20.0,20.0", *preds])))
    mp = tmp_path / "yolo_manifest.csv.gz"
    with gzip.open(mp, "wt", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["image", "split", "sha256"]); w.writeheader(); w.writerows(man)
    ip = tmp_path / "idx.csv"
    with ip.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    return d, mp, ip


def test_export_end_to_end(tmp_path, monkeypatch):
    d, mp, ip = _make(tmp_path)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["x", "--data-dir", str(d), "--manifest", str(mp), "--index", str(ip), "--expect", "2", "--out", str(out)])
    assert nf.main() == 0
    st = json.loads((out / "w6_negframes" / "stage_status.json").read_text())
    assert all(v["status"] == "OK" for v in st.values()) and st["export"]["with_pred"] == 1
    with zipfile.ZipFile(out / "w6_negframes.zip") as z:
        names = set(z.namelist())
    assert {"w6_negframes/originals/V_DRONE_001_f00000.jpg", "w6_negframes/annotated/V_DRONE_002_f00000_review.jpg",
            "w6_negframes/overview.jpg", "w6_negframes/review_index.csv", "w6_negframes/stage_status.json"} <= names
    # anh goc chep nguyen byte
    assert (out / "w6_negframes/originals/V_DRONE_001_f00000.jpg").read_bytes() == (d / "images/val/V_DRONE_001_f00000.jpg").read_bytes()


def test_export_rejects_nonempty_label(tmp_path, monkeypatch):
    d, mp, ip = _make(tmp_path, label_text="2 0.5 0.5 0.1 0.1\n")
    monkeypatch.setattr(sys, "argv", ["x", "--data-dir", str(d), "--manifest", str(mp), "--index", str(ip), "--expect", "2", "--out", str(tmp_path / "o")])
    assert nf.main() == 1
    st = json.loads((tmp_path / "o" / "w6_negframes" / "stage_status.json").read_text())
    assert st["inputs"]["status"] == "FAILED" and "khong rong" in st["inputs"]["error"] and st["export"]["status"] == "SKIPPED"


def test_parse_boxes_mismatch():
    assert nf.parse_boxes("", "", "") == []
    with pytest.raises(ValueError):
        nf.parse_boxes("Drone Bird", "0.5", "1,2,3,4")
