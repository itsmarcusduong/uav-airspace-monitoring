# Hướng dẫn cho An — W5 (25/10–31/10/2026)

Người soạn: Quang · 29/10/2026 · Kế hoạch: `docs/w5/W5_PLAN.md` · Quy trình GitHub: `docs/governance/github_workflow.md`

Mỗi việc làm trên **một nhánh mới từ `main`** (GitHub Desktop: `main` → Fetch → Pull → New Branch). PR chọn reviewer `itsmarcusduong`, cuối mô tả ghi `Closes #<issue>`.

## Thứ tự ưu tiên
| # | Issue | Việc | Hạn đề xuất |
|---|---|---|---|
| 1 | PR #55 | Review và duyệt ADR-0007 (tin nhắn trước) | 30/10 |
| 2 | #58 W5-02 | Duyệt ADR-0008 + cấu hình tracker `*_e1.yaml` + giao thức | 30/10 tối (để Quang chạy run 12b ngày 31/10) |
| 3 | #60 W5-04 | Mục 2.3 (hạn nháp template 31/10) | 31/10 |
| 4 | #40 W4-06 | Phân tích bảng so sánh + model card B | 31/10 |
| 5 | #61 W5-05 | Phân tích lỗi liên kết (cần kết quả run 12) | 31/10; nếu không kịp thì chuyển sang W6 (W6 của An theo phân công là "so sánh tracker và phân tích lỗi") |

---

## 1. #58 — Cấu hình tracker và giao thức đánh giá liên kết
Nhánh `issue-58-tracker-config`. Đọc trước:
- `docs/decisions/ADR-0008-tracking-eval-derived-gt.md` (Quang soạn, đang Proposed): GT dẫn xuất "1 track/video", độ đo, luật so sánh ByteTrack/BoT-SORT;
- `configs/tracker_bytetrack_default.yaml`, `configs/tracker_botsort_default.yaml` (mặc định Ultralytics);
- tài liệu: https://docs.ultralytics.com/modes/track/ và mục 2.1.2 trong `docs/w4/chuong2_nhap_An.md`.

Nộp:
1. **ADR-0008**: đồng ý thì sửa dòng trạng thái thành `Accepted (Quang 29/10/2026, An <ngày>)`. Không đồng ý điểm nào thì sửa trực tiếp và ghi lý do trong PR. Lưu ý mục 7: luật so sánh hai tracker phải chốt **trước** khi xem kết quả run 12b.
2. `configs/tracker_bytetrack_e1.yaml`, `configs/tracker_botsort_e1.yaml`: copy từ bản `default`, chỉ đổi những tham số có lý do. Mỗi dòng đổi có comment lý do. Gợi ý cần xem xét (không bắt buộc đổi):
   - `track_buffer` (mặc định 30 frame = 1 giây ở 30 fps): UAV nhỏ có thể mất phát hiện vài frame liên tiếp.
   - `new_track_thresh` và `track_high_thresh` (0,25) so với ngưỡng vận hành detector 0,25 (model card baseline A).
   - `match_thresh` (0,8 là ngưỡng *chi phí*, tương ứng IoU ≥ 0,2): vật nhỏ di chuyển nhanh có IoU giữa hai frame thấp.
   - BoT-SORT `gmc_method`: camera Svanström đặt trên đế pan-tilt, có video xoay/zoom (ADR-0005), nên bù chuyển động có thể có ích. Giữ `with_reid: False` (chưa có model ReID cho UAV).
3. `docs/w5/tracking_protocol_w5.md`: bảng 4 biến thể (ByteTrack/BoT-SORT × default/e1), tham số khác nhau, lý do, độ đo chính (ADR-0008), luật chọn biến thể dùng cho W6.

Có thể xem `results/W05/kaggle_run_12/` khi Quang đã đưa lên (dự kiến 30/10). **Chỉ được chỉnh một lần**, có lý do. Không thử nhiều bộ tham số rồi chọn bộ đẹp nhất.

Commit: `config(w5): tracker e1 configs, tracking protocol and ADR-0008 review (#58)`. PR title: `W5-02: cấu hình tracker và giao thức đánh giá liên kết (#58)`.

## 2. #60 — Mục 2.3 Công nghệ và lý do lựa chọn
Nhánh `issue-60-section-2-3`, file `docs/w5/muc_2_3_nhap_An.md`. Viết 1–2 trang, cùng cách trích dẫn như 2.1–2.2 (danh mục [1]–[19] trong v0.4). Template yêu cầu trả lời:
- Vì sao chọn stack/model này thay vì 1–2 lựa chọn khác?
- Rủi ro lock-in/licensing?
- Bằng chứng: bảng đánh đổi có tiêu chí.

Gợi ý nội dung:
- **Detector:**
  - Ultralytics YOLO (YOLOv8/YOLO11) [12] so với RT-DETR [6] và một framework khác (MMDetection hoặc Detectron2; nêu nguồn nếu dùng).
  - Dùng số liệu W4 đã đo (`results/W04/comparison_w4.md`, ADR-0007): tốc độ, mAP, độ khó cài đặt. Nói rõ RT-DETR trong W4 train lỗi nên không kết luận được.
- **Tracker:**
  - ByteTrack [2] / BoT-SORT [3] tích hợp sẵn trong Ultralytics [1], so với dùng repo gốc của từng tracker.
  - Vì sao chưa dùng DeepSORT: cần model ReID; thang chấm có nhắc DeepSORT (ADR-0005 mục Hệ quả).
- **Hạ tầng:** PyTorch [9], Kaggle T4 (miễn phí, khoảng 30 giờ GPU/tuần, có lưu output/version) so với Colab hoặc máy cá nhân; GitHub và Drive cho minh chứng.
- **License:**
  - Ultralytics là AGPL-3.0 (theo kết quả #20 của An ở W3): dùng cho học thuật thì được, nhưng nếu phân phối phần mềm thì phải công khai mã nguồn.
  - Dữ liệu Svanström theo CC0-1.0.
  - Rủi ro lock-in: định dạng nhãn YOLO, API `model.track`. Cách giảm rủi ro: lưu track log dạng CSV trung lập, detector thay được.

Commit: `docs(w5): draft thesis section 2.3 (#60)`. PR title: `W5-04: bản nháp mục 2.3 (#60)`.

## 3. #40 (W4) — Phân tích so sánh + model card B
Như tin nhắn trước: `docs/w4/phan_tich_so_sanh_w4.md` + `docs/w4/model_card_detector_B.md`. Nếu đồng ý ADR-0007, sửa trạng thái ADR-0007 trong cùng nhánh này.

## 4. #61 — Phân tích lỗi liên kết (sau khi có run 12)
Quang sẽ gửi:
- `results/W05/kaggle_run_12/w5_track/per_video_metrics.csv`;
- link 3 video demo trên Drive `demo/W05`: video Drone và Bird có nhiều frame nhất, cộng video Drone có nhiều ID switch nhất.

Nhánh `issue-61-tracking-errors`, file `docs/w5/tracking_error_review.md`:
- Mỗi ID switch hoặc đứt track nhìn thấy trong video demo: ghi video, khoảng frame, ID trước/sau, nguyên nhân. Phân loại nguyên nhân: mất phát hiện (vật quá nhỏ/mờ), nhầm lớp, vật khác chen vào (chim, máy bay), camera xoay/zoom, nhãn lệch.
- Bảng tổng hợp theo nguyên nhân. Mọi số đếm phải ghi nguồn (file + cột).
- Đề xuất cho W6 (geofence + cảnh báo theo quỹ đạo): track cần ổn định bao lâu thì mới cảnh báo.
