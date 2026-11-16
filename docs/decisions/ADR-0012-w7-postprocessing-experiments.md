# ADR-0012: Thí nghiệm W7 — hậu xử lý detection chống hộp trùng, đánh giá offline tới tracking và cảnh báo

- Trạng thái: **Accepted** (An 16/11/2026; review follow-up sau khi PR #102 đã merge).
  - Biến thể V1, V2 **chỉ được chạy sau khi ADR này Accepted**. Script `scripts/experiments/w7_postproc.py` tự kiểm trạng thái này và từ chối chạy nếu chưa Accepted.
  - V0 (cổng tái tạo) đã chạy trước khi viết luật, vì V0 không đổi gì.
- Liên quan:
  - #97 W7-01 (Quang), #98 W7-02 (An);
  - ADR-0007 (YOLO11n `s20261030`), ADR-0008 (ByteTrack-e1, GT dẫn xuất), ADR-0009 (luật cảnh báo, không đổi);
  - `results/W06/duplicate_boxes.json`, `docs/w6/alert_error_review.md`, `docs/w6/val_negative_frames.md`.

## Bối cảnh
- [Kết quả đo, W6] Đổi detector sang YOLO11n làm ID switch / 1000 frame GT tăng từ 8,96 lên 18,01.
  - 54/58 cặp ID track chồng nhau là **cùng lớp**.
  - Cảnh báo sai R0 trên video không Drone đến từ hộp Drone **khác lớp** chồng lên máy bay/trực thăng: 104/120 frame trong các cửa sổ cảnh báo sai.
  - Cả hai đều xảy ra sau NMS theo lớp IoU 0,7 của Ultralytics.
- [Kết quả đo, W7] Cổng tái tạo: chạy lại ByteTrack-e1 **offline** trên detection thô đã lưu của run 14, không giải mã video (`results/W07/postproc/repro_check.json`):
  - track log trùng run 14 ở 37/38 video, 13.380/13.402 dòng (99,84%). Video lệch, `V_AIRPLANE_037`, do detection lưu được làm tròn 2 chữ số;
  - đánh giá cảnh báo R0/R1 (ROI `center_hex`, điểm tâm) **giống hệt** run 14;
  - P/R từng lớp ở conf 0,25 trên ảnh val tính lại từ `predictions.json.gz` **giống hệt** `operating_points.csv` của run 13;
  - ID switch / 1000 frame GT: 18,011 (run 14) và 18,183 (offline). Vì vậy **mốc so sánh là V0 offline**, không phải số của run 14.
- [Thang chấm W7] "hard negatives + confusion analysis". Không có tập âm tính ngoài trong W7 (xem ADR-0013), nên hard negative của W7 là lỗi trên chính vật thể khó trong val: hộp Drone trên máy bay/trực thăng/chim, và hộp trùng.

## Quyết định [DECISION]
1. **Biến thể**, mỗi biến thể chỉ đổi **một** yếu tố so với V0. Giá trị chốt trước, không quét tham số:
   - **V0 `none`**: detection run 14 giữ nguyên (conf ≥ 0,1, NMS theo lớp IoU 0,7);
   - **V1 `agnostic_nms`**: NMS **không phân lớp** IoU 0,5 trên detection đã lưu. Hộp chồng IoU ≥ 0,5 với hộp conf cao hơn bị bỏ, bất kể lớp;
   - **V2 `nms_iou`**: NMS **cùng lớp** IoU 0,5 (thay cho 0,7);
   - không thử tổ hợp V1 + V2 ở W7, vì đó là một yếu tố khác.
2. **Pipeline đo** (`scripts/experiments/w7_postproc.py`), giống nhau cho mọi biến thể:
   - hậu xử lý detection → ByteTrack-e1 offline (`scripts/tracking/offline_track.py`) → độ đo liên kết GT dẫn xuất, IoU 0,5;
   - cảnh báo theo ADR-0009, không đổi: ROI `center_hex`, điểm tâm; R0 dùng detection đã hậu xử lý, R1 dùng track mới;
   - mức ảnh: cùng hậu xử lý áp lên `predictions.json.gz` của run 13. P/R/F1 theo lớp ở conf 0,25, ghép tham lam theo conf, IoU ≥ 0,5. **Bỏ 40 ảnh val không nhãn** (cả 40 có vật thật, PR #94).
3. **Chỉ số chính**: ID switch / 1000 frame GT (tất cả lớp), số cảnh báo sai R0 trên video không Drone, event recall R1, cảnh báo sai R1 trên video không Drone, recall lớp Drone ở conf 0,25.
4. **Luật chọn** (đặt trước, so với V0 offline). Một biến thể **đạt** khi thỏa **đủ cả**:
   - recall Drone mức ảnh (conf 0,25) không giảm quá 0,02;
   - event recall R1 không giảm (không mất sự kiện nào);
   - số cảnh báo sai R1 trên video không Drone không tăng;
   - **và ít nhất một cải thiện**: ID switch / 1000 frame GT giảm ≥ 20% tương đối, **hoặc** cảnh báo sai R0 trên video không Drone giảm ≥ 30%.

   Chọn:
   - không biến thể nào đạt → giữ V0;
   - một biến thể đạt → chọn biến thể đó;
   - cả hai đạt → chọn biến thể giảm ID switch nhiều hơn nếu chênh ≥ 5 điểm %; nếu chênh < 5 điểm thì chọn biến thể bỏ ít detection hơn.
5. **Áp dụng**: biến thể được chọn đưa vào pipeline đầu-cuối W8. Ở lần chạy Kaggle đầu tiên của W8, phải đo lại trên video thật (NMS chạy trong detector, không phải sau). Kết quả phải cùng chiều với số offline; nếu ngược chiều thì giữ V0 và ghi lại.
6. **Báo cáo**: báo **mọi** biến thể (kể cả biến thể kém), kèm ma trận nhầm và bảng theo video. Mọi phân tích thêm sau khi xem kết quả ghi rõ là thăm dò.

## Giới hạn
- Hậu xử lý chạy trên detection **đã qua** NMS theo lớp 0,7 và lọc conf ≥ 0,1. V1, V2 chỉ có thể bỏ thêm hộp, không tái tạo được NMS chạy trên dự đoán thô. Mục 5 kiểm lại điều này ở W8.
- Chỉ 38 video val (17 Drone, 23 sự kiện GT, 3,7 phút không Drone); chênh lệch nhỏ không đáng tin. Đơn vị phân tích là video.
- Tập test vẫn khóa; chọn trên val.

## Hệ quả
- Không đổi weights, tracker hay luật cảnh báo. Chỉ có thể đổi bước hậu xử lý detection.
- Huấn luyện lại với hard negative (ADR-0011 mục 3–4) và việc xử lý ảnh âm tính lỗi nhãn trong train **không** làm ở W7 (xem ADR-0013).

## Kết quả (17/11/2026, #97) — luật trên giữ nguyên
- Chạy sau khi ADR Accepted (PR #105). Chi tiết: `docs/w7/postproc_results.md`, `results/W07/postproc/postproc_summary.json`.
- ID switch / 1000 frame GT: V0 18,183 → V1 1,120 (−93,8%), V2 1,982 (−89,1%).
  - Recall Drone mức ảnh không đổi (0,8291).
  - R1 vẫn 23/23 sự kiện và 0 cảnh báo sai.
  - Cảnh báo sai R0 trên video không Drone: V1 8, V2 7, V0 7.
- Cả hai đạt; chênh mức giảm ID switch 4,7 điểm < 5 → **chọn V2 (NMS cùng lớp IoU 0,5)**, biến thể bỏ ít detection hơn.
- Mục 5 áp dụng cho W8: đo lại trên Kaggle với `iou=0.5` trong detector.
- Thăm dò (không đổi quyết định):
  - track recall giảm ở 4 video, mạnh nhất V_HELICOPTER_012 −0,19, và tăng ở 1 video;
  - detection video có hộp trùng cùng lớp nhiều gấp ~20 lần dự đoán ảnh val trên cùng frame (11,7% so với 0,6%);
  - xem `results/W07/postproc/exploratory.json`.
