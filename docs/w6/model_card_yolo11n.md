# Model card — YOLO11n @640

> Trạng thái: đủ bằng chứng train và phân tích từ Kaggle run 13 (30/10/2026). Các số kết quả dưới đây là trên **validation**; test vẫn khóa. ADR-0007 cập nhật việc chọn model cho W6 đang ở trạng thái **Proposed**.

## 1. Thông tin mô hình

| Mục | Giá trị | Nguồn |
|---|---|---|
| Kiến trúc | YOLO11n (Ultralytics), khởi tạo pretrained từ `yolo11n.pt` | `results/W05/kaggle_run_13/train_yolo11n_640_s20261030/yolo11n_640_s20261030.yaml` |
| Kích thước ảnh vào | 640 × 640 | Cấu hình run, `train/args.yaml` |
| Lớp | Airplane=0, Bird=1, Drone=2, Helicopter=3 | `dataset_card.json`; thứ tự lớp theo ADR-0004 |
| Seed được chọn | `20261030`; mAP@0.5:0.95 = 0,34332, là giá trị trung vị trong ba seed YOLO11n | `results/W05/seed_comparison.csv`, ADR-0007 |
| Phiên bản thư viện | Ultralytics 8.4.183; torch 2.11.0+cu128; Python 3.13.15 | `results/W05/kaggle_run_13/train_yolo11n_640_s20261030/env.json` |
| Phần cứng train | 1 × Tesla T4, 15 GB | `env.json` |
| Commit mã / cấu hình | `26c94626db6f325befad039be8a654a7488656d2`; SHA-256 cấu hình gốc `yolo11n_640.yaml`: `11963e4df253c157…` (cấu hình run ghi seed override) | `env.json`, `yolo11n_640_s20261030.yaml` |
| Dữ liệu | `e1-yolo-v1`, fingerprint SHA-256 `d0ac7e230b385132c4bbec90eb5af2c5740a478fec6c79aeb245acca032c27de`; train 5.667 ảnh, val 1.202 ảnh | `stage_status.json`, `dataset_card.json` |
| Epoch chạy / epoch tốt nhất | 28 / 50; epoch 13 theo mAP@0.5:0.95 (0,3483 trong đường cong train) | `train/results.csv`, `analysis_yolo11n_640_s20261030/stage_status.json` |
| Thời gian train | 1.244,91 giây (≈20,7 phút), thời gian tích lũy ghi ở `train/results.csv` | `train/results.csv` |
| Weights tốt nhất | `best.pt`, SHA-256 `a3de1e0195e4380aac497612296ed57f67e41ceb5ae3314e82a5ad66b125ef8a`, 5.493.658 byte; [tải từ Drive](https://drive.google.com/file/d/12nwiAizDxphbciMc7ogYzV-FWI6CYzp5/view) | `weights_manifest.json`; manifest ghi SHA-256 và kích thước bản tải về khớp (30/10/2026) |
| Weights cuối | `last.pt`, SHA-256 `0cfc4474e56f74d01388f0b112577f263a955ccf43e0d1b7669d1cff28a00b93`, 5.493.658 byte; [tải từ Drive](https://drive.google.com/file/d/140Ok2xbPBEzkW2l_Ts9C5oylydT17D8x/view) | `weights_manifest.json`; manifest ghi SHA-256 và kích thước bản tải về khớp |
| Giấy phép | Ultralytics YOLOv8/YOLO11 được ghi AGPL-3.0 trong ma trận giấy phép. Ma trận hiện không có dòng riêng xác nhận giấy phép của tệp pretrained `yolo11n.pt`. | `data/manifests/license_matrix.csv` |

## 2. Dữ liệu

`e1-yolo-v1` dùng dữ liệu Svanström, ảnh Visible gốc 640×512, lấy mẫu stride 10 và chính sách offset0. Run này dùng 5.667 ảnh train từ 178 video Visible và 1.202 ảnh val từ 38 video Visible; test chưa sử dụng. Nguồn: `results/W05/kaggle_run_13/train_yolo11n_640_s20261030/dataset_card.json`, `stage_status.json`, ADR-0004 và ADR-0006. Dataset card ghi nguồn theo giấy phép CC0-1.0.

## 3. Mục đích sử dụng

Ứng viên detector YOLO11n @640 được chọn cho W6 theo cập nhật Proposed của ADR-0007; seed `20261030` cung cấp checkpoint cụ thể cho lượt tracking. Dùng cho phân tích offline khả năng phát hiện Airplane, Bird, Drone và Helicopter trên ảnh Visible ban ngày. **Không dùng cho vận hành thật tại sân bay hoặc quyết định an toàn**: kết quả validation lạc quan, test chưa đánh giá độc lập và dữ liệu có giới hạn về cảnh và chất lượng nhãn.

## 4. Kết quả trên validation

Các chỉ số dưới đây là của `best.pt` seed `20261030`; precision/recall là giá trị Ultralytics tại ngưỡng dùng trong validation, còn AP được tính từ đường PR. Đây không phải kết quả test hay ngưỡng vận hành.

| Lớp | Precision | Recall | AP@0.5 | AP@0.5:0.95 |
|---|---:|---:|---:|---:|
| Airplane | 0,738 | 0,678 | 0,717 | 0,348 |
| Bird | 0,549 | 0,785 | 0,731 | 0,354 |
| Drone | 0,816 | 0,828 | 0,804 | 0,257 |
| Helicopter | 0,828 | 0,828 | 0,829 | 0,415 |
| Tất cả | 0,733 | 0,780 | 0,770 | 0,343 |

Nguồn: `results/W05/kaggle_run_13/train_yolo11n_640_s20261030/yolo11n_640_s20261030_val_metrics.json` và `yolo11n_640_s20261030_val_per_class.csv`.

**Lý do chọn seed trung vị:** ba seed YOLO11n đều có `train_health = OK`. mAP@0.5:0.95 lần lượt là 0,34702 (20261013), 0,34175 (20261029), 0,34332 (20261030). Chọn seed có kết quả nằm giữa thay vì seed cao nhất giúp tránh lấy cực đại của một thước đo nhiễu trên validation; lựa chọn này nhằm lấy checkpoint cụ thể đại diện hơn cho cấu hình, không khẳng định seed đó có năng lực thật cao hơn. Bảng ba seed cho YOLO11n: mAP@0.5:0.95 trung bình 0,3440 ± 0,0027 (min–max 0,34175–0,34702), tốc độ inference trung bình 3,21 ms/ảnh, F1 Drone trung bình 0,834 ± 0,042. Nguồn: `results/W05/seed_comparison.csv`, ADR-0007 cập nhật run 13.

## 5. Phân tích validation

**Ngưỡng tham khảo** được chọn bằng luật tối đa F1 Drone trên validation, nếu hòa chọn confidence cao hơn: **conf = 0,25**. Tại ngưỡng này, Drone P=0,812, R=0,829, F1=0,820; toàn bộ lớp P=0,775, R=0,789, F1 macro=0,750. Ngưỡng và checkpoint cùng được chọn trên validation, nên kết quả lạc quan; ngưỡng này không phải khuyến nghị vận hành. Nguồn: `results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030/analysis_summary.json`, `operating_points.csv`.

**Recall theo cỡ hộp** tại conf 0,25 (`recall_by_size.csv`):

| Lớp | Nhỏ (<32²) | Vừa (32²–96²) | Lớn (≥96²) |
|---|---:|---:|---:|
| Airplane | 0,914 (74/81) | 0,586 (102/174) | 0,618 (21/34) |
| Bird | 0,789 (56/71) | 0,500 (1/2) | — |
| Drone | 0,852 (224/263) | 0,806 (203/252) | — |
| Helicopter | 0,550 (33/60) | 0,849 (124/146) | 1,000 (79/79) |
| Tất cả | 0,815 (387/475) | 0,749 (430/574) | 0,885 (100/113) |

Trong ngoặc là TP/GT. Drone có AP@0.5:0.95 thấp nhất (0,257); recall theo cỡ hộp giảm từ 0,852 ở nhóm nhỏ xuống 0,806 ở nhóm vừa. Nguồn: `recall_by_size.csv`, `yolo11n_640_s20261030_val_per_class.csv`.

**Độ bao phủ phân tích:** `analysis_summary.json` ghi có dự đoán cho 1.194/1.202 ảnh val (thiếu 8 ảnh so với manifest). Bảng metric Ultralytics ở trên lấy từ tệp metric validation riêng; các phân tích theo ngưỡng/cỡ hộp dựa trên bộ dự đoán của stage analysis và cần được hiểu với sai khác bao phủ này.

**Ảnh không có hộp:** 38/40 ảnh được đánh dấu không có hộp có dự đoán tại conf 0,25. Đây không phải phép đo false positive trên nền trống: các ảnh chưa được xác nhận là cảnh âm tính thật, và frame ngoài phạm vi nhãn là UNKNOWN. Nguồn: `analysis_yolo11n_640_s20261030/negatives_fp.json`, `docs/w2/annotation_audit_w2.md`.

Thời gian inference là 3,137 ms/ảnh trong bước validation, chưa gồm tiền xử lý 1,031 ms và hậu xử lý 0,793 ms; batch 32 trên Tesla T4. Đây không phải FPS đo trên toàn pipeline. Nguồn: `yolo11n_640_s20261030_val_metrics.json`.

## 6. Giới hạn đã biết

- Validation được dùng để dừng sớm/chọn `best.pt` và chọn ngưỡng phân tích; các chỉ số và ngưỡng có thể lạc quan. Test còn khóa tới đánh giá cuối theo ADR-0005.
- Quyết định dùng YOLO11n và seed cụ thể vẫn là Proposed trong bản cập nhật ADR-0007; model card không thay trạng thái phê duyệt đó.
- Chỉ dùng ảnh Visible ban ngày thu tại Thụy Điển; không đại diện ảnh hồng ngoại, ban đêm, thời tiết xấu hoặc môi trường sân bay tại Việt Nam. Nguồn: ADR-0004, `docs/w2/annotation_audit_w2.md`.
- Dữ liệu giữ offset0 theo ADR-0006, nhưng chiều lệch nhãn của video dư một mục vẫn UNDETERMINED; video có nhãn lỗi hoặc chưa gán nhãn có thể ảnh hưởng metric.
- Các ảnh không có hộp không được xác nhận là nền trống; số dự đoán trên chúng không thể diễn giải thành false-positive rate trên cảnh âm tính thật.
- Stage phân tích có dự đoán cho 1.194/1.202 ảnh val; chưa có bằng chứng trong artefact giải thích 8 ảnh thiếu.
- Giá trị mAP@0.5:0.95 của epoch tốt nhất theo đường cong (0,3483) khác với giá trị trong tệp metric validation và seed comparison (0,34332). Bảng kết quả dùng giá trị từ tệp metric validation; chênh lệch này chưa được giải thích trong artefact.
- Một lần chạy cho mỗi seed; ba seed cho thấy biến thiên giữa lần chạy nhưng không tạo khoảng tin cậy tổng quát hóa. Độ lệch chuẩn theo epoch trong từng lần train không phải độ lệch chuẩn giữa seed hay khoảng tin cậy.
- Ảnh gốc Visible 640×512; imgsz 640 không làm tăng chi tiết quang học. AP@0.5:0.95 Drone là 0,257, thấp hơn các lớp còn lại.
