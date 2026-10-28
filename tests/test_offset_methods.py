"""Kiem tra luat quyet dinh offset (run 06, ADR-0006) va cham tap chuan CVAT tren du lieu tong hop."""
import csv
import gzip
import io
import json
import random
import sys
import zipfile

import pytest

import score_cvat_gold as sg
import w4_offset_check as w


def test_sign_test_p():
    assert w.sign_test_p(10, 10) == pytest.approx(2 / 2 ** 10)
    assert w.sign_test_p(5, 10) == 1.0
    assert w.sign_test_p(0, 0) == 1.0
    assert sg.sign_p(8, 8) == pytest.approx(w.sign_test_p(8, 8))


def _make(tmp_path, truth_offset):
    rnd = random.Random(0)
    labels, man, preds, audit = {}, [], [], []

    def video(vid, cls, kind, n=60):
        pos = [(100 + 4 * t, 100 + 2 * t, 20, 20) for t in range(n)]
        lab = ([None] + pos) if kind == "plus1" and truth_offset == 1 else (pos + [pos[-1]] if kind == "plus1" else list(pos))
        labels[vid] = lab
        audit.append({"video_id": vid, "label_entries": len(lab), "frames_decoded": n})
        for i in range(0, n, 10):
            man.append({"image": f"images/val/{vid}_f{i:05d}.jpg", "split": "val", "video_id": vid, "class_name": cls, "frame_index": i})
            x, y, ww, hh = pos[i]
            preds.append({"image_id": f"{vid}_f{i:05d}", "category_id": w.CLASSES.index(cls) + 1,
                          "bbox": [x + rnd.uniform(-1, 1), y, ww, hh], "score": 0.9})
    for k in range(8):
        video(f"V_AIRPLANE_{k:03d}", "Airplane", "equal")
    for k in range(10):
        video(f"V_DRONE_{k:03d}", "Drone", "plus1")
    (tmp_path / "raw" / "Data" / "Video_V").mkdir(parents=True)
    with gzip.open(tmp_path / "m.csv.gz", "wt") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(man[0])); wr.writeheader(); wr.writerows(man)
    (tmp_path / "p.json").write_text(json.dumps(preds))
    with open(tmp_path / "a.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(audit[0])); wr.writeheader(); wr.writerows(audit)
    return labels


@pytest.mark.parametrize("truth,expected", [(1, "offset1"), (0, "offset0")])
def test_offset_check_end_to_end(tmp_path, monkeypatch, truth, expected):
    labels = _make(tmp_path, truth)
    monkeypatch.setattr(w, "load_labels", lambda p: labels[p.name.replace("_LABELS.mat", "")])
    monkeypatch.setattr(sys, "argv", ["x", "--data-root", str(tmp_path / "raw"), "--manifest", str(tmp_path / "m.csv.gz"),
                                      "--predictions", str(tmp_path / "p.json"), "--audit", str(tmp_path / "a.csv"),
                                      "--out", str(tmp_path), "--commit", "test"])
    assert w.main() == 0
    s = json.loads((tmp_path / "w4_offset_check" / "offset_check_summary.json").read_text())
    assert s["control_ok"] is True
    assert s["verdict"]["Drone|plus1"] == expected


def test_score_cvat_gold_detects_offset1(tmp_path, monkeypatch):
    rows, ann = [], {}
    for k in range(12):
        kind = "plus1" if k < 6 else "equal"
        li, lj = [100 + 5 * k, 100, 20, 20], [108 + 5 * k, 100, 20, 20]
        truth = lj if kind == "plus1" else li
        gid = f"gold_{k:04d}"
        rows.append({"gold_id": gid, "video_id": f"V_X_{k:03d}", "class_name": "Drone" if kind == "plus1" else "Airplane",
                     "kind": kind, "frame_index": 10, "width": 640, "height": 512,
                     "label_i": json.dumps(li), "label_i1": json.dumps(lj), "image_sha256": "x"})
        ann[gid] = f"0 {(truth[0] + 10) / 640} {(truth[1] + 10) / 512} {20 / 640} {20 / 512}\n"
    buf = io.StringIO(); wr = csv.DictWriter(buf, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    with zipfile.ZipFile(tmp_path / "key.zip", "w") as z:
        z.writestr("gold_key.csv", buf.getvalue())
    with zipfile.ZipFile(tmp_path / "ann.zip", "w") as z:
        for gid, txt in ann.items():
            z.writestr(f"obj_train_data/{gid}.txt", txt)
    monkeypatch.setattr(sys, "argv", ["x", "--annotations", str(tmp_path / "ann.zip"), "--key", str(tmp_path / "key.zip"),
                                      "--out", str(tmp_path / "sc")])
    assert sg.main() == 0
    s = json.loads((tmp_path / "sc" / "gold_score.json").read_text())
    assert s["groups"]["Drone|plus1"]["videos_i1_better"] == 6
    assert s["groups"]["control_equal"]["videos_i1_better"] == 0
    assert s["label_quality"]["frac_best_iou_ge_0_5"] == 1.0


def test_score_cvat_gold_center_metric_ignores_tight_boxes(tmp_path, monkeypatch):
    """Hop ve sat (nho hon nhan goc) van phai cho ket qua tam dung chieu; phan tham do khong co verdict."""
    rows, ann = [], {}
    for k in range(12):
        kind = "plus1" if k < 6 else "equal"
        li, lj = [100 + 5 * k, 100, 40, 40], [106 + 5 * k, 100, 40, 40]
        truth = lj if kind == "plus1" else li
        gid = f"gold_{k:04d}"
        rows.append({"gold_id": gid, "video_id": f"V_X_{k:03d}", "class_name": "Drone" if kind == "plus1" else "Airplane",
                     "kind": kind, "frame_index": 10, "width": 640, "height": 512,
                     "label_i": json.dumps(li), "label_i1": json.dumps(lj), "image_sha256": "x"})
        cx, cy = truth[0] + 20, truth[1] + 20
        ann[gid] = f"0 {cx / 640} {cy / 512} {12 / 640} {12 / 512}\n"   # hop 12x12 trong nhan 40x40
    buf = io.StringIO(); wr = csv.DictWriter(buf, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    with zipfile.ZipFile(tmp_path / "key.zip", "w") as z:
        z.writestr("gold_key.csv", buf.getvalue())
    with zipfile.ZipFile(tmp_path / "ann.zip", "w") as z:
        for gid, txt in ann.items():
            z.writestr(f"obj_train_data/{gid}.txt", txt)
    monkeypatch.setattr(sys, "argv", ["x", "--annotations", str(tmp_path / "ann.zip"), "--key", str(tmp_path / "key.zip"),
                                      "--out", str(tmp_path / "sc")])
    assert sg.main() == 0
    s = json.loads((tmp_path / "sc" / "gold_score.json").read_text())
    ex = s["exploratory_center"]
    assert ex["groups"]["Drone|plus1"]["videos_closer_to_i1"] == 6
    assert ex["groups"]["control_equal"]["videos_closer_to_i1"] == 0
    assert ex["box_vs_label"]["median_center_dist_px"] == 0
    assert ex["box_vs_label"]["median_area_ratio_annot_over_label_i"] == pytest.approx(144 / 1600, abs=1e-3)
    assert "verdict" not in ex
