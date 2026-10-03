# Annotation sanity-check notes W1

## Verified from source

- [WEB SOURCE] Svanstrom labels are MATLAB Computer Vision Toolbox `groundTruth` MCOS `.mat` objects, not ordinary `scipy.io.loadmat` matrices.
- [WEB SOURCE] A supported decoder returns a per-frame `(x, y, w, h)` bbox or `None` when the target is absent.
- [WEB SOURCE] The public description identifies four video labels: Airplane, Bird, Drone and Helicopter.

## Local W1 check status

| Check | Result | Evidence |
|---|---|---|
| Label assets available locally | PASS | 650 video/`*_LABELS.mat` pairs are present. |
| `.mat` parser installed/runnable | PASS | `mcos-decoder` + SciPy decoded all 650 label files. |
| Bbox width/height and image bounds | PASS (100-frame sanity check) | Every selected bbox had positive extent and lay within its decoded image. |
| Class ID consistency | PASS (100-frame sanity check) | Filename-derived classes match IDs: Airplane=0, Bird=1, Drone=2, Helicopter=3. |
| Frame association | PASS (100-frame sanity check) | Each sample indexes a readable source video and its paired label file. |
| Track identity | NO | Decoder output is per-frame bbox only; no persistent track ID is present in the inspected representation. |

Across all 650 parsed label files, 12 sequences had no positive bbox on any frame: `IR_BIRD_007`, `IR_BIRD_038`, `IR_DRONE_143`–`IR_DRONE_147`, `V_BIRD_005`, `V_BIRD_009`, `V_DRONE_106`, `V_DRONE_107`, and `V_HELICOPTER_040`. There were no malformed labels. They were excluded from the 100-frame sample selection; this is an observed data-quality condition, not a parser failure.

Do not treat this as a full annotation audit. The validation script will perform the W1 checks once a real sample index exists.
