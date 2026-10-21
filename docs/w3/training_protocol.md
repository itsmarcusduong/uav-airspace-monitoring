# Giao thức huấn luyện baseline A (W3-04)

> Khung do Quang chuẩn bị 13/10/2026. **An điền các ô `[An điền]`, sửa giá trị nếu không đồng ý và ghi lý do.** Quang review trong PR. Không đổi giao thức sau khi đã chạy run chính thức; muốn đổi → phiên bản mới + ADR.

## 1. Mục tiêu
Huấn luyện detector cơ sở (baseline A) theo Đề cương W3 để có Weights A, learning curves và mAP trên validation, làm mốc so sánh cho W4 (detector B / tuning).

## 2. Dữ liệu
| Mục | Giá trị | Nguồn |
|---|---|---|
| Bộ dữ liệu | Svanström Drone-detection-dataset, ảnh khả kiến | ADR-0004 mục 1 |
| Phiên bản dữ liệu xuất | `e1-yolo-v1` (fingerprint ghi trong `dataset_card.json`) | Kaggle run 03 |
| Split | video v1, chỉ train + val; test khóa | ADR-0003, ADR-0004 |
| Lấy mẫu | stride 10 | ADR-0004 mục 4 |
| Xử lý nhãn lệch | theo kết quả run 03 | ADR-0004 mục 5–6 |
| Số ảnh/lớp/split | `[An điền từ dataset_stats.csv]` | run 03 |

## 3. Mô hình
YOLOv8n COCO-pretrained, ảnh 640. Lý do chọn: `[An điền: tại sao n, tại sao 640, liên hệ Thuyết minh 7.2 và kích thước ảnh gốc 640×512]`.
License mã nguồn và weights: `[An điền sau W3-07, kèm URL nguồn chính thức]`.

## 4. Siêu tham số (`configs/baseline_A.yaml`)
| Tham số | Giá trị | Lý do |
|---|---|---|
| imgsz | 640 | `[An điền]` |
| epochs / patience | 50 / 15 | `[An điền]` |
| batch | 32 | `[An điền]` |
| optimizer, lr | auto (mặc định Ultralytics) | `[An điền]` |
| augmentation | mặc định Ultralytics (mosaic tắt 10 epoch cuối) | không tuning ở W3 |
| seed / deterministic | 20261013 / true | tái lập |

## 5. Ngân sách và phần cứng
GPU Kaggle (loại GPU ghi trong `env.json` của run 04). Thời gian train: `[điền sau run 04]`. Mỗi run chính thức ghi: seed, config SHA-256, commit, dataset fingerprint, phiên bản torch/ultralytics.

## 6. Chọn checkpoint và giới hạn
`best.pt` = epoch có fitness cao nhất trên val (Ultralytics: 0,1·mAP@0.5 + 0,9·mAP@0.5:0.95). Vì val vừa dùng để chọn checkpoint vừa để báo cáo, số liệu W3 là **lạc quan**. Test chỉ dùng ở đánh giá cuối. `[An bổ sung: có cần tách một phần train làm val nội bộ không? đề xuất + lý do]`

## 7. Chỉ số báo cáo (Thuyết minh mục 12)
- Precision, recall, mAP@0.5, mAP@0.5:0.95: tổng và theo từng lớp (`baseline_A_val_per_class.csv`).
- Learning curves (`results.csv`, `results.png`), PR curve, confusion matrix.
- Theo cỡ bbox (nhỏ < 32×32 px trên ảnh gốc): recall theo nhóm cỡ, tính từ `predictions.json` + `yolo_manifest.csv.gz` (W3-06).
- `[An điền: ngưỡng conf dùng khi báo P/R/F1 vận hành, chọn trên val như thế nào]`

## 8. Không làm ở W3
Tuning, augmentation riêng, so sánh model, tracker, đánh giá trên test, tuyên bố đạt/không đạt chỉ tiêu.

## 9. Tái lập
Lệnh và notebook: `docs/w3/W3_PLAN.md` mục D. Kết quả: `results/W03/kaggle_run_04/`. Weights: Drive + SHA-256 trong `weights_manifest.json`.
