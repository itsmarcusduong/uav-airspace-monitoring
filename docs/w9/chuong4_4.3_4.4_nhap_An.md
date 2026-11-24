# Chương IV. Thiết kế hệ thống — bản nháp mục 4.3–4.4

**Trạng thái:** Bản nháp ngày 24/11/2026. Mục 4.3 mô tả pipeline và luật đã có; kết quả benchmark W9 và số đo tập âm tính sẽ được bổ sung sau khi các run được duyệt, thực hiện và kiểm tra. Không dùng số liệu dự kiến thay cho kết quả đo.

## 4.3. Các mô-đun trí tuệ nhân tạo

Hệ thống xử lý video theo từng frame, theo thứ tự: giải mã, phát hiện đối tượng, theo vết, phát hiện sự kiện và lưu kết quả. Các mô-đun được ghép thành pipeline `e1pipe`; cùng một luồng dữ liệu được dùng cho suy luận trên Kaggle và cho phép đo thời gian từng công đoạn. Mỗi run gắn với commit, SHA-256 của weights và cấu hình để có thể truy nguyên đầu vào.

| Mô-đun | Chức năng | Đầu vào và đầu ra |
|---|---|---|
| Giải mã và tiền xử lý | Đọc tuần tự các frame từ video, giữ thứ tự và thời gian nguồn. Bộ benchmark dùng đầu vào cố định từ manifest; phép đo tập âm tính chuẩn hóa video theo ADR-0013. | Video và metadata → frame BGR, chỉ số frame, thời gian nguồn. |
| Phát hiện đối tượng | YOLO11n nhận diện Airplane, Bird, Drone và Helicopter. Cấu hình mốc C0 dùng PyTorch fp32, batch 1, `imgsz=640`, ngưỡng phát hiện 0,1 và NMS cùng lớp IoU 0,5. Ngưỡng 0,25 được dùng riêng cho phép đánh giá detection, không thay cho ngưỡng suy luận. | Frame → hộp giới hạn, lớp và độ tin cậy. |
| Theo vết | BYTETracker gán và duy trì ID cho các đối tượng qua các frame, theo `configs/tracker_bytetrack_e1.yaml`. | Detection theo frame → track có ID, lớp và hộp giới hạn. |
| Cảnh báo | AlertEngine áp dụng luật R1 theo track: tích lũy bằng chứng để xác nhận đối tượng, kiểm tra vùng quan tâm và thời gian hiện diện, sau đó mở, nối lại hoặc đóng sự kiện. Engine xử lý trực tuyến từng frame; hàm đánh giá dữ liệu đã lưu gọi cùng engine để giữ nhất quán giữa hai cách chạy. | Track theo frame và ROI → sự kiện R1 cùng các chuyển trạng thái. |
| Lưu trữ và đo lường | Mỗi `FrameResult` ghi thời gian nguồn, track, chuyển trạng thái và độ trễ theo công đoạn. Sự kiện đã chốt được ghi vào SQLite; dữ liệu frame lưu dạng JSONL nén. | Kết quả từng frame → bundle có thể kiểm tra và phát lại. |

`stage_latency_ms` trong `FrameResult` có `latency_scope=pre_write`, tức phép đo kết thúc trước khi ghi chính dòng đó. Chỉ số trong `latency.csv` của benchmark tính `total` và `persist` sau khi ghi xong dòng, theo W9_PLAN mục B; các số p95 dùng cho luật C và NFR1 lấy từ phạm vi benchmark này.

W9 so sánh bốn cấu hình: C0 (PyTorch fp32), C1 (PyTorch fp16), C2 (TensorRT fp16) và CPU (PyTorch fp32). C0 là mốc đối chiếu; CPU chỉ dùng để báo cáo. Cấu hình vận hành chỉ được chọn nếu đạt ngưỡng hiệu năng đã định trước và không vượt các giới hạn suy giảm độ chính xác trong W9_PLAN. Nếu C2 cần đệm đầu vào 640×640 khác với PyTorch, khác biệt tiền xử lý này được ghi nhận; vì vậy chênh lệch C2–C1 không được diễn giải như tác động thuần túy của runtime.

**Kết quả W9:** Chưa điền. Bổ sung cấu hình được chọn, FPS, p50/p95 độ trễ, kết quả kiểm tra độ chính xác và chạy ổn định sau khi hoàn tất các run được duyệt. Mọi kết quả được báo theo tập dữ liệu và cấu hình; tập val dùng để đánh giá không đồng nghĩa với dữ liệu triển khai thực tế.

## 4.4. Bảo mật, quyền riêng tư và rủi ro

### Ranh giới dữ liệu và quyền truy cập

