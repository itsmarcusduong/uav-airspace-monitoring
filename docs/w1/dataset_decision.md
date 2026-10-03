# Dataset decision W1

## Decision

**[DECISION] Svanstrom is the W1 primary dataset.** The local archive was decoded end-to-end: 650 paired videos/labels and 203,328 readable frames were verified, and 100 traced samples passed validation. The training/validation/test protocol remains intentionally unfrozen until W2, when it will be allocated by video/source group.

| Dataset | Category | Suitability | Reason |
|---|---|---|---|
| Svanstrom Drone-detection-dataset | Primary candidate | suitable | [WEB SOURCE] Ground/sensor-facing IR and visible video, four target/hard-negative labels, 650 video IDs, and per-frame `.mat` labels. Its Drone/Bird/Airplane/Helicopter semantics align with the proposal. |
| Anti-UAV | Secondary candidate | partially suitable | [WEB SOURCE] Purpose-built UAV RGB/IR tracking data, boxes and visibility flags add single-target tracking/occlusion cases. Code is MIT, but dataset-media terms need separate verification; class diversity/hard negatives are less clear. |
| VisDrone | Reference only | reference | [WEB SOURCE] Its camera is mounted on a drone and it labels ground objects. It helps study tiny objects, occlusion and MOT conventions, but is not the thesis's camera/target geometry. **Not automatically included in primary training.** |
| UAVDT and datasets cited by UAV benchmark | Reference only | reference | [DOCUMENT/WEB SOURCE] Useful for small-object and moving-camera methodology; it is not a drone-as-target source. |

## Comparison

| Criterion | Svanstrom | Anti-UAV | VisDrone | UAVDT |
|---|---|---|---|---|
| Viewpoint | sensor watching sky | sensor watching UAV | UAV watching ground | UAV watching ground |
| UAV as target | yes | yes | no | no |
| Bird/airplane negatives | yes | UNKNOWN | no target-equivalent class | no |
| Video | yes | yes | yes | yes |
| Bbox | yes | yes | yes | yes |
| Track ID | UNKNOWN | implicit single target; confirm | yes | yes |
| License evidence | CC0 declared | code MIT only | NEEDS_REVIEW | NEEDS_REVIEW |
| Detection use | strong candidate | supporting | methodological only | methodological only |
| Tracking use | requires ID validation | strong supplemental candidate | benchmark reference | benchmark reference |

## W2 gate

Decode a reproducible Svanstrom subset, inspect bbox/frame alignment, inspect `Video_dataset_description.xlsx`, allocate whole video IDs to train/val/test, and record the exact commit/checksum. Do not train until this gate passes.
