# W5 (25/10–31/10/2026) — Tích hợp tracker, video kiểm thử có ID ổn định

Mốc: thang chấm E1 W5 "tích hợp tracker, video test ID ổn định"; ADR-0005 mục 4 (W5 = tracker; ByteTrack chính, BoT-SORT đối chiếu); template: mục 2.3 hạn nháp 31/10, Chương II hoàn chỉnh bản 1 trước 31/10.
"Video test" ở đây là video kiểm thử lấy từ tập **val**. Tập test của split v1 vẫn khóa tới W10 (ADR-0008).

## A. Issue và phân công (milestone Tuan5)
| Issue | Việc | Phụ trách | Review | Evidence |
|---|---|---|---|---|
| #57 W5-01 | Pipeline video → baseline A → ByteTrack/BoT-SORT, track log, độ đo liên kết, video demo (run 12) | Quang | An | `results/W05/kaggle_run_12/`, demo trên Drive |
| #58 W5-02 | Duyệt ADR-0008; cấu hình tracker `*_e1.yaml` có lý do; giao thức so sánh tracker (trước run 12b) | An | Quang | `configs/tracker_*_e1.yaml`, `docs/w5/tracking_protocol_w5.md` |
| #59 W5-03 | 2 seed mới cho A và YOLO11n (run 13), chọn lại theo luật mục 6 | Quang | An | `results/W05/kaggle_run_13/`, `results/W05/seed_comparison.csv`, ADR-0007 cập nhật |
| #60 W5-04 | Mục 2.3 Công nghệ và lý do lựa chọn | An | Quang | `docs/w5/muc_2_3_nhap_An.md` |
| #61 W5-05 | Phân tích lỗi liên kết trên video demo và `per_video_metrics.csv` | An | Quang | `docs/w5/tracking_error_review.md` |
| #62 W5-06 | Báo cáo W5, v0.5, Evidence/W05, tag `w05` | Quang | An | `reports/w5/`, `Evidence/W05/` |
| #40 (W4) | Phân tích so sánh, model card B; duyệt ADR-0007 | An | Quang | `docs/w4/` |

## B. Thứ tự và điều kiện dừng
1. Run 12 (cấu hình tracker mặc định) và run 13 (seed) độc lập, chạy song song được.
2. An đọc kết quả run 12 → chỉnh `*_e1.yaml` và ghi giao thức (#58) → run 12b. **Không** chỉnh tham số tracker bằng cách nhìn số rồi chạy lại nhiều lần; mỗi lần đổi ghi lý do.
3. Nếu run 13 đổi detector sang YOLO11n (luật mục 6): chạy lại run 12 với weights YOLO11n trong W6, ghi ADR-0007 bản cập nhật.
- **Dừng** nếu: stage FAILED; số frame đọc được khác `annotation_audit.csv`; SHA-256 weights khác `65dd67fb…`.

## C. Ngân sách GPU (ước lượng, chưa đo)
Run 12: 38 video val × khoảng 300 frame × 2 tracker, ước lượng 15–30 phút. Run 13: 4 lần train, ước lượng 2 giờ.

## D. Không làm ở W5
Đánh giá trên test, geofence/cảnh báo (W6), báo HOTA/IDF1 như kết quả chính, tuyên bố đạt chỉ tiêu.
