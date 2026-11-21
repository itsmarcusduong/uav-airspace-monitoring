# W8 — Kết quả xác nhận V2 trên video thật và chẩn đoán hộp trùng (#115)

Áp luật mục B, C của `docs/w8/W8_PLAN.md`. Luật commit ngày 17/11, An sửa mục C ngày 18/11 (#122); run 17 chạy ngày 21/11. Không sửa luật sau khi có kết quả.

Nguồn: `results/W08/v2_verify/v2_verify.json`, tạo bằng `python scripts/experiments/w8_v2_verify.py --out results/W08/v2_verify`. Bằng chứng gốc: `results/W06/kaggle_run_14/`, `results/W08/kaggle_run_17/`. Mọi số đo trên **val**.

## B. V2 trong detector: **áp dụng** (đạt cả 5 điều kiện)
Run 17 (NMS cùng lớp IoU 0,5 trong detector) so với run 14 (IoU 0,7). Cả hai run đánh giá bằng cùng hàm, ngoài Kaggle.

| # | Điều kiện | Run 14 | Run 17 | Đạt |
|---|---|---|---|---|
| 1 | Recall Drone mức ảnh giảm ≤ 0,02 (detection video, 1.162 ảnh, bỏ 40 ảnh lỗi nhãn, conf 0,25) | 0,8718 | 0,8718 | ✓ |
| 2 | Event recall R1 không giảm (`center_hex`, điểm tâm) | 23/23 | 23/23 | ✓ |
| 3 | Cảnh báo sai R1 trên video không Drone không tăng | 0 | 0 | ✓ |
| 4 | ID switch / 1000 frame GT giảm ≥ 20% | 18,011 | 1,982 (−89,0%) | ✓ |
| 5 | Track recall gộp giảm ≤ 0,02 | 0,8425 | 0,8379 (−0,0046) | ✓ |

→ **[DECISION]** Pipeline W8 dùng V2: `iou=0.5` trong detector, bundle demo dựng từ run 17.

Báo thêm (không phải điều kiện):
- Fragment tăng từ 295 lên 321.
- FPS trung vị 88,0 → 84,9. Đây chỉ là số tham khảo, đo ở W9.
- ID switch của run 17 bằng đúng V2 offline (1,982). Cảnh báo sai R0 trên video không Drone vẫn là 7.
- Track recall giảm ở 7 video, tăng ở 1. Chỉ 4 video giảm quá 0,02, giống thăm dò W7: V_HELICOPTER_012 (−0,194), V_DRONE_025 (−0,092), V_DRONE_023 (−0,037), V_AIRPLANE_009 (−0,025).
- Precision Drone mức ảnh từ detection video tăng từ 0,778 lên 0,896: hộp trùng bị tính là FP, nay đã bị loại.

## C. Hộp trùng video so với ảnh val: **trường hợp 3**
| Điều kiện | Hộp (conf ≥ 0,25) | Hộp trùng | D |
|---|---|---|---|
| `jpg_fp32` | 1.308 | 146 | 11,16% |
| `frame_fp32` | 1.307 | 153 | 11,71% |
| `jpg_fp16` | 1.303 | 141 | 10,82% |
| `frame_fp16` | 1.305 | 150 | 11,49% |

- **Cổng tái tạo:** đạt. `frame_fp32` trùng 1.959/1.959 hộp với detection lưu của run 14, và D = 11,71%, nằm trong 11,7% ± 1.
- **Đầu vào:** |D(jpg_fp32) − D(frame_fp32)| = 0,55 điểm, dưới 3 điểm, nên không phải yếu tố. Ảnh JPG lệch frame giải mã trung bình 0,48 mức xám.
- **Độ chính xác số:** |D(frame_fp16) − D(frame_fp32)| = 0,22 điểm, dưới 3 điểm, nên không phải yếu tố.
- **Cả bốn điều kiện ≥ 8%:** đạt. Mức hộp trùng cao vẫn còn qua mọi biến thể đầu vào và độ chính xác, trong khi mốc `model.val` là 0,6%.
- **Kết luận:** khác biệt giữa đường `model.val` và `model.predict` là một điểm có liên quan. Không kết luận đó là nguyên nhân duy nhất.

→ **[DECISION]** Từ W9, số đo mức ảnh dùng để chọn mô hình hoặc báo cáo phải tính từ đầu ra `predict`, tức cùng đường với hệ thống. Không đổi mô hình.

## Kiểm tra phép đo (không phải luật)
- Đánh giá ngoài Kaggle khớp `track_summary.json` của run 17: ID switch 1,982 và track recall 0,8379.
- fp16 có tác dụng thật: detection khác fp32 ở 1.162/1.202 ảnh JPG và 1.155/1.202 frame. Cảnh báo `'half' is deprecated` của Ultralytics 8.4.183 chỉ là đổi tên tham số thành `quantize`.
- Detection run 17 so với NMS 0,5 offline áp lên detection run 14:
  - trùng 94,5% hộp; 10.616/11.388 frame giống hệt;
  - run 17 có 13.902 hộp, offline có 13.215 hộp.
  - [INFERENCE] NMS một bước ở 0,5 có thể giữ một hộp mà hai bước (0,7 rồi 0,5) đã bỏ. Ở hai bước, hộp đó đã bị một hộp trung gian loại ở bước 0,7, rồi chính hộp trung gian lại bị loại ở bước 0,5. Kết quả tracking và cảnh báo vẫn trùng với V2 offline.

## Giới hạn
- Một seed, một bộ weights, 38 video val. Track recall giảm ở V_HELICOPTER_012 là rủi ro cần theo dõi khi đánh giá trên test (W10).
- GT dẫn xuất một track mỗi video (ADR-0008), nên không báo IDF1/HOTA.
- Cảnh báo sai mỗi giờ vẫn chỉ đo trên 3,7 phút video không Drone. Tập âm tính ngoài (`e1-neg-v1`) chưa được đo.
