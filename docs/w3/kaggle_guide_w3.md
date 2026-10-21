# Hướng dẫn Kaggle W3 (run 03a → 03b → 04)

Giao diện Kaggle có thể đổi tên nút đôi chút; các bước giữ nguyên. Mọi xử lý dữ liệu thật chạy trên Kaggle, không chạy trên máy local.

## 0. Chuẩn bị một lần
- Tài khoản Kaggle đã xác minh số điện thoại (cần để bật **Internet** trong notebook).
- Dataset thô `e1-svanstrom-raw` (Private) đã có từ W2. Không tạo lại.
- **SHA commit (`COMMIT`)**: sau khi PR chứa script đã merge, mở GitHub Desktop → nhánh `main` → *Fetch/Pull origin* → tab **History** → chuột phải commit trên cùng → **Copy SHA**. Dán đủ 40 ký tự. File script upload lên Kaggle phải lấy từ đúng commit đó; sửa script thì upload lại và dùng SHA mới.

## 1. Tạo dataset công cụ `e1-w3-tools`
1. kaggle.com → **Datasets** (menu trái) → **+ New Dataset**.
2. Kéo thả **7 file** (lấy từ repo sau khi pull `main`, đúng commit dùng làm `COMMIT`; đường dẫn tính từ gốc repo):

