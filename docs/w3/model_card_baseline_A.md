# Model card — Baseline A (YOLOv8n @640)

> Trạng thái: **đã có kết quả train (run 04)**, 21/10/2026. Ô `[chờ run 05]` điền từ `results/W03/kaggle_run_05/`; không điền số không có file nguồn. Toàn bộ số ở mục 4 là trên **validation**.

## 1. Thông tin mô hình
| Mục | Giá trị | Nguồn |
|---|---|---|
| Kiến trúc | YOLOv8n (Ultralytics), khởi tạo từ trọng số COCO `yolov8n.pt` | `configs/baseline_A.yaml` |
| Kích thước ảnh vào | 640 | config |
| Lớp | Airplane=0, Bird=1, Drone=2, Helicopter=3 | ADR-0004 |
| Phiên bản thư viện | ultralytics 8.4.183, torch 2.11.0+cu128, Python 3.13.15 | `results/W03/kaggle_run_04/train_evidence/env.json` |
| Phần cứng train | 1 × Tesla T4 15 GB (Kaggle "GPU T4 x2", Ultralytics chỉ dùng GPU 0) | `env.json`, `train/args.yaml` (`device: ''`) |
| Commit mã / config | `9597fce` / `baseline_A.yaml` SHA-256 `822b1a3c…` (bản trên Kaggle là CRLF; nội dung trùng `configs/baseline_A.yaml`) | `env.json`, `stage_status.json` |
| Dữ liệu | `e1-yolo-v1`, fingerprint `d0ac7e23…`, train 5.667 / val 1.202 ảnh | `stage_status.json` (stage data) |
| Số epoch chạy / epoch tốt nhất | 36 / 50 (dừng sớm, patience 15); tốt nhất epoch 21 theo fitness 0,1·mAP@0.5 + 0,9·mAP@0.5:0.95 | `train/results.csv` |
| Thời gian train | 1.622 s (≈ 27 phút) cho 36 epoch | cột `time` của `train/results.csv` |
| Weights | `best.pt` SHA-256 `65dd67fb8968eb3d…826ab` (6.495.530 byte); `last.pt` `b5785db00f3a…de29`; link Drive: `[chờ]` | `weights_manifest.json` |
| Giấy phép | Ultralytics và `yolov8n.pt`: AGPL-3.0 (#20, PR #31) | `data/manifests/license_matrix.csv` |

## 2. Dữ liệu
`e1-yolo-v1` (fingerprint `d0ac7e23…`): Svanström, chỉ ảnh khả kiến 640×512, stride 10, offset0; train 178 video / 5.667 ảnh, val 38 video / 1.202 ảnh; test (98 video) khóa. Run 03b bản 2 (`--pack-zip`) tạo lại đúng fingerprint này (`results/W03/kaggle_run_03b_v2/`). Chi tiết và giới hạn: ADR-0004.

## 3. Mục đích sử dụng
Mốc so sánh (baseline) cho W4; phát hiện 4 lớp vật thể bay trên ảnh camera mặt đất ban ngày. **Không** dùng cho vận hành thật tại sân bay.

## 4. Kết quả trên validation (`best.pt`, conf 0,001, NMS IoU 0,6)
| Lớp | P | R | AP@0.5 | AP@0.5:0.95 |
|---|---|---|---|---|
| Airplane | 0,764 | 0,672 | 0,677 | 0,306 |
| Bird | 0,729 | 0,849 | 0,865 | 0,382 |
| Drone | 0,838 | 0,871 | 0,809 | 0,266 |
| Helicopter | 0,921 | 0,867 | 0,879 | 0,414 |
| Tất cả | 0,813 | 0,815 | 0,807 | 0,342 |

Nguồn: `baseline_A_val_metrics.json`, `baseline_A_val_per_class.csv`. P/R là giá trị Ultralytics báo tại điểm F1 tối đa của từng lớp, chưa phải ngưỡng vận hành.

Nhận xét [INFERENCE từ `train/results.csv`, `val/confusion_matrix_normalized.png`]:
- Loss train giảm đều; `val/box_loss` và `val/dfl_loss` có xu hướng tăng lại từ khoảng epoch 12–20 trong khi mAP val đạt đỉnh ở epoch 21 rồi giảm → mô hình bắt đầu khớp quá mức với train; dừng sớm đã giữ checkpoint epoch 21.
- AP@0.5:0.95 thấp hơn nhiều so với AP@0.5, thấp nhất ở Drone (0,266): định vị hộp chưa chặt với vật thể nhỏ; phù hợp với việc lệch nhãn 1 frame (offset chưa xác định) có thể làm giảm IoU cao.
- Ma trận nhầm lẫn: dự đoán thừa trên nền chủ yếu bị gán Drone hoặc Airplane; Airplane có recall thấp nhất (0,672).
- Thời gian suy luận trong bước val: 3,26 ms/ảnh (chưa gồm tiền/hậu xử lý 1,07 + 0,91 ms), batch 32 trên T4. **Không** phải FPS của pipeline (đo ở W9).

Ngưỡng vận hành (F1 lớp Drone lớn nhất trên val): `[chờ run 05]`. Recall theo cỡ bbox (nhỏ/vừa/lớn): `[chờ run 05]`. Ảnh âm tính có false positive: `[chờ run 05]`.

## 5. Giới hạn đã biết
- Val vừa dùng để dừng sớm/chọn `best.pt` vừa để báo cáo → số liệu lạc quan; **không** so với chỉ tiêu mAP@0.5 ≥ 0,80 (tính trên test, ADR-0005).
- Val chỉ có 3 video Bird (73 ảnh có hộp) → AP lớp Bird (0,865) dao động lớn, không kết luận Bird dễ hơn Drone.
- Offset nhãn của video dư 1 mục chưa xác định (dùng offset0); kiểm ở W4 bằng tập chuẩn CVAT (#24).
- Chỉ ảnh khả kiến ban ngày, thu ở Thụy Điển; không đại diện đêm, mưa, sương hoặc sân bay Việt Nam.
- Trùng cảnh giữa các split không kiểm soát được (ADR-0003).
- Một lần train, một seed: chưa có khoảng dao động giữa các lần chạy.
