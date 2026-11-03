# 40 ảnh val "âm tính" của `e1-yolo-v1`: FP ở đâu (trả lời An trên PR #89)

- Người soạn: Dương Minh Quang, 03/11/2026. Người xem tận mắt và kết luận: Lê Ngọc An (phân tích nhầm lẫn W7).
- Đây là **phân tích thăm dò** làm sau khi xem kết quả. Không đổi nhãn, ngưỡng hay luật nào.
- Số liệu: `results/W06/val_negative_frames/val_negative_frames.csv` và `val_negative_summary.json`, tạo bằng `scripts/reporting/val_negative_frames.py`.
  - Nguồn dự đoán: run 13, `val/predictions.json.gz` của `yolo11n_640_s20261030`. Đây là đúng các dự đoán trên ảnh JPEG mà `negatives_fp.json` đã đếm.
  - Nguồn nhãn: GT theo frame của run 14 (offset0, như `e1-yolo-v1`).
- Ảnh gốc và ảnh vẽ hộp: Kaggle run 16 (`scripts/kaggle/w6_negative_frames_export.py`) xuất `w6_negframes.zip`. Ảnh không đưa vào Git.

## Kết luận
**[INFERENCE, chờ An xem ảnh] 38/40 ảnh "âm tính" có FP gần như toàn bộ là ảnh có vật thật nhưng nhãn rỗng, không phải FP trên nền trời.**
- Chỉ tìm được **1 FP thật** trong 38 ảnh: `V_DRONE_080` frame 0, hộp Drone 0,587 trên vùng trời trống. Đây chính là cảnh báo sai R0 An đã xác nhận ở #90.
- Vì vậy con số "38/40" không dùng được để đánh giá FP nền. Svanström cũng không có ảnh nền trống đáng tin, nên tập âm tính ngoài (ADR-0011) càng cần.

## Kiểm chéo
- Dựng lại danh sách 40 ảnh từ GT run 14 (frame stride 10 không có hộp GT) cho **đúng 40 ảnh**.
- Đếm ảnh có dự đoán conf ≥ 0,25 cho **38 ảnh**, khớp `negatives_fp.json` của run 13.
- Detection run 14 (giải mã video) và dự đoán run 13 (ảnh JPEG) cùng có hoặc cùng không có dự đoán trên **40/40 ảnh**.

## Hai nhóm ảnh
| Nhóm | Ảnh | Có dự đoán | Bằng chứng |
|---|---|---|---|
| A. Frame 0, trước frame có nhãn đầu tiên (`before_first_label`) | 20: frame 0 của 17 video Drone và 3 video Bird | 18 | Ở cả 18 ảnh, một dự đoán chồng IoU ≥ 0,3 với hộp GT của frame 1 (trung vị khoảng 0,73). Lớp dự đoán trùng lớp video, trừ `V_BIRD_041` (dự đoán Airplane trên con chim). Hai ảnh không có dự đoán (`V_DRONE_010`, `V_DRONE_096`) là đối chứng. |
| B. `V_BIRD_041` frame 110–300, sau frame có nhãn cuối (107) (`after_last_label`) | 20 | 20 (42 hộp: 36 Bird, 6 Airplane) | Video dài 305 frame nhưng nhãn chỉ tới frame 107 (`label_len_mismatch` trong split v1). ByteTrack-e1 giữ **một track liên tục từ frame 0 tới 304** qua điểm hết nhãn; ở frame 107 hộp dự đoán trùng hộp GT. Track thứ hai xuất hiện từ frame 105, gợi ý có con chim thứ hai không được gán nhãn. |

**[INFERENCE] Cơ chế:**
- Nhóm A: các video Bird/Drone "dư một mục nhãn" có mục 0 rỗng. Đây là đúng hiện tượng ADR-0004/ADR-0006 đã ghi (chiều lệch offset0/offset1 vẫn UNDETERMINED).
  - Dù đúng chiều nào, frame 0 của các video này vẫn **không phải** frame không có vật: dưới offset0 là nhãn thiếu, dưới offset1 là nhãn đặt lệch một frame.
- Nhóm B: nhãn dừng sớm trong khi chim vẫn bay trong khung.

## Hệ quả cần An kiểm tra ở W7
1. **Precision lớp Bird trên val có thể bị kéo xuống bởi chính một video.**
   - Ở conf 0,25, run 13 có Bird P 0,548 và R 0,781 trên 73 hộp GT, tức khoảng 47 FP lớp Bird (`operating_points.csv`).
   - 36/47 FP này nằm trong 20 ảnh nhóm B.
   - Nếu An xác nhận đó là chim thật, Bird P thấp chủ yếu là lỗi nhãn của `V_BIRD_041`, không phải lỗi mô hình. Con số này là thăm dò, chưa sửa metric.
2. **Ảnh âm tính trong train có thể cùng loại.** `e1-yolo-v1` có 123 ảnh train âm tính.
   - Có thể là frame 0 của video dư mục và đoạn sau khi nhãn hết (vd. `V_BIRD_008` có nhãn 72/321 frame, `V_BIRD_011` có 97/318). Như vậy mô hình đang được dạy "không có vật" trên ảnh có vật.
   - Chưa kiểm được vì repo không có GT theo frame của train.
   - Đây là một thay đổi dữ liệu khác với hard negative của ADR-0011. Nếu sửa thì cần giao thức riêng đặt trước, vd. coi frame ngoài vùng nhãn tin cậy là "bỏ qua" thay vì "âm tính", và chỉ đổi một yếu tố.
3. **Báo cáo W6:** không viết "38/40 ảnh âm tính có FP" như bằng chứng FP nền.

## Gói ảnh cho An (`w6_negframes.zip`, Kaggle run 16)
| File | Nội dung |
|---|---|
| `originals/<stem>.jpg` | 40 ảnh gốc 640×512, chép nguyên byte từ `e1-yolo-v1`, SHA-256 khớp `yolo_manifest.csv.gz` |
| `annotated/<stem>_review.jpg` | dự đoán run 13 conf ≥ 0,25 (màu theo lớp, ghi lớp + conf) và hộp GT gần nhất (nét đứt vàng, `GT f<k>`); hộp vẽ nới 3 px để không che vật nhỏ |
| `overview.jpg` | lưới 8×5 để xem nhanh |
| `review_index.csv` | `sample_no`, video, frame, nhóm, `role` (FP / `control_no_fp`), nhãn hiện tại (rỗng), lớp/conf/bbox dự đoán, hộp GT gần nhất, SHA-256 ảnh |

Bbox ghi dạng `x,y,w,h` theo pixel, góc trên trái, trong ảnh 640×512.

An điền cột kết luận cho từng ảnh: `vat_that_thieu_nhan`, `FP_that`, `khong_ro`. Nếu cần, xem thêm clip gốc của video tương ứng.
