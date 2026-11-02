# ADR-0010: Cấu trúc GitHub và Evidence theo mẫu bắt buộc của GVHD

- Trạng thái: **Accepted** (Quang 03/11/2026). An duyệt trong PR của issue #79.
- Thay thế phần lịch tag của ADR-0001: ADR-0001 chỉ gắn tag ở W4, W8, W11, W14. Từ nay **mỗi tuần một tag `wNN`**, thêm release ở W4, W8, W11, W14.
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

[Kết quả đo] Kiểm tra ngày 03/11/2026 bằng `scripts/github/check_structure.py --weeks 1-6`:
- `Evidence/W01`–`W05`, milestone `Tuan1`–`Tuan14`, tag `w04`, `w05` và mọi PR có review request cho thành viên còn lại đều đã đúng mẫu.
- Các điểm lệch mẫu:
  1. milestone `Tuan1` không có issue, vì W1 làm trước khi áp dụng Issue/PR;
  2. #7 và #19 gán cho hai sinh viên;
  3. thiếu tag `w01`, `w02`, `w03`;
  4. 20 PR của Quang chưa có review của An (chỉ là cảnh báo, không sai mẫu).

## Quyết định [DECISION]
1. **Milestone `TuanN` cho mọi tuần từ W1.** W1 được bổ sung 2 issue đã đóng (#84 Quang, #85 An). Mỗi issue ghi rõ là tạo bổ sung ngày 03/11 và trỏ tới commit W1.
2. **Mỗi issue một sinh viên, một kết quả.**
   - Tên issue: `WN-xx – <Họ tên> – <kết quả>`, đúng 1 assignee khớp tên.
   - Việc chung thì tách thành hai issue.
   - Đã sửa #7 (giao An, chờ GVHD xác nhận ADR-0005) và #19 (giao An; phần job run 05 của Quang thuộc #18).
3. **Mỗi PR:** reviewer là thành viên còn lại, milestone của tuần, `Closes #n` hoặc `Refs #n`. PR merge trước khi được review thì người còn lại vẫn phải review sau merge.
4. **Tag `wNN` mỗi tuần,** trên commit `main` cuối tuần (thường là merge của PR báo cáo tuần), tạo cùng release `WN — v0.N`. Tag bổ sung cho W1–W3 trỏ vào commit cuối của từng tuần:

   | Tag | Commit | Lý do chọn commit |
   |---|---|---|
   | `w01` | `966b2c1` | gói nộp W1 |
   | `w02` | `1b0f144` | merge PR #15, báo cáo W2 |
   | `w03` | `e060d28` | merge PR #35, báo cáo W3 và v0.3 |

   Ngày commit là ngày đưa lên GitHub, có thể sau ngày kết thúc tuần.
5. **`Evidence/WNN/` bắt buộc** có `README.md`, `metrics.csv`, `test-results.*`, `figures/` (không rỗng), `manifest.json` (SHA-256 khớp file). Thư mục được tạo bằng `scripts/reporting/build_evidence.py`, không nhập tay.
6. **Kiểm tra trước khi gắn tag và nộp báo cáo:** chạy `python scripts/github/check_structure.py --weeks 1-N` (tuần đang làm thêm `--current N`). Không có dòng FAIL mới được gắn tag. Kết quả ghi vào báo cáo tuần.

## Hệ quả
- Mỗi tuần, issue báo cáo (`WN-06`) có thêm mục kiểm tra cấu trúc.
- An review sau merge các PR còn thiếu review (W2–W4, W6).
- Tag phải tạo bằng GitHub Desktop hoặc giao diện web, vì môi trường của Claude không tạo được tag qua API.
