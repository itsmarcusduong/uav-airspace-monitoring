# Manual download and W1 completion guide

## Why manual download is required

Historical status: `DS-SVANSTROM` was **MANUAL_DOWNLOAD_REQUIRED** after the automated shallow clone stalled on 2026-10-03. Quang manually downloaded the archive on 2026-10-04; it is now `downloaded-verified`. This guide remains as the reproducible retrieval procedure.

## Resource to download

| Item | Official link | What to download | Destination in this project |
|---|---|---|---|
| Svanstrom dataset repository | [Repository](https://github.com/DroneDetectionThesis/Drone-detection-dataset) | Click **Code -> Download ZIP**, or use [official master archive](https://github.com/DroneDetectionThesis/Drone-detection-dataset/archive/refs/heads/master.zip). | Extract to `resources/datasets/svanstrom-drone-detection-dataset/` |
| Dataset metadata | [Video_dataset_description.xlsx](https://raw.githubusercontent.com/DroneDetectionThesis/Drone-detection-dataset/master/Data/Video_dataset_description.xlsx) | Included in the ZIP; download this alone only if the archive extraction is incomplete. | `resources/datasets/svanstrom-drone-detection-dataset/Data/Video_dataset_description.xlsx` |
| License | [LICENSE](https://github.com/DroneDetectionThesis/Drone-detection-dataset/blob/master/LICENSE) | Included in the ZIP. | Dataset root `LICENSE` |

The extracted root must contain `README.md`, `LICENSE`, `Data/Video_IR/`, `Data/Video_V/`, and `Data/Video_dataset_description.xlsx`. Keep video files together with their matching `*_LABELS.mat` files. Do not commit this dataset or generated samples to Git without an explicit storage plan.

## Validate the manual download

From the project root in PowerShell:

```powershell
$dataset = 'resources/datasets/svanstrom-drone-detection-dataset'
Get-FileHash "$dataset\Data\Video_dataset_description.xlsx" -Algorithm SHA256
python scripts/dataset/inspect_dataset.py --root $dataset --output resources/metadata/svanstrom_files.csv
```

Record the archive SHA-256 and the generated inventory in `docs/w1/resource_inventory.csv`. The file inventory produces individual content hashes, making the subset traceable even if the upstream `master` branch changes.

## Required local runtime

Use an isolated Python environment with `opencv-python`, `scipy`, `Pillow`, and `mcos-decoder`. `mcos-decoder` is specifically documented by the upstream repository for its MATLAB MCOS labels; ordinary `scipy.io.loadmat` is not enough for these labels.

```powershell
python -m venv .venv-w1
.\.venv-w1\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install opencv-python scipy Pillow mcos-decoder
```

## Completion sequence after download

1. Keep the internal `Data` tree unchanged; the extractor accepts either this inner root or its archive-created parent.
2. Run the inventory command above and retain its output.
3. Run the sample extractor. It will stop safely unless at least 100 readable source videos exist:

```powershell
python scripts/dataset/extract_samples.py --root resources/datasets/svanstrom-drone-detection-dataset --output data/samples --seed 20261003
```

4. Run validation:

```powershell
python scripts/dataset/validate_manifest.py --manifest data/manifests/dataset_manifest_v1.csv --samples data/samples/index_100_frames.csv
```

5. Update the manifest checksums, local counts, annotation notes and validation report from observed output. Only then can W1 move from `NOT READY` to `READY FOR QUANG REVIEW`.

## Secondary resource, not required to finish W1 primary-data gate

Anti-UAV300's official repository supplies its [download entry](https://github.com/ZhaoJ9014/Anti-UAV#data-preparation) and recommends the RGB+IR 300 variant. Do **not** download it yet: dataset-media terms are still `NEEDS_REVIEW`, and it is a secondary candidate rather than the W1 primary-source gate.
