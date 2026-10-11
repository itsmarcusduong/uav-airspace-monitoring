# Annotation audit W2 (tự động, toàn bộ 650 video)

Nguồn: `results/W02/kaggle_run_01/w2_outputs_bundle/annotation_audit*.{csv,json}`, `video_inventory.csv`, `class_stats.csv`. Chạy bằng `scripts/kaggle/w2_eda_audit_split.py` (CPU Kaggle, 4 core, Python 3.13, OpenCV 4.14, mcos-decoder 0.1.0; không GPU). Toàn vẹn dữ liệu: 1.303/1.303 file khớp SHA-256 với bản W1 (`checksum_verification.csv`).

## Số liệu đã xác minh
| Mục | Giá trị |
|---|---|
| Video / frame giải mã | 650 / 203.328 (IR 365 @320×256, Visible 285 @640×512; 30 fps) |
| Video theo lớp | Airplane 133, Bird 130, Drone 271, Helicopter 116 |
| bbox ngoài ảnh / w,h ≤ 0 / NaN-malformed | 0 / 0 / 0 |
| Video không có bbox dương | 12 (IR_BIRD_007, IR_BIRD_038, IR_DRONE_143–147, V_BIRD_005, V_BIRD_009, V_DRONE_106, V_DRONE_107, V_HELICOPTER_040) |
| Video có ≥ 1 cảnh báo | 276/650 |
| Số mục nhãn ≠ số frame | **253 video**: 231 video nhiều hơn đúng 1 mục (toàn bộ 114 V-Drone, 40/51 V-Bird, 77/79 IR-Bird); 6 video lệch 1–3 mục (ít hơn); 13 video có nhãn ngắn hơn nhiều (ví dụ V_BIRD_005: 302 frame/1 nhãn; IR_BIRD_027: 319/85); 3 video IR-Drone nhãn dài hơn video (096: +76, 101: +21, 104: +49) |
| Nhảy tâm bbox > 25% chiều rộng giữa 2 frame liên tiếp | 58 video |
| Ghi chú khác | 239 video có chuyển trạng thái có/không bbox; 117 video có bbox lặp y hệt ở frame liền kề; 4 video bbox chạm biên |

## Diễn giải (phân loại rõ)
- **[Kết quả đo]** Lệch +1 mục nhãn tập trung ở 3 nhóm (V-Drone, V-Bird, IR-Bird) → mang tính hệ thống theo nhóm quay/gán nhãn, không phải lỗi ngẫu nhiên.
- **[Suy luận – chưa kiểm chứng]** Mục dư có thể nằm ở đầu hoặc cuối chuỗi. Nếu dư ở đầu thì frame i ↔ nhãn[i+1]; nếu ở cuối thì frame i ↔ nhãn[i]. Với vật thể bay nhanh, lệch 1 frame làm bbox lệch vài pixel — đáng kể với vật thể < 32×32.
- **[Kết quả đo – xem tay 1 sheet]** `IR_AIRPLANE_018` nhảy tâm lớn do **camera dịch chuyển/zoom** giữa các frame (khung hình thay đổi cảnh), không phải nhãn sai. Nghĩa là "camera cố định" không đúng cho toàn bộ dữ liệu. Chưa xem các video khác — cần kiểm tra tay.
- Frame nằm ngoài độ dài nhãn là **chưa gán nhãn (UNKNOWN)**, không được dùng làm ảnh âm tính.

## Quy tắc đề xuất (chờ ADR-0003)
1. Không chuyển YOLO cho 253 video lệch cho tới khi chạy `scripts/kaggle/w2b_label_alignment.py` (chẩn đoán offset: đối chứng 0 mục lệch phải chọn offset 0).
2. Video có nhãn ngắn hơn video: chỉ dùng phần có nhãn; đuôi chưa gán nhãn bị loại.
3. 12 video không bbox: giữ làm âm tính (đã gắn `all_absent=True` trong split).
4. Nhảy tâm lớn: kiểm tra tay trong `review_sheets`; ghi vào `review_assignment.csv`.

## Kiểm tra bằng mắt (review sơ bộ có hỗ trợ công cụ) — 358/358 video
File: `results/W02/review/review_assignment_w2.csv` (cột `review_quang`, `review_quang_notes`, `review_method`). Phương pháp: xem 3 frame/video trên review sheet; **chưa xem video đầy đủ** và chưa có người thứ hai xác nhận.
| Kết quả | Số video |
|---|---|
| OK (thấy vật trong box) | 204 |
| KHONG_RO (vật quá nhỏ/mờ, hoặc video không có bbox) | 144 |
| SAI_NHAN (box trống/lệch, vật nằm ngoài box) | 10 |
SAI_NHAN: IR_BIRD_035, IR_DRONE_096, IR_DRONE_104, V_BIRD_003, 017, 019, 020, 021, 022, 023. Trong 51 video V-Bird có 7 video SAI_NHAN (chim nằm cạnh box) — cùng nhóm với lệch +1 mục nhãn. [INFERENCE] Đây là dấu hiệu nhãn trễ/sớm 1 frame ở V-Bird (chim bay nhanh), chưa phải kết luận. IR_DRONE_096/104 là hai video có nhãn dài hơn video và lệch ở cuối chuỗi. An xác nhận/sửa ở issue W3-01.

## Chẩn đoán căn nhãn bằng độ tương phản (Kaggle run 02)
`results/W02/kaggle_run_02/w2b_outputs_bundle/label_alignment*.{csv,json}`. Nhóm đối chứng (số nhãn = số frame) chỉ chọn offset 0 ở 3–7/25 video mỗi nhóm → **phương pháp không đáng tin, bỏ qua kết quả** (đúng quy tắc đặt trước). Độ tương phản giữa offset −1/0/+1 gần như bằng nhau (ví dụ IR_AIRPLANE_012: 0,2962 / 0,2963 / 0,2957) vì bbox lớn so với dịch chuyển 1 frame.

## Giới hạn
Chưa có xác nhận của người thứ hai. Thuyết minh 8.2 yêu cầu 100% video test và ≥ 10% train do hai thành viên xem chéo — mới đạt mức review sơ bộ.
