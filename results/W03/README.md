# Kết quả W03

| Thư mục | Nội dung | Nguồn |
|---|---|---|
| `kaggle_run_03a/review_v2/` | Chỉ mục bảng review nhãn v2 (358 video, 179 bảng; ảnh bảng không đưa vào Git) | `scripts/kaggle/w3_review_sheets.py`, commit `680043b` |
| `kaggle_run_03a/export_evidence/` | Độ nhạy lệch 1 frame, bảng thăm dò offset (+ khóa đáp án; không phải review mù độc lập, xem ADR-0004), quyết định chọn video (chưa xuất dữ liệu) | `scripts/kaggle/w3_export_yolo.py --skip-export` |
| `kaggle_run_03b/export_evidence/` | Dataset card, thống kê, manifest ảnh YOLO (SHA-256 từng ảnh), quyết định chọn video | `w3_export_yolo.py --plus1-policy offset0`, review = `review/review_assignment_w3.csv` |
| `review/` | Review nhãn v2 (`review_quang_v2`), tổng hợp, kết quả thăm dò offset và chấm điểm | `scripts/dataset/score_offset_review.py` |
| `kaggle_run_04/` | (chờ) train baseline A | `w3_train_baseline.py` |

Ảnh/nhãn YOLO (`e1-yolo-v1`, 6.869 ảnh) nằm trong output notebook Kaggle `e1-w3-run03b`, không đưa vào Git; tra cứu bằng `yolo_manifest.csv.gz`.
Diễn giải: `docs/decisions/ADR-0004-w3-baseline-a-data.md` (mục "Kết quả thực hiện").
