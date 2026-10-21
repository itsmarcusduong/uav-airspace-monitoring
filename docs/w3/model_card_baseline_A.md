# Model card — Baseline A (YOLOv8n @640)

> Trạng thái: **khung** (21/10/2026). Ô `[chờ run 04/05]` được điền từ `results/W03/kaggle_run_04/` và `results/W03/kaggle_run_05/`; không điền số không có file nguồn.

## 1. Thông tin mô hình
| Mục | Giá trị | Nguồn |
|---|---|---|
| Kiến trúc | YOLOv8n (Ultralytics), khởi tạo từ trọng số COCO `yolov8n.pt` | `configs/baseline_A.yaml` |
| Kích thước ảnh vào | 640 | config |
| Lớp | Airplane=0, Bird=1, Drone=2, Helicopter=3 | ADR-0004 |
| Phiên bản thư viện | `[chờ run 04: env.json]` | `kaggle_run_04/env.json` |
| Phần cứng train | `[chờ run 04: GPU]` | `kaggle_run_04/env.json` |
| Số epoch chạy / epoch tốt nhất | `[chờ]` | `results.csv`, `kaggle_run_05/analysis_summary.json` |
| Weights | `best.pt` SHA-256 `[chờ]`; link Drive `[chờ]` | `weights_manifest.json` |
| Giấy phép | Ultralytics và `yolov8n.pt`: AGPL-3.0 (An kiểm 14/10, #20) | `data/manifests/license_matrix.csv` |

## 2. Dữ liệu
`e1-yolo-v1` (fingerprint `d0ac7e23…`): Svanström, chỉ ảnh khả kiến 640×512, stride 10, offset0; train 178 video / 5.667 ảnh, val 38 video / 1.202 ảnh; test (98 video) khóa. Chi tiết và giới hạn: ADR-0004, `results/W03/kaggle_run_03b/export_evidence/`.

## 3. Mục đích sử dụng
Mốc so sánh (baseline) cho W4 trong đồ án; phát hiện 4 lớp vật thể bay trên ảnh camera mặt đất ban ngày. **Không** dùng cho vận hành thật tại sân bay.

## 4. Kết quả trên validation
| Lớp | P | R | AP@0.5 | AP@0.5:0.95 |
|---|---|---|---|---|
| Airplane | `[chờ]` | | | |
| Bird | `[chờ]` | | | |
| Drone | `[chờ]` | | | |
| Helicopter | `[chờ]` | | | |
| Tất cả | `[chờ]` | | | |

Ngưỡng vận hành (F1 macro lớn nhất trên val): `[chờ run 05]`. Recall theo cỡ bbox (nhỏ/vừa/lớn): `[chờ run 05]`. Ảnh âm tính có false positive: `[chờ run 05]`.

## 5. Giới hạn đã biết
- Val vừa dùng để dừng sớm/chọn `best.pt` vừa để báo cáo → số liệu lạc quan; không so với chỉ tiêu mAP@0.5 ≥ 0,80 (tính trên test).
- Val chỉ có 3 video Bird → AP lớp Bird dao động lớn.
- Offset nhãn của video dư 1 mục chưa xác định (dùng offset0); kiểm ở W4 bằng tập chuẩn CVAT.
- Chỉ ảnh khả kiến ban ngày, 3 sân bay Thụy Điển; không đại diện đêm, mưa, sương hoặc sân bay Việt Nam.
- Trùng cảnh giữa các split không kiểm soát được (ADR-0003).
