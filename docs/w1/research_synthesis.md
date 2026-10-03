# Research synthesis W1

## 1. Problem definition

[DOCUMENT] The thesis is a video system that detects, classifies and tracks UAVs in a simulated airport-airspace monitoring view, distinguishing hard negatives and later alerting on an image polygon. This is not aerial imagery collected by a drone.

## 2. Dataset landscape

[WEB SOURCE] Svanstrom supplies visible and IR videos plus Airplane, Bird, Drone and Helicopter labels. Anti-UAV is closer to tracking UAV targets and records bbox/visibility in RGB/IR. VisDrone and UAVDT view ground objects from a UAV, so they are methodological references only.

## 3-4. Detection and small objects

[INFERENCE] UAV pixels will often be tiny, low contrast and easily confused with birds or aircraft. Preserve native resolution where possible, report performance by bbox size, and evaluate false positives on hard-negative videos. The VisDrone and UAVDT literature supports the importance of scale variation, camera motion and crowd/background complexity but does not establish matching target semantics.

## 5-7. Tracking, ByteTrack and BoT-SORT

[WEB SOURCE] ByteTrack takes scored detector boxes and associates high-confidence detections first, then uses low-score detections to recover existing tracks; it outputs per-frame tracks with IDs. It is attractive where temporary low confidence can occur but score thresholds must be tuned against false positives. BoT-SORT retains tracking-by-detection, adds a better Kalman state, camera-motion compensation and optional ReID. [INFERENCE] For mostly static monitoring cameras, start with ByteTrack; evaluate BoT-SORT later only if ID switches/occlusions justify ReID overhead. Neither tracker is integrated in W1.

## 8. RT-DETR

[WEB SOURCE] RT-DETR is an end-to-end real-time detector with a hybrid multi-scale encoder and uncertainty-minimal query selection; its official implementation is Apache-2.0. [INFERENCE] It is a valid detector baseline candidate but tiny-UAV performance must be measured on the fixed thesis split, not inferred from COCO speed/AP.

## 9. YOLO/Ultralytics

[WEB SOURCE] Ultralytics track mode supports ByteTrack and BoT-SORT with configurable score, matching and track-buffer thresholds. It is an interface reference, not a W1 integration task. Licensing must be decided independently before code adoption.

## 10-13. Challenges, hard negatives and annotation

Birds, aircraft, helicopters, blur, IR/visible domain shift, thin silhouettes, intermittent appearance and background clutter are likely failure modes. Svanstrom's hard-negative classes are unusually useful. Bounding boxes must be checked for positive extent, image bounds, frame synchronization and valid class mapping before any training.

## 14-16. Split, leakage and reproducibility

Split by video/sequence/source group; never randomize adjacent frames across partitions. Record upstream URL, retrieval date, commit/version, checksum, license and source IDs. Keep large data out of Git.

## 17. Dataset recommendation

[DECISION] Svanstrom is the primary dataset: its local archive, 650 pairs, 203,328 decodable frames and 100 traced samples passed the W1 gate. Anti-UAV remains tracking-focused secondary candidate, and VisDrone/UAVDT remain reference. Do not begin training until W2 freezes a video-level split.
