#!/usr/bin/env python3
"""Validate W1 manifest and sample-frame evidence without inventing missing metadata."""
from __future__ import annotations
import argparse, csv, json, logging, sys
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image

MANIFEST_COLUMNS = {"dataset_id", "dataset_name", "source_url", "license", "license_url"}
SAMPLE_COLUMNS = {"sample_id", "dataset_id", "source_id", "video_id", "frame_index", "image_path", "width", "height", "class_ids", "class_names", "bbox_count", "bbox_metadata", "source_reference"}
CLASS_IDS = {"Airplane": "0", "Bird": "1", "Drone": "2", "Helicopter": "3"}

def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle); return reader.fieldnames or [], list(reader)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, help="Optional root for source video/label traceability checks")
    args = parser.parse_args(); failures = []
    fields, datasets = read_csv(args.manifest)
    if MANIFEST_COLUMNS - set(fields): failures.append("manifest missing required columns")
    ids = [row.get("dataset_id", "") for row in datasets]
    if len(ids) != len(set(ids)): failures.append("duplicate dataset IDs")
    for row in datasets:
        for key in ("source_url", "official_repository"):
            if key in row and row[key] and row[key] != "UNKNOWN" and not urlparse(row[key]).scheme: failures.append(f"invalid URL for {row.get('dataset_id')}: {key}")
        if not row.get("source_url"): failures.append(f"missing source for {row.get('dataset_id')}")
        if not row.get("license"): failures.append(f"missing license for {row.get('dataset_id')}")
    if not args.samples.exists(): failures.append("sample index missing; exactly 100 samples required")
    else:
        sf, samples = read_csv(args.samples)
        if SAMPLE_COLUMNS - set(sf): failures.append("sample index missing required columns")
        sample_ids = [r.get("sample_id", "") for r in samples]
        if len(sample_ids) != len(set(sample_ids)): failures.append("duplicate sample IDs")
        if len(samples) != 100: failures.append(f"expected exactly 100 samples, got {len(samples)}")
        for row in samples:
            image = args.samples.parent / row["image_path"]
            try:
                with Image.open(image) as loaded: loaded.verify()
            except Exception: failures.append(f"unreadable image: {image}")
            if not row.get("source_id") or not row.get("video_id") or not row.get("source_reference"): failures.append(f"missing traceability: {row.get('sample_id')}")
            if row.get("class_ids") != CLASS_IDS.get(row.get("class_names", "")):
                failures.append(f"class inconsistency: {row.get('sample_id')}")
            try:
                metadata = json.loads(row["bbox_metadata"])
                x, y, width, height = (float(metadata[key]) for key in ("x", "y", "w", "h"))
                image_width, image_height = float(row["width"]), float(row["height"])
                if min(x, y, width, height) < 0 or width <= 0 or height <= 0 or x + width > image_width or y + height > image_height:
                    failures.append(f"invalid bbox: {row.get('sample_id')}")
                label_file = metadata.get("label_file")
                if not label_file:
                    failures.append(f"missing label metadata: {row.get('sample_id')}")
                elif args.dataset_root and not (args.dataset_root / label_file).is_file():
                    failures.append(f"missing label asset: {row.get('sample_id')}")
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                failures.append(f"malformed bbox metadata: {row.get('sample_id')}")
    if failures:
        for item in failures: logging.error(item)
        return 1
    logging.info("Validation passed"); return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s"); sys.exit(main())
