# Kết quả W03

| Thư mục | Nội dung | Nguồn |
|---|---|---|
| `kaggle_run_03a/review_v2/` | Chỉ mục bảng review nhãn v2 (358 video, 179 bảng; ảnh bảng không đưa vào Git) | `scripts/kaggle/w3_review_sheets.py`, commit `680043b` |
| `kaggle_run_03a/export_evidence/` | Độ nhạy lệch 1 frame, bảng thăm dò offset (+ khóa đáp án; không phải review mù độc lập, xem ADR-0004), quyết định chọn video (chưa xuất dữ liệu) | `scripts/kaggle/w3_export_yolo.py --skip-export` |
| `kaggle_run_03b/export_evidence/` | Dataset card, thống kê, manifest ảnh YOLO (SHA-256 từng ảnh), quyết định chọn video | `w3_export_yolo.py --plus1-policy offset0`, review = `review/review_assignment_w3.csv` |
| `review/` | Review nhãn v2 (`review_quang_v2`), tổng hợp, kết quả thăm dò offset và chấm điểm | `scripts/dataset/score_offset_review.py` |
| `kaggle_run_03b_v2/export_evidence/` | Xuất lại `e1-yolo-v1` dạng 1 file zip (`--pack-zip`) sau sự cố gắn input; fingerprint `d0ac7e23…` **trùng** bản 03b; `yolo_manifest.csv.gz`, `dataset_stats.csv`, `inclusion_decisions.csv` trùng từng byte nên không lưu lại | `w3_export_yolo.py --pack-zip`, commit `9597fce` |
| `kaggle_run_05/analysis/` | Phân tích val: ngưỡng vận hành (F1 Drone), recall theo cỡ hộp và theo video, nhầm lớp, ảnh không nhãn có dự đoán | `w3_analyze_baseline.py`, commit `4532858`; gói `w3_analysis.zip` SHA-256 `0a7eb03f0b92eac9896d1b5963b63a5b22d6b62dc23cda0bb37761453b9c57b1` |
| `kaggle_run_04/train_evidence/` | Train baseline A: env, stage status, metrics val theo lớp, learning curves, PR curve, ma trận nhầm lẫn, `predictions.json.gz`, SHA-256 weights | `w3_train_baseline.py`, commit `9597fce`; tóm tắt: `docs/w3/model_card_baseline_A.md` |

Ảnh/nhãn YOLO (`e1-yolo-v1`, 6.869 ảnh) nằm trong output notebook Kaggle `e1-w3-run03b`, không đưa vào Git; tra cứu bằng `yolo_manifest.csv.gz`.
Diễn giải: `docs/decisions/ADR-0004-w3-baseline-a-data.md` (mục "Kết quả thực hiện").

SHA-256 của gói tải về từ Kaggle (giữ ngoài Git): `w3_train_evidence.zip` (run 04) `3e6038da597a5c35ef88a4036d4e9edfd607576ec553fe63186a81e882f29e21`; `w3_export_evidence.zip` (run 03b bản 2) `8739f92a980602d8dd9dc74f303b40bbaf54854baae1e592783ba8c08874ab5a`. `predictions.json` gốc: `5e5b0c320b6d4d735d4d669eaeae8103c72221f677ca02da5e24e8e49276833d` (lưu dạng gzip). `best.pt`/`last.pt` lưu Google Drive, SHA-256 trong `weights_manifest.json`.
