# W4 (18/10–24/10/2026) — Detector B, tuning + augmentation, so sánh baseline (tag release)

Mốc: Đề cương W4 "Train detector B / tuning" → *Weights B; comparison table*, cùng split cố định. Thang chấm E1 W4: tuning + augmentation, so sánh baseline, **tag release**. ADR-0005 (áp dụng tạm): augmentation vật thể nhỏ chuyển vào W4. Template: mục 2.1, 2.2 hạn nháp 24/10. Thuyết minh 7.2: đối chứng YOLOv8s @960; tách riêng ảnh hưởng độ phân giải nếu đủ tài nguyên.

## A. Issue và phân công (milestone W4)
| Issue | Việc | Phụ trách | Review | Evidence |
|---|---|---|---|---|
| #36 W4-02 | Kiểm chứng chiều lệch nhãn (run 06, CPU) theo luật đặt trước ADR-0006 | Quang | An | `results/W04/kaggle_run_06/`, ADR-0006 |
| #24 W4-01 | Tập chuẩn CVAT ~200 frame + kiểm tra thủ công review v2 | An | Quang | `results/W04/cvat_gold/` |
| #37 W4-03 | Nếu offset1: xuất lại `e1-yolo-v2` + train lại baseline A | Quang | An | `results/W04/kaggle_run_07|08/` |
| #38 W4-04 | Giao thức + config detector B (YOLOv8s@960) + biến thể augmentation | An | Quang | `configs/*.yaml`, `docs/w4/training_protocol_w4.md` |
| #39 W4-05 | Train B + biến thể augmentation (GPU) | Quang | An | `results/W04/kaggle_run_09|10/`, weights Drive |
| #40 W4-06 | Bảng so sánh, model card B, phân tích lỗi | An (phân tích), Quang (số liệu) | Chéo | `results/W04/comparison_w4.csv`, model card |
| #41 W4-07 | Báo cáo W4 + version v0.4 (2.1, 2.2 của An; chương V của Quang) | An, Quang | Chéo | `reports/w4/` |
| #42 W4-08 | Tag release `v0.4-w4` | Quang | An | GitHub release |
| #5 W2-04 | Duyệt ADR-0002/0003, đóng băng split v1 | An | Quang | ADR Accepted |
| #7 W2-06 | GVHD xác nhận ADR-0005 | Cả hai | — | Biên bản |

## B. Thứ tự và điều kiện dừng
1. **Run 06** (CPU, vài phút) → điền ADR-0006 theo luật đặt trước. Không chờ CVAT để quyết định train; CVAT là kiểm chứng thứ hai.
2. Nếu Drone|plus1 = offset1 → run 07 (export v2, CPU) → run 08 (train lại A trên v2, GPU ~30 phút). Ngược lại bỏ qua.
3. An chốt config B + augmentation (#38) **trước** run 09/10. Không đổi config sau khi đã chạy.
4. Run 09 (B: YOLOv8s@960) và run 10 (A + augmentation) trên cùng dữ liệu đã chốt, cùng seed, cùng epochs/patience.
5. Run phân tích (job run 05 dùng lại) cho từng model → bảng so sánh → model card → báo cáo → tag.
- **Dừng** nếu: stage FAILED; fingerprint dữ liệu khác giữa các model được so; GPU quota < thời gian dự kiến (ưu tiên B trước augmentation).

## C. Ngân sách GPU (ước lượng, chưa đo)
A' ≈ 30 phút (giống run 04); B (s@960) ước lượng 2–3 giờ trên T4; A+aug ≈ 30–40 phút. Tổng ≈ 4 giờ trong hạn mức 30 giờ/tuần.

## D. Không làm ở W4
Đánh giá trên test, tracker, ROI/cảnh báo, tuyên bố đạt chỉ tiêu.
