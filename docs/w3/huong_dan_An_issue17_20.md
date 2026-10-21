# Hướng dẫn cho An: đưa #17 và #20 từ nhánh `code-lna` vào `main`

Người soạn: Quang · 21/10/2026 · Quy trình chung: `docs/governance/github_workflow.md` (PR #30)

## 1. Đánh giá nhanh
| Issue | File trên `code-lna` | Đánh giá | Cần sửa trước khi tạo PR |
|---|---|---|---|
| #17 W3-04 | `docs/w3/training_protocol.md` | Dùng được. Lý do chọn imgsz, epochs/patience, batch, optimizer, seed và quyết định không tách val nội bộ đều rõ ràng. Mục 7 (chọn ngưỡng theo F1 Drone) đã được áp dụng vào script phân tích ở PR #28 | (a) Mục 2, dòng "Số ảnh/lớp/split": dữ liệu **đã có** trong `results/W03/kaggle_run_03b/export_evidence/dataset_stats.csv` (đã merge, PR #25) → chép số ảnh theo lớp × split từ file này, ghi nguồn. (b) Mục 2, dòng "Xử lý nhãn lệch": đổi "theo kết quả run 03" thành "giữ video dư 1 mục với offset 0 (ADR-0004, mục Kết quả thực hiện)". (c) Mục 5 giữ nguyên "chờ run 04" |
| #20 W3-07 | `data/manifests/license_matrix.csv` (2 dòng `TOOL-ULTRALYTICS`, `MODEL-YOLOV8N`) | Dùng được: đúng AGPL-3.0, có URL nguồn chính thức, ngày kiểm | (a) Thêm ý vào cột `notes` của `TOOL-ULTRALYTICS`: AGPL-3.0 mục 13 yêu cầu cung cấp mã nguồn cho người dùng tương tác qua mạng → lưu ý khi làm API/dashboard W8. (b) Thêm dòng trống cuối file (hiện tại thiếu newline cuối file) |

Các file khác trên `code-lna` **không đưa vào `main`**: split cũ theo file (`data/splits/train_v1.csv`, `val_v1.csv`, `test_v1.csv`, `split_v1_manifest.json`, `data/splits.zip`, `dataset_yolo.yaml`), script W2 cũ, `results/W03/kaggle_run_03/` (chạy local, thứ tự lớp ngược), `docs/w3/task16.md`, `docs/w3/ADR0004.md`, `debug.log`, `python`, `.gitignore` sửa, việc xoá `data/samples/README.md`. Lý do: trùng hoặc mâu thuẫn với ADR-0003/ADR-0004 trên `main`.

## 2. Vì sao không đổi tên `code-lna`
Đổi tên thì PR vẫn mang theo khoảng 28 file ở trên, phải gỡ từng file. Cách gọn hơn: tạo **hai nhánh mới từ `main`**, mỗi nhánh chỉ chép đúng 1 file. `code-lna` giữ nguyên làm bản nháp cá nhân, không tạo PR từ nhánh này. Có thể xoá sau khi #17 và #20 đã merge.

## 3. Các bước (GitHub Desktop)
Trước khi làm: ở `code-lna` không còn thay đổi chưa commit (tab Changes trống).

### 3.1 Nhánh cho #20
1. **Current Branch → main → Fetch origin → Pull origin**.
2. **Current Branch → New Branch** → `issue-20-license` → *Create branch based on main*.
3. **Repository → Open in Command Prompt**, chạy:
   ```
   git restore --source=code-lna -- data/manifests/license_matrix.csv
   ```
4. Mở file, sửa theo mục 1 (#20 a, b). Kiểm tra trong GitHub Desktop: tab Changes **chỉ có 1 file**, phần diff chỉ thêm 2 dòng.
5. Commit: `data(w3): add Ultralytics and YOLOv8n license rows (#20)` → **Publish branch**.
6. **Create Pull Request**:
   - Title: `W3-07: kiểm tra license Ultralytics và YOLOv8n (#20)`
   - Description (khung tự điền từ template):
     ```
     ## Tóm tắt
     Thêm 2 dòng license cho mã nguồn Ultralytics và weights YOLOv8n vào license matrix.

     ## Thay đổi
     - data/manifests/license_matrix.csv: TOOL-ULTRALYTICS, MODEL-YOLOV8N (AGPL-3.0, kiểm 14/10/2026)

     ## Bằng chứng / Kiểm tra
     - LICENSE chính thức: https://github.com/ultralytics/ultralytics/blob/main/LICENSE
     - Repository weights: https://github.com/ultralytics/assets

     ## Giới hạn / chưa xác minh
     - AGPL-3.0 mục 13: khi phục vụ qua mạng (API/dashboard W8) phải cung cấp mã nguồn cho người dùng.

     Closes #20
     ```
   - Reviewers: `itsmarcusduong` · Assignees: An · Milestone: W3 → **Create pull request**.

### 3.2 Nhánh cho #17
1. **Current Branch → main → Fetch origin** (nếu PR #28 đã merge thì Pull).
2. **New Branch** → `issue-17-training-protocol` → *based on main*.
3. Command Prompt:
   ```
   git restore --source=code-lna -- docs/w3/training_protocol.md
   ```
4. Sửa theo mục 1 (#17 a, b, c). Tab Changes chỉ có 1 file.
5. Commit: `docs(w3): fill training protocol rationale and dataset counts (#17)` → **Publish branch**.
6. **Create Pull Request**:
   - Title: `W3-04: giao thức huấn luyện baseline A (#17)`
   - Description:
     ```
     ## Tóm tắt
     Điền lý do cho các quyết định trong giao thức huấn luyện baseline A và số ảnh theo lớp/split.

     ## Thay đổi
     - docs/w3/training_protocol.md: mục 2 (số ảnh, xử lý nhãn lệch), mục 3 (lý do YOLOv8n@640, license), mục 4 (lý do siêu tham số), mục 6 (không tách val nội bộ), mục 7 (chọn ngưỡng theo F1 Drone trên val)

     ## Bằng chứng / Kiểm tra
     - Số ảnh: results/W03/kaggle_run_03b/export_evidence/dataset_stats.csv
     - Xử lý nhãn: ADR-0004, mục "Kết quả thực hiện"

     ## Giới hạn / chưa xác minh
     - GPU và thời gian train chờ results/W03/kaggle_run_04/env.json

     Closes #17
     ```
   - Reviewers: `itsmarcusduong` · Assignees: An · Milestone: W3 → **Create pull request**.

### 3.3 Sau khi Quang review
- Có **Request changes** → sửa trên đúng nhánh đó, commit mới, Push; trả lời từng comment.
- Có **Approve** → An bấm **Merge pull request** (Create a merge commit, giữ tiêu đề mặc định) → **Delete branch**.

## 4. Việc review của An đang chờ
| PR | Nội dung | An cần kiểm tra |
|---|---|---|
| #28 | Sửa theo 3 góp ý của An ở PR #23, #25, #26 | Các lỗi An nêu đã được xử lý đúng chưa; chọn ngưỡng theo F1 Drone khớp mục 7 giao thức chưa |
| #29 | ADR-0005 (lựa chọn 1A/2A/3A/4A, áp dụng tạm) | Nội dung có đúng với comment của An trên #7 không |
| #30 | Quy trình GitHub + PR template | Có đồng ý áp dụng từ W4 không |

Với mỗi PR: tab **Files changed → Review changes → Approve / Request changes / Comment**. Review **trước** khi merge.