| File | Đường dẫn trong repo |
|---|---|
| `w3_review_sheets.py` | `scripts\kaggle\` |
| `w3_export_yolo.py` | `scripts\kaggle\` |
| `w3_train_baseline.py` | `scripts\kaggle\` |
| `baseline_A.yaml` | `configs\` |
| `video_split_v1.csv` | `data\splits\` |
| `annotation_audit.csv` | `results\W02\kaggle_run_01\` |
| `review_assignment_w2.csv` | `results\W02\review\` |

3. Title: `e1-w3-tools`. Visibility: **Private**. Bấm **Create**. Đợi trạng thái xử lý xong.
4. **Cập nhật phiên bản về sau** (ví dụ thêm `review_assignment_w3.csv` trước run 03b, hoặc config mới sau khi An duyệt): mở trang dataset → **New Version** → thêm/thay file → ghi chú phiên bản (vd. `review v2 + SHA <7 ký tự>`) → **Create**. Notebook dùng dataset sẽ hỏi cập nhật input sang bản mới: chọn cập nhật.

## 2. Nhập notebook
1. kaggle.com → **Code** → **+ New Notebook**.
2. Trong editor: menu **File → Import Notebook** → chọn file `.ipynb` trong `scripts\kaggle\notebooks\` → **Import**.
3. Đổi tên notebook (góc trên trái) theo bảng:

| Notebook | Tên trên Kaggle | Accelerator | Input cần add |
|---|---|---|---|
| `w3_run03a_review_offset.ipynb` | `e1-w3-run03a` | None | `e1-svanstrom-raw`, `e1-w3-tools` |
| `w3_run03b_export_yolo.ipynb` | `e1-w3-run03b` | None | `e1-svanstrom-raw`, `e1-w3-tools` (bản có `review_assignment_w3.csv`) |
| `w3_run04_train_baseline_A.ipynb` | `e1-w3-run04` | GPU T4 x2 (hoặc P100) | `e1-w3-tools`, **output của notebook `e1-w3-run03b` bản có `e1-yolo-v1.zip`** |
| `w3_run05_analyze_baseline_A.ipynb` | `e1-w3-run05` | None | `e1-w3-tools` (bản có `w3_analyze_baseline.py`), output `e1-w3-run03b`, output `e1-w3-run04` |

## 3. Thêm input và cài đặt
1. Cột phải → **Input** → **+ Add Input**.
   - Dataset: lọc **Your Datasets** → chọn `e1-svanstrom-raw`, `e1-w3-tools` → **+**.
   - Output của notebook khác (chỉ run 04): lọc **Your Work → Notebooks** → chọn `e1-w3-run03b` (phải là bản đã *Save Version* chạy xong).
2. Cột phải → **Session options**: **Accelerator** theo bảng trên; **Internet: On**.
3. Run 04: trước khi chạy xem hạn mức GPU còn lại (Settings tài khoản → GPU quota).

## 4. Điền tham số và chạy
1. Ô code đầu tiên: điền `COMMIT = "<40 ký tự>"`. Run 03b thêm `PLUS1_POLICY` (`offset0`/`offset1`, theo `offset_review_score.json` Claude gửi).
2. Có thể bấm **Run All** để thử nhanh. Nếu ô kiểm tra in `FAIL`, dừng và gửi Claude nội dung `stage_status.json` (đừng chạy lại nhiều lần).
3. Chạy chính thức để lưu kết quả: **Save Version** → **Save & Run All (Commit)** → **Save**. Phiên bản chạy nền; theo dõi ở trang notebook (Version → Logs).

## 5. Tải kết quả
Mở phiên bản đã chạy xong → tab **Output** → di chuột lên file → biểu tượng tải về.

| Run | Tải về | Giải nén vào |
|---|---|---|
| 03a | `w3_review_v2.zip`, `w3_export_evidence.zip` | `results/W03/kaggle_run_03a/` |
| 03b | `w3_export_evidence.zip` (không tải thư mục `e1-yolo-v1/`) | `results/W03/kaggle_run_03b/` |
| 04 | `w3_train_evidence.zip` | `results/W03/kaggle_run_04/` |
| 05 | `w3_analysis.zip` | `results/W03/kaggle_run_05/` |
| 04 | `runs/baseline_A/weights/best.pt`, `last.pt` | Google Drive `E1/weights/W03/` (quyền xem); **không** đưa vào Git |

Xong mỗi run, nhắn Claude "đã có kết quả run 03a/03b/04" để đọc, đối chiếu và cập nhật tài liệu.

## 6. Tự kiểm tra (ô cuối mỗi notebook)
- 03a: 358 video được vẽ, không lỗi; mọi stage OK (export = SKIPPED); nhóm `V|Drone|plus1` và `V|Bird|plus1` có `passes=True`. Nếu không: **dừng**, không chạy 03b/04.
- 03b: mọi stage OK; `split_counts` = 454/98/98; không có `images/test`; train và val đều có đủ 4 lớp.
- 04: mọi stage OK; có GPU; `results.csv` có dòng mỗi epoch; có PR curve trên val.

## Sự cố gắn input run 04 (21/10/2026) và cách xử lý
- Run 04 bản 1 thất bại trước khi chạy ô code đầu: `ERRORED_MOUNTING_DATASET … e1-w3-run03b … retry budget exhausted (30 attempts)`. Output run 03b bản đầu có khoảng 14 nghìn file nhỏ (ảnh + nhãn); tạo Dataset từ output này cũng lỗi (`Unexpected end of JSON input`).
- Cách xử lý: chạy lại run 03b với `--pack-zip` (đã có trong notebook 03b mới) → output chỉ còn `e1-yolo-v1.zip` (ZIP_STORED, không nén lại JPEG), `w3_export_evidence/` và `w3_export_evidence.zip`. Run 04/05 giải nén zip vào `/tmp`, kiểm tra SHA-256 của zip với `dataset_zip.json` và SHA-256 từng ảnh với `yolo_manifest.csv.gz`, rồi in fingerprint và so với bản gốc `d0ac7e23…`.
- Nếu fingerprint khác bản gốc (ví dụ OpenCV trên Kaggle đổi phiên bản làm khác byte JPEG): vẫn dùng được nhưng phải lưu bằng chứng run 03b mới thay cho bản cũ và ghi vào ADR-0004.
- Luôn chạy thử các ô đến bước dữ liệu ở chế độ Edit trước khi *Save Version* để phát hiện lỗi gắn input sớm.
