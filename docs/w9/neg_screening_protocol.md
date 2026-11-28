# Sàng lọc clip âm tính công khai (W9-03 #131, W9-04 #132), viết trước khi lập manifest

Áp dụng ADR-0013 và W9_PLAN mục D. Bản đầu viết 24/11/2026. Bản này sửa ngày 28/11/2026 theo review của An trên PR #138, **vẫn trước** khi có danh sách ứng viên. Không sửa sau khi đã xem danh sách hay kết quả detector.

| Sửa so với bản 24/11 | Căn cứ |
|---|---|
| Loại clip có người, logo, chữ hoặc watermark; loại cảnh chỉnh sửa (time-lapse, slow-motion, ghép đoạn); bỏ category time-lapse | W9_PLAN mục D; ADR-0013 mục 2 |
| Mỗi người sàng lọc trên một tệp riêng; chỉ gộp khi cả hai đã xong | Review của An |
| Khóa tác giả chuẩn hóa; tác giả trống hoặc không rõ → `needs_review`; nhóm tác giả gộp cả theo người tải lên; finalize báo lỗi nếu thiếu một split | Review của An |
| Tỷ lệ `neg_train` khoảng 1/4 thời lượng, không phải 1/2 | ADR-0013 mục 2. Bản 24/11 chia theo chẵn/lẻ của hash nên cho khoảng 1/2, sai với ADR |

## 1. Lập danh sách ứng viên (Quang)
- Chạy `python scripts/dataset/commons_manifest.py --out data/manifests/neg_commons_candidates.csv` trên máy có Internet.
- Script đọc trực tiếp Commons API (`commons.wikimedia.org/w/api.php`), không qua bản sao. Category: chim bay, đàn chim, máy bay cất và hạ cánh, mây. Không có category time-lapse; script từ chối category có chữ time-lapse hay slow-motion.
- Chỉ giữ tệp video thỏa cả năm điều kiện:
  - giấy phép CC0, Public domain, CC BY hoặc CC BY-SA;
  - dài ≥ 10 giây;
  - rộng ≥ 640 px;
  - tên tệp không gợi ý drone hay quay từ trên không;
  - tên tệp không gợi ý cảnh chỉnh sửa (time-lapse, hyperlapse, slow-motion, montage, compilation).
- Manifest ghi tác giả, người tải lên, khóa tác giả, giấy phép, URL trang, SHA-1 của Commons. SHA-256 tính khi tải trên Kaggle.
- Script tạo thêm **hai tệp sàng lọc riêng**, cùng thư mục:
  - `neg_commons_screen_quang.csv`;
  - `neg_commons_screen_an.csv`.
  Mỗi tệp chỉ có `title`, `page`, `screen`, `screen_note`, và chỉ gồm clip có khóa tác giả rõ (mục 3).
- Pixabay (ADR-0013) chưa đưa vào W9: không có API công khai không cần khóa. Nếu còn thời gian thì lập riêng, theo cùng cách.

## 2. Sàng lọc độc lập (Quang và An, mỗi người một tệp)
Mở trang Commons của từng clip (cột `page`) và xem trên trình duyệt. Không tải video về máy.

Điền `keep` khi clip thỏa **cả** năm điều kiện:
1. camera ở mặt đất hoặc vị trí cố định, nhìn lên trời hoặc ra xa; không phải quay từ máy bay hay drone;
2. không thấy drone hay vật nghi là UAV ở bất kỳ đoạn nào;
3. phần lớn khung hình là trời, có thể có chim, máy bay, mây; không phải cảnh trong nhà;
4. **không có người**, và **không có logo, chữ, watermark hay phụ đề** ở bất kỳ đoạn nào;
5. **không phải cảnh đã chỉnh sửa**: time-lapse, slow-motion, ghép nhiều đoạn, chèn hiệu ứng.

