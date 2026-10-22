# Giao thức huấn luyện W4: detector B và augmentation

## 1. Mục tiêu và điều kiện so sánh

So sánh baseline A với một biến thể augmentation cho vật thể nhỏ và detector B theo Thuyết minh 7.2. Cả ba cấu hình dùng cùng phiên bản dataset, split train/val theo video, seed `20261013`, tối đa 50 epoch, patience 15, optimizer `auto` và cùng phiên bản Ultralytics đã ghi trong `env.json`. Không dùng split test ở W4.

| Cấu hình | Model | imgsz (train/val) | Batch train | Thay đổi so với A | Lý do |
|---|---|---:|---:|---|---|
| A (`configs/baseline_A.yaml`) | YOLOv8n | 640 / 640 | 32 | Cấu hình baseline, augmentation mặc định; mosaic đóng ở 10 epoch cuối | Mốc YOLOv8n @640 theo Thuyết minh 7.2. |
| A + aug (`configs/baseline_A_aug.yaml`) | YOLOv8n | 640 / 640 | 32 | `scale: 0.3` thay mặc định `0.5`; mosaic giữ `1.0`, `close_mosaic: 10` | Giảm mức phóng/thu ngẫu nhiên để tránh thu nhỏ thêm bbox vốn nhỏ. Không đổi `degrees`, `translate`, `fliplr` để tránh thêm biến số khi chưa có lý do/thí nghiệm hỗ trợ; không dùng `copy_paste` vì dữ liệu chỉ có bbox, không có nhãn segmentation. |
| B (`configs/detector_B.yaml`) | YOLOv8s | 960 / 960 | 16 | Model `yolov8n.pt` → `yolov8s.pt`; `imgsz` 640 → 960; train batch 32 → 16 | YOLOv8s @960 là detector B theo Thuyết minh 7.2. Đề xuất batch 16 cho GPU T4 15 GB vì batch 32 ở độ phân giải 960 có nguy cơ OOM; cố định giá trị, không dùng `-1`/auto để phép so sánh tái lập được. |

`mosaic` ở A dùng mặc định Ultralytics là `1.0`; A + aug ghi rõ cùng giá trị để giữ nguyên baseline. Các tham số augmentation không được nêu riêng giữ nguyên mặc định Ultralytics.

## 2. Dataset và quyết định ADR-0006

Dùng cùng một bản xuất cho cả ba run: `e1-yolo-v1` nếu ADR-0006 sau Kaggle run 06 giữ offset0 hoặc chưa xác định; nếu kết quả theo luật đặt trước yêu cầu offset1 thì dùng `e1-yolo-v2` sau khi xuất lại và huấn luyện lại A. Quang cập nhật phiên bản dataset đã chốt và fingerprint từ `dataset_card.json` sau run 06, trước khi chạy các run so sánh. Không so sánh các model có fingerprint hoặc split khác nhau.

## 3. Đánh giá và giới hạn

Chỉ báo cáo kết quả trên validation; test được giữ khóa đến đánh giá cuối. Validation được dùng để chọn checkpoint và ngưỡng, vì vậy các chỉ số validation có thể lạc quan, không phải đánh giá độc lập.

Báo cáo các chỉ số và learning curves theo giao thức W3. Chọn ngưỡng vận hành bằng F1 của lớp Drone trên validation theo mục 7 của [`docs/w3/training_protocol.md`](../w3/training_protocol.md): duyệt conf từ 0,05 đến 0,90, bước 0,05; nếu hòa thì chọn ngưỡng cao hơn. Không dùng test để chọn ngưỡng.

Nếu có GPU và ngân sách phù hợp, huấn luyện thêm YOLOv8n @960 như một đối chứng riêng. So sánh A với YOLOv8n @960 giúp ước lượng ảnh hưởng của độ phân giải; so sánh YOLOv8n @960 với YOLOv8s @960 giúp tách ảnh hưởng kiến trúc/model size.
