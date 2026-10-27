# ADR-0006: Chiều lệch nhãn của video dư một mục (offset0 hay offset1)

- Trạng thái: **Accepted (27/10/2026) — kết luận theo luật: UNDETERMINED, giữ offset0 / `e1-yolo-v1`**. Luật đặt trước (commit `ffb2ed0`, PR #43, 22/10) không được sửa sau khi xem kết quả. Kiểm chứng tiếp bằng tập chuẩn CVAT (#24).
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

## Kết quả (Kaggle run 06, commit `bb8a695`, 27/10/2026)
Nguồn: `results/W04/kaggle_run_06/w4_offset_check/` (`offset_check_summary.json`, `offset_per_video.csv`, `offset_pairs.csv`; gói zip SHA-256 `9575aa35a64aca71de1dd588fdec0bac172368ee324a954be89691ef46b52d15`). Đầu vào khớp bằng chứng đã có: `predictions.json` `5e5b0c32…` (run 04), manifest `4766ab0d…` (run 03b).

[Kết quả đo] 1.202 ảnh val, 674 cặp dùng được, 37 video có cặp.

| Nhóm | Video | Video nghiêng về mục i+1 | Trung vị Δ | Sign test p | Đạt luật? |
|---|---|---|---|---|---|
| Đối chứng (Airplane, Helicopter khớp số nhãn) | 17 | 4 (13/17 = 76,5% nghiêng về i) | −0,0154 | 0,049 | **Không** (cần ≥ 80% và p < 0,01) |
| Drone dư 1 mục | 17 | 16 (94,1%) | +0,0278 | 0,00027 | — (không xét vì đối chứng không đạt) |
| Bird dư 1 mục | 3 | 3 | +0,0247 | 0,25 | — (dưới 6 video) |

**Kết luận theo luật [DECISION]:** đối chứng không đạt → mọi nhóm UNDETERMINED → giữ offset0, các mô hình W4 train và so sánh trên `e1-yolo-v1`; #37 không xuất lại dữ liệu trong W4.

**Diễn giải [INFERENCE], không dùng để quyết định:**
- Đối chứng nghiêng đúng chiều (13/17 video, trung vị Δ âm) nhưng không đủ mạnh. 4 video "ngược chiều" đều có Δ rất nhỏ (+0,004 đến +0,014) và ít cặp (4–10 cặp): vật gần như đứng yên nên lệch 1 frame khó phân biệt.
- Nhóm Drone dư 1 mục nghiêng rõ về i+1, **ngược chiều** với đối chứng. Baseline A được train bằng nhãn offset0, nên nếu có thiên lệch thì thiên lệch đó đẩy dự đoán về phía mục i. Việc dự đoán vẫn khớp i+1 hơn càng củng cố giả thuyết offset1. Kết quả này cùng chiều với hai quan sát độc lập: mục rỗng nằm ở frame 0 (ADR-0004), và thăm dò bằng mắt 26/34.
- Không đổi luật sau khi đã xem kết quả. Bằng chứng quyết định tiếp theo là tập chuẩn CVAT (#24): đo trực tiếp trên ảnh, đối chứng 80 frame.

## Việc tiếp theo
1. #24: An vẽ tập chuẩn (gói `cvat_package.zip`, run 11), Quang chấm bằng `scripts/dataset/score_cvat_gold.py` sau khi annotation đã được commit.
2. Nếu CVAT kết luận offset1: xuất `e1-yolo-v2` (#37), train lại mốc A và mô hình được chọn trên v2, cập nhật ADR (bản mới) — dự kiến W5.
3. (Tùy chọn, thăm dò) train baseline A trên `e1-yolo-v2` để xem mAP@0.5:0.95 thay đổi thế nào. Kết quả chỉ để tham khảo, vì nhãn val của v1 và v2 khác nhau nên hai mAP không cùng thước đo.
