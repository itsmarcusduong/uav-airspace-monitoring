# ADR-0014: Đưa lại FBD-SV-2024 vào tập âm tính, chỉ để đánh giá

- Trạng thái: **Accepted** (An approve PR #114 ngày 18/11/2026; merge 21/11/2026). Quang đề xuất 17/11/2026. Dòng trạng thái này trước đây chưa được cập nhật khi merge; An phát hiện khi review #140 ngày 28/11/2026.
- Sửa ADR-0013 ở một điểm: FBD-SV-2024 không còn bị loại mà được dùng trong `neg_eval` theo điều kiện ở mục Quyết định. Các mục khác của ADR-0013 giữ nguyên.
- Liên quan: #113 W8-01, #99, PR #106, ADR-0011, ADR-0013, `data/manifests/license_matrix.csv`.

## Bối cảnh
- ADR-0013 (sau PR #106) loại FBD-SV-2024 cho tới khi điều khoản được làm rõ và nhóm xem xét lại.
- Kiểm lại ngày 17/11/2026:
  - [WEB SOURCE] Trang Figshare của bộ dữ liệu có mục "Licence" nhưng để trống. Phần mô tả ghi: "This dataset is for learning and research purposes only, not for commercial use."
  - [WEB SOURCE] Metadata API của bản ghi (`data/manifests/license_evidence/fbd_sv_2024_figshare_27377595.json`, Quang lưu 17/11/2026) ghi `license` = **CC BY 4.0**. Trường `description` vẫn có câu giới hạn học tập, nghiên cứu, không thương mại. Kết quả này khớp với ghi nhận của An.
  - Bản ghi có một tệp `FBD-SV-2024.zip`, 1.790.526.712 byte, MD5 `8a78846b16329466347be71da10d608a`.
  - [WEB SOURCE] Trang Figshare, trang arXiv:2409.00317 (HTML và PDF) không có email tác giả. Bài báo chỉ ghi tác giả liên hệ là Ze-Xi Hua và Heng-Chao Li.
- [Quyết định của Quang, 17/11] Không có địa chỉ để xin phép, nên không chờ email. Lý do được nêu ở mục Lập luận.

## Lập luận [INFERENCE — không phải tư vấn pháp lý]
- Cả hai cách đọc đều cho phép đúng cách dùng của nhóm:
  - đọc theo mô tả (chỉ học tập, nghiên cứu, không thương mại): đồ án tốt nghiệp, đánh giá nội bộ, không thương mại → thỏa;
  - đọc theo metadata CC BY 4.0: được dùng, kể cả sửa, khi ghi công → thỏa.
- Vì vậy nhóm áp dụng **ràng buộc chặt hơn** của hai cách đọc: không thương mại, ghi công. Thêm điều kiện không phân phối lại, dù cả hai cách đọc đều không cấm, để tránh rủi ro khi điều khoản chưa rõ.

## Quyết định [DECISION]
1. FBD-SV-2024 vào `e1-neg-v1` **chỉ ở phần `neg_eval`** (như kế hoạch gốc của ADR-0011). Không dùng để huấn luyện, chọn ngưỡng hay chọn mô hình.
2. Điều kiện sử dụng:
   - chỉ trong đồ án, không thương mại;
   - không phân phối lại video, frame hay nhãn: không đưa vào Git, không đặt trên Drive công khai, không chèn frame gốc vào báo cáo;
   - báo cáo chỉ nêu số đo tổng hợp, báo riêng theo nguồn (ADR-0011 mục 7), trích dẫn bài báo [20] và bản ghi Figshare;
   - lưu bằng chứng license (văn bản mô tả và metadata kèm ngày truy cập) trong `data/manifests/license_evidence/`.
3. Tiền xử lý theo ADR-0013 mục 2: dữ liệu gốc 1280×720, 25 fps → cắt giữa 5:4, resize 640×512, đưa về 30 fps; chạy trên Kaggle; manifest từng clip có SHA-256.
4. `license_matrix.csv`: FBD-SV-2024 chuyển sang `usable` (chỉ đánh giá, không thương mại) khi ADR này Accepted. Trước khi dùng, kiểm MD5 của tệp zip tải về với metadata.
5. Dừng dùng ngay nếu trang dữ liệu hoặc tác giả đổi điều khoản theo hướng không cho phép cách dùng trên. Nếu sau này tìm được email tác giả thì gửi thư xác nhận (bản nháp đã soạn ngày 17/11/2026).

## Hệ quả
- `neg_eval` có thêm nguồn chim bay từ camera giám sát. Đây là loại hard negative quan trọng nhất mà Svanström thiếu: val chỉ có 3 video Bird.
- Khác biệt miền: camera giám sát, 1280×720, 25 fps, khác Svanström. Vì vậy số đo trên FBD-SV báo riêng, không gộp với các nguồn khác.
