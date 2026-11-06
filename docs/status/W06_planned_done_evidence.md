# W6 (01/11–07/11/2026) — Planned / Done / Evidence / Problems / Next

Milestone `Tuan6`. Kế hoạch: `docs/w6/W6_PLAN.md`. Evidence: `Evidence/W06/` (86/86 kiểm tra PASS), tạo bằng `scripts/reporting/build_evidence.py`. Mọi số đo trên **val**; test vẫn khóa tới W10.

| Issue | Planned | Done | Evidence | Trạng thái |
|---|---|---|---|---|
| #74 W6-01 (Quang) | Run 14: YOLO11n `s20261030` + ByteTrack-e1 trên 38 video val; lưu detection thô, GT, ghép theo frame | Run 14 đủ 7 stage OK, đúng weights `a3de1e01…`, `test_used = false`; một file dets/GT/track/ghép cho mỗi video | `results/W06/kaggle_run_14/`; PR #80, #83 | DONE |
| #75 W6-02 (An) | Duyệt ADR-0009, ca kiểm thử ROI **trước** khi đánh giá | ADR-0009 Accepted (PR #81 merge 02/11 17:03 UTC); đánh giá chạy sau đó; sửa 2 lỗi (phiếu hòa lớp, `test_used`) | `docs/w6/roi_test_cases_w6.md`; PR #81 | DONE |
| #76 W6-03 (Quang) | Mô-đun geofence + cảnh báo R0/R1, đánh giá sự kiện, video demo | Luật đặt trước: **PASS** (ROI `center_hex`, điểm tâm). Cảnh báo sai trên video không Drone: R0 7 → R1 0; event recall 23/23 cả hai. Run 15: 3 video demo, cảnh báo vẽ trùng `alert_log.csv` (56). Sửa theo review: precision một-một bằng ghép cặp lớn nhất, cận trên Poisson | `scripts/alert/`, `results/W06/alert_eval/`, `results/W06/kaggle_run_15/`; PR #80, #83, #87, #91–#93 | DONE |
| #77 W6-04 (An) | Model card YOLO11n | Xong | `docs/w6/model_card_yolo11n.md`; PR #82 | DONE |
| #78 W6-05 (An) | Phân tích lỗi cảnh báo | 7 cảnh báo sai R0 đều là nhầm lớp Drone trên máy bay/trực thăng có nhãn (đã xem video); `V_DRONE_080` f0 là FP trên trời trống. Phân loại 40 ảnh val âm tính: cả 40 có vật thật nhưng nhãn rỗng | `docs/w6/alert_error_review.md`, `results/W06/val_negative_frames/manual_review_classification.csv`; PR #90, #94 | DONE |
| #88 W6-07 (Quang) | Khảo sát dữ liệu bổ sung, kế hoạch W7–W12 | ADR-0011 Accepted (sửa theo An): tập âm tính `e1-neg-v1` cho W7, hard negative có điều kiện, OOD ở W11; lịch quay W7 đã chốt | `docs/w7/data_expansion_proposal.md`, ADR-0011, `results/W06/dataset_coverage.json`; PR #89, #95 | DONE |
| #79 W6-06 (Quang) | Báo cáo W6, v0.6, Evidence/W06, commit cuối tuần | `E1_W06_bao_cao_cong_viec`, `E1_DoAn_v0.6_W06` (docx và pdf), Evidence/W06; cấu trúc GitHub theo mẫu GVHD (ADR-0010) | `reports/w6/`, `Evidence/W06/`, `scripts/github/check_structure.py`; PR #86, #96 | DONE (bản nộp) |

Ngoài kế hoạch: Kaggle run 16 xuất 40 ảnh val âm tính cho An xem (`w6_negframes.zip`, SHA `67ec70c1…`, không đưa vào Git). Lý do: kiểm lại con số "38/40 ảnh âm tính có FP" (`docs/w6/val_negative_frames.md`).

## Kết quả chính (nguồn: `Evidence/W06/metrics.csv`)
| Chỉ số (val, ROI `center_hex`, điểm tâm) | R0 chỉ detector | R1 theo track |
|---|---|---|
| Sự kiện GT phát hiện được | 23/23 | 23/23 |
| Cảnh báo sai trên video không Drone (3,7 phút) | 7 | 0 |
| Cận trên 95% cảnh báo sai/giờ (Poisson, chỉ báo) | 215,3 | 49,1 |
| Cảnh báo sai trên video Drone | 1 | 0 |
| Cảnh báo lặp | 0 | 2 |
| Event precision một-một | 0,742 | 0,920 |
| Độ trễ trung vị (s) | −0,033 | 0,233 |

Đổi detector sang YOLO11n với cùng ByteTrack-e1: ID switch / 1000 frame GT tăng từ 8,96 lên 18,01 (riêng Drone từ 6,72 lên 24,00).

## Problems
1. Video không có Drone chỉ có 3,7 phút, xa mức ≥ 2 giờ của Thuyết minh mục 13. Kết quả "R1 có 0 cảnh báo sai" chỉ có nghĩa trên mẫu này: cận trên 95% vẫn khoảng 49 cảnh báo/giờ. Toàn bộ Svanström khả kiến không có Drone chỉ 29,9 phút, nên cần dữ liệu ngoài (ADR-0011).
2. Đổi sang YOLO11n làm ID switch tăng gấp đôi, chủ yếu do hai track **cùng lớp** chồng trên một vật (54/58 cặp ID). mAP không phản ánh độ ổn định ID.
3. Ảnh val "âm tính" đều có vật thật nhưng nhãn rỗng:
   - 20 frame 0 có mục nhãn rỗng (liên quan ADR-0006);
   - 20 frame `V_BIRD_041` sau khi nhãn hết.
   - Vì vậy không đo được FP nền trên Svanström. 123 ảnh âm tính của tập train có thể cùng lỗi, chưa kiểm.
   - 36/47 FP lớp Bird nằm ở `V_BIRD_041` (thăm dò), nên Bird P 0,548 có thể chủ yếu do nhãn.
4. Phần lớn PR là review sau merge. Một review của An còn ở mức Comment (#91), vì lỗi đã sửa ở #93.
5. ROI là vùng mô phỏng chung cho mọi video, không phải vùng cấm bay thật. Cảnh báo sớm theo ngoại suy quỹ đạo chỉ là thăm dò.

## Next (W7: hard negatives + phân tích nhầm lẫn)
- Quay và lập manifest `e1-neg-v1` theo lịch ADR-0011 mục 8 (08–12/11). Đo cảnh báo sai/giờ riêng theo nguồn/session bằng mô hình hiện tại.
- Thí nghiệm `e1-yolo-v1-hn` chỉ chạy khi chạm điều kiện kích hoạt (ADR-0011 mục 3); chọn theo mục 4.
- An: phân tích nhầm lẫn theo lớp, cỡ hộp, video. Viết giao thức đặt trước cho ảnh âm tính lỗi nhãn trong train.
- Giao thức đặt trước cho NMS không phân lớp và NMS IoU thấp hơn (track trùng cùng lớp, hộp Drone khác lớp).
- Template: Chương III bản 1 hạn 14/11.
