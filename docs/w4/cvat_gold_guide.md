# Hướng dẫn tập chuẩn CVAT (issue #24)

Người vẽ: An · Người giữ khóa đáp án và chấm: Quang · Luật kết luận: ADR-0006 (đặt trước).

## 1. Mục đích
Vẽ lại hộp bao **độc lập** trên khoảng 200 frame ảnh khả kiến để:
1. xác định chiều lệch nhãn của video dư một mục (nhãn đúng của frame i là mục i hay mục i + 1);
2. ước lượng chất lượng nhãn gốc (IoU giữa hộp vẽ lại và nhãn gốc).

Frame lấy từ video train và val; **không có ảnh test**. Mỗi frame được chọn sao cho vật thể dịch chuyển ít nhất 2 px giữa hai mục nhãn liên tiếp, nên vẽ chính xác thì phân biệt được hai giả thuyết.

## 2. Quy tắc mù (bắt buộc)
- Gói ảnh `cvat_package.zip` chỉ có ảnh `gold_0001.jpg…` đã xáo trộn, không có tên video, số frame hay nhãn gốc.
- Khóa đáp án `gold_KEY.zip` do Quang giữ, **không đưa vào Git và không gửi An** cho tới khi An đã commit file annotation (mục 5).
- Khi vẽ, An không mở nhãn gốc, review sheet, bảng thăm dò offset hay kết quả run 06.
- Không dùng tính năng tự động (AI tools, auto-annotation, interpolation, tracking) của CVAT.

## 3. Tạo task trên CVAT
1. Đăng nhập https://app.cvat.ai (tài khoản miễn phí).
2. **Projects → +** → tên `E1-gold-W4` → thêm một label tên `object`, kiểu **Rectangle** → **Submit**.
3. Trong project: **Tasks → + Create a new task** → tên `gold_w4` → **Select files**: kéo thả toàn bộ ảnh trong thư mục `images/` của `cvat_package.zip` (giải nén trước) → **Submit & Open**.
4. Mở job của task (**Job #…**).

## 4. Quy tắc vẽ
| Tình huống | Cách làm |
|---|---|
| Thấy vật thể bay | Vẽ **đúng 1** hình chữ nhật sát mép ngoài của vật (gồm cánh, cánh quạt, càng), không chừa nền |
| Vật rất nhỏ | Phóng to (cuộn chuột) tới khi thấy rõ từng pixel rồi mới vẽ; sửa bằng cách kéo 4 cạnh |
| Vật bị mờ, nhòe chuyển động | Bao phần nhòe nhìn thấy được |
| Vật bị cắt ở mép ảnh | Chỉ bao phần nằm trong ảnh |
| Có nhiều vật | Chỉ vẽ vật lớn hoặc rõ nhất; ghi `gold_XXXX` vào ghi chú (mục 6) |
| Không thấy vật nào / không chắc | **Không vẽ** (để trống ảnh); ghi `gold_XXXX` vào ghi chú |

Phím tắt: `N` vẽ hình mới, `F` / `D` ảnh sau / trước, `Ctrl+S` lưu. Lưu sau mỗi 20 ảnh.

## 5. Xuất và nộp
1. Vẽ xong → **Menu → Finish the job**.
2. Trang task → **Actions → Export task dataset** → định dạng **YOLO 1.1**, *Save images* **tắt** → tải file zip về.
3. Đổi tên `cvat_gold_an_YYYYMMDD.zip` → commit vào `results/W04/cvat_gold/` trên nhánh `issue-24-cvat-annotations`, PR title `W4-01: annotation tập chuẩn CVAT (#24)`, reviewer Quang.
4. Sau khi commit đã có trên GitHub, Quang mới thêm khóa đáp án và chạy:
   ```
   python scripts/dataset/score_cvat_gold.py --annotations results/W04/cvat_gold/cvat_gold_an_YYYYMMDD.zip --key <gold_KEY.zip> --out results/W04/cvat_gold
   ```
   Thứ tự commit (annotation trước, khóa sau) là bằng chứng việc vẽ là mù.

## 6. Ghi chú kèm theo
Tạo `results/W04/cvat_gold/notes_an.md`: thời gian vẽ (phút), danh sách ảnh không vẽ hoặc không chắc, khó khăn gặp phải. Không ghi đoán về offset.

## 7. Kiểm tra thủ công review v2 (phần còn lại của #24)
Sau khi vẽ xong: mở `results/W03/review/review_assignment_w3.csv`, với 40 video ngẫu nhiên (seed 20261022) điền cột `verdict` (OK / SAI_NHAN / KHONG_RO) và `notes` theo cùng quy tắc review v2; Quang tính tỷ lệ đồng ý với `review_quang_v2`.
