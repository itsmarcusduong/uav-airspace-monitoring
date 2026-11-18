# Hướng dẫn cho An — W8 (15–21/11/2026) · Quang gửi 17/11

Milestone `Tuan8`. Kế hoạch: [REPO] `docs/w8/W8_PLAN.md`. Hạn chót tuần: **21/11**. Tuần này có **tag `w08` bắt buộc**.

## 1. Review (theo thứ tự ưu tiên)
| PR | Việc của An | Hạn |
|---|---|---|
| #114 ADR-0014 | Duyệt hoặc phản biện: FBD-SV-2024 chỉ dùng trong `neg_eval`. JSON metadata Figshare đã lưu (`data/manifests/license_evidence/`), trường `license` = **CC BY 4.0**, khớp với An thấy | 18/11 |
| #120 kế hoạch W8 (đã merge để kịp chạy Kaggle) | Review hậu kiểm **mục B** (5 điều kiện áp dụng V2 trên video thật; điều kiện 5 track recall là mới) và **mục C** (luật diễn giải chẩn đoán hộp trùng). Phải xong **trước** khi Quang có kết quả run 17 để áp luật | 18–19/11 |
| #121 ADR-0015 | Duyệt kiến trúc đầu-cuối: dashboard HTML/JS thuần thay React/Vue, SQLite thay PostgreSQL, demo chế độ phát lại. Đây cũng là đầu vào cho mục 4.2 | 19/11 |
| #112 | Review hồ sơ W7 (còn WARN ở `check_structure --weeks 7`) | sớm |

Nếu An thấy luật mục B hoặc C chưa hợp lý thì **sửa trước khi có kết quả run 17**. Sau khi có kết quả thì không sửa nữa.

## 2. #117 W8-04 — Chương IV bản nháp 4.1–4.2 (hạn Template 21/11)
File: [REPO] `docs/w8/chuong4_4.1_4.2_nhap_An.md`, nhánh `issue-117-chuong4`.
- **4.1 Kiến trúc tổng thể**: các thành phần (theo ADR-0015), luồng dữ liệu, ranh giới tin cậy.
  - Bằng chứng bắt buộc: sơ đồ kiến trúc + sơ đồ triển khai (Mermaid được; Quang render khi dựng DOCX).
  - Ghi rõ: suy luận chạy trên Kaggle, API và dashboard phát lại trên máy cá nhân.
- **4.2 Thiết kế CSDL/API**:
  - ERD hoặc schema cho `runs`, `sources`, `events`, `event_reviews`, `config_audit`;
  - tính nhất quán và phiên bản: `model_version` = SHA weights; review chỉ thêm, không sửa;
  - hợp đồng API (REST + WebSocket `FrameResult`) và sơ đồ tuần tự "phát lại → cảnh báo → người quan sát xác nhận".
  - Nếu An thấy schema hay endpoint trong ADR-0015 cần đổi, ghi lên PR #121 để Quang sửa ADR trước khi code.

## 3. #118 W8-05 — Kịch bản kiểm thử đầu-cuối
File: [REPO] `docs/w8/e2e_test_cases.md`. **Commit trước khi chạy.**
- Lấy 12 tình huống ở Thuyết minh mục 13.3. Với mỗi tình huống ghi:
  - dữ liệu dùng (video val nào, hoặc dữ liệu tổng hợp);
  - bước thực hiện;
  - kết quả mong đợi;
  - tiêu chí đạt.
- Ghi rõ tình huống nào **không kiểm được** ở chế độ phát lại và lý do (ví dụ camera mất kết nối, FPS đầu vào vượt năng lực).
- Khi Quang báo dashboard chạy được (dự kiến 20/11): chạy từng kịch bản, ghi đạt / không đạt / chưa kiểm được, kèm lý do.

## 4. Quy trình
Mỗi việc làm trên nhánh `issue-<n>-…`, commit có `(#n)`, PR gán milestone `Tuan8`, gửi review request cho Quang, ghi `Closes #n`.
