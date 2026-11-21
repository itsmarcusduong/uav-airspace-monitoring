# W8 (15/11–21/11/2026) — Pipeline đầu-cuối + dashboard/log; kiểm lại V2; tập âm tính

Mốc:
- Thang chấm cột E1, W8: "pipeline E2E + dashboard/log".
- Đề cương: W8 "FastAPI/dashboard streaming", sản phẩm "End-to-end demo"; **tag `w08` bắt buộc** (mục 10).
- Template: bản nháp 4.1 và 4.2 hạn 21/11; 4.3 và 4.4 hạn 28/11.

Test vẫn khóa tới W10; mọi số đo trên **val**. W8 bắt đầu muộn (17/11) vì W7 làm bù.

## A. Issue và phân công (milestone Tuan8)
| Issue | Việc | Phụ trách | Review | Evidence |
|---|---|---|---|---|
| #113 W8-01 | Tập âm tính `e1-neg-v1`: manifest, license, sàng lọc, job chuẩn hóa (ADR-0013, ADR-0014) | Quang | An | `data/manifests/`, `data/manifests/license_evidence/` |
| #115 W8-02 | Kaggle run 17: V2 trong detector, chẩn đoán hộp trùng; áp luật mục B, C | Quang | An | `results/W08/kaggle_run_17/` |
| #116 W8-03 | Pipeline lõi `e1pipe`, SQLite, FastAPI + WebSocket, dashboard phát lại, nhật ký (ADR-0015) | Quang | An | `src/` hoặc `scripts/pipeline/`, OpenAPI, pytest |
| #117 W8-04 | Duyệt ADR-0014, ADR-0015 và luật mục B–C; bản nháp 4.1–4.2 | An | Quang | PR duyệt; `docs/w8/chuong4_4.1_4.2_nhap_An.md` |
| #118 W8-05 | Kịch bản kiểm thử E2E (Thuyết minh 13.3), viết **trước** khi chạy, rồi chạy trên dashboard | An | Quang | `docs/w8/e2e_test_cases.md` |
| #119 W8-06 | Báo cáo W8, v0.8, Evidence/W08, tag `w08` | Quang | An | `reports/w8/`, `Evidence/W08/` |

## B. Luật xác nhận V2 trên video thật (ADR-0012 mục 5) — viết trước run 17
So sánh **run 17** (NMS cùng lớp IoU 0,5 trong detector) với **run 14** (IoU 0,7). Hai run cùng weights `a3de1e01…`, ByteTrack-e1, 38 video val, Ultralytics 8.4.183; chỉ khác `--iou`. Đánh giá chạy ngoài Kaggle bằng cùng script cho cả hai run.

V2 được **áp dụng** cho pipeline W8 khi thỏa **đủ cả** năm điều kiện:
1. Recall Drone mức ảnh không giảm quá 0,02.
   - Cách tính: từ detection lưu của mỗi run, trên các frame có ảnh val (bước 10); bỏ 40 ảnh lỗi nhãn; conf 0,25; ghép tham lam cùng lớp, IoU ≥ 0,5.
   - Cả hai run tính cùng cách này, không lấy số của `model.val`.
2. Event recall R1 không giảm (ROI `center_hex`, điểm tâm, ADR-0009).
3. Số cảnh báo sai R1 trên video không Drone không tăng.
4. ID switch / 1000 frame GT giảm ≥ 20% so với run 14 (cùng chiều với số offline).
5. **Mới, đặt trước run 17**: track recall gộp không giảm quá 0,02. Lý do: phân tích thăm dò W7 thấy track recall giảm ở 4 video.

Không đủ thì giữ V0 (IoU 0,7) và ghi lại. Báo thêm (không phải điều kiện):
- track recall theo video, fragment;
- FPS trung vị;
- chênh lệch so với V2 offline (1,982);
- cảnh báo sai của R0.

## C. Chẩn đoán hộp trùng — luật diễn giải viết trước
Job `scripts/kaggle/w8_dup_diagnostic.py` đo tỷ lệ hộp trùng D (cùng lớp, IoU 0,5–0,7, conf ≥ 0,25) trên 1.202 ảnh val. Có bốn điều kiện, cùng weights, NMS 0,7:

| Điều kiện | Đầu vào | Độ chính xác số |
|---|---|---|
| `jpg_fp32` | ảnh JPG của e1-yolo-v1 | fp32 |
| `frame_fp32` | frame giải mã từ mp4 | fp32 |
| `jpg_fp16` | ảnh JPG của e1-yolo-v1 | fp16 |
| `frame_fp16` | frame giải mã từ mp4 | fp16 |

Mốc từ W7: D video = 11,7%, D của `model.val` = 0,6%.

0. **Cổng tái tạo**:
   - `frame_fp32` phải trùng detection lưu của run 14 ở ≥ 99% hộp, nếu có input run 14;
   - và D(`frame_fp32`) trong khoảng 11,7% ± 1 điểm (phép đếm đã kiểm bằng test trên dữ liệu run 14).
   - Không đạt thì không diễn giải.
1. |D(`jpg_fp32`) − D(`frame_fp32`)| ≥ 3 điểm % → **đầu vào** (JPG nén lại so với frame giải mã) là một yếu tố.
2. |D(`frame_fp16`) − D(`frame_fp32`)| ≥ 3 điểm % → **độ chính xác số** là một yếu tố.
3. Cả bốn điều kiện đều ≥ 8% → mức hộp trùng cao còn tồn tại qua các biến thể đầu vào và độ chính xác, trong khi mốc `model.val` là 0,6%; ghi nhận khác biệt giữa đường `model.val` và `model.predict` là điểm khác biệt có liên quan, **không kết luận đó là nguyên nhân duy nhất**.
   - Vẫn báo chênh lệch ở điều kiện 1–2 nếu có; kết quả không loại trừ ảnh hưởng đồng thời của đầu vào hoặc fp16.
   - Hệ quả: từ W9, số đo mức ảnh dùng để chọn hay báo cáo phải tính từ đầu ra `predict`, tức cùng đường với hệ thống.
4. Trường hợp khác: ghi là "chưa xác định", không suy diễn thêm.

Kết quả chỉ quyết định **cách đánh giá** ở W9–W10. Không đổi mô hình.

## D. Pipeline đầu-cuối (ADR-0015, chờ An duyệt)
- Pipeline lõi `e1pipe` chạy trên Kaggle, xuất SQLite + JSONL + video.
- Trên máy cá nhân: API FastAPI + WebSocket và dashboard một trang **phát lại** kết quả theo thời gian nguồn, không suy luận cục bộ.
- Dữ liệu demo: 3 video demo của run 17 (hoặc run 14 nếu V2 không được áp dụng).
- Báo cáo ghi rõ demo là đầu-cuối về luồng dữ liệu, không phải đo thời gian thực. FPS và độ trễ đo ở W9.

## E. Thứ tự và hạn
1. 18/11:
   - merge PR kế hoạch và job run 17 (ADR-0015 tách PR riêng, chờ An);
   - Quang chạy run 17 theo `docs/w8/kaggle_guide_w8_LOCAL.md`.
2. 18–19/11: An duyệt ADR-0014 (#114), ADR-0015 và mục B–C. Claude áp luật B, C ngay khi có bằng chứng run 17 và mục B–C đã duyệt.
3. 19–20/11:
   - Quang: pipeline lõi, API, dashboard (#116); thu thập và lập manifest nguồn công khai (#113);
   - An: kịch bản kiểm thử (#118) và bản nháp 4.1–4.2 (#117).
4. 20/11: An chạy kịch bản kiểm thử trên dashboard.
5. 21/11: báo cáo W8, v0.8, Evidence/W08, `check_structure --weeks 8`, **tag `w08`** (#119).

## F. Dừng nếu
- run 17 không qua cổng tái tạo hoặc `stage_status` có FAIL;
- luật mục B hoặc C bị sửa sau khi đã có kết quả run 17;
- ADR-0015 chưa Accepted thì không merge code W8-03.