Ngược lại điền `reject` và **bắt buộc** ghi lý do ngắn vào `screen_note`, ví dụ "có người", "logo góc phải", "time-lapse".

**Độc lập:**
- Mỗi người chỉ mở tệp của mình.
- Không gửi, không commit tệp của mình trước khi người kia báo đã xong.
- Hai tệp được đưa vào repo cùng lúc, trong cùng một PR.
- Không trao đổi về từng clip trong lúc sàng lọc.

**Luật gộp:** chỉ giữ clip khi **cả hai** người đều điền `keep`. Bất đồng thì loại, không thảo luận để đổi. Báo tỷ lệ đồng ý và Cohen's κ.

## 3. Khóa tác giả và gán neg_train / neg_eval (trước khi chạy detector)
**Khóa tác giả** (`author_key`), tính bằng script từ trường Artist của Commons:
- Nếu Artist có liên kết tới đúng một tài khoản `User:` thì khóa là `user:<tên tài khoản>`.
- Nếu không có liên kết, khóa là `name:<tên>`. Tên được chuẩn hóa: NFKC, chữ thường, bỏ dấu câu, gộp khoảng trắng, bỏ cụm "own work".
- Các trường hợp `needs_review`: Artist trống, không rõ ("unknown", "anonymous"…), hoặc trỏ tới nhiều tài khoản khác nhau.
  - Clip `needs_review` không vào tệp sàng lọc và không vào `neg_commons_v1` ở W9.
  - Số clip loại vì lý do này được báo trong thống kê.

**Nhóm tác giả:**
- Hai clip cùng nhóm nếu có cùng khóa tác giả **hoặc** cùng người tải lên. Quan hệ này có tính bắc cầu, để bắt trường hợp một người dùng nhiều cách ghi tên.
- Mọi clip của một nhóm nằm cùng một split.

**Gán split** (bằng script; ghi vào cột `split`; không đổi sau đó):
1. Sắp các nhóm theo SHA-256 của khóa nhóm.
2. Lần lượt đưa nhóm vào `neg_train` cho tới khi tổng thời lượng `neg_train` đạt 25% tổng thời lượng các clip được giữ.
3. Các nhóm còn lại vào `neg_eval`.
- Cách gán chỉ dùng khóa tác giả và thời lượng, không dùng kết quả detector.
- `finalize` báo lỗi và không ghi manifest khi:
  - một trong hai split rỗng;
  - một nhóm nằm ở cả hai split;
  - tệp sàng lọc thiếu, thừa hoặc trùng clip;
  - còn ô `screen` trống;
  - có `reject` mà không ghi lý do.
- W9 chỉ đo trên `neg_eval`. `neg_train` để dành cho thí nghiệm hard negative ở W10 (ADR-0011 mục 3).

Lệnh gộp, chạy sau khi cả hai tệp đã xong:

```
python scripts/dataset/commons_manifest.py --finalize data/manifests/neg_commons_candidates.csv \
    --screen-quang data/manifests/neg_commons_screen_quang.csv \
    --screen-an data/manifests/neg_commons_screen_an.csv \
    --out data/manifests/neg_commons_v1.csv
```

Kết quả gồm `neg_commons_v1.csv` và `neg_commons_v1.json`. Tệp json ghi số clip, số nhóm, số phút theo split, tỷ lệ đồng ý, κ, và SHA-256 của ba tệp đầu vào.

## 4. Chuẩn hóa và đo
- Giống FBD-SV (W9_PLAN mục D): job Kaggle tải bằng URL trong manifest, kiểm SHA-1 với Commons, tính SHA-256, cắt giữa 5:4, 640×512, 30 fps, đo bằng `e1pipe` cấu hình C0.
- Báo riêng nguồn `wikimedia_commons`, không gộp với FBD-SV.
- Nếu tổng thời lượng `neg_eval` của mọi nguồn < 120 phút thì báo đúng thời lượng thực có (W9_PLAN mục D).
