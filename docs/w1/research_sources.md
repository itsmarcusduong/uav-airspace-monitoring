# W1 research source map

| ID | Topic | Paper | Official Code | Dataset | License | Local Resource | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| SRC-001 | Thesis scope | [Proposal](../../%C4%90%E1%BB%81%20c%C6%B0%C6%A1ng.docx) | N/A | Candidate drone data | Project rules | Local DOCX | VERIFIED | W1 requires dataset manifest and 100 traceable frames; split by video to avoid leakage. |
| SRC-002 | Report/evidence template | [E1 template](../../E1_Template_QuyenDoAn_2026_v0.docx) | N/A | N/A | N/A | Local DOCX | VERIFIED | Requires data card, license, split protocol, EDA and reproducible evidence. |
| SRC-003 | Svanstrom dataset | [Dataset repository](https://github.com/DroneDetectionThesis/Drone-detection-dataset) | Same repository | IR/visible/audio; 650 videos | CC0-1.0 | Local archive + file inventory + 100 samples | VERIFIED | 650 paired videos/labels and 203,328 readable frames verified; MATLAB MCOS `.mat` labels. |
| SRC-004 | Anti-UAV | [Anti-UAV repository](https://github.com/ZhaoJ9014/Anti-UAV) | Same repository | Anti-UAV300/410/600 | MIT for code; media terms NEEDS_REVIEW | Web source | PARTIALLY_VERIFIED | RGB+IR stated for 300; 410/600 IR-only; per-frame boxes/visibility flags. |
| SRC-005 | VisDrone | [VisDrone repository](https://github.com/VisDrone/VisDrone-Dataset) | Same repository | Drone-mounted-camera benchmark | UNKNOWN | Local DET/MOT papers | VERIFIED | Supporting reference, not target-UAV primary training data. |
| SRC-006 | ByteTrack | [arXiv:2110.06864](https://arxiv.org/abs/2110.06864) | [FoundationVision/ByteTrack](https://github.com/FoundationVision/ByteTrack) | MOT benchmarks | MIT | Local PDF + code | VERIFIED | Detector boxes with score feed two-stage association and track IDs. |
| SRC-007 | BoT-SORT | [arXiv:2206.14651](https://arxiv.org/abs/2206.14651) | [NirAharon/BoT-SORT](https://github.com/NirAharon/BoT-SORT) | MOT benchmarks | MIT | Local PDF + code | VERIFIED | Adds camera-motion compensation and optional ReID to tracking-by-detection. |
| SRC-008 | RT-DETR | [arXiv:2304.08069](https://arxiv.org/abs/2304.08069) | [lyuwenyu/RT-DETR](https://github.com/lyuwenyu/RT-DETR) | COCO/Objects365 pretraining | Apache-2.0 | Local PDF + code | VERIFIED | End-to-end detector; official repo lists small-object sliced inference support. |
| SRC-009 | YOLO tracking | N/A | [Ultralytics](https://github.com/ultralytics/ultralytics) | N/A | AGPL-3.0 / Enterprise terms | Web docs | VERIFIED | Official track mode exposes ByteTrack and BoT-SORT configs; verify licensing before integration. |
| SRC-010 | UAVDT benchmark | [arXiv:1804.00518](https://arxiv.org/abs/1804.00518) | OFFICIAL SOURCE CODE NOT FOUND | UAVDT | UNKNOWN | Local PDF | PARTIALLY_VERIFIED | UAV-camera vehicle benchmark, not a target-UAV dataset. |
