from pathlib import Path
import csv

import math
import cv2
from mcos_decoder import load_groundtruth

from w2_eda_audit_split import clean_box

REPO_ROOT = Path(__file__).resolve().parents[2]

split_csv = REPO_ROOT / "data/splits/video_split_v1.csv"
inventory_csv = REPO_ROOT / "results/W02/kaggle_run_01/video_inventory.csv"
data_root = REPO_ROOT / "resources/datasets/svanstrom-drone-detection-dataset"
out_root = REPO_ROOT / "results/W03/kaggle_run_03/yolo_dataset"

CLASS_ID = {"AIRPLANE": 0, "BIRD": 1, "DRONE": 2, "HELICOPTER": 3}
STRIDE = 5  # replace with the value approved in ADR-0004

def resolve_data_root(root: Path) -> Path:
    """Find the directory containing Data/Video_V, including nested dataset folders."""
    if (root / "Data" / "Video_V").is_dir():
        return root

    candidates = [
        video_v.parent.parent
        for video_v in root.rglob("Video_V")
        if video_v.is_dir() and video_v.parent.name == "Data"
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected one dataset root containing Data/Video_V under {root}; "
            f"found {len(candidates)}"
        )
    return candidates[0]


def write_yolo_image_and_label(
    output_root: Path,
    split: str,
    video_id: str,
    frame_index: int,
    frame,
    lines: list[str],
) -> None:
    if split not in {"train", "val", "test"}:
        raise ValueError(f"Unexpected split {split!r} for {video_id}")

    stem = f"{video_id}_{frame_index:06d}"
    image_path = output_root / split / "images" / f"{stem}.jpg"
    label_path = output_root / split / "labels" / f"{stem}.txt"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(image_path), frame):
        raise RuntimeError(f"Failed to write image {image_path}")

    # An empty file is the YOLO representation for a verified negative frame.
    label_path.write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )


data_root = resolve_data_root(data_root)
exclusions: list[dict[str, str]] = []

with open(split_csv, newline="", encoding="utf-8-sig") as f:
    split_rows = list(csv.DictReader(f))
with open(inventory_csv, newline="", encoding="utf-8-sig") as f:
    inventory = {r["video_id"]: r for r in csv.DictReader(f)}

for row in split_rows:
    if row["modality"] != "V":
        continue

    video_id, split = row["video_id"], row["split"]
    audit = inventory.get(video_id)
    if audit is None:
        raise KeyError(f"No inventory row for {video_id}")
    
    video = data_root / "Data" / "Video_V" / f"{video_id}.mp4"
    label_mat = data_root / "Data" / "Video_V" / f"{video_id}_LABELS.mat"

    if not video.is_file() or not label_mat.is_file():
        raise FileNotFoundError(f"Missing video or labels for {video_id}")
    
    # boxes = load_groundtruth(label_mat)
    boxes = [clean_box(box) for box in load_groundtruth(label_mat)]

    # Quarantine mismatched videos; record video_id and reason in an exclusions file.
    if len(boxes) != int(audit["frames_decoded"]):
        exclusions.append({
            "video_id": video_id,
            "split": split,
            "reason": f"labels={len(boxes)} decoded={audit['frames_decoded']}",
        })
        continue

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video}")

    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_index % STRIDE == 0:
            height, width = frame.shape[:2]
            box = boxes[frame_index]
            lines = []

            if box is not None:
                if not isinstance(box, (list, tuple)) or len(box) < 4:
                    raise ValueError(
                        f"Malformed bbox in {video_id}, frame {frame_index}: {box!r}"
                    )
                
                x, y, w, h = map(float, box[:4])
                if not all(math.isfinite(v) for v in (x, y, w, h)):
                    raise ValueError(
                        f"Non-finite bbox in {video_id}, frame {frame_index}: {box!r}"
                    )
                if w <= 0 or h <= 0 or x < 0 or y < 0:
                    raise ValueError(f"Invalid bbox: {video_id} frame {frame_index}: {box}")
                if x + w > width or y + h > height:
                    raise ValueError(f"Out-of-image bbox: {video_id} frame {frame_index}: {box}")

                class_name = row["class_name"].upper()
                if class_name not in CLASS_ID:
                    raise ValueError(f"Unknown class {class_name!r} for {video_id}")
                
                class_id = CLASS_ID[class_name]
                cx, cy = (x + w / 2) / width, (y + h / 2) / height
                lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w/width:.6f} {h/height:.6f}")

            # Write the frame under <split>/images/ and matching .txt under <split>/labels/.
            # Create the .txt even when `lines` is empty (verified negative frame).
            write_yolo_image_and_label(out_root, split, video_id, frame_index, frame, lines)

        frame_index += 1

    cap.release()
    if frame_index != int(audit["frames_decoded"]):
        raise RuntimeError(
            f"Decoded count changed for {video_id}: {frame_index} != {audit['frames_decoded']}"
        )

exclusions_path = out_root / "exclusions.csv"
exclusions_path.parent.mkdir(parents=True, exist_ok=True)

with exclusions_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["video_id", "split", "reason"])
    writer.writeheader()
    writer.writerows(exclusions)