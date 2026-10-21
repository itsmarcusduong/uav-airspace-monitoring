# Giao thức huấn luyện baseline A (W3-04)

> Khung do Quang chuẩn bị 13/10/2026. **An rà soát các quyết định và lý do; số liệu phụ thuộc run 03b và run 04 được bổ sung khi có bằng chứng.** Quang review trong PR. Không đổi giao thức sau khi đã chạy run chính thức; muốn đổi → phiên bản mới + ADR.

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
| Số ảnh/lớp/split | Chưa có trong repository; chép số liệu từ `dataset_stats.csv` sau run 03b, không suy ra từ số video | `results/W03/kaggle_run_03b/` |

## 3. Mô hình
YOLOv8n COCO-pretrained, ảnh 640, theo lựa chọn baseline dự kiến trong Thuyết minh 7.2 và ADR-0004 mục 10. Biến thể `n` là cấu hình nhỏ của họ YOLOv8, phù hợp làm mốc detector gọn trong ngân sách GPU Kaggle; dùng weights COCO-pretrained để khởi tạo thay vì huấn luyện từ đầu. `imgsz=640` bằng chiều rộng ảnh Visible gốc 640×512; tiền xử lý letterbox về khung 640×640 giữ nguyên tỷ lệ ảnh, tránh kéo giãn nội dung. W3 chỉ chạy một cấu hình baseline, không so sánh biến thể.

Theo `data/manifests/license_matrix.csv` (kiểm tra 14/10/2026, W3-07), mã nguồn Ultralytics YOLOv8/YOLOv11 và weights YOLOv8n pretrained được ghi nhận theo AGPL-3.0. Nguồn chính thức được ghi trong manifest: [license mã nguồn](https://github.com/ultralytics/ultralytics/blob/main/LICENSE), [repository Ultralytics](https://github.com/ultralytics/ultralytics) và [repository weights](https://github.com/ultralytics/assets). Tuân thủ điều khoản AGPL-3.0 khi sử dụng hoặc phân phối; manifest là hồ sơ căn cứ cho quyết định này.

## 4. Siêu tham số (`configs/baseline_A.yaml`)
| Tham số | Giá trị | Lý do |
|---|---|---|
| imgsz | 640 | Theo Thuyết minh 7.2; tương ứng chiều rộng ảnh Visible gốc 640×512, letterbox giữ nguyên tỷ lệ. |
| epochs / patience | 50 / 15 | Giới hạn 50 epoch với dừng sớm sau 15 epoch không cải thiện fitness trên val; giới hạn thời gian GPU nhưng vẫn cho mô hình cơ hội hội tụ. |
| batch | 32 | Cố định theo cấu hình baseline để tái lập; nếu không đủ bộ nhớ GPU, dừng và ghi nhận thay vì âm thầm đổi cấu hình run chính thức. |
| optimizer, lr | auto (mặc định Ultralytics) | Không thêm biến tuning trong W3; dùng mặc định framework và lưu tham số thực tế đã phân giải trong `args.yaml`. |
| augmentation | mặc định Ultralytics (mosaic tắt 10 epoch cuối) | không tuning ở W3 |
| seed / deterministic | 20261013 / true | Cố định seed và bật chế độ tất định để hỗ trợ tái lập; khác biệt phần cứng/thư viện vẫn có thể gây sai khác số nhỏ. |

## 5. Ngân sách và phần cứng
Chạy trên GPU Kaggle; loại GPU phải lấy từ `results/W03/kaggle_run_04/env.json` (W3_PLAN dự kiến T4 hoặc P100). Chưa có bằng chứng run 04 trong repository nên GPU thực tế và thời gian train còn chờ bổ sung sau khi chạy; không ước lượng trước. Mỗi run chính thức ghi seed, config SHA-256, commit, dataset fingerprint và phiên bản torch/ultralytics.

## 6. Chọn checkpoint và giới hạn
`best.pt` = epoch có fitness cao nhất trên val (Ultralytics: 0,1·mAP@0.5 + 0,9·mAP@0.5:0.95). **Không tách thêm một phần train làm val nội bộ ở W3**: dùng split val trong ADR-0004 nhất quán cho dừng sớm, chọn checkpoint và báo cáo; tách thêm sẽ giảm dữ liệu train mà không loại bỏ việc val đã tham gia chọn checkpoint. Vì val vừa dùng để chọn checkpoint vừa để báo cáo, số liệu W3 là **lạc quan** và chỉ là mốc phát triển. Test vẫn khóa, chỉ dùng ở đánh giá cuối.

## 7. Chỉ số báo cáo (Thuyết minh mục 12)
- Precision, recall, mAP@0.5, mAP@0.5:0.95: tổng và theo từng lớp (`baseline_A_val_per_class.csv`).
- Learning curves (`results.csv`, `results.png`), PR curve, confusion matrix.
- Theo cỡ bbox (nhỏ < 32×32 px trên ảnh gốc): recall theo nhóm cỡ, tính từ `predictions.json` + `yolo_manifest.csv.gz` (W3-06).
- P/R/F1 vận hành: chọn một ngưỡng confidence chung trên val để tối đa hóa F1 lớp Drone theo PR curve/predictions; nếu nhiều ngưỡng đồng hạng, chọn ngưỡng cao hơn. Ghi ngưỡng đã chọn và P/R/F1 tại ngưỡng đó; không chọn lại trên test. Đây là bước báo cáo sau huấn luyện, không thay đổi weights hay siêu tham số. Tính mAP và PR curve đầy đủ riêng ở ngưỡng đánh giá `conf=0.001` trong config.

## 8. Không làm ở W3
Tuning siêu tham số/model, augmentation riêng, so sánh model, tracker, đánh giá trên test, tuyên bố đạt/không đạt chỉ tiêu. Chọn ngưỡng confidence để báo cáo P/R/F1 trên val theo mục 7 không làm thay đổi mô hình.

## 9. Tái lập
Lệnh và notebook: `docs/w3/W3_PLAN.md` mục D. Kết quả: `results/W03/kaggle_run_04/`. Weights: Drive + SHA-256 trong `weights_manifest.json`.
