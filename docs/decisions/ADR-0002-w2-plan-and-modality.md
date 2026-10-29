# ADR-0002: Kế hoạch tuần W2–W6 và phạm vi modality

- Trạng thái: **Accepted** (An 26/10, Quang 27/10); mục 1–2 **Superseded by ADR-0005**; GVHD: chờ xác nhận qua #7 (ADR-0005).
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
Chờ GVHD xác nhận qua #7 (chưa có tới 29/10/2026).

## Review (26/10/2026)
**Người review:** Lê Ngọc An

- Mục 1: Superseded by ADR-0005 (mục 1–2). Thứ tự tuần hiện hành là W4 tuning + augmentation, W5 tích hợp tracker, W6 geofence + cảnh báo.
- Mục 2: Superseded by ADR-0005 (mục 1–2). ADR-0005 chọn ByteTrack làm tracker chính và BoT-SORT đối chiếu.
- Mục 3: **Accepted** — giữ SQLite cho MVP và PostgreSQL làm hướng mở rộng; ADR-0004, ADR-0005 và giao thức split hiện hành không đưa ra quyết định CSDL mâu thuẫn.
- Mục 4: **Accepted** — nhất quán với ADR-0005 mục 2: Visible là nhánh chính, IR là thí nghiệm phụ và báo cáo riêng, không gộp số liệu.
- Mục 5: Giữ nguyên; ADR-0004 và ADR-0005 không thay đổi quyết định về tên đề tài.

Duyệt: Lê Ngọc An, 2026-10-26
