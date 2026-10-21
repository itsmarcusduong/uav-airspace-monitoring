# ADR-0006: Chiều lệch nhãn của video dư một mục (offset0 hay offset1)

- Trạng thái: **Proposed — luật quyết định đặt trước khi chạy** (Quang soạn 22/10/2026, issue #36). Phần "Kết quả" chỉ được điền sau Kaggle run 06; không sửa luật sau khi đã thấy kết quả.
- Liên quan: ADR-0004 (offset0 tạm thời, mục 5–6 và Giới hạn), #24 (tập chuẩn CVAT), #37 (xuất lại nếu đổi).

## Bối cảnh
- [Kết quả đo] Video "dư 1 mục" (số mục nhãn = số frame + 1): 114/114 Drone khả kiến, 40 Bird khả kiến, 77 Bird IR (`annotation_audit.csv`). 111/114 video Drone khả kiến có đúng 1 mục rỗng; với 92/92 video Drone trong `e1-yolo-v1`, mục rỗng nằm ở frame 0 (`yolo_manifest.csv.gz`), trong khi review v2 thấy drone ở frame 0.
- [Kết quả đo] Độ nhạy: lệch 1 frame hầu như không đổi khớp ở IoU 0,5 (V-Drone plus1 98,6% cặp frame liên tiếp có IoU ≥ 0,5) → ảnh hưởng chủ yếu ở mAP@0.5:0.95 (Drone 0,266 trên val, run 04).
- Thăm dò bằng mắt (run 03a) không đạt đối chứng (53%) nên không kết luận được; ở nhóm plus1 26/34 lựa chọn nghiêng về i+1.

## Phương pháp (run 06, `scripts/kaggle/w4_offset_check.py`)
1. Dùng `best.pt` của baseline A và `predictions.json` trên **val** (video không dùng để train).
2. Mỗi ảnh val (frame i, stride 10): lấy dự đoán điểm cao nhất **đúng lớp** của video với score ≥ 0,25; bỏ ảnh không có dự đoán hoặc nhãn i / i+1 không phải hộp hợp lệ.
3. Tính IoU(dự đoán, nhãn i) và IoU(dự đoán, nhãn i+1); bỏ cặp có cả hai IoU < 0,1 (dự đoán không trúng vật) hoặc |chênh lệch| < 0,01 (vật gần như đứng yên).
4. Mỗi video: Δ = trung bình [IoU(i+1) − IoU(i)]. Đơn vị kiểm định là **video** (các frame trong một video không độc lập).

Giả định [INFERENCE]: detector chỉ nhìn một frame nên vị trí dự đoán bám vị trí thật của vật trong frame đó, không học được độ trễ của nhãn. Nhóm đối chứng dùng để kiểm tra giả định này.

## Luật quyết định (đặt trước)
- **Đối chứng** = video khả kiến khớp số nhãn (Airplane, Helicopter; mặc định đúng offset0). Phương pháp được coi là tin cậy khi có ≥ 5 video, ≥ 80% video có Δ < 0 và sign test hai phía theo video p < 0,01.
- Đối chứng **không đạt** → mọi nhóm ghi UNDETERMINED, giữ offset0, chờ tập chuẩn CVAT (#24).
- Đối chứng đạt → với từng nhóm `lớp|plus1`:
  - ≥ 80% video có Δ > 0 và p < 0,01 → **offset1** (nhãn đúng của frame i là mục i + 1).
  - ≥ 80% video có Δ < 0 và p < 0,01 → **offset0** được xác nhận.
  - Còn lại → UNDETERMINED (giữ offset0).
- Nhóm có dưới 6 video không thể đạt p < 0,01 (sign test) → tự động UNDETERMINED; ghi rõ, không suy rộng từ Drone sang Bird.

## Hệ quả theo từng kết luận
- Drone|plus1 = offset1 → #37: xuất lại `e1-yolo-v2` với `--plus1-policy offset1` (áp cho nhóm đạt), train lại baseline A cùng config trước khi so với detector B; ghi ADR mới thay ADR-0004 mục 5.
- offset0 hoặc UNDETERMINED → giữ `e1-yolo-v1`, đóng #37 kèm lý do; detector B train trên v1.
- Tập chuẩn CVAT (#24) là kiểm chứng độc lập thứ hai; nếu mâu thuẫn với run 06 thì ghi nhận và chọn theo CVAT (đo trực tiếp trên ảnh).

## Kết quả
`[chờ Kaggle run 06 — results/W04/kaggle_run_06/]`
