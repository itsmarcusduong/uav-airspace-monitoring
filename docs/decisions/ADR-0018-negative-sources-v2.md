# ADR-0018: Nguồn âm tính bổ sung W10 — Wikimedia Commons v2 và AirBirds; Pixabay/Pexels chờ cho phép

- Trạng thái: **Proposed** (Quang đề xuất và xác nhận phương án 29/11/2026). Áp dụng theo ADR-0017 mục 5 (An review ≤ 6 giờ, hoặc sau merge).
- Liên quan: ADR-0011 (mục 2, 4, 6, 7), ADR-0013, ADR-0014, ADR-0017; giao thức `docs/w10/neg_sources_v2_protocol.md`.

## Bối cảnh
- `neg_eval` cần ≥ 120 phút (ADR-0011 mục 2); sau W9 mới có khoảng 23 phút đã đo (FBD-SV, val Svanström).
- ADR-0013 chọn Pixabay làm nguồn chính thứ hai. Ngày 29/11, đọc Terms of Service đầy đủ (cập nhật 20/10/2026): mục 8 cấm thu thập tự động "cho mọi mục đích không được phép, kể cả học máy" và cấm sao chép hàng loạt hoặc có hệ thống nếu chưa được phép rõ ràng. Content License (mục 5) cho dùng thương mại và phi thương mại và không cấm học máy, nhưng cách lấy dữ liệu dự kiến (API + script) rơi vào mục 8. Pexels có điều khoản giống hệt.

## Quyết định [DECISION]
1. Pixabay, Pexels: `needs_review`, **không dùng** cho tới khi có văn bản cho phép (Quang đã gửi email xin phép Pixabay 29/11/2026). ADR-0013 mục về Pixabay được thay bằng điều này.
2. Thêm **Wikimedia Commons v2** (category mở rộng, subcategory một cấp, trần 330 phút ứng viên), cùng giao thức sàng lọc và chia split của W9.
3. Thêm **AirBirds** (camera đường băng sân bay thật, CC BY-NC-SA 4.0, nghiên cứu phi thương mại) **chỉ cho `neg_eval`**, báo riêng nguồn, không vào `neg_train`.
4. DVIDS (tác phẩm chính phủ Mỹ) là dự phòng, chỉ dùng nếu vẫn thiếu 120 phút, với phụ lục riêng.
5. Không hạ tiêu chí sàng lọc; nếu vẫn thiếu 120 phút thì báo đúng thời lượng thực có.

## Hệ quả
- Thêm 4–5 giờ sàng lọc mỗi người cho Commons v2 và một lượt sàng lọc mẫu AirBirds.
- AirBirds 5 fps, chim rất nhỏ: số đo không so trực tiếp với nguồn 30 fps; báo riêng.
- Cần dung lượng Kaggle cho một phần AirBirds (khoảng 14 GB mỗi phần).
