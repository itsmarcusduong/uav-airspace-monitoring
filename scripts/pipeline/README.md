# Pipeline đầu-cuối W8 — chế độ phát lại (ADR-0015)

Luồng xử lý:
```
Kaggle:   video → YOLO11n → ByteTrack-e1          (job run 17: w5_track_videos.py, track log)
          video → H.264                            (w8_transcode_media.py, để trình duyệt phát được)
Máy cá nhân, chỉ đọc CSV/JSON, không giải mã, không suy luận:
          track log → AlertEngine R1 → SQLite + FrameResult JSONL   (build_bundle.py)
          bundle → API FastAPI (REST + WebSocket) → dashboard → review của người quan sát   (api.py, static/)
```
Demo là đầu-cuối về **luồng dữ liệu**, không phải đo thời gian thực. Đo FPS và độ trễ từng bước làm ở W9 trên Kaggle (`stage_latency_ms` trong `FrameResult` hiện là `null`).

## Chạy
```
pip install fastapi uvicorn pyyaml
python scripts/pipeline/build_bundle.py --evidence <thư mục w8_run17> --run-id run17 --commit <sha> \
    --media-dir <thư mục w8_media> --out <thư mục bundle>
python scripts/pipeline/api.py --bundle <thư mục bundle>          # mở http://127.0.0.1:8000/
python scripts/pipeline/api.py --bundle <thư mục bundle> --openapi docs/w8/openapi_w8.json
```
Bundle chứa video của dữ liệu nên **không đưa vào Git**. `bundle.json` giữ SHA-256 mọi tệp; `build_bundle.verify()` kiểm lại.

## Kho sự kiện (`e1store.py`)
| Bảng | Ghi chú |
|---|---|
| `runs` | `model_version` = SHA-256 weights, cấu hình ROI/cảnh báo/tracker và SHA-256 của nó |
| `sources` | khóa chính (`run_id`, `source_id`) |
| `events` | bất biến, không có cột trạng thái |
| `event_reviews` | chỉ thêm; `reviewer_id` là định danh cục bộ, **chưa xác thực** |
| `config_audit` | chỉ thêm; W8 chưa có endpoint sửa cấu hình |

- Trigger SQLite chặn mọi UPDATE/DELETE trên `events`, `event_reviews`, `config_audit`.
- View `event_status`: trạng thái = `action` của review có `review_id` lớn nhất, `new` nếu chưa có review.

## Hợp đồng API
REST: xem `docs/w8/openapi_w8.json` (FastAPI sinh tự động).

WebSocket `/ws/stream?run_id=&source_id=&speed=1&start_frame=0` gửi lần lượt:
```json
{"type": "frame", "run_id": "run17", "source_id": "V_DRONE_025", "model_version": "a3de1e01…",
 "frame_index": 19, "source_time_ms": 633,
 "tracks": [{"id": 1, "cls": 2, "cls_name": "Drone", "conf": 0.71, "box": [x1, y1, x2, y2]}],
 "events": [{"event_id": "run17:V_DRONE_025:0", "transition": "open"}],
 "stage_latency_ms": null}
{"type": "eos", "frames": 301}
{"type": "error", "detail": "..."}
```
- Frame được gửi theo thời gian nguồn chia cho `speed`, đúng thứ tự `frame_index`.
- Dashboard báo "kết quả quá hạn" nếu quá 1 giây không nhận được frame, và báo "hết video" khi nhận `eos`. Khi đó dashboard xóa lớp vẽ, không giữ hình cũ.

## Kiểm thử
`tests/test_w8_pipeline.py`:
- ràng buộc chỉ thêm (append-only) và trạng thái suy ra;
- bundle dựng từ dữ liệu tổng hợp;
- **đối chiếu chéo**: bundle dựng từ run 14 cho đúng 25 sự kiện R1 như `results/W06/alert_eval/alert_log.csv`;
- REST và WebSocket;
- dashboard chạy thật trong Chromium headless (Playwright): phát tới hết video, review chỉ thêm, nguồn Bird không có cảnh báo.
