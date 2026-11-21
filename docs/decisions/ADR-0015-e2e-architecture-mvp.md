# ADR-0015: Kiến trúc đầu-cuối của MVP: pipeline lõi, kho sự kiện SQLite, API FastAPI + WebSocket, dashboard phát lại

- Trạng thái: **Accepted** (An duyệt PR #121 ngày 21/11/2026).
  - Quang đề xuất 17/11. Sửa ngày 21/11 theo review của An trên PR #121: sự kiện bất biến, trạng thái suy ra từ review mới nhất, `reviewer_id` chưa xác thực, `config_audit` rõ phạm vi.
  - Sửa tiếp ngày 21/11 theo review của An trên PR #124: `config_audit` thêm đối tượng `detector` và hai cột run cũ/mới; bundle chứa được nhiều run; thêm `GET /config_audit` chỉ đọc. An duyệt các sửa đổi này trên PR #124.
- Liên quan: W8-03, W8-04 (Chương IV 4.1–4.2), ADR-0009 (luật cảnh báo), ADR-0012 (hậu xử lý), Thuyết minh mục 9, 11, 13.

## Bối cảnh
- [DOCUMENT] Đề cương:
  - mục 7 đề xuất FastAPI + WebSocket, dashboard React/Vue, PostgreSQL, Docker;
  - kế hoạch W8: "FastAPI/dashboard streaming", sản phẩm "End-to-end demo".
- [DOCUMENT] Thang chấm W8: "pipeline E2E + dashboard/log". Thuyết minh mục 9:
  - tách suy luận khỏi API;
  - mỗi kết quả gắn `model_version` và thời gian nguồn;
  - người quan sát xác nhận hoặc báo sai cảnh báo;
  - nhật ký thay đổi cấu hình.
- [Quy tắc dự án] Mọi giải mã video và suy luận trên dữ liệu thật chạy trên Kaggle, không chạy trên máy cá nhân.
- [Đã có] Các mô-đun đã đánh giá tách rời:
  - detector YOLO11n;
  - ByteTrack-e1;
  - luật R1 (`scripts/alert/alert_engine.py`);
  - đánh giá offline.

## Quyết định [DECISION]
1. **Pipeline lõi** (`e1pipe`, chạy được từng frame):
   - chuỗi xử lý: `VideoSource` → `Detector` (YOLO11n; NMS theo kết quả run 17) → `Tracker` (ByteTrack-e1) → `AlertEngine` (R1, ADR-0009, không đổi) → `EventStore` + `RunLog`;
   - mỗi frame sinh một bản ghi `FrameResult`: thời gian nguồn, các track, sự kiện mở/đóng, độ trễ từng bước;
   - chế độ **batch** chạy trên Kaggle cho video val và cho demo.
2. **Kho sự kiện SQLite** (MVP, theo Thuyết minh; PostgreSQL là mở rộng). Bảng:
   - `runs`: commit, `model_version` = SHA-256 weights, SHA-256 cấu hình ROI/cảnh báo/tracker, thiết bị;
   - `sources`: video, fps, kích thước; khóa chính **(`run_id`, `source_id`)**, vì cùng một video có thể xuất hiện ở nhiều run (vd. run 14 và run 17);
   - `events`: run, nguồn, thời điểm và frame bắt đầu/kết thúc, loại, ROI, track tham gia, đường dẫn bằng chứng.
     - Đây là **bản ghi bất biến** do pipeline sinh: **không có cột trạng thái**, không UPDATE/DELETE sau khi tạo.
   - `event_reviews`: `review_id` (tự tăng), `event_id`, `reviewer_id`, `action` ∈ {`confirmed`, `false_alarm`}, `created_at`, `note`.
     - **Chỉ thêm**: không UPDATE/DELETE. Muốn đổi kết luận thì thêm review mới.
   - **Trạng thái hiện tại của sự kiện là giá trị suy ra, không lưu**:
     - `new` khi chưa có review;
     - ngược lại là `action` của review có `review_id` lớn nhất. Dùng `review_id` tự tăng làm thứ tự, không dùng `created_at`, vì hai review có thể trùng thời điểm.
     - API trả trạng thái này qua một view SQL `event_status`.
   - `config_audit`: `audit_id`, `actor_id`, `changed_at`, đối tượng cấu hình (ROI, cảnh báo, tracker, **detector**, weights), run cũ và run mới, SHA-256 cũ và mới, lý do. **Chỉ thêm.**
     - Có thêm `detector` vì run 14 và run 17 chỉ khác nhau ở NMS IoU của detector. Thiếu đối tượng này thì lịch sử thay đổi giữa hai run sẽ trống.
     - Ở W8 cấu hình của mỗi run là cố định, ghi trong `runs`. API W8 **không có endpoint sửa cấu hình**, nên bảng này chỉ được ghi khi pipeline tạo run với cấu hình khác run trước.
     - "Run trước" là run thêm gần nhất vào cùng kho sự kiện: `build_bundle.py --append` thêm run mới vào bundle có sẵn. Mỗi đối tượng khác nhau được ghi một dòng, bắt buộc có `--reason`.
     - Endpoint sửa cấu hình (kèm luật hiệu lực và phân quyền) để ở tuần 9 cùng mục 4.4, cần ADR riêng.
   - **Ràng buộc ở mức CSDL**, không chỉ ở code API: trigger SQLite `RAISE(ABORT)` cho mọi UPDATE/DELETE trên `events`, `event_reviews`, `config_audit`; bật `foreign_keys`. Có pytest kiểm rằng UPDATE/DELETE bị từ chối.
   - Track log và `FrameResult` lưu ở JSONL nén, không nằm trong SQLite.
3. **API FastAPI**:
   - REST: `GET /health`, `GET /runs`, `GET /sources?run_id=`, `GET /events?run_id=&source_id=`, `GET /events/{event_id}`, `POST /events/{event_id}/review` (chỉ INSERT), `GET /media/{run_id}/{source_id}` (chỉ nhận ID, không nhận đường dẫn hay URL), `GET /config_audit` (chỉ đọc);
   - WebSocket `/ws/stream?run_id=&source_id=`: phát `FrameResult` theo thời gian nguồn, đúng thứ tự `frame_index`;
   - hợp đồng API công bố bằng OpenAPI do FastAPI sinh, lưu vào repo.
4. **Dashboard** (một trang HTML/JS thuần, FastAPI phục vụ):
   - video kèm lớp vẽ hộp, ID, ROI và dải cảnh báo;
   - danh sách sự kiện có nút xác nhận hoặc báo sai;
   - trạng thái kết nối; báo "kết quả quá hạn" khi luồng WebSocket trễ quá 1 giây.
   - Không dùng React/Vue ở MVP: một trang đủ cho kịch bản kiểm thử, ít phụ thuộc. Đây là điểm lệch so với Đề cương mục 7, ghi nhận ở ADR này.
5. **Hai chế độ chạy**:
   - **phát lại (W8)**: Kaggle chạy pipeline lõi, xuất SQLite + JSONL + video. Máy cá nhân chỉ chạy API và dashboard, phát lại `FrameResult` đúng nhịp thời gian nguồn; không suy luận cục bộ;
   - **trực tiếp** (camera hoặc tệp, suy luận cùng lúc trên GPU): mở rộng; giao diện `FrameResult` giống hệt nên không phải sửa API hay dashboard.
6. **Ranh giới tin cậy**:
   - API chỉ nghe `127.0.0.1`;
   - nguồn video chỉ lấy từ danh sách do quản trị cấu hình, không nhận URL tùy ý;
   - review cảnh báo ghi `reviewer_id` và thời điểm. Ở W8, `reviewer_id` là **định danh cục bộ do người dùng tự nhập, chưa xác thực**. Nó không được coi là danh tính đã xác minh, và báo cáo không dùng nó làm bằng chứng ai đã duyệt;
   - phân quyền tài khoản (Thuyết minh 9.3) để ở tuần 9 cùng mục 4.4.

## Hệ quả
- Demo W8 là đầu-cuối về **luồng dữ liệu**: video → detector → tracker → cảnh báo → lưu → API → dashboard. Bước suy luận chạy trước trên Kaggle. Báo cáo phải ghi rõ điều này, không gọi là "thời gian thực".
- Ở W8, pipeline lõi gồm hai phần: job tracking trên Kaggle (detector + tracker, run 17) và `build_bundle.py` (cảnh báo R1 → kho sự kiện → `FrameResult`), chạy trên track log đã lưu. Gộp thành một lớp `e1pipe` chạy từng frame, có đo `stage_latency_ms`, làm ở W9 cùng benchmark.
- FPS và độ trễ đo ở tuần 9 trên Kaggle bằng chính pipeline lõi; bảng `runs` giữ phần cứng.
- Kiểm thử: pipeline lõi và API có pytest trên dữ liệu tổng hợp. Kịch bản kiểm thử E2E (Thuyết minh 13.3) do An viết trước khi chạy (W8-05).
