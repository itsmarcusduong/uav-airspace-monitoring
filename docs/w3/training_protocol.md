# Giao thức huấn luyện baseline A (W3-04)

> Khung do Quang chuẩn bị 13/10/2026. Quang review trong PR. Không đổi giao thức sau khi đã chạy run chính thức; muốn đổi → phiên bản mới + ADR. Tất cả các ô `[An điền]` đã điền, chờ run 04 cho mục 5

## 1. Mục tiêu
Huấn luyện detector cơ sở (baseline A) theo Đề cương W3 để có Weights A, learning curves và mAP trên validation, làm mốc so sánh cho W4 (detector B / tuning).

## 2. Dữ liệu
| Mục | Giá trị | Nguồn |
|---|---|---|
| Bộ dữ liệu | Svanström Drone-detection-dataset, ảnh khả kiến | ADR-0004 mục 1 |
| Phiên bản dữ liệu xuất | `e1-yolo-v1` (fingerprint ghi trong `dataset_card.json`) | Kaggle run 03 |
| Split | video v1, chỉ train + val; test khóa | ADR-0003, ADR-0004 |
| Lấy mẫu | stride 10 | ADR-0004 mục 4 |
| Xử lý nhãn lệch | giữ video dư 1 mục với offset 0 (ADR-0004, mục Kết quả thực hiện) | ADR-0004 mục 5–6 |
| Số ảnh/lớp/split | train: Airplane 1.280, Bird 672, Drone 2.386, Helicopter 1.329 (5.667 ảnh (gồm âm tính)); val: Airplane 289, Bird 96, Drone 532, Helicopter 285 (1.202 ảnh (gồm âm tính)) | `results/W03/kaggle_run_03b/export_evidence/dataset_stats.csv` |

## 3. Mô hình
YOLOv8n COCO-pretrained, ảnh 640. Lý do chọn: YOLOv8n @640 là baseline đã nêu trong Thuyết minh 7.2; biến thể nano là lựa chọn gọn để làm mốc so sánh, không hàm ý đã chứng minh ưu việt. Ảnh Visible gốc rộng 640 px, nên đầu vào 640 giữ nguyên chiều rộng và letterbox thêm padding theo chiều cao để giữ tỷ lệ.
License mã nguồn và weights: theo kiểm tra W3-07 (#20), Ultralytics và `yolov8n.pt` dùng AGPL-3.0; nguồn chính thức: [LICENSE Ultralytics](https://github.com/ultralytics/ultralytics/blob/main/LICENSE) và [kho assets Ultralytics](https://github.com/ultralytics/assets). AGPL-3.0 mục 13 có nghĩa vụ cung cấp Corresponding Source khi người dùng tương tác từ xa qua mạng với phiên bản đã sửa đổi; cần đánh giá điều kiện áp dụng cụ thể, đây không phải tư vấn pháp lý.

## 4. Siêu tham số (`configs/baseline_A.yaml`)
| Tham số | Giá trị | Lý do |
|---|---|---|
| imgsz | 640 | Theo baseline Thuyết minh 7.2; phù hợp chiều rộng ảnh Visible gốc 640 px, letterbox giữ tỷ lệ khung hình. |
| epochs / patience | 50 / 15 | 50 là giới hạn epoch; dừng sớm nếu fitness trên val không cải thiện 15 epoch để khống chế ngân sách mà không thêm tiêu chí tuning. |
| batch | 32 | Cố định theo cấu hình baseline để các lần chạy có điều kiện so sánh và tái lập nhất quán. |
| optimizer, lr | auto (mặc định Ultralytics) | Giữ lựa chọn tự động và learning rate do Ultralytics quyết định, tránh thêm một chiều tuning ở W3; ghi phiên bản thư viện và giá trị thực tế từ log run. |
| augmentation | mặc định Ultralytics (mosaic tắt 10 epoch cuối) | không tuning ở W3 |
| seed / deterministic | 20261013 / true | tái lập |

## 5. Ngân sách và phần cứng
GPU Kaggle (loại GPU ghi trong `env.json` của run 04). Thời gian train: `[điền sau run 04]`. Mỗi run chính thức ghi: seed, config SHA-256, commit, dataset fingerprint, phiên bản torch/ultralytics.

## 6. Chọn checkpoint và giới hạn
`best.pt` = epoch có fitness cao nhất trên val (Ultralytics: 0,1·mAP@0.5 + 0,9·mAP@0.5:0.95). Vì val vừa dùng để chọn checkpoint vừa để báo cáo, số liệu W3 là **lạc quan**. Test chỉ dùng ở đánh giá cuối. Không tách thêm val nội bộ ở W3: split v1 đã chia theo video, tách tiếp sẽ giảm dữ liệu train (5.667 ảnh) mà không loại bỏ việc dùng val để chọn checkpoint; giữ test khóa và diễn giải số liệu val là lạc quan. Đánh giá độc lập cần một giao thức/tập đánh giá mới, không đổi split sau khi chạy.

## 7. Chỉ số báo cáo (Thuyết minh mục 12)
- Precision, recall, mAP@0.5, mAP@0.5:0.95: tổng và theo từng lớp (`baseline_A_val_per_class.csv`).
- Learning curves (`results.csv`, `results.png`), PR curve, confusion matrix.
- Theo cỡ bbox (nhỏ < 32×32 px trên ảnh gốc): recall theo nhóm cỡ, tính từ `predictions.json` + `yolo_manifest.csv.gz` (W3-06).
- Theo PR #28, chọn ngưỡng vận hành trong lưới 0,05–0,90, bước 0,05, bằng F1 của lớp Drone cao nhất trên val; nếu hòa, chọn ngưỡng conf cao hơn. Báo cáo ngưỡng đã chọn cùng P/R/F1 theo lớp và tổng thể; val đã dùng chọn checkpoint nên kết quả ngưỡng cũng có thể lạc quan, không dùng test để chọn. Bộ phân tích `scripts/kaggle/w3_analyze_baseline.py` tại main triển khai đúng quy tắc này: duyệt ngưỡng tăng dần và cập nhật lựa chọn khi `Drone_F1` bằng hoặc cao hơn kết quả tốt nhất (`>=`), nên trường hợp hòa sẽ giữ ngưỡng conf cao hơn. Macro-F1 được tính riêng làm chỉ số tham khảo, không dùng để chọn ngưỡng.

## 8. Không làm ở W3
Tuning, augmentation riêng, so sánh model, tracker, đánh giá trên test, tuyên bố đạt/không đạt chỉ tiêu.

## 9. Tái lập
Lệnh và notebook: `docs/w3/W3_PLAN.md` mục D. Kết quả: `results/W03/kaggle_run_04/`. Weights: Drive + SHA-256 trong `weights_manifest.json`.
