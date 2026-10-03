# E1 UAV Airspace Monitoring

**Repository description:** Reproducible research, data governance and implementation evidence for the E1 graduation project, *Detection, classification and tracking of UAVs in airport airspace using deep learning*.

This is the clean handoff repository for weekly review by Lê Ngọc An, Dương Minh Quang, and the supervisor. It deliberately excludes large datasets, model weights, downloaded upstream repositories, dependency caches, and generated image frames.

## Week 1 status

Svanstrom Drone-detection-dataset is the primary W1 dataset. The local evidence records 650 paired videos/labels, 203,328 readable frames, and 100 validated, traceable representative frames from distinct source videos. Anti-UAV is secondary; VisDrone is reference-only and must not be treated as a drone-as-target training dataset.

See [W1 status](docs/w1/w1_data_status.md), [MVP specification](docs/w1/mvp_specification.md), [dataset decision](docs/w1/dataset_decision.md), and [validation report](docs/w1/validation_report.md).

## Weekly submission

The W1 deliverables to upload to Google Drive are in [`reports/w1/`](reports/w1/). The group keeps each submitted week immutable and creates a new pair of PDFs for the following week. Follow the [submission checklist](docs/w1/submission_checklist.md); one group representative submits the two shared links.

## Repository layout

| Path | Purpose |
|---|---|
| `docs/w1/` | Research synthesis, source map, decisions, risks, handoff review, and W1 evidence. |
| `docs/reference/` | Project brief and E1 assessment tracker supplied by the group; reference-only. |
| `data/manifests/` | Dataset manifest and license matrix. |
| `data/samples/index_100_frames.csv` | Traceable metadata for the 100 validated samples. |
| `scripts/dataset/` | Reproducible dataset inspection, sample extraction, and validation scripts. |
| `scripts/reporting/` | Script used to regenerate weekly submission PDFs. |
| `reports/w1/` | The two immutable W1 PDFs submitted to the supervisor. |
| `resources/metadata/` | Small file-level inventory and hashes for the Svanstrom archive. |

## Reproduce W1 evidence

1. Follow [the manual retrieval guide](docs/w1/manual_download_guide.md) to obtain the official Svanstrom archive. Do not commit extracted data.
2. Install Python dependencies in an isolated environment: OpenCV, SciPy, Pillow, and `mcos-decoder`.
3. Run the commands documented in [scripts/dataset/README.md](scripts/dataset/README.md).

## Data and license note

The repository stores links, manifests, checksums and metadata only. Consult [license_matrix.csv](data/manifests/license_matrix.csv) before downloading or redistributing any dataset. The upstream Svanstrom repository declares CC0-1.0; Anti-UAV and VisDrone media terms remain subject to separate verification.
