# Hướng dẫn cho An — W6 (01/11–07/11/2026)

Người soạn: Quang · 01/11/2026 · Kế hoạch: `docs/w6/W6_PLAN.md` · Quy trình GitHub: `docs/governance/github_workflow.md`

Mỗi việc làm trên **một nhánh mới từ `main`**, đặt tên theo mẫu `issue-<số>-<chủ-đề>`. PR chọn reviewer `itsmarcusduong`, cuối mô tả ghi `Closes #<issue>`.

## Thứ tự ưu tiên
| # | Issue | Việc | Hạn đề xuất |
|---|---|---|---|
| 1 | #75 W6-02 | Duyệt ADR-0009 và cấu hình ROI/cảnh báo, viết ca kiểm thử | 03/11. Quang chỉ chạy đánh giá cảnh báo sau khi PR này merge |
| 2 | #77 W6-04 | Model card YOLO11n `s20261030` | 05/11 |
| 3 | #78 W6-05 | Phân tích lỗi cảnh báo (sau khi Quang có kết quả đánh giá) | 07/11 |
| — | PR #80 | Review công cụ W6 (đã merge để kịp chạy Kaggle) | khi tiện |

## 1. #75 — Duyệt giao thức cảnh báo (làm trước khi có kết quả)
Nhánh `issue-75-roi-alert-protocol`. Đọc:
- `docs/decisions/ADR-0009-roi-alert-protocol.md` (Proposed);
- `configs/roi_w6.yaml` (3 polygon: `full_frame`, `center_hex` là ROI chính, `lower_half`);
- `configs/alert_e1.yaml` (ngưỡng R1: xác nhận 3/5, ở trong vùng 0,3 s, kết thúc 1 s, gộp track trùng IoU 0,3);
- `scripts/alert/alert_engine.py` và `tests/test_alert.py`;
- Thuyết minh mục 10.2 và 12, cùng phần đề xuất W6 trong `docs/w5/tracking_error_review.md` của An.

Nộp:
1. **ADR-0009:**
   - Đồng ý → sửa dòng trạng thái thành `Accepted (Quang 01/11/2026, An <ngày>)`.
   - Không đồng ý điểm nào (ROI, ngưỡng, luật đạt, cách ghép sự kiện) → sửa trực tiếp ADR và file cấu hình, ghi lý do trong PR.
   - Mọi sửa đổi phải xong **trước** khi có kết quả cảnh báo. Không sửa sau khi xem kết quả.
2. **`docs/w6/roi_test_cases_w6.md`:** bảng ca kiểm thử với các cột tình huống, dữ liệu vào (mô tả track/detection), kết quả mong đợi của R0 và R1, test tương ứng. Tối thiểu gồm:
   - UAV bay vào vùng;
   - UAV xuất hiện ngay trong vùng;
   - UAV ra khỏi vùng rồi vào lại;
   - chim ở trong vùng;
   - detection Drone chập chờn 1–2 frame;
   - hai track trùng trên cùng vật;
   - đổi ID sau khi mất dấu ngắn;
   - lớp dao động Drone/Airplane;
   - UAV ở sát biên polygon (tâm ngoài, hộp cắt biên).
   
   Ca nào chưa có test thì thêm vào `tests/test_alert.py` (dữ liệu tổng hợp, theo mẫu các test sẵn có), chạy `python -m pytest -q tests`.

Commit: `docs(w6): review ADR-0009 and ROI test cases (#75)`. PR title: `W6-02: duyệt giao thức cảnh báo và ca kiểm thử ROI (#75)`.

## 2. #77 — Model card YOLO11n
Nhánh `issue-77-model-card-yolo11n`, file `docs/w6/model_card_yolo11n.md`. Theo mẫu `docs/w3/model_card_baseline_A.md` và `docs/w4/model_card_detector_B.md`.

Nguồn:
- `results/W05/kaggle_run_13/train_yolo11n_640_s20261030/` (cấu hình, metrics, theo lớp, `weights_manifest.json` có SHA và link Drive);
- `results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030/` (theo cỡ hộp, theo video, ngưỡng vận hành, nhầm lớp);
- `results/W05/seed_comparison.csv` (3 seed);
- ADR-0007 bản cập nhật.

Nêu rõ:
- số liệu là val (lạc quan);
- vì sao chọn seed trung vị;
- license AGPL-3.0;
- giới hạn (chỉ ảnh khả kiến, ban ngày, dữ liệu Thụy Điển).

## 3. #78 — Phân tích lỗi cảnh báo (sau khi Quang gửi kết quả)
Quang sẽ gửi:
- `results/W06/alert_eval/alert_log.csv`, `per_video_alerts.csv`, `gt_events.csv`;
- 3 video demo có vẽ ROI và cảnh báo.

File `docs/w6/alert_error_review.md`:
- mỗi cảnh báo sai và mỗi sự kiện bị bỏ sót của R1: ghi video, thời điểm, nguyên nhân (nhầm lớp, vật khác không được gán nhãn, track trùng, biên ROI, mất phát hiện);
- bảng tổng hợp theo nguyên nhân, mọi số đếm ghi nguồn;
- đề xuất cho W7 (hard negative, hiệu chỉnh ngưỡng): chỉ là đề xuất, chưa đổi ngưỡng.
