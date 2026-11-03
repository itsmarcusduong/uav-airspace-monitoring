"""Kiem tra thong ke do phu du lieu (issue #88) tren du lieu tong hop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "reporting"))
import dataset_coverage_stats as dc  # noqa: E402


def row(split, cls, frames, modality="V"):
    return {"split": split, "class_name": cls, "frames": str(frames), "modality": modality}


def test_coverage_counts_only_modality_and_non_drone_minutes():
    rows = [row("train", "Drone", 1800), row("train", "Bird", 1800), row("val", "Airplane", 900),
            row("val", "Drone", 300), row("train", "Bird", 99999, modality="IR")]
    c = dc.coverage(rows, fps=30.0)
    assert c["by_split"]["train"]["Bird"] == {"videos": 1, "frames": 1800, "minutes": 1.0}
    assert c["non_drone_minutes"] == {"train": 1.0, "val": 0.5}
    assert c["non_drone_minutes_all_splits"] == 1.5
    assert c["drone_videos_val"] == 1
    assert c["target_reachable_with_svanstrom_only"] is False


def test_confusion_counts_predicted_as_drone(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("gt,pred,count\nAirplane,Airplane,10\nAirplane,Drone,2\nAirplane,missed,3\nDrone,Drone,5\n", encoding="utf-8")
    c = dc.confusion(p)
    assert c["non_drone_gt_predicted_as_drone"] == {"Airplane": {"gt_boxes": 15, "pred_drone": 2}}


def test_val_negative_frames_causes():
    import val_negative_frames as vn
    meta = [{"video_id": "V_DRONE_001", "class_name": "Drone", "frames": "40"}]
    gt = {"V_DRONE_001": {f: (10.0, 10.0, 10.0, 10.0) for f in range(1, 21)} | {25: (10.0, 10.0, 10.0, 10.0)}}
    dets = {"V_DRONE_001": {0: [(2, 0.6, (11.0, 10.0, 10.0, 10.0)), (2, 0.1, (50.0, 50.0, 5.0, 5.0))], 30: [(1, 0.3, (90.0, 90.0, 5.0, 5.0))]}}
    rows = vn.negative_frames(meta, gt, dets, stride=10, conf=0.25)
    assert [(r["frame"], r["cause"], r["n_det"]) for r in rows] == [(0, "before_first_label", 1), (30, "after_last_label", 1)]
    assert rows[0]["best_iou_with_nearest_gt"] > 0.8 and rows[0]["image"] == "images/val/V_DRONE_001_f00000.jpg"
    assert vn.cause(22, [1, 20, 25]) == ("gap_inside_labels", 20)
    s = vn.summarize(rows)
    assert s["negative_frames"] == 2 and s["by_cause"]["before_first_label"]["det_iou_ge_0.3_with_nearest_gt"] == 1
