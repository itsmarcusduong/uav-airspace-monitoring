# W7-01 (#97): kết quả thí nghiệm hậu xử lý V0/V1/V2 (ADR-0012)

- Chạy ngày 17/11/2026, sau khi ADR-0012 Accepted (PR #105, merge `7237dd6`). Luật chọn giữ nguyên như lúc An duyệt.
- Dữ liệu: val, 38 video, detection thô Kaggle run 14 (YOLO11n `s20261030`, conf ≥ 0,1, NMS theo lớp IoU 0,7); ByteTrack-e1 chạy offline, Ultralytics 8.4.183.
- Lệnh:
  ```
  python scripts/experiments/w7_postproc.py --variants none agnostic_nms nms_iou --out results/W07/postproc
  python scripts/experiments/w7_postproc_explore.py --out results/W07/postproc/exploratory.json
  ```
- Nguồn số liệu:
  - `results/W07/postproc/postproc_summary.json` (có `decision`);
  - `results/W07/postproc/V*/summary.json`, `per_video_tracking.csv`;
  - `results/W07/postproc/exploratory.json`, chỉ cho mục 3.

## 1. Kết quả theo luật đặt trước [Kết quả đo]

| Chỉ số (val) | V0 `none` | V1 `agnostic_nms` | V2 `nms_iou` |
|---|---|---|---|
| Detection giữ lại / 19.567 | 19.567 | 12.655 (−35,3%) | 13.215 (−32,5%) |
| ID switch (tổng) | 211 | 13 | 23 |
| ID switch / 1000 frame GT | 18,183 | 1,120 (−93,8%) | 1,982 (−89,1%) |
| Recall Drone mức ảnh, conf 0,25 | 0,8291 | 0,8291 | 0,8291 |
| Precision Drone mức ảnh, conf 0,25 | 0,8373 | 0,8557 | 0,8406 |
| Event recall R1 | 23/23 | 23/23 | 23/23 |
| Cảnh báo sai R1, video không Drone | 0 | 0 | 0 |
| Cảnh báo sai R0, video không Drone | 7 | 8 (+14%) | 7 (0%) |

Kiểm luật ADR-0012 mục 4:
- V1 **đạt**: recall Drone không giảm, R1 không mất sự kiện, cảnh báo sai R1 không tăng, ID switch giảm 93,8% (≥ 20%).
- V2 **đạt** với cùng các điều kiện; ID switch giảm 89,1%.
- Cả hai đạt. Chênh mức giảm ID switch là 4,7 điểm %, dưới ngưỡng 5 điểm, nên chọn biến thể bỏ ít detection hơn.

> **[DECISION] Chọn V2: NMS cùng lớp, IoU 0,5** (`postproc_summary.json` → `decision.choice = nms_iou`).
>
> Theo ADR-0012 mục 5, ở lần chạy Kaggle đầu tiên của W8, V2 phải được đo lại với NMS chạy **trong** detector (`iou=0.5`). Nếu kết quả ngược chiều số offline thì giữ V0.

**Không biến thể nào giảm được cảnh báo sai R0** (mục tiêu ≥ 30%). V1 còn tăng thêm 1, có thể do bỏ hộp làm một đoạn cảnh báo bị tách thành hai. Lý do:
- Theo #108, hộp Drone trên máy bay/trực thăng phần lớn là **nhầm lớp** (Airplane→Drone 8, Helicopter→Drone 1), không phải hộp trùng.
- NMS không bỏ được hộp nhầm lớp khi nó là hộp duy nhất trên vật thể.
- Việc chống cảnh báo sai vẫn do xác nhận theo thời gian của R1 đảm nhận.

## 2. Kiểm "quá đẹp" [Kết quả đo]
Mức giảm ID switch gần 90% nên đã kiểm thêm bốn điểm trước khi tin:

1. **Không phải do mất ghép.**
   - Track recall gộp: 0,8424 (V0) → 0,8378 (V2), giảm 0,46 điểm %; số frame GT không đổi (11.604).
   - Video chỉ có một ID: 12 → 25.
   - Track sai: 19 → 5.
   - Độ phủ của ID chính (median): 0,753 → 0,869.
2. **Theo video**, đơn vị phân tích của đề tài:
   - V2 giảm ID switch ở 17/38 video, không video nào tăng, 21 video giữ nguyên (V1: 19 giảm / 0 tăng);
   - kiểm định dấu một phía, giả thuyết H0 "tăng hay giảm như nhau": p = 0,5¹⁷ ≈ 7,6·10⁻⁶.
3. **Không phụ thuộc một video.**
   - Bỏ V_DRONE_025 (60/211 ID switch của V0): V2 vẫn giảm 84,8% (151 → 23).
   - Bỏ 3 video nhiều ID switch nhất: V2 vẫn giảm 76,8%.
4. **Cơ chế.**
   - V2 bỏ 6.352 hộp; 1.539 hộp trong số đó có conf ≥ 0,25 = `new_track_thresh` của ByteTrack-e1, tức đủ để mở track mới.
   - Hộp trùng cùng lớp có IoU 0,5–0,7 với hộp tốt hơn sinh track song song. Việc ghép GT nhảy qua lại giữa hai track làm tăng ID switch.
   - Kết quả này khớp nhận định W6: 54/58 cặp ID chồng nhau là cùng lớp.

## 3. Phân tích thăm dò, làm sau khi xem kết quả (không đổi quyết định)
`results/W07/postproc/exploratory.json`.

### 3.1. Track recall giảm ở một số video
Luật ADR-0012 không có điều kiện về track recall. Cả V1 và V2 làm thay đổi đúng 5 video:

| Video | Track recall V0 | Thay đổi (V1 = V2) |
|---|---|---|
| V_HELICOPTER_012 | 0,6306 | **−0,1943** |
| V_DRONE_025 | 0,9211 | −0,0922 |
| V_DRONE_023 | 0,9900 | −0,0367 |
| V_AIRPLANE_009 | 0,8369 | −0,0246 |
| V_AIRPLANE_027 | 0,7944 | +0,1900 |

Fragment tăng 296 → 322 (V2: 7 video tăng, 2 giảm).

IoU trung bình của hộp đã ghép giảm ở các video này. Ví dụ V_HELICOPTER_012: 0,637 → 0,618. Giả thuyết: khi hai hộp chồng nhau, NMS giữ hộp conf cao hơn, nhưng đó lại là hộp lệch GT nhiều hơn. Điều này trùng với nhóm "lệch vị trí" của #108 (63/74 hộp `nen→Drone`).

→ **W8:** khi đo lại V2 trên Kaggle, báo track recall theo video. Đề xuất thêm điều kiện "track recall gộp không giảm quá 0,02" cho lần chọn sau. Điều kiện này phải ghi vào giao thức mới **trước** khi chạy, không áp ngược cho W7.

### 3.2. Detection video có hộp trùng nhiều gấp ~20 lần dự đoán ảnh val
So trên **cùng 1.194 frame val** (bước 10), conf ≥ 0,25, đếm hộp trùng cùng lớp có IoU 0,5–0,7:

| Nguồn | Hộp | Hộp trùng | Tỷ lệ |
|---|---|---|---|
| Run 14, `model.predict` trên video | 1.307 | 153 | 11,7% |
| Run 13, `model.val` trên ảnh JPG | 1.183 | 7 | 0,6% |

Hệ quả:
- P/R mức ảnh (từ `model.val`) **không thấy** vấn đề hộp trùng mà tracker gặp. Vì vậy precision Drone mức ảnh gần như không đổi giữa V0 và V2, trong khi ID switch giảm mạnh.
- Nguyên nhân **chưa xác minh**. Các khả năng: khác chế độ suy luận giữa `val` và `predict` (half precision, xử lý NMS), khác đầu vào (frame giải mã từ video so với ảnh JPG đã nén lại).

→ **W8, chạy trên Kaggle:** chạy `model.predict` với cùng tham số trên (a) ảnh JPG val và (b) frame video tương ứng, rồi đếm hộp trùng. Mục đích là tách nguyên nhân do đầu vào hay do chế độ suy luận.

## 4. Giới hạn
- Chỉ có 38 video val, 23 sự kiện và 3,7 phút không Drone. Test vẫn khóa.
- Hậu xử lý chạy **sau** NMS 0,7 đã có trong detection lưu sẵn. NMS 0,5 chạy trong detector có thể giữ một tập hộp khác (ADR-0012, phần Giới hạn), nên phải đo lại ở W8.
- Chênh V1–V2 (4,7 điểm) sát ngưỡng 5 điểm, nên lựa chọn nhạy với ngưỡng. Thăm dò cho thấy V2 cũng bỏ ít TP lớp khác hơn V1 (Airplane 197 so với 193, Helicopter 235 so với 234, Bird 57 so với 56) và không tăng cảnh báo sai R0. Điều này chỉ để tham khảo, không phải lý do chọn.
