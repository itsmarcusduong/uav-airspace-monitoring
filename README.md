# E1 UAV Airspace Monitoring

**Repository description:** Reproducible research, data governance and implementation evidence for the E1 graduation project, *Detection, classification and tracking of UAVs in airport airspace using deep learning*.

Đồ án tốt nghiệp nhóm **E1** (PTIT, Khoa CNTT1; GVHD TS. Nguyễn Tất Thắng; Lê Ngọc An, Dương Minh Quang), 27/09–31/12/2026.

Hệ thống nhận video từ camera mặt đất và chạy qua chuỗi: phát hiện, phân loại (Drone, Bird, Airplane, Helicopter), theo dõi, cảnh báo khi UAV vào vùng giám sát, lưu sự kiện, rồi hiển thị trên dashboard.

Repo này chỉ chứa mã, cấu hình, quyết định (ADR), kết quả nhỏ (CSV/JSON) và minh chứng theo tuần. **Không** chứa dữ liệu, weights hay video. Những thứ đó được lưu ngoài Git, kèm manifest và SHA-256.

> README này cập nhật khi chốt tuần, hoặc khi thay đổi cách chạy, cấu trúc thư mục hay kết quả chính. Số liệu chi tiết và nguồn của chúng nằm trong `docs/status/` và `Evidence/WNN/`.

## Trạng thái (cập nhật 24/11/2026, đang ở W9)

| Tuần | Mốc (thang chấm GVHD) | Kết quả chính | Tag / commit cuối tuần |
|---|---|---|---|
| W1–W2 | Lớp, metric, dataset, quy tắc nhãn; chuẩn hóa dataset | Svanström là dữ liệu chính (CC0-1.0); split theo video 454/98/98 (ADR-0003) | — |
| W3–W4 | Baseline; tuning, so sánh | Baseline A (YOLOv8n @640); so sánh 6 cấu hình (ADR-0007); split đóng băng | `w04` |
| W5 | Tích hợp tracker | YOLO11n chọn sau 3 seed (ADR-0007); ByteTrack-e1 (ADR-0008) | `w05` |
| W6 | Geofence, cảnh báo | Luật R1 theo track: cảnh báo sai trên video không Drone 7 → 0, event recall 23/23 trên val (ADR-0009) | `154a596` |
| W7 | Hard negative, phân tích nhầm lẫn | Hậu xử lý V2 (NMS cùng lớp IoU 0,5) chọn theo luật đặt trước, đo offline (ADR-0012) | `9c99539` |
| W8 | Pipeline E2E, dashboard, log | V2 xác nhận trên video thật: ID switch / 1000 frame GT 18,01 → 1,98. Pipeline phát lại (SQLite, FastAPI + WebSocket, dashboard). 13 ca E2E: 9 đạt, 0 trượt, 4 không kiểm được ở phát lại (ADR-0015) | `w08` |
| W9 | Tối ưu suy luận, FPS/độ trễ | Đang làm: `e1pipe` chạy từng frame; benchmark C0/C1/C2; tập âm tính FBD-SV-2024 (ADR-0014, ADR-0016) | — |

Chi tiết từng tuần: `docs/status/WNN_planned_done_evidence.md`. Kế hoạch tuần: `docs/wN/WN_PLAN.md`. Mọi số trên đây đo trên **val**; tập test khóa tới đánh giá cuối.

## Quyết định đang áp dụng
Toàn bộ trong `docs/decisions/`. Những ADR ảnh hưởng trực tiếp tới cách chạy hiện tại:

