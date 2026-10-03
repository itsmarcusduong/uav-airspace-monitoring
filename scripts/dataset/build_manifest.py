#!/usr/bin/env python3
"""Validate that a dataset-manifest CSV has the W1 schema."""
from __future__ import annotations
import argparse, csv, logging
from pathlib import Path

REQUIRED = {"dataset_id", "dataset_name", "source_url", "official_repository", "version", "license", "license_url", "media_type", "task", "classes", "num_videos", "num_sequences", "num_frames", "annotation_format", "has_bbox", "has_track_id", "split", "intended_use", "viewpoint", "source_type", "checksum", "download_status", "license_status", "limitations", "notes"}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Project root (for portable invocation)")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/dataset_manifest_v1.csv"))
    args = parser.parse_args(); manifest = args.root / args.manifest
    with manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle); missing = REQUIRED - set(reader.fieldnames or [])
        rows = list(reader)
    if missing: raise SystemExit(f"Missing columns: {sorted(missing)}")
    ids = [row["dataset_id"] for row in rows]
    if len(ids) != len(set(ids)): raise SystemExit("Duplicate dataset_id")
    logging.info("Manifest is structurally valid: %d rows", len(rows)); return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s"); raise SystemExit(main())
