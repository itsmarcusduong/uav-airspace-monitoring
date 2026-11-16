#!/usr/bin/env python3
"""Reproduce W7 V0 per-video FP categories and validate the saved confusion matrix."""
from __future__ import annotations

import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]
PREDICTIONS = ROOT / "results/W05/kaggle_run_13/train_yolo11n_640_s20261030/val/predictions.json.gz"
EVIDENCE = ROOT / "results/W06/kaggle_run_14/w6_run14"
IGNORE = ROOT / "results/W06/val_negative_frames/manual_review_classification.csv"
SUMMARY = ROOT / "results/W07/postproc/V0_none/summary.json"
CONF = 0.25
STRIDE = 10


def iou(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    intersection = ix * iy
    union = a[2] * a[3] + b[2] * b[3] - intersection
    return intersection / union if union > 0 else 0.0


def load_predictions() -> dict[str, list[tuple[int, float, tuple[float, ...]]]]:
    with gzip.open(PREDICTIONS, "rt", encoding="utf-8") as fh:
        rows = json.load(fh)
    categories = [int(row["category_id"]) for row in rows]
    offset = 1 if categories and min(categories) >= 1 else 0
    predictions: dict[str, list[tuple[int, float, tuple[float, ...]]]] = defaultdict(list)
    for row in rows:
        predictions[str(row["image_id"])].append(
            (
                int(row["category_id"]) - offset,
                float(row["score"]),
                tuple(float(value) for value in row["bbox"]),
            )
        )
    return predictions


def load_images() -> tuple[
    dict[str, list[tuple[int, tuple[float, ...]]]], dict[str, str], set[str]
]:
    with (EVIDENCE / "meta.csv").open(encoding="utf-8") as fh:
        videos = list(csv.DictReader(fh))
    gt_by_image: dict[str, list[tuple[int, tuple[float, ...]]]] = {}
    video_by_image: dict[str, str] = {}
    for video in videos:
        name = video["video_id"]
        class_id = CLASSES.index(video["class_name"])
        with (EVIDENCE / "gt" / f"{name}.csv").open(encoding="utf-8") as fh:
            gt_by_frame = {
                int(row["frame"]): tuple(float(row[key]) for key in "xywh")
                for row in csv.DictReader(fh)
            }
        for frame in range(0, int(video["frames"]), STRIDE):
            image_id = f"{name}_f{frame:05d}"
            gt_by_image[image_id] = (
                [(class_id, gt_by_frame[frame])] if frame in gt_by_frame else []
            )
            video_by_image[image_id] = name
    with IGNORE.open(encoding="utf-8-sig") as fh:
        ignored = {
            f"{row['video_id']}_f{int(row['frame']):05d}"
            for row in csv.DictReader(fh)
        }
    return gt_by_image, video_by_image, ignored


def best_match(
    prediction: tuple[int, float, tuple[float, ...]],
    gt: list[tuple[int, tuple[float, ...]]],
    used_gt: set[int],
    class_aware: bool,
) -> tuple[int | None, float]:
    pred_class, _, pred_box = prediction
    best_index, best_iou = None, 0.0
    for index, (gt_class, gt_box) in enumerate(gt):
        if index in used_gt or (class_aware and gt_class != pred_class):
            continue
        overlap = iou(pred_box, gt_box)
        if overlap >= 0.5 and overlap > best_iou:
            best_index, best_iou = index, overlap
    return best_index, best_iou


def classify_fp(
    index: int,
    prediction: tuple[int, float, tuple[float, ...]],
    gt: list[tuple[int, tuple[float, ...]]],
    correct_prediction_indices: set[int],
    predictions: list[tuple[int, float, tuple[float, ...]]],
) -> str:
    box = prediction[2]
    if any(
        other_index != index and iou(box, predictions[other_index][2]) >= 0.5
        for other_index in correct_prediction_indices
    ):
        return "duplicate"
    max_gt_iou = max((iou(box, gt_box) for _, gt_box in gt), default=0.0)
    if 0.1 <= max_gt_iou < 0.5:
        return "mislocalized"
    if max_gt_iou < 0.1:
        return "background"
    return "other_high_overlap_unmatched"


def main() -> None:
    predictions = load_predictions()
    gt_by_image, video_by_image, ignored = load_images()
    ignored &= gt_by_image.keys()
    confusion: Counter[tuple[str, str]] = Counter()
    per_class: dict[str, Counter[str]] = defaultdict(Counter)
    background_drone_categories: Counter[str] = Counter()
    background_drone_videos: dict[str, Counter[str]] = defaultdict(Counter)
    drone_gt_videos: dict[str, Counter[str]] = defaultdict(Counter)
    per_video: dict[str, Counter[str]] = defaultdict(Counter)
    per_video_class: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )

    for image_id, gt in gt_by_image.items():
        if image_id in ignored:
            continue
        video_id = video_by_image[image_id]
        image_predictions = sorted(
            (row for row in predictions.get(image_id, []) if row[1] >= CONF),
            key=lambda row: -row[1],
        )
        for gt_class, _ in gt:
            per_class[CLASSES[gt_class]]["gt"] += 1
            per_video[video_id]["gt"] += 1
            per_video_class[video_id][CLASSES[gt_class]]["gt"] += 1

        used_gt: set[int] = set()
        correct_predictions: set[int] = set()
        for index, prediction in enumerate(image_predictions):
            gt_index, _ = best_match(prediction, gt, used_gt, class_aware=True)
            pred_class = CLASSES[prediction[0]]
            if gt_index is None:
                per_class[pred_class]["fp"] += 1
                per_video[video_id]["fp"] += 1
                per_video_class[video_id][pred_class]["fp"] += 1
            else:
                used_gt.add(gt_index)
                correct_predictions.add(index)
                per_class[pred_class]["tp"] += 1
                per_video[video_id]["tp"] += 1
                per_video_class[video_id][pred_class]["tp"] += 1

        used_gt = set()
        background_prediction_indices: list[int] = []
        for index, prediction in enumerate(image_predictions):
            pred_class = CLASSES[prediction[0]]
            gt_index, _ = best_match(prediction, gt, used_gt, class_aware=False)
            if gt_index is None:
                confusion[("nen", pred_class)] += 1
                background_prediction_indices.append(index)
            else:
                gt_class = CLASSES[gt[gt_index][0]]
                used_gt.add(gt_index)
                confusion[(gt_class, pred_class)] += 1
                if gt_class != pred_class and pred_class == "Drone":
                    drone_gt_videos[gt_class][video_id] += 1
        for gt_index, (gt_class, _) in enumerate(gt):
            if gt_index not in used_gt:
                confusion[(CLASSES[gt_class], "bo_sot")] += 1
                per_video[video_id]["missed"] += 1
        for index in background_prediction_indices:
            prediction = image_predictions[index]
            if CLASSES[prediction[0]] != "Drone":
                continue
            category = classify_fp(
                index, prediction, gt, correct_predictions, image_predictions
            )
            background_drone_categories[category] += 1
            background_drone_videos[category][video_id] += 1

    observed = {
        f"{actual}->{predicted}": count
        for (actual, predicted), count in sorted(confusion.items())
    }
    saved = json.loads(SUMMARY.read_text(encoding="utf-8"))["detection"]
    expected = saved["confusion"]
    class_counts_match = all(
        per_class[name]["tp"] == saved["per_class"][name]["tp"]
        and per_class[name]["fp"] == saved["per_class"][name]["fp"]
        and per_class[name]["gt"] == saved["per_class"][name]["gt"]
        for name in CLASSES
    )
    if (
        observed != expected
        or not class_counts_match
        or len(ignored) != saved["ignored_images"]
        or sum(background_drone_categories.values()) != expected["nen->Drone"]
    ):
        raise SystemExit(
            "Recalculation mismatch with V0 summary; refusing to emit partial evidence."
        )

    top_fp_videos = sorted(
        ({"video_id": name, **counts} for name, counts in per_video.items()),
        key=lambda row: (-row.get("fp", 0), -row.get("missed", 0), row["video_id"]),
    )
    output = {
        "conf": CONF,
        "images": len(gt_by_image) - len(ignored),
        "ignored_images": len(ignored),
        "matches_saved_summary": True,
        "confusion": observed,
        "nen_to_drone_categories": {
            category: {
                "count": count,
                "videos": dict(sorted(background_drone_videos[category].items())),
            }
            for category, count in sorted(background_drone_categories.items())
        },
        "non_drone_gt_predicted_as_drone": {
            gt_class: {
                "count": sum(drone_gt_videos[gt_class].values()),
                "videos": dict(sorted(drone_gt_videos[gt_class].items())),
            }
            for gt_class in ("Airplane", "Bird", "Helicopter")
        },
        "bird_fp_by_video": {
            video: counts["fp"]
            for video, classes in sorted(per_video_class.items())
            if (counts := classes["Bird"])["fp"]
        },
        "selected_video_counts": {
            video: dict(per_video[video])
            for video in ("V_AIRPLANE_005", "V_AIRPLANE_007", "V_HELICOPTER_012", "V_BIRD_041")
            if video in per_video
        },
        "top_videos_by_fp": top_fp_videos[:8],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