| ADR | Nội dung |
|---|---|
| ADR-0003 | Chia train/val/test theo video, không chia theo frame |
| ADR-0007 | Detector YOLO11n `yolo11n_640_s20261030`, `best.pt` SHA-256 `a3de1e01…` |
| ADR-0008 | ByteTrack-e1 (`configs/tracker_bytetrack_e1.yaml`); đánh giá tracking bằng GT dẫn xuất, không báo HOTA/IDF1 |
| ADR-0009 | Cảnh báo R1 theo track, ROI `center_hex` (`configs/roi_w6.yaml`, `configs/alert_e1.yaml`) |
| ADR-0012 | NMS cùng lớp IoU 0,5 trong detector (V2), xác nhận ở W8 |
| ADR-0013, ADR-0014 | Tập âm tính từ nguồn công khai; FBD-SV-2024 chỉ dùng đánh giá, không phân phối lại |
| ADR-0015 | Kiến trúc MVP: kho sự kiện SQLite chỉ thêm, API FastAPI + WebSocket, dashboard phát lại |
| ADR-0016 | Job Kaggle có thể chạy qua GitHub Actions (chỉ khi bấm tay); kết quả vào repo qua PR |

## Cấu trúc repo

| Thư mục | Nội dung |
|---|---|
| `scripts/kaggle/` | Job chạy trên Kaggle (xuất dữ liệu, huấn luyện, tracking, benchmark, tập âm tính) và `notebooks/` |
| `scripts/pipeline/` | `e1pipe` (pipeline từng frame), kho sự kiện `e1store`, `build_bundle`, API `api.py`, dashboard `static/` |
| `scripts/alert/`, `scripts/tracking/` | Luật cảnh báo R0/R1, đánh giá sự kiện; tracker chạy offline |
| `scripts/experiments/` | Áp luật đặt trước lên kết quả Kaggle (W7, W8, W9) |
| `scripts/reporting/` | Dựng hình, báo cáo Word/PDF, `Evidence/WNN` |
| `scripts/dataset/`, `scripts/github/` | Manifest dữ liệu; kiểm cấu trúc GitHub theo mẫu GVHD |
| `configs/` | Cấu hình detector/tracker/ROI/cảnh báo (có SHA-256 trong bằng chứng) |
| `data/manifests/` | Manifest, license matrix, bằng chứng license |
| `results/WNN/` | Kết quả nhỏ (CSV/JSON) từ Kaggle và phân tích |
| `Evidence/WNN/` | Minh chứng theo tuần: README, metrics.csv, test-results, figures, manifest.json |
| `reports/wN/` | Hai báo cáo nộp hằng tuần (Word và PDF), bất biến sau khi nộp |
| `docs/` | Kế hoạch tuần, ADR, giao thức, trạng thái, tham chiếu |
| `tests/` | pytest trên dữ liệu tổng hợp và kết quả đã lưu |

## Chạy lại

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q                                   # khoảng 1 phút; test dashboard cần Playwright + Chromium
python scripts/reporting/build_evidence.py --weeks W08
python scripts/github/check_structure.py --weeks 8
```

- **Dữ liệu thật** (giải mã video, huấn luyện, benchmark) chỉ chạy trên Kaggle, theo notebook trong `scripts/kaggle/notebooks/`. Dataset tools dựng bằng `python scripts/kaggle/make_tools_bundle.py --out <thư mục> --zip`; notebook kiểm commit và SHA-256 của tools trước khi chạy.
- **Áp luật lên kết quả**, ví dụ W8: `python scripts/experiments/w8_v2_verify.py --out results/W08/v2_verify`.
- **Dashboard phát lại** (cần bundle, video không có trong repo): xem `scripts/pipeline/README.md`.

## Dữ liệu và giấy phép
- Svanström Drone-detection-dataset: CC0-1.0 theo repository gốc. Dữ liệu chính cho train, val, test.
- FBD-SV-2024: chỉ dùng đánh giá, không thương mại, không phân phối lại (ADR-0014); dataset Kaggle để chế độ private.
- Trạng thái license từng nguồn: `data/manifests/license_matrix.csv`. Kiểm license trước khi tải hay phân phối bất kỳ dữ liệu nào.

## Quy trình
Mỗi tuần có milestone `TuanN`. Mỗi issue là một kết quả của một sinh viên. PR có reviewer là người còn lại. Luật chọn mô hình hay cấu hình được viết và merge **trước** khi chạy. Tag bắt buộc ở W4, W8, W11, W14 (ADR-0010; `CONTRIBUTING.md`).
