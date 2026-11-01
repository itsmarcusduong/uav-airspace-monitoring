# W6 (01/11–07/11/2026) — Geofence và cảnh báo theo quỹ đạo

Mốc:
- Thang chấm E1 W6: "geofence + cảnh báo theo trajectory" (ADR-0005 mục 4).
- Thuyết minh mục 10: trạng thái cảnh báo; mục 12: chỉ tiêu cảnh báo.
- Template: Chương III bản 1 hạn 14/11 (W7).

Tập test của split v1 vẫn khóa tới W10. Mọi số liệu W6 đo trên **val**.

## A. Issue và phân công (milestone Tuan6)
| Issue | Việc | Phụ trách | Review | Evidence |
|---|---|---|---|---|
| #74 W6-01 | Run 14: YOLO11n `s20261030` + ByteTrack-e1 trên 38 video val; lưu detection thô, GT, ghép theo frame | Quang | An | `results/W06/kaggle_run_14/` |
| #75 W6-02 | Duyệt ADR-0009, chốt ROI, viết ca kiểm thử (**trước** khi đánh giá) | An | Quang | ADR-0009 Accepted, `docs/w6/roi_test_cases_w6.md` |
| #76 W6-03 | Mô-đun geofence và cảnh báo, đánh giá R0 so với R1, video demo cảnh báo | Quang | An | `scripts/alert/`, `results/W06/alert_eval/` |
| #77 W6-04 | Model card YOLO11n | An | Quang | `docs/w6/model_card_yolo11n.md` |
| #78 W6-05 | Phân tích lỗi cảnh báo | An | Quang | `docs/w6/alert_error_review.md` |
| #79 W6-06 | Báo cáo W6, v0.6, Evidence/W06, tag `w06` | Quang | An | `reports/w6/`, `Evidence/W06/` |

## B. Thứ tự và điều kiện dừng
1. Song song:
   - Quang chạy run 14 (Kaggle);
   - An duyệt ADR-0009 và viết ca kiểm thử (#75);
   - An làm model card (#77).
2. Chỉ khi #75 đã merge (ADR-0009 Accepted) mới chạy `scripts/alert/evaluate_alerts.py` trên run 14. Kết quả liên kết của run 14 (`track_summary.json`) được phép xem trước; kết quả cảnh báo thì không.
3. Sau đánh giá:
   - Kaggle run 15 (CPU) dựng 3 video demo có vẽ ROI và cảnh báo, chọn theo luật ghi trong job;
   - An phân tích lỗi cảnh báo (#78).
4. **Dừng** nếu:
   - stage FAILED;
   - số frame khác `annotation_audit.csv`;
   - SHA-256 weights khác `a3de1e01…`;
   - `inputs.json` không có `test_used = false`.

## C. Ngân sách GPU (ước lượng, chưa đo)
Run 14 gồm 38 video × khoảng 300 frame, chạy tracking cộng predict (detection thô). Ước lượng 15–25 phút trên T4.

## D. Không làm ở W6
- Hiệu chỉnh ngưỡng cảnh báo trên run 14.
- Đánh giá trên test.
- Báo HOTA/IDF1.
- API, dashboard (W8).
- Tuyên bố đạt chỉ tiêu ≥ 2 giờ video âm tính.
