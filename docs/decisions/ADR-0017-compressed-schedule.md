# ADR-0017: Rút lịch W10–W14 để hoàn thiện toàn bộ trước 10/12/2026

- Trạng thái: **Proposed** (Quang đề xuất 29/11/2026). Theo yêu cầu tiến độ, ADR áp dụng ngay khi merge; An review được ghi lại cả sau merge (mục 5).
- Liên quan: Đề cương (kế hoạch 14 tuần, mục 10), ADR-0001, ADR-0010, ADR-0011, ADR-0013, ADR-0014; `docs/w10/W10_W14_PLAN.md`.

## Bối cảnh
- [DOCUMENT] Đề cương: 14 tuần, 27/09–31/12/2026; tag bắt buộc ở W4, W8, W11, W14.
- Ngày 29/11/2026, GVHD báo hạn mới: quyển đồ án, demo và release mã nguồn phải **hoàn thiện toàn bộ trước 10/12/2026**. GVHD không nói gì về cách chia báo cáo tuần và tag từ W10.
- Ngày bắt đầu W10 là 30/11, nên còn 10 ngày làm việc (30/11–09/12) cho năm mốc W10–W14.
- Quang quyết định (29/11): **không cắt nội dung**. Giữ Pixabay, giữ mục tiêu ≥ 120 phút âm tính (ADR-0011 mục 2), được thêm detector nếu cần, và mô hình cuối chạy ≥ 3 seed. Cả hai thành viên làm mỗi ngày; việc sau bắt đầu ngay khi việc trước xong.

## Quyết định [DECISION]
1. **Giữ năm milestone `Tuan10`…`Tuan14`**, mỗi milestone là một đợt ngắn:

   | Milestone | Ngày | Mốc theo thang chấm GVHD |
   |---|---|---|
   | Tuan10 | 30/11–02/12 | Đánh giá detection + tracking trên test (cùng hard negative, tập âm tính) |
   | Tuan11 | 03/12–05/12 | Kiểm độ bền, feature freeze, benchmark cố định; **tag `w11`** |
   | Tuan12 | 06/12–07/12 | Hoàn thiện thực nghiệm, ablation, kiểm định thống kê |
   | Tuan13 | 08/12 | Demo rehearsal, hoàn thiện quyển |
   | Tuan14 | 09/12 | Release cuối, **tag `w14`**, nộp |

   - 10/12 không dùng để làm việc; nếu trễ thì đó là ngày dự phòng duy nhất.
   - Mỗi milestone vẫn có issue một sinh viên một kết quả, PR reviewer chéo, `Evidence/WNN/`, hai báo cáo Word → PDF (báo cáo công việc và version đồ án v0.10, v0.11, v0.12, v0.13, v1.0).
   - Tag bắt buộc giữ đúng Đề cương (W11, W14). Các milestone khác ghi commit cuối đợt.
2. **Không cắt nội dung** so với kế hoạch gốc. Thứ tự làm theo phụ thuộc, không theo ngày cố định (mục 3 của kế hoạch).
3. **Luật đặt trước vẫn bắt buộc**: luật chọn mô hình, ngưỡng, ROI và cách đánh giá test được commit trước khi xem kết quả. Không sửa luật sau khi xem kết quả.
4. **Test mở ở W10** sau khi chốt mô hình theo luật trên val (ADR-0003, ADR-0011 mục 4). Mỗi cấu hình chỉ đánh giá test **một lần** cho mỗi câu hỏi đã đăng ký trước; không chọn lại mô hình theo test.
5. **Review của An khi gấp tiến độ:**
   - PR có luật mới hoặc ADR: gửi review request và chờ tối đa **6 giờ** trong ngày. Quá hạn thì Quang merge để không chặn việc sau; An review sau merge và mọi góp ý được xử lý ở PR tiếp theo. Nếu góp ý chỉ ra lỗi trong luật **trước** khi chạy thì sửa luật trước khi chạy; nếu sau khi chạy thì ghi là sai lệch, không đổi kết quả.
   - **Không áp dụng** cho sàng lọc hai người của tập âm tính (giao thức `docs/w9/neg_screening_protocol.md`): vẫn cần hai tệp độc lập. Nếu An không kịp, clip đó chưa được dùng.
6. **Ngân sách GPU Kaggle**: theo dõi quota mỗi ngày trong `docs/w10/W10_W14_PLAN.md`; không chạy hai job cùng lúc khi job sau phụ thuộc job trước.

## Hệ quả
- Khối lượng mỗi ngày lớn; rủi ro chính là GPU queue của Kaggle và thời gian sàng lọc hai người (Commons + Pixabay).
- Báo cáo và version đồ án dựng bằng script như các tuần trước để giữ thời gian.
- Nếu đến 05/12 vẫn chưa đủ 120 phút âm tính sau sàng lọc, báo đúng thời lượng thực có (ADR-0011 mục 2) và nêu là hạn chế; không hạ tiêu chí sàng lọc.

## Còn mở
- GVHD chưa xác nhận cách nộp báo cáo của các milestone rút ngắn. Nếu GVHD yêu cầu khác, sửa ADR này.
