# ADR-0002: Kế hoạch tuần W2–W6 và phạm vi modality

- Trạng thái: **Proposed** (chờ An + Quang + GVHD)
- Ngày: 11/10/2026

## Bối cảnh
[DOCUMENT] Đề cương, Thuyết minh và thang chấm cột E1 mâu thuẫn ở nội dung W2–W6 và tracker (xem `PROJECT_CONTEXT.md` mục 5). [WEB SOURCE/DOCUMENT] Svanström gồm 365 video IR (320×256) và 285 Visible (640×512); Thuyết minh coi Visible là nguồn chính, IR là nhánh riêng.

## Đề xuất [DECISION]
1. Thứ tự ưu tiên: Đề cương > Template > thang chấm E1 > Thuyết minh. W2 = EDA + audit nhãn + split + chuẩn bị baseline; W3 = train baseline; W5 = tích hợp tracker (theo thang chấm). Nếu GVHD xác nhận khác, cập nhật ADR.
2. Tracker: ByteTrack chính, BoT-SORT đối chiếu (thang chấm ghi "DeepSORT" — hỏi GVHD).
3. CSDL: SQLite cho MVP; PostgreSQL là mở rộng.
4. Modality: huấn luyện và báo cáo **riêng từng modality** (V chính, IR riêng); không gộp số liệu hai modality trong một con số duy nhất. Split đã phân tầng theo modality nên cả hai cách đều khả thi.
5. Tên đề tài theo Template/Đề cương.

## Hệ quả
Số liệu W3 trở đi tách V/IR. Nếu GVHD muốn gộp, chỉ cần gộp ở bước huấn luyện, không đổi split.

## Còn mở
Xác nhận của GVHD (chưa có). Không coi ADR này là đã được duyệt.
