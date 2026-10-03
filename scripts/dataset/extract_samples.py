#!/usr/bin/env python3
"""Create exactly 100 traceable Svanstrom frames from distinct video sequences."""
from __future__ import annotations

import argparse
import csv
import logging
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger(__name__)
FILENAME = re.compile(r"^(IR|V)_(AIRPLANE|BIRD|DRONE|HELICOPTER)_\d+$")
CLASS_ID = {"AIRPLANE": 0, "BIRD": 1, "DRONE": 2, "HELICOPTER": 3}
TARGETS = {"DRONE": 50, "BIRD": 20, "AIRPLANE": 15, "HELICOPTER": 15}


def resolve_root(root: Path) -> Path:
    """Accept a dataset root or its single archive-created child directory."""
    if (root / "Data" / "Video_IR").is_dir() and (root / "Data" / "Video_V").is_dir():
        return root
    children = [child for child in root.iterdir() if child.is_dir()] if root.is_dir() else []
    candidates = [child for child in children if (child / "Data" / "Video_IR").is_dir()]
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(f"Cannot locate Data/Video_IR and Data/Video_V under {root}")


def choose_frame(bboxes: list[tuple | None], rng: random.Random) -> tuple[int, tuple[float, float, float, float]]:
    valid = [(index, box) for index, box in enumerate(bboxes) if box and box[2] > 0 and box[3] > 0]
    if not valid:
        raise ValueError("No valid bbox")
    low, high = len(valid) // 5, max(len(valid) // 5, (4 * len(valid)) // 5 - 1)
    return valid[rng.randint(low, high)]


def has_valid_bbox(bboxes: list[tuple | None]) -> bool:
    return any(box and box[2] > 0 and box[3] > 0 for box in bboxes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Dataset root or archive-created parent")
    parser.add_argument("--output", type=Path, default=Path("data/samples"))
    parser.add_argument("--seed", type=int, default=20261003)
    args = parser.parse_args()
    bundled_deps = Path("resources/python_deps")
    if bundled_deps.is_dir():
        sys.path.insert(0, str(bundled_deps))
    try:
        import cv2  # type: ignore
        from mcos_decoder import load_groundtruth  # type: ignore
    except ImportError as exc:
        raise SystemExit("OpenCV and mcos-decoder with SciPy are required.") from exc

    root = resolve_root(args.root)
    rng = random.Random(args.seed)
    grouped: dict[str, list[tuple[Path, Path, str]]] = defaultdict(list)
    for video in sorted(root.glob("Data/Video_*/*.mp4")):
        match = FILENAME.match(video.stem)
        label = video.with_name(video.stem + "_LABELS.mat")
        if match and label.is_file():
            modality, class_name = match.groups()
            grouped[class_name].append((video, label, modality))
    filtered: dict[str, list[tuple[Path, Path, str]]] = defaultdict(list)
    skipped = 0
    for class_name, candidates in grouped.items():
        for video, label, modality in candidates:
            try:
                if has_valid_bbox(load_groundtruth(label)):
                    filtered[class_name].append((video, label, modality))
                else:
                    skipped += 1
            except Exception as exc:
                LOG.warning("Skipping unreadable label %s: %s", label, exc)
                skipped += 1
    grouped = filtered
    missing = {name: count for name, count in TARGETS.items() if len(grouped[name]) < count}
    if missing:
        raise SystemExit(f"NOT ENOUGH VALID SAMPLES: insufficient labelled videos {missing}")

    selected: list[tuple[Path, Path, str, str]] = []
    for class_name, target in TARGETS.items():
        by_modality: dict[str, list[tuple[Path, Path, str]]] = defaultdict(list)
        for item in grouped[class_name]:
            by_modality[item[2]].append(item)
        for items in by_modality.values():
            rng.shuffle(items)
        ordered = []
        while any(by_modality.values()):
            for modality in sorted(by_modality):
                if by_modality[modality]:
                    ordered.append(by_modality[modality].pop())
        selected.extend((video, label, modality, class_name) for video, label, modality in ordered[:target])
    rng.shuffle(selected)
    if len(selected) != 100 or len({video for video, *_ in selected}) != 100:
        raise SystemExit("Internal selection error: expected 100 unique source videos")

    staging = args.output.with_name(args.output.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    frames_dir = staging / "frames"; frames_dir.mkdir(parents=True)
    rows = []
    for sample_number, (video, label, modality, class_name) in enumerate(selected, start=1):
        bboxes = load_groundtruth(label)
        frame_index, bbox = choose_frame(bboxes, rng)
        cap = cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read(); fps = cap.get(cv2.CAP_PROP_FPS) or 0.0; cap.release()
        if not ok or frame is None:
            raise SystemExit(f"Unreadable source video at selected frame: {video}#{frame_index}")
        height, width = frame.shape[:2]; x, y, box_w, box_h = map(float, bbox)
        if x < 0 or y < 0 or x + box_w > width or y + box_h > height:
            raise SystemExit(f"Out-of-bounds bbox in {label} frame {frame_index}: {bbox}, image={width}x{height}")
        filename = f"sample_{sample_number:04d}.jpg"; destination = frames_dir / filename
        if not cv2.imwrite(str(destination), frame):
            raise SystemExit(f"Cannot write {destination}")
        source_id = video.stem
        rows.append({
            "sample_id": f"S{sample_number:04d}", "dataset_id": "DS-SVANSTROM", "source_id": source_id,
            "video_id": source_id, "sequence_id": source_id, "frame_index": frame_index,
            "timestamp_sec": f"{frame_index / fps:.6f}" if fps else "UNKNOWN", "image_path": f"frames/{filename}",
            "width": width, "height": height, "class_ids": CLASS_ID[class_name], "class_names": class_name.title(),
            "bbox_count": 1, "bbox_metadata": f'{{"x":{x:.3f},"y":{y:.3f},"w":{box_w:.3f},"h":{box_h:.3f},"label_file":"{label.relative_to(root).as_posix()}"}}',
            "selection_reason": f"stratified class={class_name}; modality={modality}; unique source video; valid non-edge trajectory frame",
            "source_reference": "https://github.com/DroneDetectionThesis/Drone-detection-dataset",
        })
    with (staging / "index_100_frames.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    if args.output.exists():
        shutil.rmtree(args.output)
    staging.replace(args.output)
    LOG.info("Wrote %d samples from %d unique videos; class distribution=%s; skipped labels=%d", len(rows), len(selected), dict(Counter(row["class_names"] for row in rows)), skipped)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
