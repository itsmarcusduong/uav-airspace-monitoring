# W7 (08/11–14/11/2026, làm bù tới 18/11) — Planned / Done / Evidence / Problems / Next

Milestone `Tuan7`. Kế hoạch: `docs/w7/W7_PLAN.md`. Evidence: `Evidence/W07/`, tạo bằng `scripts/reporting/build_evidence.py`. Mọi số đo trên **val**; test vẫn khóa tới W10.

W7 trễ hạn vì lịch quay video âm tính (ADR-0011 mục 8) không thực hiện được (ADR-0013).

| Issue | Planned | Done | Evidence | Trạng thái |
|---|---|---|---|---|
| #97 W7-01 (Quang) | Thí nghiệm hậu xử lý chống hộp trùng (V1 NMS không phân lớp, V2 NMS cùng lớp 0,5), đo tới tracking và cảnh báo | Cổng tái tạo offline: 37/38 video trùng run 14, cảnh báo và P/R mức ảnh giống hệt. Chạy V1/V2 **sau** khi ADR-0012 Accepted. Cả hai đạt luật → **chọn V2** (chênh 4,7 điểm < 5) | `results/W07/postproc/`, `docs/w7/postproc_results.md`; PR #102, #109 | DONE |
| #98 W7-02 (An) | Duyệt ADR-0012 trước khi chạy V1/V2; phân tích nhầm lẫn, danh mục hard negative | ADR-0012 Accepted (PR #105). Luật phân loại commit trước khi đếm; 74 `nen→Drone` = 11 trùng + 63 lệch vị trí + 0 nền | `docs/w7/confusion_analysis.md`, `results/W07/confusion_analysis.json`; PR #105, #108 | DONE |
| #99 W7-03 (Quang) | Khảo sát nguồn video công khai thay video tự quay | ADR-0013 (Wikimedia Commons, Pixabay, Pexels dự phòng, UAVDB cho OOD); license matrix cập nhật. An loại tạm FBD-SV-2024 (PR #106) | ADR-0013, `data/manifests/license_matrix.csv`; PR #103, #104, #106 | PARTIAL: ADR-0013 còn Proposed, chờ An duyệt |
| #100 W7-04 (An) | Chương III bản 1: 3.3, 3.4 | Bản nháp, đã tích hợp vào v0.7 (Quang chỉ sửa 3 câu "ADR-0012 đang Proposed") | `docs/w7/chuong3_3.3_3.4_nhap_An.md`; PR #107 | DONE |
| #101 W7-05 (Quang) | Báo cáo W7, v0.7 (gồm mục 3.1), Evidence/W07, commit cuối tuần | 3.1 (FR/NFR, tình huống kiểm thử), 5.3.7, 5.4.6; sửa Q1–Q3 ở mục 1.2 theo Thuyết minh 6.2 | `reports/w7/`, `Evidence/W07/` | DONE (bản nộp) |

## Kết quả chính (nguồn: `Evidence/W07/metrics.csv`, `results/W07/postproc/`)
| Chỉ số (val, 38 video) | V0 hiện tại | V1 không phân lớp 0,5 | V2 cùng lớp 0,5 (chọn) |
|---|---|---|---|
| ID switch / 1000 frame GT | 18,183 | 1,120 | 1,982 |
| Track recall gộp | 0,842 | 0,838 | 0,838 |
| Recall Drone (conf 0,25) | 0,829 | 0,829 | 0,829 |
| R1: sự kiện / sai trên video không Drone | 23/23 / 0 | 23/23 / 0 | 23/23 / 0 |
| R0: sai trên video không Drone | 7 | 8 | 7 |

Kiểm "quá đẹp":
- V2 giảm ID switch ở 17/38 video, 0 video tăng.
- Bỏ video đóng góp nhiều nhất vẫn giảm 84,8%.
- Cơ chế: 1.539 hộp trùng có conf ≥ `new_track_thresh` 0,25.

## Problems
1. Kết quả V2 là **offline**, áp NMS 0,5 sau NMS 0,7 trên detection đã lưu. ADR-0012 mục 5 yêu cầu đo lại trên video thật ở lần chạy Kaggle đầu của W8; nếu ngược chiều thì giữ V0.
2. Thăm dò (sau khi xem kết quả):
   - Trên cùng 1.194 frame val, detection video (`model.predict`) có 11,7% hộp trùng cùng lớp, dự đoán ảnh val (`model.val`) chỉ 0,6%. P/R mức ảnh không thấy vấn đề tracker gặp; nguyên nhân chưa xác minh.
   - Track recall giảm ở 4 video, mạnh nhất V_HELICOPTER_012 (−0,19).
3. Không biến thể nào giảm cảnh báo sai R0: hộp Drone trên máy bay là nhầm lớp, không phải hộp trùng.
4. W7 không có tập âm tính ngoài; "hard negative" của W7 là phân tích lỗi trên val. Cảnh báo sai/giờ vẫn chỉ đo trên 3,7 phút.
5. Quy trình:
   - PR #102, #103 merge trước review (An duyệt hậu kiểm ở #105, #106);
   - ADR-0013 chưa được An duyệt;
   - nhánh của An không theo mẫu `issue-<n>-…` (do workspace đặt tên).
6. v0.6 ghi Q1–Q3 khác Thuyết minh 6.2; v0.7 đã sửa theo Thuyết minh, chờ An xác nhận.

## Next (W8: pipeline đầu-cuối + dashboard/log; tag `w08` bắt buộc)
- Kaggle: đo lại V2 trong detector (`iou=0.5`), báo track recall theo video; tách nguyên nhân hộp trùng video so với ảnh val.
- An duyệt ADR-0013. Thu thập và lập manifest clip Wikimedia/Pixabay, sàng lọc hai người, job chuẩn hóa trên Kaggle.
- Pipeline đầu-cuối (đọc video → detector → tracker → cảnh báo → lưu sự kiện), API, dashboard, nhật ký; Chương IV bản 1 (hạn 28/11).
