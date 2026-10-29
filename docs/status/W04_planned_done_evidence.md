# W4 (18/10–24/10/2026) — Planned / Done / Evidence / Problems / Next

Milestone `Tuan4`. Kế hoạch: `docs/w4/W4_PLAN.md`. Evidence: `Evidence/W04/` (tạo bằng `scripts/reporting/build_evidence.py`, 54/54 PASS).

| Issue | Planned | Done | Evidence | Trạng thái |
|---|---|---|---|---|
| #36 W4-02 (Quang) | Kiểm chứng chiều lệch nhãn bằng dự đoán baseline A, luật đặt trước | Run 06: đối chứng 13/17 (p 0,049) không đạt → UNDETERMINED | `results/W04/kaggle_run_06/`, ADR-0006; PR #43, #52 | DONE |
| #24 W4-01 (Quang, An) | Tập chuẩn CVAT mù + kiểm tra 40 video review v2 | 168 ảnh (An vẽ), chấm sau khi commit: UNDETERMINED; review 35/40 đồng ý, κ 0,40 | `results/W04/cvat_gold/`, `results/W04/review_v2_agreement.json`; PR #44, #53, #54 | DONE |
| #37 W4-03 (Quang) | Xuất `e1-yolo-v2` nếu offset1 | Không thực hiện (cả hai kiểm chứng UNDETERMINED) | ADR-0006 | CLOSED (not planned) |
| #38 W4-04 (An) | Config detector B + augmentation, giao thức | `detector_B.yaml`, `baseline_A_aug.yaml`, `training_protocol_w4.md` | PR #45 | DONE |
| #39 W4-05 (Quang, An) | Train B + biến thể, cùng dữ liệu | 5 cấu hình (run 09: phiên 1–2 Quang, phiên 3 An); weights Drive + SHA-256 | `results/W04/kaggle_run_09/`, `results/W04/comparison_w4.csv`; PR #51, #55 | DONE |
| — (ADR-0007) | Áp luật chọn đặt trước | A và YOLO11n hòa → chọn A (nhanh hơn); luật 4 → ưu tiên dữ liệu | `docs/decisions/ADR-0007-w4-model-selection.md` | PROPOSED (chờ An duyệt) |
| #40 W4-06 (An) | Phân tích bảng so sánh + model card B | Chưa | — | IN PROGRESS (hạn 30/10) |
| #41 W4-07 (An) | Mục 2.1, 2.2 | Bản nháp, đã đưa vào v0.4 | `docs/w4/chuong2_nhap_An.md`; PR #47 | DONE |
| #48 W4-09 (Quang) | metrics.csv + Evidence/W04 | 184 chỉ số, 54/54 PASS, 2 hình, 10 weights có link | `Evidence/W04/`; PR #50, #55 | DONE |
| #49 W4-10 (Quang) | Báo cáo W4 + v0.4 | `E1_W04_bao_cao_cong_viec`, `E1_DoAn_v0.4_W04` (docx + pdf) | `reports/w4/` | DONE (bản nộp) |
| #42 W4-08 (Quang) | Tag release | Tag `w04` + release note | GitHub release `w04` | Sau khi merge báo cáo |
| #5 W2-04 (An) | Duyệt ADR-0002/0003, đóng băng split | Accepted; split v1 đóng băng tại tag `w04` | PR #46 | DONE |

## Problems
1. RT-DETR-l huấn luyện lỗi (loss NaN từ epoch 3) → không hợp lệ, không dùng để kết luận.
2. Một seed, số trên val; val nhiễu (SD mAP@0.5:0.95 giữa các epoch 0,02–0,04).
3. Chiều lệch nhãn: hai phương pháp cùng nghiêng về offset1 cho Drone dư 1 mục nhưng đối chứng không đạt → cần ADR mới (W7). Hộp nhãn gốc rộng hơn vật khoảng 3 lần.
4. An chưa review các PR của Quang (#43, #44, #50–#52, #54, #55) trước khi merge; ADR-0007 chờ An duyệt; model card B (#40) chưa xong.
5. ADR-0005 (chỉ tiêu, thứ tự tuần, tracker) chưa được GVHD xác nhận.

## Next (W5)
Tích hợp ByteTrack (BoT-SORT đối chiếu) với baseline A, video test ID ổn định; chạy ≥ 3 seed cho A và YOLO11n; mục 2.3 (hạn 31/10); An duyệt ADR-0007, hoàn thành #40; thống nhất tiêu chí review 5 video lệch.
