# Quy trình GitHub của nhóm E1

Áp dụng cho cả hai thành viên từ W4. Căn cứ: Đề cương mục 10, `AGENTS.md`. Mục tiêu: mỗi thay đổi truy được Issue → nhánh → commit → PR → review → merge, và người review kiểm tra được nhanh.

## 1. Một việc = một Issue = một nhánh
- Mỗi việc bắt đầu từ một Issue trong milestone của tuần. Tên Issue: `W<tuần>-<số thứ tự> <mô tả ngắn>`, ví dụ `W3-04 Giao thức train và config baseline A`.
- Nhánh **luôn tạo mới từ `main` đã cập nhật**, đặt tên `issue-<số issue>-<chủ-đề-không-dấu>`:

| Đúng | Sai |
|---|---|
| `issue-17-training-protocol` | `code-lna` (không có số issue, gom nhiều việc) |
| `issue-20-license` | `issue-17-20` (hai issue một nhánh) |
| `issue-24-cvat-gold-set` | `Issue_24 CVAT` (có dấu cách, chữ hoa) |

- Không commit thẳng lên `main`. Không dùng lại nhánh đã merge cho việc mới.

## 2. Commit
Mẫu: `<loại>(w<tuần>): <mô tả ngắn> (#<issue>)`

| Loại | Dùng khi | Ví dụ |
|---|---|---|
| `docs` | tài liệu, ADR, giao thức, báo cáo | `docs(w3): fill training protocol rationale (#17)` |
| `data` | manifest, license matrix, split, file kết quả nhỏ | `data(w3): add Ultralytics and YOLOv8n license rows (#20)` |
| `feat` | script/chức năng mới | `feat(w4): add CVAT gold-set export job (#24)` |
| `fix` | sửa lỗi | `fix(w3): validate YOLO label lines (#19)` |
| `chore` | dọn dẹp, cấu hình repo | `chore: add PR template (#21)` |

- Mỗi commit chỉ chứa file thuộc issue đó. Trước khi commit, xem lại danh sách file ở GitHub Desktop và bỏ chọn file không liên quan.
- Tác giả commit là chính người làm (tài khoản GitHub của mình).

## 3. Không được đưa vào Git
Dữ liệu thô, ảnh/khung hình trích từ video, file zip kết quả lớn, weights (`*.pt`), file rác (`debug.log`, file rỗng `python`), đường dẫn máy cá nhân (`D:\...`, `C:\Users\...`) trong tài liệu hoặc notebook, mật khẩu/token. Dữ liệu lớn → Drive/Kaggle + SHA-256 trong manifest.

## 4. Pull Request
- **Title**: `W<tuần>-<số>: <mô tả> (#<issue>)`, ví dụ `W3-04: giao thức huấn luyện baseline A (#17)`.
- **Description**: theo mẫu `.github/pull_request_template.md` (GitHub tự điền khi tạo PR): Tóm tắt, Thay đổi, Bằng chứng/Kiểm tra, Giới hạn, liên kết Issue.
  - `Closes #n` khi PR hoàn thành issue; `Refs #n` khi chỉ là một phần.
- **Reviewers**: người còn lại (An ↔ Quang). **Assignees**: chính mình. **Milestone**: tuần hiện tại.
- Base = `main`. Tab "Files changed" chỉ được có file của issue; nếu thấy file lạ → sửa nhánh trước khi gửi review.

## 5. Review và merge
1. Tác giả tạo PR và gửi review request.
2. Người review đọc "Files changed", đối chiếu bằng chứng, rồi chọn **Review changes**:
   - **Approve** nếu dùng được;
   - **Request changes** kèm từng điểm cụ thể (file, dòng, lý do, đề xuất);
   - **Comment** nếu chỉ góp ý.
   Review trước khi merge; góp ý sau merge vẫn ghi lại nhưng phải mở PR sửa.
3. Tác giả sửa bằng commit mới trên **cùng nhánh** (PR tự cập nhật), trả lời từng góp ý.
4. Merge bằng **Create a merge commit**, giữ tiêu đề mặc định `Merge pull request #<n> from <tài khoản>/<nhánh>`. Sau merge: **Delete branch**.
5. Nếu issue đã xong, kiểm tra issue tự đóng (nhờ `Closes #n`); nếu chưa, đóng tay kèm comment trỏ tới PR.

## 6. Checklist người review
- [ ] Tên nhánh, title PR, commit đúng mẫu và đúng số issue.
- [ ] Chỉ có file trong phạm vi issue; không có dữ liệu, weights, file rác, đường dẫn máy cá nhân.
- [ ] Mọi con số có file nguồn (CSV/JSON) và script tạo ra nó; không có số "ước lượng".
- [ ] Thông tin quan trọng có nguồn hoặc được đánh dấu `[INFERENCE]` / `NEEDS_REVIEW`.
- [ ] Không mâu thuẫn ADR hiện hành (ADR-0004 dữ liệu baseline, ADR-0005 chỉ tiêu/modality/tracker); thay đổi quyết định → ADR mới.
- [ ] Test vẫn khóa; split theo video; không dùng test để chọn ngưỡng/model.
- [ ] Script: chạy được bằng lệnh trong PR, ghi `stage_status.json`, seed cố định, lỗi dữ liệu báo rõ chứ không bỏ qua.

## 7. Thao tác bằng GitHub Desktop
1. **Current Branch → main → Fetch origin → Pull origin** (nếu có).
2. **Current Branch → New Branch** → nhập tên `issue-<n>-<chủ-đề>` → *Create branch based on main*.
3. Sửa file → quay lại GitHub Desktop, chỉ tích file thuộc issue → Summary = commit message theo mục 2 → **Commit to issue-…**.
4. **Publish branch** (lần đầu) hoặc **Push origin**.
5. **Create Pull Request** (mở trình duyệt) → title/description theo mục 4 → Reviewers, Assignees, Milestone → **Create pull request**.

### Lấy file từ một nhánh cũ sang nhánh mới
Đang ở nhánh mới (tạo từ `main`): **Repository → Open in Command Prompt** (hoặc Git Bash) rồi chạy:
```
git restore --source=<nhánh-cũ> -- <đường/dẫn/file>
```
Ví dụ `git restore --source=code-lna -- docs/w3/training_protocol.md`. Lệnh chỉ chép đúng file đó; các file khác của nhánh cũ không bị kéo theo.
