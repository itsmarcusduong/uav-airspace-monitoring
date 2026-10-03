# W1 validation report

**Run date:** 2026-10-04  
**Command:**

```powershell
python scripts/dataset/build_manifest.py --root .
python scripts/dataset/validate_manifest.py --manifest data/manifests/dataset_manifest_v1.csv --samples data/samples/index_100_frames.csv --dataset-root resources/datasets/svanstrom-drone-detection-dataset/Drone-detection-dataset-master
```

## Result

`build_manifest.py` passed: `Manifest is structurally valid: 4 rows`.

`validate_manifest.py` passed: `INFO Validation passed`.

Validated evidence: 100 sample rows, 100 unique sample IDs, 100 readable JPEGs, 100 unique source video IDs, valid source URLs, class-ID mapping, valid/within-image bbox metadata, and presence of the referenced source label assets. The index SHA-256 is `540794DCB5EE1B42722350F29C981DB2E68993CC175A3339EA5CCD0EA1670DA5`.
