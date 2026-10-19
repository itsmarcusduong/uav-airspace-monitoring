from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SPLITS = ("train", "val", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_DATASET = Path("results/W03/kaggle_run_03/yolo_dataset")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_class_names(dataset: Path) -> dict[int, str]:
    for yaml_path in (dataset / "data.yaml", dataset / "dataset.yaml"):
        if not yaml_path.is_file():
            continue

        text = yaml_path.read_text(encoding="utf-8-sig")
        names: dict[int, str] = {}
        in_names = False

        for line in text.splitlines():
            if re.match(r"^\s*names\s*:", line):
                in_names = True
                inline = line.split(":", 1)[1].strip()
                if inline.startswith("["):
                    try:
                        values = ast.literal_eval(inline)
                        return {i: str(name) for i, name in enumerate(values)}
                    except (ValueError, SyntaxError):
                        pass
                continue

            if in_names:
                match = re.match(r"^\s*(\d+)\s*:\s*['\"]?([^'\"#]+)", line)
                if match:
                    names[int(match.group(1))] = match.group(2).strip()
                elif line and not line[0].isspace():
                    break

        if names:
            return names

    return {}


def read_yolo_label(path: Path, class_names: dict[int, str]) -> tuple[Counter, list[str]]:
    counts: Counter = Counter()
    errors: list[str] = []

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        return counts, [f"Cannot read label: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue

        fields = line.split()
        if len(fields) != 5:
            errors.append(f"Line {line_number}: expected 5 fields, got {len(fields)}")
            continue

        try:
            class_id = int(fields[0])
            x_center, y_center, width, height = map(float, fields[1:])
        except ValueError:
            errors.append(f"Line {line_number}: non-numeric field")
            continue

        if class_id < 0:
            errors.append(f"Line {line_number}: negative class ID {class_id}")
        if not all(0.0 <= value <= 1.0 for value in (x_center, y_center, width, height)):
            errors.append(f"Line {line_number}: coordinates/dimensions outside [0, 1]")
        if width <= 0 or height <= 0:
            errors.append(f"Line {line_number}: width and height must be positive")

        counts[class_names.get(class_id, str(class_id))] += 1

    return counts, errors


def discover_files(dataset: Path, split: str, folder: str, suffixes: set[str]) -> list[Path]:
    directory = dataset / split / folder
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write Git-trackable inventory and validation reports for a YOLO dataset."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    output = (args.output or dataset.parent / "reports").resolve()
    output.mkdir(parents=True, exist_ok=True)

    if not dataset.is_dir():
        parser.error(f"Dataset directory not found: {dataset}")

    class_names = find_class_names(dataset)
    file_rows: list[dict] = []
    split_summaries: dict[str, dict] = {}
    stages: list[dict] = []
    all_errors: list[str] = []

    for split in SPLITS:
        images = discover_files(dataset, split, "images", IMAGE_EXTENSIONS)
        labels = discover_files(dataset, split, "labels", {".txt"})

        image_by_stem = {path.stem: path for path in images}
        label_by_stem = {path.stem: path for path in labels}
        split_errors: list[str] = []

        missing_labels = sorted(set(image_by_stem) - set(label_by_stem))
        missing_images = sorted(set(label_by_stem) - set(image_by_stem))

        split_errors.extend(f"Missing label for image: {stem}" for stem in missing_labels)
        split_errors.extend(f"Label has no matching image: {stem}" for stem in missing_images)

        total_objects = 0
        empty_labels = 0
        class_counts: Counter = Counter()

        for image in images:
            label = label_by_stem.get(image.stem)
            label_counts: Counter = Counter()
            label_errors: list[str] = []

            if label is not None:
                label_counts, label_errors = read_yolo_label(label, class_names)
                if not label_counts:
                    empty_labels += 1
                total_objects += sum(label_counts.values())
                class_counts.update(label_counts)
                split_errors.extend(
                    f"{label.relative_to(dataset)}: {error}" for error in label_errors
                )

            file_rows.append({
                "split": split,
                "type": "image",
                "relative_path": image.relative_to(dataset).as_posix(),
                "paired_label": label.relative_to(dataset).as_posix() if label else "",
                "size_bytes": image.stat().st_size,
                "sha256": sha256_file(image),
                "object_count": sum(label_counts.values()),
                "class_counts_json": json.dumps(dict(label_counts), sort_keys=True),
                "validation_errors_json": json.dumps(label_errors),
            })

        for label in labels:
            counts, errors = read_yolo_label(label, class_names)
            image = image_by_stem.get(label.stem)
            file_rows.append({
                "split": split,
                "type": "label",
                "relative_path": label.relative_to(dataset).as_posix(),
                "paired_label": image.relative_to(dataset).as_posix() if image else "",
                "size_bytes": label.stat().st_size,
                "sha256": sha256_file(label),
                "object_count": sum(counts.values()),
                "class_counts_json": json.dumps(dict(counts), sort_keys=True),
                "validation_errors_json": json.dumps(errors),
            })

        status = "OK" if not split_errors else "FAILED"
        stages.append({
            "stage": f"{split}_inventory_and_validation",
            "status": status,
            "images": len(images),
            "labels": len(labels),
            "errors": split_errors,
        })
        all_errors.extend(f"{split}: {error}" for error in split_errors)

        split_summaries[split] = {
            "images": len(images),
            "labels": len(labels),
            "missing_labels": len(missing_labels),
            "labels_without_images": len(missing_images),
            "empty_labels": empty_labels,
            "objects": total_objects,
            "objects_by_class": dict(sorted(class_counts.items())),
        }

    manifest_path = output / "files.csv"
    columns = [
        "split", "type", "relative_path", "paired_label", "size_bytes",
        "sha256", "object_count", "class_counts_json", "validation_errors_json",
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(file_rows)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path_at_generation": str(dataset),
        "class_names_from_yaml": class_names,
        "splits": split_summaries,
        "file_count": len(file_rows),
        "validation_status": "OK" if not all_errors else "FAILED",
        "validation_errors": all_errors,
        "files_csv": manifest_path.name,
        "files_csv_sha256": sha256_file(manifest_path),
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    stages.extend([
        {
            "stage": "file_inventory_and_sha256",
            "status": "OK",
            "files_hashed": len(file_rows),
        },
        {
            "stage": "overall",
            "status": summary["validation_status"],
            "errors": all_errors,
        },
    ])
    (output / "stage_status.json").write_text(
        json.dumps({"stages": stages}, indent=2),
        encoding="utf-8",
    )

    readme = f"""# W3 YOLO dataset export evidence

The image/label dataset is intentionally kept out of Git. This directory contains
compact inventory, checksum, summary, and validation reports for it.

## Reproduce

From the repository root, run the exporter with the same approved ADR-0004
settings and inputs used for this run:

```powershell
python scripts/kaggle/w3_export_yolo.py
```

Then regenerate these reports:

```powershell
python scripts/kaggle/report_yolo_dataset.py --dataset results/W03/kaggle_run_03/yolo_dataset --output results/W03/kaggle_run_03/reports
```

The exporter must use the approved video split and annotation policy. Record the
actual split hash, stride, class mapping, source data version, and exporter commit
in the run evidence before treating a rerun as equivalent.

## Reports

- `files.csv`: one row per image and label file, with relative path, size, SHA-256,
  paired file, and label counts.
- `summary.json`: per-split image/label/object counts, class counts, and validation result.
- `stage_status.json`: validation status and any errors.

## Current run summary

```json
{json.dumps(split_summaries, indent=2)}
```

Validation status: **{summary["validation_status"]}**
"""

    (output / "README.md").write_text(readme, encoding="utf-8")
    print(f"Reports written to: {output}")
    print(f"Validation status: {summary['validation_status']}")
    return 0 if not all_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
```

Run it from the repository root:

```powershell
python .\scripts\reporting\report_yolo_dataset.py `
  --dataset .\results\W03\kaggle_run_03\yolo_dataset `
  --output .\results\W03\kaggle_run_03\reports
```

It returns exit code `1` and marks validation as failed if it finds missing image/label pairs or malformed labels; it won’t silently treat those results as valid."""