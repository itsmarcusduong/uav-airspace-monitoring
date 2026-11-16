# W7 (08/11–14/11/2026, làm bù tới 18/11) — Hard negatives và phân tích nhầm lẫn

Mốc:
- Thang chấm cột E1, W7: "hard negatives + confusion analysis".
- Template: Chương III bản 1, hạn 14/11.

W7 trễ hạn vì lịch quay video âm tính (ADR-0011 mục 8) không thực hiện được (ADR-0013). Tập test vẫn khóa tới W10; mọi số đo trên **val**.

## A. Issue và phân công (milestone Tuan7)
| Issue | Việc | Phụ trách | Review | Evidence |
|---|---|---|---|---|
| #97 W7-01 | Cổng tái tạo tracker offline; thí nghiệm hậu xử lý V1 (NMS không phân lớp) và V2 (NMS cùng lớp 0,5) theo ADR-0012 | Quang | An | `results/W07/postproc/` |
| #98 W7-02 | Duyệt ADR-0012 **trước** khi chạy V1/V2; phân tích nhầm lẫn và danh mục hard negative trong val | An | Quang | `docs/w7/confusion_analysis.md` |
| #99 W7-03 | Khảo sát nguồn video công khai có license, ADR-0013 (thu thập ở W8) | Quang | An | ADR-0013, `license_matrix.csv` |
| #100 W7-04 | Chương III bản 1: mục 3.3–3.4 | An | Quang | bản nháp `.md` → v0.7 |
| #101 W7-05 | Báo cáo W7, v0.7 (gồm mục 3.1), Evidence/W07 | Quang | An | `reports/w7/`, `Evidence/W07/` |

## B. Thứ tự và điều kiện dừng
1. **Đã xong (16/11):** cổng tái tạo V0.
   - Track log offline trùng run 14 ở 37/38 video (99,84% dòng).
   - Cảnh báo R0/R1 và P/R từng lớp ở conf 0,25 giống hệt (`results/W07/postproc/repro_check.json`).
2. An duyệt ADR-0012 (#98). Chỉ sau đó Quang mới chạy `python scripts/experiments/w7_postproc.py --variants none agnostic_nms nms_iou --out results/W07/postproc`. Script tự từ chối nếu ADR chưa Accepted.
3. Song song:
   - An phân tích nhầm lẫn trên V0 (#98);
   - An viết mục 3.3–3.4 (#100);
   - Quang viết mục 3.1 (#101) và tìm nguồn video (#99).
4. Chốt: Evidence/W07, báo cáo, v0.7.
5. **Dừng** nếu:
   - cổng tái tạo không đạt (cảnh báo khác run 14);
   - ADR-0012 bị sửa sau khi đã xem kết quả V1/V2.

## C. Gợi ý cho phân tích nhầm lẫn (#98)
Đầu vào: `results/W07/postproc/V0_none/summary.json` (`detection.confusion`, `per_class`), `per_video_tracking.csv`, run 13 (`recall_by_size.csv`, `recall_by_video.csv`), `duplicate_boxes.json`.
- Khi bỏ 40 ảnh lỗi nhãn, P lớp Bird ở conf 0,25 là 0,864 (so với 0,548 khi giữ cả 40 ảnh). Nên báo cả hai và giải thích.
- "nen → Drone" (74 hộp) là dự đoán Drone không ghép được với hộp nhãn nào ở IoU 0,5. Nên tách thành ba loại theo luật viết trước khi đếm:
  - trùng (chồng một dự đoán khác đã ghép);
  - lệch vị trí (IoU 0,1–0,5 với GT);
  - nền thật (IoU < 0,1 với mọi GT).
- Ma trận nhầm ở đây ghép tham lam theo conf, nên khác cách ghép theo GT của run 13 (vd. Airplane → Drone 8 so với 15). Ghi rõ cách ghép khi trích số.

## D. Không làm ở W7
- Huấn luyện lại; sửa nhãn; hiệu chỉnh ngưỡng cảnh báo.
- Đánh giá trên test.
- Thu thập video (W8).
