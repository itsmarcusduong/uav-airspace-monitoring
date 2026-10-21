# Model card — Baseline A (YOLOv8n @640)

> Trạng thái: **đủ kết quả run 04 (train) và run 05 (phân tích)**, 22/10/2026. Toàn bộ số ở mục 4–5 là trên **validation**; test khóa.

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
| Weights | `best.pt` SHA-256 `65dd67fb8968eb3d…826ab` (6.495.530 byte); `last.pt` `b5785db00f3a…de29`; link Drive: `[chờ tải lại file .pt nguyên bản]` | `weights_manifest.json` |
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

Nguồn: `baseline_A_val_metrics.json`, `baseline_A_val_per_class.csv`. Cách đọc (góp ý của An, PR #34):
- AP@0.5 và AP@0.5:0.95 tính từ toàn bộ đường PR với `conf: 0.001`; giá trị 0,001 chỉ là ngưỡng thấp để vẽ đủ đường PR/mAP, **không** phải ngưỡng vận hành.
- P/R trong bảng là giá trị Ultralytics 8.4.183 lấy tại **một ngưỡng confidence chung cho mọi lớp**, chọn để tối đa F1 trung bình các lớp đã làm trơn (`ap_per_class`: `smooth(f1_curve.mean(0), 0.1).argmax()`); **không** phải mỗi lớp một ngưỡng F1 riêng, và cũng không phải ngưỡng vận hành của đồ án.
- Ngưỡng vận hành của đồ án chọn theo giao thức (`training_protocol.md` mục 7): xem mục 5.

Nhận xét [INFERENCE từ `train/results.csv`, `val/confusion_matrix_normalized.png`]:
- Loss train giảm đều; `val/box_loss` và `val/dfl_loss` có xu hướng tăng lại từ khoảng epoch 12–20 trong khi mAP val đạt đỉnh ở epoch 21 rồi giảm → mô hình bắt đầu khớp quá mức với train; dừng sớm đã giữ checkpoint epoch 21.
- AP@0.5:0.95 thấp hơn nhiều so với AP@0.5, thấp nhất ở Drone (0,266): định vị hộp chưa chặt với vật thể nhỏ; phù hợp với việc lệch nhãn 1 frame (offset chưa xác định) có thể làm giảm IoU cao.
- Ma trận nhầm lẫn: dự đoán thừa trên nền chủ yếu bị gán Drone hoặc Airplane; Airplane có recall thấp nhất (0,672).
- Thời gian suy luận trong bước val: 3,26 ms/ảnh (chưa gồm tiền/hậu xử lý 1,07 + 0,91 ms), batch 32 trên T4. **Không** phải FPS của pipeline (đo ở W9).

## 5. Phân tích trên validation (run 05)
Nguồn: `results/W03/kaggle_run_05/analysis/` (commit `4532858`, khớp dự đoán – nhãn: cùng lớp, IoU ≥ 0,5, tham lam theo score; lưới conf 0,05–0,90 bước 0,05).

**Ngưỡng vận hành** (F1 lớp Drone lớn nhất; đồng hạng → ngưỡng cao hơn): **conf = 0,25** → Drone P = 0,832, R = 0,882, F1 = 0,856; toàn bộ 4 lớp P = 0,814, R = 0,837, F1 macro = 0,808. Ngưỡng tối đa F1 macro (tham khảo) là 0,35 (F1 macro 0,814). Lạc quan vì chọn trên val (`operating_points.csv`).

**Recall theo cỡ hộp** tại conf 0,25 (`recall_by_size.csv`):

| Lớp | Nhỏ (< 32²) | Vừa (32²–96²) | Lớn (≥ 96²) |
|---|---|---|---|
| Airplane | 0,951 (81) | 0,563 (174) | 0,794 (34) |
| Bird | 0,916 (71) | 0,500 (2) | — |
| Drone | 0,867 (263) | 0,897 (252) | — |
| Helicopter | 0,667 (60) | 0,932 (146) | 0,949 (79) |
| Tất cả | 0,863 (475) | 0,803 (574) | 0,903 (113) |

(số trong ngoặc = số hộp GT). Recall thấp ở Airplane-vừa tập trung theo video: `V_AIRPLANE_027` 0/33, `V_AIRPLANE_007` 8/30, `V_AIRPLANE_005` 16/33 (`recall_by_video.csv`) → lỗi theo cảnh, không phải theo cỡ [INFERENCE].

**Nhầm lớp** (class-agnostic, conf 0,25, `class_confusion.csv`): ít nhầm giữa các lớp (Bird → Airplane 5, Helicopter → Airplane 6, Airplane → Helicopter 3); lỗi chủ yếu là **bỏ sót** (Airplane 83/289, Drone 58/511, Helicopter 30/285).

**"Ảnh âm tính"**: 40/40 ảnh val không có hộp đều có dự đoán (`negatives_fp.json`). Con số này **không** đo được false positive thật, vì các ảnh đó không phải ảnh trời trống:
- 20/40 là frame 0 của video dư 1 mục nhãn (17 Drone, 3 Bird); review v2 ghi "f0 khong co nhan du thay drone" ở các video Drone.
- 20/40 là đoạn thiếu nhãn f110–f300 của `V_BIRD_041` (review v2: KHONG_RO, có chấm nhỏ có thể là chim).
- Audit W2: 111/114 video Drone khả kiến và 27/40 video Bird khả kiến dư 1 mục có **đúng 1 mục rỗng**, và manifest cho thấy mục rỗng đó rơi vào frame 0 (cả 92/92 video Drone trong `e1-yolo-v1` có frame 0 không nhãn).
→ Val **không có ảnh âm tính thật**; FP trên nền trời phải đo bằng video không vật thể ở W7 (hard negatives).

## 6. Giới hạn đã biết
- Val vừa dùng để dừng sớm/chọn `best.pt` vừa để báo cáo → số liệu lạc quan; **không** so với chỉ tiêu mAP@0.5 ≥ 0,80 (tính trên test, ADR-0005).
- Val chỉ có 3 video Bird (73 ảnh có hộp) → AP lớp Bird (0,865) dao động lớn, không kết luận Bird dễ hơn Drone.
- Offset nhãn của video dư 1 mục chưa xác định (dùng offset0). [INFERENCE] Mục nhãn rỗng nằm ở đầu (frame 0) trong khi vật thể đã thấy ở frame 0 nghiêng về giả thuyết **mục 0 là mục thừa, nhãn đúng là i+1 (offset1)**, cùng chiều với thăm dò bằng mắt (26/34). Chưa phải kết luận: kiểm chứng ở W4 bằng tập chuẩn CVAT (#24) và bằng so IoU dự đoán của baseline A với nhãn i và i+1.
- Chỉ ảnh khả kiến ban ngày, thu ở Thụy Điển; không đại diện đêm, mưa, sương hoặc sân bay Việt Nam.
- Trùng cảnh giữa các split không kiểm soát được (ADR-0003).
- Một lần train, một seed: chưa có khoảng dao động giữa các lần chạy.
