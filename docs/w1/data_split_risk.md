# Dataset split and leakage risk

The proposal requires train/validation/test splitting by video. [INFERENCE] Random frame splitting is unacceptable because adjacent frames share scene, target appearance, motion and compression artifacts; it would inflate detection and tracking results.

Svanstrom is organized by 650 video IDs and labels are associated with each video. Its workbook has 650 data records and six fields: `SENSOR`, `CLASS`, `NUMBER`, `DISTANCE BIN`, `INTER BIN NUMBER`, and `DRONE TYPE / INTERNET SOURCE`. No thesis split has been frozen. Anti-UAV and VisDrone publish benchmark partitions, but they must not be merged casually with Svanstrom. W2 action: create a deterministic video-ID split manifest; keep all frames from a sequence and source group in one partition; reserve a held-out test set before tuning; record seed, source IDs and class/modalities in the split report.
