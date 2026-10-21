# ADR-0003: Split theo video và chính sách nhãn W2

- Trạng thái: **Proposed**
- Ngày: 11/10/2026

## Bối cảnh
[Kết quả đo] `docs/w2/annotation_audit_w2.md`: 253/650 video có số mục nhãn ≠ số frame (231 video dư đúng 1 mục), 12 video không bbox, 58 video nhảy tâm lớn. `docs/w2/split_protocol.md`: split v1 = 454/98/98 video.
[DOCUMENT] Svanström không có track ID; mỗi frame ≤ 1 bbox.

## Đề xuất [DECISION]
1. **Đơn vị split = video**; không gom cặp IR/V (chưa chứng minh cùng sự kiện). Split v1 = `data/splits/video_split_v1.csv` (seed 20261217), đóng băng khi hai thành viên duyệt và tag commit.
2. **Căn nhãn**: chẩn đoán độ tương phản (run 02) không kết luận được (nhóm đối chứng không chọn offset 0). Quan sát bằng mắt: 7/51 video V-Bird có chim nằm ngoài box. Đề xuất: **loại 231 video dư 1 mục khỏi train/val/test chính** cho tới khi xác định offset (đo IoU liên frame hoặc xem tay), hoặc dùng làm tập riêng; ghi rõ số video bị loại trong báo cáo W3.
3. **Frame không có nhãn do nhãn ngắn hơn video** = UNKNOWN, không dùng làm âm tính.
4. **12 video không bbox**: giữ làm âm tính (`all_absent=True`).
5. **GT tracking**: không báo HOTA/IDF1 trên Svanström. Nếu cần, chỉ dẫn xuất "track đơn" mỗi video (một ID) và ghi rõ giới hạn; ADR riêng trước khi báo bất kỳ số nào. Anti-UAV là ứng viên bổ sung (chưa kiểm license media).
6. Stride lấy mẫu frame cho huấn luyện: quyết ở W3 (đề xuất 5–10 frame, chưa chọn).

> **Cập nhật 13/10/2026:** mục 2 (loại 231 video dư 1 mục) không khả thi: toàn bộ 114 video V-Drone thuộc nhóm này (đối chiếu `annotation_audit.csv` run 01 với split v1), loại đi thì baseline ảnh khả kiến không còn Drone. Mục 2 được thay bằng ADR-0004 (mục 5–6). Mục 6 (stride) chốt trong ADR-0004 (stride 10).

## Rủi ro chấp nhận
Trùng cảnh giữa các split không kiểm soát được (562 cặp video gần giống khác split theo dHash) → ghi trong báo cáo là giới hạn, không tuyên bố "test là cảnh chưa thấy".
