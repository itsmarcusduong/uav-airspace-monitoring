# Hướng dẫn việc của An — W7 (làm bù, mục tiêu xong 18/11/2026)

Repo: [REPO] `D:\code_source\e1-uav-airspace-monitoring` hoặc bản clone của An. Trước khi làm: Fetch + Pull `main` (commit trên cùng: `Merge pull request #103`).

## 1. Duyệt ADR-0012 — PR #102 (việc đầu tiên, chặn thí nghiệm của Quang)
- File: `docs/decisions/ADR-0012-w7-postprocessing-experiments.md`. Bằng chứng cổng tái tạo: `results/W07/postproc/repro_check.json`.
- Cần xem:
  - hai biến thể (NMS không phân lớp IoU 0,5; NMS cùng lớp IoU 0,5) có đúng một yếu tố không;
  - luật chọn mục 4 có hợp lý không (ngưỡng recall Drone −0,02, event recall không giảm, giảm ID switch ≥ 20% hoặc cảnh báo sai R0 ≥ 30%);
  - việc bỏ 40 ảnh lỗi nhãn khỏi số đo mức ảnh.
- Trả lời bằng **Review changes → Approve** (đồng ý) hoặc **Request changes** (ghi rõ sửa gì). Quang chỉ chạy V1/V2 sau khi An approve.
- PR #103 (ADR-0013, nguồn video công khai): review trong tuần, không chặn.

## 2. Issue #98 — Phân tích nhầm lẫn trên val
- Nhánh: `issue-98-confusion-analysis`. File: `docs/w7/confusion_analysis.md`.
- **Commit 1 (trước khi đếm):** ghi luật tách dự đoán sai thành ba loại:
  - trùng: chồng IoU ≥ 0,5 với một dự đoán khác đã ghép đúng;
  - lệch vị trí: IoU với GT trong khoảng 0,1–0,5;
  - nền thật: IoU < 0,1 với mọi GT.
- **Commit 2:** số liệu và nhận xét. Đầu vào:
  - `results/W07/postproc/V0_none/summary.json`: `detection.per_class`, `detection.confusion` (conf 0,25, bỏ 40 ảnh lỗi nhãn);
  - `results/W07/postproc/V0_none/per_video_tracking.csv`;
  - run 13: `results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030/` (`recall_by_size.csv`, `recall_by_video.csv`, `operating_points.csv`);
  - `results/W06/duplicate_boxes.json`, `docs/w6/alert_error_review.md`.
- Nội dung tối thiểu:
  - ma trận nhầm 4 lớp + nền + bỏ sót, có ghi cách ghép (tham lam theo conf, IoU ≥ 0,5);
  - P/R lớp Bird khi giữ và khi bỏ 40 ảnh lỗi nhãn (0,548 → 0,864);
  - nhầm theo cỡ hộp và theo video (video nào chiếm phần lớn lỗi);
  - **danh mục hard negative trong val**: máy bay/trực thăng/chim bị đoán là Drone, hộp trùng, nền;
  - mỗi loại ghi số lượng, video ví dụ và đề xuất xử lý (dữ liệu hay hậu xử lý).
- Nếu cần thêm số liệu không có trong file, viết script trong `scripts/reporting/` và ghi lệnh chạy; không nhập tay số.
- PR: title `W7-02: phân tích nhầm lẫn trên val (#98)`; mô tả gồm Tóm tắt / Thay đổi / Bằng chứng / Giới hạn; `Closes #98`; reviewer Quang; milestone Tuan7.

## 3. Issue #100 — Chương III bản 1: mục 3.3 và 3.4
- File: `docs/w7/chuong3_3.3_3.4_nhap_An.md`. Viết như văn báo cáo, không gạch đầu dòng dài. Quang sẽ đưa vào v0.7.
- **3.3 Phương pháp đề xuất:**
  - pipeline video → detector (YOLO11n, chọn theo ADR-0007) → ByteTrack-e1 → mô-đun cảnh báo R1 (ADR-0009);
  - vì sao xác nhận nhiều frame giảm cảnh báo giả;
  - hậu xử lý chống hộp trùng (ADR-0012).
  - Trả lời đúng câu hỏi trong bảng hạn nháp của template (pipeline từng bước, baseline so với phương pháp đề xuất, hyperparameter/ngưỡng chọn thế nào). Có thể vẽ lưu đồ (Mermaid) như mục 2.1.
- **3.4 Thiết kế thí nghiệm và tiêu chí đánh giá:**
  - câu hỏi nghiên cứu Q1–Q3 (mục 1.2);
  - split theo video, test khóa tới W10;
  - nguyên tắc một yếu tố mỗi lần, nhiều seed, ngưỡng hòa 0,01, luật đặt trước;
  - các độ đo: mAP, P/R/F1, ID switch trên GT dẫn xuất, event recall, cảnh báo sai/giờ, FPS;
  - giới hạn thống kê.
  - Dẫn nguồn đúng số tài liệu tham khảo hiện có ([1]–[21]).
- PR: title `W7-04: Chương III bản 1, mục 3.3–3.4 (#100)`; `Closes #100`; reviewer Quang.