Video nguồn và weights được xử lý trong môi trường Kaggle theo quy trình của dự án. Không đưa video, frame hoặc nhãn của FBD-SV-2024 vào Git hay artifact công khai; bằng chứng dùng cho báo cáo chỉ gồm số liệu tổng hợp và mã định danh clip. Nguồn Wikimedia Commons phải được ghi nhận theo giấy phép của từng tệp. Với FBD-SV-2024, nhóm áp dụng điều kiện thận trọng đã nêu trong ADR-0014: chỉ đánh giá trong phạm vi đồ án, không thương mại và không phân phối lại video, frame hoặc nhãn.

API phát lại W8 chỉ bind vào `127.0.0.1`, và media được phân giải từ danh sách nguồn trong bundle thay vì nhận đường dẫn hoặc URL tùy ý từ client. Đây là giới hạn phạm vi truy cập cho bản demo cục bộ, không phải cơ chế xác thực. Hệ thống hiện chưa có tài khoản, xác thực người dùng hay phân quyền; `reviewer_id` do người dùng nhập chỉ là định danh cục bộ, không chứng minh danh tính. Vì vậy không triển khai API ra mạng dùng chung hoặc xem nhật ký review là bằng chứng kiểm toán danh tính.

### Tính toàn vẹn và lưu vết

Manifest, SHA-256 của video/weights/cấu hình và commit được dùng để phát hiện đầu vào hoặc mã nguồn không khớp. Sự kiện pipeline là bản ghi bất biến; thao tác xác nhận hoặc báo sai được lưu thành bản ghi review mới, không ghi đè sự kiện gốc. Bundle có thể chứa đường dẫn media cục bộ nên chỉ chia sẻ theo quy trình có kiểm soát và không đưa lên nơi công khai nếu còn dữ liệu bị giới hạn.

### Rủi ro và biện pháp giảm thiểu

| Rủi ro | Tác động | Biện pháp và giới hạn còn lại |
|---|---|---|
| Sai lệch miền dữ liệu | Cảnh báo sai hoặc bỏ sót có thể thay đổi theo camera, nền, kích thước vật thể và điều kiện ghi hình. | Báo cáo riêng theo nguồn, không gộp các tập khác miền; nêu rõ thời lượng thực đo và không suy rộng từ tập val sang vận hành. |
| Chuẩn hóa 25 fps lên 30 fps | Lặp frame có thể làm thay đổi đầu ra detector/tracker và hành vi theo frame, dù thời lượng clip được giữ gần với nguồn. | Giữ đúng tiền xử lý ADR-0013 để bảo đảm cùng giao thức; ghi fps nguồn/đích và diễn giải đây là giới hạn của phép đo, không xem như video gốc 30 fps. |
| Giới hạn hiệu năng hoặc tăng bộ nhớ | Không đạt yêu cầu FPS/độ trễ hoặc phát sinh lỗi trong thời gian chạy dài. | Đo từng công đoạn, lặp benchmark theo giao thức W9 và chạy ổn định 60 phút; nếu không cấu hình nào qua cổng độ chính xác thì giữ C0, đồng thời báo NFR1 không đạt nếu C0 không qua ngưỡng hiệu năng. |
| Cảnh báo giả trên tập âm tính | Làm giảm độ tin cậy của cảnh báo khi có chim hoặc vật thể khó. | Đo R0/R1 và cảnh báo sai trên từng nguồn; sàng lọc độc lập clip công khai trước khi đưa vào đánh giá. Theo W9_PLAN, loại clip có drone, người hoặc logo; loại cảnh time-lapse, slow-motion hoặc chỉnh sửa. Số liệu chỉ đại diện cho các clip đã sàng lọc. |
| Lộ dữ liệu hoặc sử dụng sai giấy phép | Có thể tiết lộ hình ảnh/nhãn hoặc vi phạm điều kiện nguồn dữ liệu. | Giữ dữ liệu bị giới hạn trong môi trường được phép, không phân phối lại; lưu giấy phép, nguồn, tác giả và hash trong manifest. Không lưu video/frame trong bằng chứng công khai. |
| Truy cập trái phép vào API hoặc giả mạo người review | Review có thể bị ghi bởi người không được xác minh nếu API bị mở rộng khỏi máy cá nhân. | Chỉ bind loopback trong MVP và không tuyên bố có xác thực. Trước khi dùng qua mạng cần thiết kế riêng xác thực, phân quyền và bảo vệ kênh truyền. |

Các biện pháp trên giảm rủi ro cho quy trình thí nghiệm và demo cục bộ, nhưng không biến hệ thống thành dịch vụ an ninh vận hành. Kết quả cảnh báo cần có người xem xét; các ngưỡng, dữ liệu và cấu hình được đánh giá trong W9 chưa chứng minh độ an toàn cho quyết định tự động hoặc môi trường thực tế.

### Tài liệu liên quan

- ADR-0013, *Thay video tự quay bằng nguồn video công khai có giấy phép; dời tập âm tính sang W8–W9*.
- ADR-0014, *Đưa lại FBD-SV-2024 vào tập âm tính, chỉ để đánh giá*.
- ADR-0015, *Kiến trúc đầu-cuối của MVP*.
- W9_PLAN, mục B–E (sau khi được duyệt).
