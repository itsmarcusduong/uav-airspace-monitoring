# Pixabay và Pexels: điều khoản về thu thập tự động và học máy (truy cập 29/11/2026)

Kiểm khi lập giao thức Pixabay cho W10 (ADR-0017). Bản tóm tắt license (Pixabay, 16/11) không nhắc tới học máy, nên phải đọc Terms of Service đầy đủ, vì trang tóm tắt ghi rõ Terms of Service mới là bản ràng buộc.

| Nguồn | Trang | Cập nhật | Nội dung liên quan (diễn đạt lại, trích ngắn) |
|---|---|---|---|
| Pixabay Terms of Service | https://pixabay.com/cs/service/terms/ (bản hiển thị tiếng Anh) | 20/10/2026 | Mục 8 cấm khai thác dữ liệu, trích xuất, scraping và dùng chương trình để thu thập tự động "cho mọi mục đích không được phép", nêu rõ gồm cả mục đích học máy; cấm sao chép nội dung hàng loạt hoặc có hệ thống nếu không được cho phép rõ ràng. |
| Pixabay API docs | https://pixabay.com/api/docs/ (Quang gửi nội dung 29/11) | — | API dành cho truy vấn của người dùng thật; không cho phép tải hàng loạt có hệ thống. |
| Pixabay License Summary | https://pixabay.com/en/service/license/ | — | Không nhắc học máy; dẫn sang Terms of Service là bản ràng buộc. |
| Pexels Terms of Service | https://pexels.com/terms-of-service | 20/10/2026 | Mục 8 có cùng điều cấm như Pixabay (thu thập tự động cho mục đích học máy; sao chép hàng loạt). |

Kết luận [DECISION đề xuất, chờ Quang và An xác nhận]: dùng clip Pixabay/Pexels làm `neg_train` (huấn luyện) hoặc `neg_eval` (đánh giá mô hình học máy) qua script là mục đích học máy không có cho phép rõ ràng. Không dùng hai nguồn này cho tới khi có cho phép bằng văn bản của Pixabay/Pexels. `license_matrix.csv` chuyển DS-PIXABAY-VIDEO và DS-PEXELS-VIDEO sang `needs_review`.
