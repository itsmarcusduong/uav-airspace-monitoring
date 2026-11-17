"""Kiem tra logic dem hop trung cua job W8 (scripts/kaggle/w8_dup_diagnostic.py) tren du lieu gia va doi chieu voi W7."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "kaggle"))
import w8_dup_diagnostic as dd  # noqa: E402


def test_dup_count_same_class_only_and_conf_filter():
    a = (2, 0.9, (0.0, 0.0, 10.0, 10.0))
    b = (2, 0.5, (1.0, 0.0, 10.0, 10.0))      # IoU ~0,82 cung lop -> trung
    c = (0, 0.6, (1.0, 0.0, 10.0, 10.0))      # khac lop -> khong tinh
    d = (2, 0.2, (0.0, 1.0, 10.0, 10.0))      # duoi conf 0,25 -> bo qua
    assert dd.dup_count([a, b, c, d]) == (3, 1)


def test_match_rate_tolerance():
    a = [(2, 0.9, (1.0, 2.0, 3.0, 4.0)), (1, 0.4, (5.0, 5.0, 2.0, 2.0))]
    b = [(2, 0.9, (1.01, 2.0, 3.0, 4.0)), (1, 0.4, (5.5, 5.0, 2.0, 2.0))]
    assert dd.match_rate(a, b) == (1, 2)


def test_summarize_matches_w7_explore_on_saved_run14():
    """Dem tren detection run 14 (frame buoc 10 co anh val) phai bang con so tham do W7 (153 hop trung)."""
    ex = ROOT / "results/W07/postproc/exploratory.json"
    dets = ROOT / "results/W06/kaggle_run_14/w6_run14/dets"
    import gzip
    pred = ROOT / "results/W05/kaggle_run_13/train_yolo11n_640_s20261030/val/predictions.json.gz"
    if not (ex.exists() and dets.exists() and pred.exists()):
        import pytest
        pytest.skip("thieu ket qua W6/W7")
    ids = {r["image_id"] for r in json.load(gzip.open(pred, "rt"))}
    per = {}
    for p in sorted(dets.glob("*.csv")):
        r14 = dd.read_run14(p)
        for k in ids:
            v, f = k.rsplit("_f", 1)
            if v == p.stem:
                per[k] = {"frame_fp32": r14.get(int(f), [])}
    s = dd.summarize(per)["frame_fp32"]
    w7 = json.loads(ex.read_text(encoding="utf-8"))["duplicates_on_same_val_frames"]["video_predict"]
    assert (s["boxes"], s["dup_same_class_iou_0.5_0.7"]) == (w7["boxes"], w7["dup_same_class_iou_0.5_0.7"])


def test_main_end_to_end_with_fake_model(tmp_path, monkeypatch):
    """Chay main tren video/anh tong hop voi YOLO gia: kiem cac stage, 4 dieu kien, cong tai tao va zip."""
    import csv
    import gzip
    import hashlib
    import cv2
    import numpy as np
    import pytest
    pytest.importorskip("ultralytics")
    raw = tmp_path / "raw" / "Data" / "Video_V"; raw.mkdir(parents=True)
    vw = cv2.VideoWriter(str(raw / "V_DRONE_001.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (64, 48))
    for i in range(25):
        vw.write(np.full((48, 64, 3), i * 5, np.uint8))
    vw.release()
    data = tmp_path / "e1"; (data / "images/val").mkdir(parents=True)
    rows = []
    for f in (0, 10, 20):
        p = data / f"images/val/V_DRONE_001_f{f:05d}.jpg"
        cv2.imwrite(str(p), np.full((48, 64, 3), f * 5, np.uint8))
        rows.append({"image": f"images/val/V_DRONE_001_f{f:05d}.jpg", "split": "val", "video_id": "V_DRONE_001",
                     "frame_index": str(f), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    man = tmp_path / "m.csv.gz"
    with gzip.open(man, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    weights = tmp_path / "best.pt"; weights.write_bytes(b"w")
    r14 = tmp_path / "dets"; r14.mkdir()
    (r14 / "V_DRONE_001.csv").write_text("frame,cls,conf,x,y,w,h\n0,2,0.9,1.0,1.0,10.0,10.0\n0,2,0.5,2.0,1.0,10.0,10.0\n", encoding="utf-8")

    import torch

    class Boxes:
        def __init__(self, src):
            dup = not isinstance(src, str)          # gia lap: frame co hop trung, anh JPG thi khong
            self.xyxy = torch.tensor([[1.0, 1.0, 11.0, 11.0]] + ([[2.0, 1.0, 12.0, 11.0]] if dup else []))
            self.cls = torch.tensor([2.0] * len(self.xyxy)); self.conf = torch.tensor([0.9, 0.5][: len(self.xyxy)])

    class R:
        def __init__(self, src):
            self.boxes = Boxes(src)

    class FakeYOLO:
        def __init__(self, *_):
            pass

        def predict(self, src, **kw):
            return [R(src)]

    import ultralytics
    monkeypatch.setattr(ultralytics, "YOLO", FakeYOLO)
    import w3_export_yolo
    monkeypatch.setattr(w3_export_yolo, "find_video_dir", lambda root: tmp_path / "raw" / "Data")
    monkeypatch.setattr(sys, "argv", ["x", "--data-dir", str(data), "--manifest", str(man), "--data-root", str(tmp_path / "raw"),
                                      "--weights", str(weights), "--weights-sha", hashlib.sha256(b"w").hexdigest(),
                                      "--run14-dets", str(r14), "--device", "cpu", "--out", str(tmp_path / "out")])
    assert dd.main() == 0
    res = json.loads((tmp_path / "out/w8_dupdiag/dup_diagnostic.json").read_text(encoding="utf-8"))
    c = res["conditions"]
    assert c["jpg_fp32"]["dup_same_class_iou_0.5_0.7"] == 0 and c["frame_fp32"]["dup_same_class_iou_0.5_0.7"] == 3
    assert res["repro_frame_fp32_vs_run14"] == {"matched": 2, "boxes": 6, "rate": 0.3333}
    assert (tmp_path / "out/w8_dupdiag_evidence.zip").is_file()
