# E1 UAV Airspace Monitoring

Reproducible research evidence for the E1 graduation project: **Detection, classification and tracking of UAVs in airport airspace using deep learning**.

This is repository for weekly review by Lê Ngọc An, Dương Minh Quang, and the supervisor. It deliberately excludes large datasets, model weights, downloaded upstream repositories, dependency caches, and generated image frames.

## Week 1 status

Svanstrom Drone-detection-dataset is the primary W1 dataset. The local evidence records 650 paired videos/labels, 203,328 readable frames, and 100 validated, traceable representative frames from distinct source videos. Anti-UAV is secondary; VisDrone is reference-only and must not be treated as a drone-as-target training dataset.

See [W1 status](docs/w1/w1_data_status.md), [dataset decision](docs/w1/dataset_decision.md), and [validation report](docs/w1/validation_report.md).

## Repository layout

| Path | Purpose |
|---|---|
| `docs/w1/` | Research synthesis, source map, decisions, risks, handoff review, and W1 evidence. |
| `data/manifests/` | Dataset manifest and license matrix. |
| `data/samples/index_100_frames.csv` | Traceable metadata for the 100 validated samples. |
| `scripts/dataset/` | Reproducible dataset inspection, sample extraction, and validation scripts. |
| `resources/metadata/` | Small file-level inventory and hashes for the Svanstrom archive. |

## Reproduce W1 evidence

1. Follow [the manual retrieval guide](docs/w1/manual_download_guide.md) to obtain the official Svanstrom archive. Do not commit extracted data.
2. Install Python dependencies in an isolated environment: OpenCV, SciPy, Pillow, and `mcos-decoder`.
3. Run the commands documented in [scripts/dataset/README.md](scripts/dataset/README.md).

## Data and license note

The repository stores links, manifests, checksums and metadata only. Consult [license_matrix.csv](data/manifests/license_matrix.csv) before downloading or redistributing any dataset. The upstream Svanstrom repository declares CC0-1.0; Anti-UAV and VisDrone media terms remain subject to separate verification.
