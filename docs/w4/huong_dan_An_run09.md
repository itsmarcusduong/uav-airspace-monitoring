# Hướng dẫn An chạy run 09 — PHIÊN 3 (RT-DETR-l @640) trên tài khoản Kaggle của An

Người soạn: Quang · 27/10/2026 · Issue #39 · Giao thức: `docs/w4/training_protocol_w4.md` mục 4
Phân công: **An chạy phiên 3**; Quang chạy phiên 1 và 2. Không chạy config khác để tránh trùng.

## 1. Tạo notebook mới
1. Kaggle → Create → New Notebook → File → **Import Notebook** → chọn file repo `scripts/kaggle/notebooks/w4_run09_train_compare.ipynb`. GitHub Desktop: `main` → Fetch → Pull trước; nếu không mở repo được thì tải file từ GitHub (Raw → Save as).
2. Đổi tên notebook thành **`e1-w4-run09-phien3`**.
3. **Add Input**, chỉ dùng 2 nguồn Quang đã chia sẻ qua group:
   - Datasets → `e1-w3-tools` (bản mới nhất);
   - Notebook Output Files → `e1-w3-run03b`.
   Nếu không thấy một trong hai → nhắn Quang, không dùng nguồn khác.
4. Settings: Accelerator **GPU T4 x2** (không chọn P100), Internet **On**.
5. **Share → Collaborators → thêm group chung của nhóm**, để Quang mở được và tải output. Làm ngay lúc tạo notebook, không đợi chạy xong.

## 2. Ô code đầu tiên: điền đúng như sau, không sửa gì khác
```python
COMMIT = "1a71f5bdba154818310a741fe38fd14fe86fb946"
DATASET = "e1-yolo-v1"
CONFIGS = ["rtdetr_l_640.yaml"]
ULTRALYTICS_VERSION = "8.4.183"
```
Không sửa file config, batch hay epoch. Các giá trị này phải giống phiên của Quang thì kết quả mới so sánh được.

## 3. Chạy thử, rồi chạy thật
1. Ở chế độ Edit, Run từng ô từ ô đầu tới ô bắt đầu bằng `TRAIN = find(...)`. **Không chạy** ô có vòng lặp `for c, p in CFG.items():`.
2. Kiểm tra:
   - ô `pip` in `ultralytics 8.4.183 … cuda True`;
   - ô dữ liệu in `images 6869 | fingerprint d0ac7e230b385132 | trung ban goc: True` (bắt buộc đúng);
   - ô config in `rtdetr_l_640.yaml  rtdetr_l_640  rtdetr-l.pt  imgsz=640 batch=8`.
   - Lỗi `KHONG TIM THAY rtdetr_l_640.yaml` → `e1-w3-tools` chưa phải bản mới, nhắn Quang.
3. Đúng hết → **Save Version** → *Save & Run All (Commit)*, version name `run09 phien3`. Bấm **Stop session** để phiên Edit không tốn GPU. Bản chạy thật chạy nền, có thể đóng trình duyệt.
4. Ước lượng 3–4 giờ (chưa đo). Ô cuối phải in bảng có `ok True` và chữ **`PASS`**.

## 4. Báo Quang
Nhắn Quang: "xong phiên 3, PASS/FAIL", kèm link version notebook. Quang tự vào tab Output để tải `w4_compare_evidence.zip` và weights `runs/rtdetr_l_640/weights/best.pt`, `last.pt`. An không cần tải hay upload gì.
- Nếu `FAIL` hoặc `CUDA out of memory`: không chạy lại, không đổi batch; chỉ cần báo Quang.
- Phần này không liên quan tới CVAT (#24). An không cần xem kết quả run 06 / ADR-0006.

## 5. Ghi nhận đóng góp
Bảng so sánh W4 và báo cáo tuần sẽ ghi: "rtdetr_l_640 — chạy bởi Lê Ngọc An (tài khoản Kaggle của An)". Thời gian suy luận (ms/ảnh) có thể lệch nhẹ so với các mô hình Quang chạy, vì mỗi phiên nhận một máy T4 khác; tên GPU nằm trong `env.json`.
