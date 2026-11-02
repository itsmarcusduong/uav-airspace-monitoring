# ADR-0010: Cấu trúc GitHub và Evidence theo mẫu bắt buộc của GVHD

- Trạng thái: **Accepted** (Quang 03/11/2026; sửa ngày 03/11/2026 sau khi đối chiếu lại Đề cương mục 10). An duyệt trong PR của issue #79.
- Áp dụng **từ W6**. Không rà soát lại các tuần đã qua.
- Liên quan: ADR-0001, `docs/governance/github_workflow.md` mục 0, `Evidence/README.md`.

## Bối cảnh
[DOCUMENT] GVHD yêu cầu từ W4 mọi nhóm có cùng cấu trúc theo dõi trên GitHub:

```
Milestone: TuanN
├── Issue #xx – Sv A – ket qua A
├── Issue #yy – Sv B – ket qua B
├── Issue #zz – Sv C – ket qua C (nếu có)
│
├── PR #xx → reviewer là thành viên khác
├── PR #yy → reviewer là thành viên khác
│
└── Tag/commit cuối tuần: wNN

Evidence/
├── W01/ … WNN/
    ├── README.md
    ├── metrics.csv
    ├── test-results.*
    ├── figures/
    └── manifest.json
```

[Kết quả đo] Kiểm tra ngày 03/11/2026 bằng `scripts/github/check_structure.py`:
- `Evidence/W01`–`W05`, milestone `Tuan1`–`Tuan14`, tag `w04` và review request cho thành viên còn lại ở mọi PR đều đã đúng mẫu.
- Hai issue gán cho hai sinh viên (#7, #19) đã được sửa.
- Milestone `Tuan1` được bổ sung issue #84, #85.

## Quyết định [DECISION]
1. **Milestone `TuanN` cho mọi tuần từ W1.** W1 được bổ sung 2 issue đã đóng (#84 Quang, #85 An). Mỗi issue ghi rõ là tạo bổ sung ngày 03/11 và trỏ tới commit W1.
2. **Mỗi issue một sinh viên, một kết quả.**
   - Tên issue: `WN-xx – <Họ tên> – <kết quả>`, đúng 1 assignee khớp tên.
   - Việc chung thì tách thành hai issue.
   - Đã sửa #7 (giao An, chờ GVHD xác nhận ADR-0005) và #19 (giao An; phần job run 05 của Quang thuộc #18).
3. **Mỗi PR:** reviewer là thành viên còn lại, milestone của tuần, `Closes #n` hoặc `Refs #n`. PR merge trước khi được review thì người còn lại vẫn phải review sau merge.
4. **Tag/commit cuối tuần.**
   - [DOCUMENT] Đề cương mục 10: "tag milestone tối thiểu ở các tuần W4, W8, W11, W14". Mẫu của GVHD ghi "Tag/commit cuối tuần".
   - **Bắt buộc gắn tag** `wNN` kèm release `WN — v0.N` ở W4, W8, W11, W14 (đã có `w04`; `w05` gắn thêm, không bắt buộc).
   - **Các tuần khác:** báo cáo tuần ghi **commit cuối tuần** trên `main` (SHA của merge PR báo cáo tuần). Gắn tag là tùy chọn.
   - Bản đầu của ADR này yêu cầu tag cho mọi tuần và bổ sung `w01`–`w03`. Điều đó vượt yêu cầu của Đề cương nên đã bỏ; không tạo tag cho W1–W3.
5. **`Evidence/WNN/` bắt buộc** có `README.md`, `metrics.csv`, `test-results.*`, `figures/` (không rỗng), `manifest.json` (SHA-256 khớp file). Thư mục được tạo bằng `scripts/reporting/build_evidence.py`, không nhập tay.
6. **Kiểm tra mỗi tuần từ W6:** chạy `python scripts/github/check_structure.py --weeks N --current N` khi mở và trong tuần. Khi chốt tuần, chạy `--weeks N` (không kèm `--current`). Không được có dòng FAIL. Dòng INFO cho commit cuối tuần thì ghi vào báo cáo.

## Hệ quả
- Mỗi tuần, issue báo cáo (`WN-xx` cuối tuần) có thêm mục kiểm tra cấu trúc.
- Không rà soát lại review của các tuần đã qua. Từ W6, PR nào chưa có review của người còn lại thì người đó review trong tuần.
- Tag ở W8, W11, W14 tạo bằng GitHub Desktop hoặc giao diện web, vì môi trường của Claude không tạo được tag qua API.
