# W3 YOLO dataset export evidence

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
{
  "train": {
    "images": 5172,
    "labels": 5172,
    "missing_labels": 0,
    "labels_without_images": 0,
    "empty_labels": 0,
    "objects": 5172,
    "objects_by_class": {
      "0": 2538,
      "3": 2634
    }
  },
  "val": {
    "images": 1136,
    "labels": 1136,
    "missing_labels": 0,
    "labels_without_images": 0,
    "empty_labels": 0,
    "objects": 1136,
    "objects_by_class": {
      "0": 573,
      "3": 563
    }
  },
  "test": {
    "images": 1078,
    "labels": 1078,
    "missing_labels": 0,
    "labels_without_images": 0,
    "empty_labels": 0,
    "objects": 1078,
    "objects_by_class": {
      "0": 570,
      "3": 508
    }
  }
}
```

Validation status: **OK**
