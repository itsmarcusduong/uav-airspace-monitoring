# ADR-0013: Thay video tự quay bằng nguồn video công khai có giấy phép; dời tập âm tính sang W8–W9

- Trạng thái: **Proposed** (Quang 16/11/2026). Chuyển **Accepted** khi An duyệt.
- Thay thế ADR-0011 mục 2 (nguồn của `e1-neg-v1`) và mục 8 (lịch quay). Các mục khác của ADR-0011 giữ nguyên: luật kích hoạt (mục 3), luật chọn (mục 4), OOD (mục 5), license (mục 6), báo cáo theo nguồn (mục 7).
- Liên quan: #99 W7-03, ADR-0011, `docs/w7/data_expansion_proposal.md`, `data/manifests/license_matrix.csv`.

## Bối cảnh
- [Quyết định của nhóm, 16/11] Lịch quay W7 (ADR-0011 mục 8) không thực hiện được. Video âm tính tự quay không cần bay drone, nhưng nhóm không chắc chắn về quy định quay gần khu vực sân bay, và W7 đã trễ hạn. Quay video có UAV thì cần giấy phép bay, nằm ngoài khả năng của nhóm.
- [Kết quả đo, W6] Svanström không có ảnh nền trống đáng tin: cả 40 ảnh val không nhãn đều có vật thật (PR #94). Video khả kiến không có Drone chỉ 29,9 phút.
- [DOCUMENT] Đề cương mục 8 cho phép "tập video tự thu hoặc sưu tầm hợp pháp". Thuyết minh mục 13: nếu không đủ 2 giờ âm tính thì công bố thời lượng thực có.

## Nguồn đã kiểm (16/11/2026)
Chỉ ghi điều trang chính thức hoặc nguồn được dẫn nói. Không xác minh được ghi `needs_review`.

| Nguồn | Nội dung [WEB SOURCE] | Giấy phép | Vai trò đề xuất |
|---|---|---|---|
| FBD-SV-2024 | 483 clip chim bay từ camera giám sát, 1280×720, 25 fps, bbox + track ID | figshare ghi "for learning and research purposes only, not for commercial use" (không có tên license); `needs_review` | **Loại khỏi nguồn hiện tại. Không tải hoặc sử dụng** cho tới khi license/điều khoản được rà soát rõ ràng, ghi nhận trong license matrix và được nhóm xem xét lại |
| Wikimedia Commons (video) | Kho media có giấy phép ghi **riêng từng tệp** (CC0, CC BY, CC BY-SA, public domain) | Theo từng tệp; ghi tên tác giả, license, URL vào manifest | Âm tính: bầu trời, máy bay, chim. Chỉ nhận tệp có license tự do ghi rõ |
| Pixabay (video) | Video tự do của người dùng đóng góp | Bản tóm tắt Content License (Quang đọc trang gốc 16/11/2026): được dùng miễn phí, không bắt buộc ghi công, được sửa/chuyển thành tác phẩm mới. Cấm: bán hoặc phân phối nội dung ở dạng "standalone" (giữ gần nguyên như trên web), dùng thương mại nội dung có nhãn hiệu, dùng sai trái hoặc gây hiểu lầm. Bản tóm tắt **không nhắc** tới huấn luyện AI/ML; bài tổng hợp trước đó nói có cho phép, chưa đối chiếu với bản license đầy đủ. Ảnh có người nhận diện được cần thêm đồng ý của bên thứ ba. → `usable` cho đánh giá và dữ liệu âm tính nội bộ, không phân phối lại clip | Âm tính. Không đưa clip hay frame gốc vào Git hay Drive công khai; chỉ dùng clip không có người, logo hay nhãn hiệu |
| Pexels (video) | Video tự do | Cho phép dùng và sửa; không thấy điều khoản về AI/ML; cấm gộp thành dịch vụ cạnh tranh → `needs_review` | Dự phòng |
| UAVDB (Zenodo 14534940) | Ảnh RGB 1080p từ camera mặt đất cố định, UAV rất nhỏ (13–53 px), 18.061 ảnh. Dựng từ bộ multi-view drone tracking của ETH Zurich | Zenodo ghi CC BY 4.0. License của bộ gốc ETH chưa kiểm → `needs_review` | OOD dương tính ở W11, bổ sung cho Anti-UAV300 RGB |
| YouTube, YouTube-8M, AOD 4 (dựng từ YouTube-8M + Anti-UAV + Roboflow) | — | Không rõ hoặc không cho phép | **Loại** |
| LRDDv3 | Quay không đối không (drone quay drone) | CDLA-v2, đang tạm dừng cấp quyền tải | **Loại** (sai góc nhìn) |

## Quyết định [DECISION]
1. **Bỏ video tự quay.** Các nguồn hiện tại cho `e1-neg-v1`, theo thứ tự ưu tiên:
   1. video Wikimedia Commons có license tự do;
   2. video Pixabay (bản tóm tắt license đã kiểm 16/11; chỉ clip không có người, logo, nhãn hiệu);
   3. 21 video val không Drone của Svanström.
   - FBD-SV-2024 không nằm trong danh sách hiện tại và không được tải hoặc dùng trước khi license/điều khoản được rà soát rõ ràng, ghi nhận trong license matrix và nhóm xem xét lại. Việc ghi nhận câu "for learning and research purposes only" không thay cho bước rà soát này.
   - Mục tiêu ≥ 120 phút; nếu thiếu thì báo thời lượng thực có.
   - Pexels chỉ dùng khi ba nguồn hiện tại không đủ.
2. **Chuẩn hóa thành dataset** (W8, Quang). Các bước:
   - manifest từng clip: nguồn, URL, tác giả, license, ngày tải, SHA-256, fps, độ phân giải, thời lượng;
   - hai người cùng sàng lọc bằng mắt, loại clip có vật nghi là UAV, logo/chữ che trời, hoặc cảnh chỉnh sửa (time-lapse, slow-motion);
   - tiền xử lý giống Svanström: cắt giữa tỉ lệ 5:4, resize 640×512, đưa về 30 fps. Giải mã và chuẩn hóa chạy trên Kaggle, không chạy trên máy cá nhân;
   - gán clip vào `neg_train` / `neg_eval` **theo nguồn và theo người đăng** trước khi chạy detector: mọi clip của cùng một tác giả nằm cùng một phần, khoảng 1/4 thời lượng vào `neg_train`. FBD-SV-2024 không thuộc `neg_train` hoặc `neg_eval` khi chưa qua bước rà soát và xem xét lại nêu trên;
   - video không đưa vào Git; Git chỉ giữ manifest, SHA-256 và ghi công tác giả.
3. **Lịch**:
   - W8: tìm nguồn, kiểm license, sàng lọc, manifest, job chuẩn hóa;
   - W9: đo cảnh báo sai/giờ trên `neg_eval` (mô hình hiện tại, theo ADR-0011 mục 7). Nếu chạm điều kiện kích hoạt (ADR-0011 mục 3) thì chạy thí nghiệm `e1-yolo-v1-hn` ngay trong W9, để mô hình được chốt trước W11.
   - Không kịp thì báo thời lượng thực có và bỏ thí nghiệm huấn luyện.
4. **OOD W11**: Anti-UAV300 RGB là tập chính (ADR-0011). UAVDB thay DUT làm tập bổ sung, vì có license CC BY 4.0 ghi rõ trên Zenodo. Chỉ dùng sau khi kiểm license của bộ gốc ETH.
5. **License**: mọi nguồn mới vào `license_matrix.csv` trước khi tải. Clip không có license tự do ghi rõ thì không dùng.

## Hệ quả
- W7 không có tập âm tính ngoài. "Hard negatives" của W7 là phân tích lỗi trên vật thể khó trong val và thí nghiệm hậu xử lý (ADR-0012).
- Thí nghiệm huấn luyện lại với hard negative, nếu có, dời sang W9.
- Mọi con số cảnh báo sai/giờ trước W9 chỉ đo trên 3,7 phút val, nên chỉ có tính chỉ báo.
