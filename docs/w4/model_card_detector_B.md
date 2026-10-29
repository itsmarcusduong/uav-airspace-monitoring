# Model card — detector B (YOLOv8s @960)

> Trạng thái: hoàn tất train và phân tích W4, run 09 phiên 2, 29/10/2026. Các số kết quả dưới đây là trên **validation**; test vẫn khóa. Nguồn trạng thái/ngày: `results/W04/kaggle_run_09/phien_2/train_detector_B/stage_status.json`, `analysis_detector_B/stage_status.json`.

## 1. Thông tin mô hình

| Mục | Giá trị | Nguồn |
|---|---|---|
| Kiến trúc | YOLOv8s, khởi tạo từ trọng số COCO `yolov8s.pt` | `results/W04/kaggle_run_09/phien_2/train_detector_B/detector_B.yaml` |
| Kích thước ảnh vào | 960 × 960 | `detector_B.yaml`, `train/args.yaml` |
| Lớp | Airplane=0, Bird=1, Drone=2, Helicopter=3 | `results/W04/kaggle_run_09/phien_2/train_detector_B/dataset_card.json`; thứ tự lớp: ADR-0004 |
| Phiên bản thư viện | Ultralytics 8.4.183; torch 2.11.0+cu128; Python 3.13.15 | `results/W04/kaggle_run_09/phien_2/train_detector_B/env.json` |
| Phần cứng train | 1 × Tesla T4, 15 GB | `env.json`, `train/args.yaml` |
| Commit mã / cấu hình | `1a71f5b`; SHA-256 config `a565bc9d…` | `env.json` |
| Dữ liệu | `e1-yolo-v1`, fingerprint `d0ac7e23…`; train 5.667 ảnh, val 1.202 ảnh | `stage_status.json`, `dataset_card.json` |
| Số epoch chạy / epoch tốt nhất | 42 / 50; epoch tốt nhất 27 theo mAP@0.5:0.95 | `results/W04/comparison_w4.csv`, `analysis_detector_B/analysis_summary.json` |
| Thời gian train | 112,9 phút | `results/W04/comparison_w4.csv` (`train_minutes`) |
| Weights tốt nhất | `best.pt`, SHA-256 `04f320964b63a3df227572428a6e977eea2b715eb558db90711127b6cbf316ba`, 22.563.050 byte; [tải từ Drive](https://drive.google.com/file/d/1BfJQlurjwIOAs8kxf6oR3pXrRKxItuMt/view) | `results/W04/kaggle_run_09/phien_2/train_detector_B/weights_manifest.json`; manifest ghi bản tải về khớp SHA-256 và kích thước (28/10/2026) |
| Weights cuối | `last.pt`, SHA-256 `3578b6fe6a9f285c8e0f8abb5cc5ce0bc5a6341c08ec33ae00981d2c003681cb`, 22.563.050 byte; [tải từ Drive](https://drive.google.com/file/d/1g9IUlzP-ydLqolw_7xiK3soLWy5IWzsl/view) | `weights_manifest.json`; manifest ghi bản tải về khớp SHA-256 và kích thước (28/10/2026) |
| Giấy phép | Ultralytics và weights COCO: AGPL-3.0 theo ma trận giấy phép của repo | `data/manifests/license_matrix.csv` |

## 2. Dữ liệu

`e1-yolo-v1` dùng ảnh Visible gốc 640×512, stride 10, chính sách offset0. Run này có 5.667 ảnh train và 1.202 ảnh val; dữ liệu chia theo video và test chưa sử dụng. Nguồn: `results/W04/kaggle_run_09/phien_2/train_detector_B/dataset_card.json`, `train_detector_B/stage_status.json`, `docs/w2/annotation_audit_w2.md`, ADR-0006.

## 3. Mục đích sử dụng

Đối chứng YOLOv8s @960 trong W4 và phân tích offline khả năng phát hiện bốn lớp vật thể bay trên ảnh Visible ban ngày. **Không dùng cho vận hành thật tại sân bay hoặc quyết định an toàn**: kết quả chỉ là validation, dữ liệu có giới hạn nhãn/cảnh và chưa có đánh giá test độc lập. Nguồn: `docs/w4/training_protocol_w4.md`, `docs/decisions/ADR-0007-w4-model-selection.md`, `docs/w2/annotation_audit_w2.md`.

## 4. Kết quả trên validation

| Lớp | Precision | Recall | AP@0.5 | AP@0.5:0.95 |
|---|---:|---:|---:|---:|
| Airplane | 0,843 | 0,615 | 0,756 | 0,348 |
| Bird | 0,582 | 0,986 | 0,671 | 0,315 |
| Drone | 0,748 | 0,813 | 0,713 | 0,229 |
| Helicopter | 0,913 | 0,905 | 0,932 | 0,413 |
| Tất cả | 0,772 | 0,830 | 0,768 | 0,326 |

Nguồn mọi số trong bảng: `results/W04/kaggle_run_09/phien_2/train_detector_B/detector_B_val_metrics.json` và `detector_B_val_per_class.csv`. AP được tính từ đường PR; không phải kết quả tại ngưỡng vận hành.

## 5. Phân tích validation

Phân tích dùng `best.pt`, IoU khớp 0,5 và chọn ngưỡng theo quy tắc tối đa F1 Drone trên validation, hòa thì chọn ngưỡng cao hơn. Ngưỡng vận hành là **conf=0,30**; Drone P=0,743, R=0,818, F1=0,778; F1 macro=0,780. Số liệu lạc quan vì ngưỡng và checkpoint cùng được chọn trên validation. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/analysis_summary.json`, `operating_points.csv`.

**Recall theo cỡ hộp** tại conf 0,30 (`recall_by_size.csv`):

| Lớp | Nhỏ (<32²) | Vừa (32²–96²) | Lớn (≥96²) |
|---|---:|---:|---:|
| Airplane | 0,790 (64/81) | 0,494 (86/174) | 0,941 (32/34) |
| Bird | 1,000 (71/71) | 0,500 (1/2) | — |
| Drone | 0,894 (235/263) | 0,738 (186/252) | — |
| Helicopter | 0,633 (38/60) | 0,973 (142/146) | 1,000 (79/79) |
| Tất cả | 0,859 (408/475) | 0,723 (415/574) | 0,982 (111/113) |

Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/recall_by_size.csv`; trong ngoặc là TP/GT.

**Theo video:** Airplane recall là 0/33 ở `V_AIRPLANE_027`, 10/33 ở `V_AIRPLANE_005`, 8/30 ở `V_AIRPLANE_007`, nhưng 32/32 ở `V_AIRPLANE_030`. Khác biệt theo cảnh cho thấy recall tổng hợp có thể che khuất các video khó. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/recall_by_video.csv`.

**Nhầm lớp và bỏ sót** (`class_confusion.csv`, conf 0,30): bỏ sót Airplane 80, Bird 1, Drone 91, Helicopter 25; nhầm chéo Airplane→Drone 23, Airplane→Helicopter 9, Airplane→Bird 4, Drone→Airplane 3, Drone→Bird 3, Helicopter→Airplane 3. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/class_confusion.csv`, `analysis_summary.json`.

**Ảnh không có hộp:** 39/40 ảnh được đánh dấu không có hộp có dự đoán tại conf 0,30. Đây không phải phép đo false positive trên nền trống: các ảnh này không được xác nhận là cảnh âm tính thật và frame ngoài phạm vi nhãn là UNKNOWN. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/negatives_fp.json`, `docs/w2/annotation_audit_w2.md`.

## 6. Giới hạn đã biết

- Validation được dùng để dừng sớm, chọn `best.pt` và chọn ngưỡng; các chỉ số và ngưỡng có thể lạc quan. Test còn khóa. Nguồn: `train_detector_B/stage_status.json`, `analysis_detector_B/analysis_summary.json`.
- Một lần chạy với một seed; không có ước lượng dao động giữa seed. Độ lệch chuẩn mAP@0.5:0.95 giữa epoch của B là 0,0196, không phải khoảng tin cậy giữa lần chạy. Nguồn: `results/W04/comparison_w4.csv` (`val_map50_95_epoch_sd`).
- Dù input `imgsz` là 960, ảnh nguồn Visible chỉ 640×512; phóng to không tạo thêm chi tiết ảnh gốc. Nguồn: `docs/w2/annotation_audit_w2.md`, `train_detector_B/train/args.yaml`.
- AP@0.5:0.95 Drone là 0,229; recall Drone giảm từ 0,894 ở hộp nhỏ xuống 0,738 ở hộp vừa. Nguồn: `detector_B_val_metrics.json`, `analysis_detector_B/recall_by_size.csv`.
- Nhãn có vấn đề lệch frame và vùng ngoài phạm vi nhãn không phải negative; dữ liệu không đại diện ảnh đêm, thời tiết xấu hay môi trường sân bay tại Việt Nam. Nguồn: `docs/w2/annotation_audit_w2.md`, ADR-0006.
- Thời gian inference 20,82 ms/ảnh là số đo trong bước validation theo batch, không bao gồm đánh giá FPS toàn pipeline. Nguồn: `results/W04/comparison_w4.csv`, `detector_B_val_metrics.json`.
- YOLOv8s @960 không được chọn làm detector cho W5 theo ADR-0007; model card này ghi nhận kết quả so sánh chứ không thay đổi quyết định chọn model. Nguồn: `docs/decisions/ADR-0007-w4-model-selection.md`.
