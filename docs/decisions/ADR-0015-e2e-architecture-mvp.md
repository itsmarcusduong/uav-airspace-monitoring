# ADR-0015: Kiến trúc đầu-cuối của MVP: pipeline lõi, kho sự kiện SQLite, API FastAPI + WebSocket, dashboard phát lại

- Trạng thái: **Proposed** (Quang 17/11/2026). Chuyển **Accepted** khi An duyệt trên PR. Code W8-03 chỉ merge sau khi ADR này Accepted.
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
   - `sources`: video, fps, kích thước;
   - `events`: run, nguồn, thời điểm và frame bắt đầu/kết thúc, loại, ROI, track tham gia, đường dẫn bằng chứng, trạng thái `new`/`confirmed`/`false_alarm`;
   - `event_reviews`: ai, khi nào, hành động; chỉ thêm, không sửa;
   - `config_audit`: chỉ thêm.
   - Track log và `FrameResult` lưu ở JSONL nén, không nằm trong SQLite.
3. **API FastAPI**:
   - REST: `GET /health`, `GET /runs`, `GET /sources`, `GET /events`, `GET /events/{id}`, `POST /events/{id}/review`, `GET /media/{source}`;
   - WebSocket `/ws/stream?run=&source=`: phát `FrameResult` theo thời gian nguồn;
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
   - review cảnh báo ghi người dùng và thời điểm;
   - phân quyền tài khoản (Thuyết minh 9.3) để ở tuần 9 cùng mục 4.4.

## Hệ quả
- Demo W8 là đầu-cuối về **luồng dữ liệu**: video → detector → tracker → cảnh báo → lưu → API → dashboard. Bước suy luận chạy trước trên Kaggle. Báo cáo phải ghi rõ điều này, không gọi là "thời gian thực".
- FPS và độ trễ đo ở tuần 9 trên Kaggle bằng chính pipeline lõi; bảng `runs` giữ phần cứng.
- Kiểm thử: pipeline lõi và API có pytest trên dữ liệu tổng hợp. Kịch bản kiểm thử E2E (Thuyết minh 13.3) do An viết trước khi chạy (W8-05).
