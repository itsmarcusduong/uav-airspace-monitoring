# Kaggle run 19b3 — FBD-SV-2024, đo cảnh báo sai trên neg_eval (C0)

- Chạy qua GitHub Actions run `46149322093`, notebook `e1-w9-run19-neg-fbdsv-b3`, COMMIT `f18a4d38b9dd01aaaf8e5aa3f54612398b8c71a8`, ngày 28/11/2026, GPU Tesla T4. Ô cuối in `PASS`.
- Tệp `w9_neg_fbdsv_evidence.zip`: SHA-256 `93fbf488719c012f18b740802092a365b3d1ccd081e9fa5150c931b25c828eb0`. Tệp zip không đưa vào Git; thư mục `w9_neg_fbdsv/` là nội dung đã giải nén. SHA-256 của từng tệp ghi trong `ACTIONS_OUTPUT_MANIFEST.json`.
- Theo ADR-0014, ở đây chỉ có số tổng hợp và ID clip, không có video, frame hay nhãn.
- Các lần chạy trước không có kết quả:
  - run 19 chạy tay lần 1: lỗi `OverflowError` ở `poisson_upper` sau khoảng 4 giờ, đã sửa ở #150;
  - run 19b2: Quang hủy vì dùng code cũ (sẽ gặp đúng lỗi trên) và bước chuẩn hóa chậm, khoảng 11 giây/clip; đã sửa ở #151.
- Riêng `env.json` có `actions_run_id` để trống, vì biến môi trường của GitHub không truyền vào được phiên Kaggle. ID run nằm trong `ACTIONS_OUTPUT_MANIFEST.json`.
