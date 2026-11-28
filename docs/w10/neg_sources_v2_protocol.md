# Nguồn âm tính bổ sung W10: Wikimedia Commons v2 và AirBirds (viết trước khi lập danh sách và trước khi tải)

ADR-0018. Viết 29/11/2026, trước khi có danh sách Commons v2, trước khi có link tải AirBirds và trước khi chạy detector trên hai nguồn này. Không sửa sau khi đã xem danh sách hay kết quả detector; sai lệch (nếu có) ghi ở mục 6.

## 1. Vì sao thêm nguồn
- Mục tiêu `neg_eval` ≥ 120 phút (ADR-0011 mục 2). Đã có: FBD-SV 19,13 phút, val Svanström không Drone 3,7 phút; test không Drone cộng ở W10; Commons v1 chờ gộp.
- Pixabay và Pexels: Terms of Service cấm thu thập tự động cho học máy và sao chép có hệ thống nếu chưa được phép (`data/manifests/license_evidence/pixabay_pexels_terms_2026-11-29.md`). Quang đã gửi email xin phép Pixabay ngày 29/11. **Không dùng** cho tới khi có văn bản cho phép; nếu có thì viết phụ lục riêng.

## 2. Wikimedia Commons v2
- Giao thức sàng lọc, khóa tác giả, gộp và chia split **giữ nguyên** `docs/w9/neg_screening_protocol.md` (mục 1–3).
- Khác v1:
  - category cha: `CATEGORIES_V2` trong `scripts/dataset/commons_manifest.py` (chim bay, đàn chim, chim, mòng biển, máy bay, máy bay cất/hạ cánh, máy bay dân dụng, trực thăng, mây, bầu trời);
  - thêm subcategory **một cấp**; bỏ subcategory có tên gợi ý drone, quay từ trên không, cảnh chỉnh sửa, mô hình/đồ chơi, trong nhà, sở thú (`SUBCAT_EXCLUDE`);
  - bỏ mọi tệp đã có trong `neg_commons_candidates.csv` (v1);
  - trần **330 phút** ứng viên, chọn tất định theo SHA-256 của tên tệp (khoảng 4–5 giờ sàng lọc mỗi người), không dùng nội dung hay kết quả detector.
- Lệnh (máy có Internet):
  ```
  python scripts/dataset/commons_manifest.py --v2 --exclude data/manifests/neg_commons_candidates.csv \
      --out data/manifests/neg_commons_v2_candidates.csv
  ```
- Gộp: `--finalize` như v1, ra `neg_commons_v2.csv`. Commons v1 và v2 báo chung nguồn `wikimedia_commons`, nhưng ghi rõ phiên bản. Một tác giả không được nằm ở hai split: nhóm tác giả v2 nào trùng (cùng khóa tác giả hoặc cùng người tải lên) với một nhóm đã chia ở `neg_commons_v1.csv` thì theo split của v1; các nhóm còn lại chia theo luật 25% thời lượng trên phần v2 (`--finalize ... --prior data/manifests/neg_commons_v1.csv`, cài ở W10 trước khi gộp v2).

## 3. AirBirds (Sun và cộng sự, ACCV 2022)
**Nguồn và giấy phép** [WEB SOURCE, truy cập 29/11/2026]:
- Trang dataset `airbirdsdata.github.io`: 118.312 ảnh 1920×1080 từ mạng camera đặt dọc đường băng một sân bay thật, chụp 9/2020–8/2021; 409.967 hộp chim có nhãn; chim trung bình nhỏ hơn 10 px.
- Bài báo (arXiv 2304.11662): video gốc 25 fps; nhóm tác giả chọn các đoạn có chim rồi lấy 1 frame trên 5 frame liên tiếp, giữ thứ tự thời gian trong mỗi chuỗi → chuỗi tương đương **5 fps**.
- Giấy phép theo trang dataset: chỉ dùng cho nghiên cứu và giáo dục phi thương mại, CC BY-NC-SA 4.0. Đồ án phi thương mại, không phân phối lại dữ liệu → dùng được. Đối chiếu tệp LICENSE của repo trước khi tải; nếu khác thì dừng và ghi lại.
- Tải: Quang điền form 29/11; form chỉ dẫn người dùng ngoài Trung Quốc tải từ Hugging Face `huggingface.co/datasets/auniquesun/AirBirds` (không cần đăng ký thêm). Dataset card ghi license `cc-by-nc-sa-4.0` và "for non-commercial research and educational use only" (truy cập 29/11/2026).
- Tệp trên Hugging Face: `images0.zip`…`images9.zip` (11,7–21,7 GB mỗi tệp; tổng khoảng 176 GB gồm cả test), `labels0.zip`…`labels9.zip` (nhãn YOLO, một tệp mỗi ảnh, lớp 0 = chim, tệp rỗng = không có chim), hai cặp tệp test `*_test_D02_*`. Ghi commit/revision của repo Hugging Face vào manifest khi tải.

