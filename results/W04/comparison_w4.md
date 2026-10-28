| Mô hình | imgsz | mAP@0.5 | mAP@0.5:0.95 | AP@0.5 Drone | F1 Drone @ngưỡng | ngưỡng | recall nhỏ | ms/ảnh | epoch (best) | train |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline_A (yolov8n.pt) | 640 | 0.807 | 0.342 | 0.809 | 0.856 | 0.25 | 0.8632 | 3.26 | 36 (21) | OK |
| baseline_A_aug (yolov8n.pt) | 640 | 0.739 | 0.331 | 0.795 | 0.807 | 0.3 | 0.8 | 3.14 | 24 (9) | OK |
| baseline_A_960 (yolov8n.pt) | 960 | 0.723 | 0.323 | 0.742 | 0.815 | 0.35 | 0.8547 | 6.86 | 45 (30) | OK |
| yolo11n_640 (yolo11n.pt) | 640 | 0.831 | 0.347 | 0.842 | 0.880 | 0.3 | 0.8821 | 3.28 | 35 (20) | OK |
| detector_B (yolov8s.pt) | 960 | 0.768 | 0.326 | 0.713 | 0.778 | 0.3 | 0.8589 | 20.82 | 42 (27) | OK |
| rtdetr_l_640 (rtdetr-l.pt) | 640 | 0.659 | 0.277 | 0.738 | 0.798 | 0.4 | 0.8063 | 42.74 | 17 (2) | INVALID: loss NaN tu epoch 3 |

Tất cả trên **val** (lạc quan: val dùng để dừng sớm, chọn checkpoint và ngưỡng); cùng dữ liệu (fingerprint `d0ac7e230b385132…`), cùng seed và ngân sách 50 epoch/patience 15; GPU Tesla T4. Thời gian suy luận đo trong bước val (batch), không phải FPS pipeline.
