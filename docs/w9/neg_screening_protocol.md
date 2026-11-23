# Sàng lọc clip âm tính công khai (W9-03 #131, W9-04 #132), viết trước khi lập manifest

Áp dụng ADR-0013 và W9_PLAN mục D. Viết ngày 24/11/2026, **trước** khi có danh sách ứng viên. Không sửa sau khi đã xem kết quả detector.

## 1. Lập danh sách ứng viên (Quang)
- Chạy `python scripts/dataset/commons_manifest.py --out data/manifests/neg_commons_candidates.csv` trên máy có Internet.
- Script đọc trực tiếp Commons API (`commons.wikimedia.org/w/api.php`), không qua bản sao.
- Chỉ giữ tệp video thỏa cả bốn điều kiện:
  - giấy phép CC0, Public domain, CC BY hoặc CC BY-SA;
  - dài ≥ 10 giây;
  - rộng ≥ 640 px;
  - tên tệp không gợi ý drone hay quay từ trên không.
- Manifest ghi tác giả, giấy phép, URL trang, SHA-1 của Commons. SHA-256 tính khi tải trên Kaggle.
- Pixabay (ADR-0013) chưa đưa vào W9: không có API công khai không cần khóa. Nếu còn thời gian thì lập riêng, theo cùng cách.

## 2. Sàng lọc độc lập (Quang và An, mỗi người một cột, không xem cột của người kia)
Mở trang Commons của từng clip (cột `page`), không tải video về máy.

Điền `keep` khi clip thỏa **cả** ba điều kiện:
1. camera ở mặt đất hoặc vị trí cố định, nhìn lên trời hoặc ra xa (không phải quay từ máy bay hay drone);
2. không thấy drone hay UAV ở bất kỳ đoạn nào;
3. phần lớn khung hình là trời, có thể có chim, máy bay, mây; không phải cảnh trong nhà.

Ngược lại điền `reject`, ghi lý do ngắn vào `screen_note`. Clip có người, biển số hay logo vẫn giữ được, vì Commons có giấy phép tự do và báo cáo không chèn frame.

**Luật gộp:** chỉ giữ clip khi **cả hai** người đều điền `keep`. Bất đồng thì loại, không thảo luận để đổi.

## 3. Gán neg_train / neg_eval (trước khi chạy detector)
- Theo người đăng (cột `artist`), để clip của cùng một tác giả không nằm ở cả hai tập.
- `neg_eval` nếu chữ số hex cuối của SHA-256(`artist`) là chẵn, ngược lại `neg_train`.
- Gán bằng script, ghi vào cột `split`; không đổi sau đó.
- W9 chỉ đo trên `neg_eval`. `neg_train` để dành cho thí nghiệm hard negative ở W10 (ADR-0011 mục 3).

## 4. Chuẩn hóa và đo
- Giống FBD-SV (W9_PLAN mục D): job Kaggle tải bằng URL trong manifest, kiểm SHA-1 với Commons, tính SHA-256, cắt giữa 5:4, 640×512, 30 fps, đo bằng `e1pipe` cấu hình C0.
- Báo riêng nguồn `wikimedia_commons`, không gộp với FBD-SV.
