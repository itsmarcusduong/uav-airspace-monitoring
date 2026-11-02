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