**Dùng thế nào:**
- **Chỉ `neg_eval`**, không vào `neg_train`. Lý do: ảnh có chim được gán nhãn; dùng làm ảnh nền nhãn rỗng sẽ dạy detector coi chim là nền, mâu thuẫn với lớp Bird của Svanström.
- Phần dùng: các phần có nhãn (images0–9), **theo thứ tự chỉ số tăng dần** (images0, images1, …) cho tới khi tổng `neg_eval` mọi nguồn đạt 120 phút hoặc hết ngân sách GPU/dung lượng; không chọn theo nội dung. Job Kaggle đọc ảnh trực tiếp trong zip (không giải nén toàn bộ), xử lý từng phần rồi xóa. Ước lượng thô: khoảng 10 nghìn ảnh mỗi phần, tức khoảng 33 phút ở 5 fps [INFERENCE: 118.312 ảnh / 12 phần].
- Chuỗi: tách theo camera và thời gian trong tên tệp; khoảng cách giữa hai ảnh liên tiếp lớn hơn 1 giây thì bắt đầu chuỗi mới. Quy tắc đọc tên tệp được viết vào script sau khi xem **cấu trúc thư mục và tên tệp**, trước khi chạy detector.
- Chuẩn hóa: cắt giữa 5:4, resize 640×512, **giữ 5 fps** (không nội suy frame). Thời lượng = số frame / 5.
- Pipeline: e1pipe cấu hình đã chọn ở W9 (luật C), ROI `center_hex`, R0/R1, **không đổi tham số** (ByteTrack-e1 `track_buffer` tính theo frame nên ở 5 fps tương đương thời gian dài hơn 6 lần; ghi là giới hạn, không chỉnh).
- Sàng lọc hai người, độc lập, trên mẫu: với mỗi chuỗi, xem ảnh đầu, giữa, cuối; `reject` cả chuỗi nếu thấy drone hay vật nghi UAV, hoặc ảnh hỏng. Chỉ giữ chuỗi cả hai người cùng `keep`. Tệp: `neg_airbirds_screen_quang.csv`, `neg_airbirds_screen_an.csv`.
- Báo riêng nguồn `airbirds` (ADR-0011 mục 7): cảnh báo sai/giờ, cận trên Poisson 95%, tỷ lệ frame có detection Drone; thêm số hộp chim có nhãn bị detector gọi là Drone (IoU ≥ 0,3), là phép đo hard negative trực tiếp.

## 4. DVIDS (dự phòng)
- Chỉ dùng nếu sau Commons v2 và AirBirds tổng `neg_eval` vẫn dưới 120 phút. Khi đó viết phụ lục riêng (xử lý gói B-roll ghép nhiều cảnh, phù hiệu, câu miễn trừ của Bộ Quốc phòng Mỹ).

## 5. Rủi ro đã biết trước
- `neg_train` (từ Commons) chứa clip có chim với nhãn rỗng. Luật ADR-0011 mục 4 giữ nguyên; báo thêm AP lớp Bird trên val của v1 và `-hn` (chỉ báo cáo, không phải điều kiện chọn).
- AirBirds 5 fps và chim rất nhỏ sau khi resize: cảnh báo sai/giờ của nguồn này không so trực tiếp được với nguồn 30 fps.

## 6. Sai lệch so với giao thức
(chưa có)
