| Mô hình | Seed | mAP@0.5:0.95 (TB ± SD) | min–max | ms/ảnh (TB) | F1 Drone (TB) |
|---|---|---|---|---|---|
| baseline_A | 20261013, 20261029, 20261030 | 0.3379 ± 0.0037 | 0.3352–0.3421 | 3.19 | 0.819 |
| yolo11n_640 | 20261013, 20261029, 20261030 | 0.3440 ± 0.0027 | 0.3417–0.3470 | 3.21 | 0.834 |

**Quyết định theo luật:** yolo11n_640 — hoa mAP va toc do, |delta F1 Drone| >= 0.01. delta mAP50-95 (yolo11n_640 - baseline_A) = +0.0061; hoa mAP; chenh toc do tuong doi = 0.007; hoa toc do; delta F1 Drone = +0.0142
