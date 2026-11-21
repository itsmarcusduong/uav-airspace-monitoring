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
python scripts/pipeline/build_bundle.py --evidence results/W06/kaggle_run_14/w6_run14 --run-id run14 --commit <sha> \
    --media-dir <thư mục w8_media> --out <thư mục bundle>
python scripts/pipeline/build_bundle.py --evidence results/W08/kaggle_run_17/w8_run17 --run-id run17 --commit <sha> \
    --media-dir <thư mục w8_media> --out <thư mục bundle> --append --reason "<lý do đổi cấu hình>"
python scripts/pipeline/api.py --bundle <thư mục bundle>          # mở http://127.0.0.1:8000/
python scripts/pipeline/api.py --bundle <thư mục bundle> --openapi docs/w8/openapi_w8.json
```
Bundle chứa video của dữ liệu nên **không đưa vào Git**. `bundle.json` giữ SHA-256 mọi tệp; `build_bundle.verify()` kiểm lại.

Chế độ ghi của `build_bundle.py`:
- mặc định: `--out` chưa tồn tại hoặc là thư mục rỗng;
- `--append`: thêm run vào bundle có sẵn. Nếu cấu hình khác run trước thì ghi `config_audit`, bắt buộc có `--reason`;
- `--overwrite`: dựng lại bundle. Chỉ xóa các mục của bundle (`bundle.json`, `events.sqlite`, `frames/`, `media/`). Script từ chối khi:
  - `--out` không có `bundle.json`;
  - `--out` là thư mục gốc, home, repo, thư mục hiện tại hoặc thư mục cha của chúng;
  - `--out` có tệp lạ;
  - bundle đã có review hoặc audit, vì đó là lịch sử chỉ thêm.

## Kho sự kiện (`e1store.py`)
| Bảng | Ghi chú |
|---|---|
| `runs` | `model_version` = SHA-256 weights, cấu hình ROI/cảnh báo/tracker và SHA-256 của nó |
| `sources` | khóa chính (`run_id`, `source_id`) |
| `events` | bất biến, không có cột trạng thái |
| `event_reviews` | chỉ thêm; `reviewer_id` là định danh cục bộ, **chưa xác thực** |
| `config_audit` | chỉ thêm; ghi khi `--append` thêm run có cấu hình khác run trước (roi, alert, tracker, detector, weights); W8 chưa có endpoint sửa cấu hình |

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
- Dashboard báo "kết quả quá hạn" nếu quá 1 giây không nhận được frame, và báo "hết video" khi nhận `eos`. Khi đó dashboard xóa lớp vẽ và dừng video, không giữ hình cũ. Frame đến lại thì video tua tới đúng thời gian nguồn rồi phát tiếp.

## Kiểm thử
`tests/test_w8_pipeline.py`:
- ràng buộc chỉ thêm (append-only) và trạng thái suy ra;
- bundle dựng từ dữ liệu tổng hợp;
- **đối chiếu chéo**: bundle dựng từ run 14 cho đúng 25 sự kiện R1 như `results/W06/alert_eval/alert_log.csv`;
- REST và WebSocket;
- dashboard chạy thật trong Chromium headless (Playwright): phát tới hết video, review chỉ thêm, nguồn Bird không có cảnh báo;
- an toàn theo review của An ở PR #124:
  - `--overwrite` từ chối đường dẫn ngoài bundle;
  - `config_audit` được ghi khi `--append`;
  - giá trị từ bundle hiện dạng chữ, không thành HTML;
  - WebSocket ngắt giữa chừng thì dashboard báo "kết quả quá hạn" và **dừng video**, frame đến lại thì phát tiếp.
- Hai test dashboard mới đều trượt khi bỏ bản sửa tương ứng (đã thử).
