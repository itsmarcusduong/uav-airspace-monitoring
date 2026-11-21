#!/usr/bin/env python3
"""Ban nhap 4.1-4.2 cua Le Ngoc An (docs/w8/chuong4_4.1_4.2_nhap_An.md, PR #122) + sua cua Quang khi tich hop v0.8.

Ban nhap viet ngay 18/11, truoc khi code W8 merge (PR #124) va truoc review cua An tren #121/#124. Quang chi sua cac cho
lech voi cai dat va ADR-0015 da Accepted; moi cau bi sua phai con nguyen van trong ban nhap (assert), de An doi chieu.
Dung chung cho make_w8_figures.py (render Mermaid) va build_w8_project_version.py.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFT = ROOT / "docs/w8/chuong4_4.1_4.2_nhap_An.md"

ERD_NEW = """```mermaid
erDiagram
    direction LR
    RUNS ||--o{ SOURCES : contains
    SOURCES ||--o{ EVENTS : contains
    EVENTS ||--o{ EVENT_REVIEWS : reviewed_by
    RUNS ||--o{ CONFIG_AUDIT : new_run
    RUNS {
        string run_id PK
        string commit_sha
        string model_version
        string config_json
        string config_sha256
        string device
        string source_evidence
        datetime created_at
    }
    SOURCES {
        string run_id PK
        string source_id PK
        string class_name
        string media_path
        string media_sha256
        real fps
        int width
        int height
        int frame_count
    }
    EVENTS {
        string event_id PK
        string run_id FK
        string source_id FK
        string rule
        string roi
        string kind
        int start_frame
        int end_frame
        int start_ms
        int end_ms
        string track_ids_json
        datetime created_at
    }
    EVENT_REVIEWS {
        int review_id PK
        string event_id FK
        string reviewer_id
        string action
        datetime created_at
        string note
    }
    CONFIG_AUDIT {
        int audit_id PK
        string actor_id
        datetime changed_at
        string target
        string old_run_id FK
        string new_run_id FK
        string old_sha256
        string new_sha256
        string reason
    }
```"""

FIX4 = [
    # 4.1: W8 tach job Kaggle (detector + tracker) va build_bundle (R1 -> kho su kien) chay tren track log da luu (ADR-0015 muc Hệ quả)
    ("Trên Kaggle, pipeline `e1pipe` đọc video và weights, chạy detector YOLO11n, ByteTrack-e1 và AlertEngine R1, rồi xuất bundle kết quả.",
     "Trên Kaggle, job tracking đọc video và weights, chạy detector YOLO11n (NMS cùng lớp IoU 0,5, mục 5.3.8) và ByteTrack-e1, xuất track log và video mã hóa lại H.264. Bước AlertEngine R1 → kho sự kiện → `FrameResult` (`build_bundle.py`) chạy trên track log đã lưu, không giải mã video hay suy luận, rồi đóng gói thành bundle. Gộp hai phần thành một pipeline `e1pipe` chạy từng frame và đo độ trễ từng bước được để ở tuần 9 (ADR-0015)."),
    ('        P["e1pipe: decode → YOLO11n → ByteTrack-e1 → R1"]\n        B["Bundle: SQLite + JSONL + video"]',
     '        P["Job tracking: decode → YOLO11n → ByteTrack-e1"]\n        B["Track log + video H.264 + SHA-256"]'),
    ('        DB["SQLite + JSONL/video trong bundle"]',
     '        BB["build_bundle: R1 → SQLite + JSONL"]\n        DB["Bundle: SQLite + JSONL + video"]\n        BB --> DB'),
    ('    B -->|"chuyển bundle có kiểm soát"| DB', '    B -->|"tải về có kiểm soát"| BB'),
    ('        E["e1pipe và weights"]', '        E["Job tracking và weights; build_bundle (R1)"]'),
    ("Bundle được tạo từ manifest và cấu hình đã lưu cùng run; `model_version` là SHA-256 của weights. Bundle chuyển sang máy cá nhân theo cách có kiểm soát,",
     "Bundle được tạo từ bằng chứng của run và cấu hình ROI/cảnh báo đã lưu cùng run; `model_version` là SHA-256 của weights. Bằng chứng và bundle chuyển sang máy cá nhân theo cách có kiểm soát,"),
    # 4.2: luoc do theo cai dat (scripts/pipeline/e1store.py) va ADR-0015 da Accepted
    ("Các bảng dưới đây là lược đồ đề xuất cho bundle W8. Khóa ngoại SQLite được bật; khi ghi một sự kiện hoặc review, các thao tác liên quan thực hiện trong transaction.",
     "Các bảng dưới đây là lược đồ đã cài đặt cho bundle W8 (`scripts/pipeline/e1store.py`). Khóa ngoại SQLite được bật; khi ghi một sự kiện hoặc review, các thao tác liên quan thực hiện trong transaction. Trigger SQLite chặn mọi UPDATE/DELETE trên `events`, `event_reviews` và `config_audit` ở mức cơ sở dữ liệu."),
    ("| `runs` | `run_id` PK, `commit_sha`, `model_version`, `config_sha256`, `device`, `created_at` |",
     "| `runs` | `run_id` PK, `commit_sha`, `model_version`, `config_json`, `config_sha256`, `device`, `source_evidence`, `created_at` |"),
    ("| `sources` | `source_id` PK, `run_id` FK, `name`, `media_path`, `sha256`, `fps_num`, `fps_den`, `width`, `height`, `frame_count` | Một nguồn video trong run. `media_path` là đường dẫn tương đối trong bundle; `UNIQUE(run_id, source_id)` hỗ trợ kiểm tra khóa tổng hợp của `events`. |",
     "| `sources` | (`run_id`, `source_id`) PK, `class_name`, `media_path`, `media_sha256`, `fps`, `width`, `height`, `frame_count` | Một nguồn video trong run. Khóa chính tổng hợp vì cùng một video có trong nhiều run (run 14 và run 17). `media_path` là đường dẫn tương đối trong bundle. |"),
    ("| `events` | `event_id` PK, `run_id`, `source_id`, `start_ms`, `end_ms`, `start_frame`, `end_frame`, `event_type`, `roi_id`, `track_ids_json`, `evidence_path`, `created_at` |",
     "| `events` | `event_id` PK, (`run_id`, `source_id`) FK, `rule`, `roi`, `kind`, `start_frame`, `end_frame`, `start_ms`, `end_ms`, `track_ids_json`, `created_at` |"),
    ("| `config_audit` | `audit_id` PK, `run_id` FK, `actor_id`, `changed_at`, `old_config_sha256`, `new_config_sha256`, `change_summary` | Nhật ký append-only cho thay đổi cấu hình. Không lưu bí mật trong trường tóm tắt. Endpoint và thời điểm cho phép sửa cấu hình cần được chốt trong ADR trước khi triển khai. |",
     "| `config_audit` | `audit_id` PK, `actor_id`, `changed_at`, `target` (roi, alert, tracker, detector, weights), `old_run_id`, `new_run_id`, `old_sha256`, `new_sha256`, `reason` | Nhật ký append-only cho thay đổi cấu hình. W8 ghi khi thêm một run có cấu hình khác run trước vào cùng bundle (bắt buộc có lý do); bundle demo có một dòng `detector` run14 → run17. Endpoint sửa cấu hình giữa phiên cần ADR riêng ở tuần 9. |"),
    ("`events[]` (ID và chuyển trạng thái), và `stage_latency_ms` (decode, detect, track, alert, persist).",
     "`events[]` (ID và chuyển trạng thái), và `stage_latency_ms` (decode, detect, track, alert, persist; W8 phát lại từ track log đã lưu nên ghi `null`, đo ở tuần 9)."),
    ("nếu có thì lấy `action` của review mới nhất theo `(created_at, review_id)`.",
     "nếu có thì lấy `action` của review có `review_id` lớn nhất (view `event_status`); không dùng `created_at` vì hai review có thể trùng thời điểm."),
    ("`config_audit` không thay thế cấu hình có phiên bản và chỉ ghi nhận thay đổi khi có thao tác được cho phép.",
     "`config_audit` không thay thế cấu hình có phiên bản (`runs.config_json`) và chỉ ghi nhận thay đổi khi có thao tác được cho phép."),
    ("**Hình 4.3.** ERD đề xuất; `FrameResult` nằm trong JSONL, không phải bảng SQLite.",
     "**Hình 4.3.** ERD của kho sự kiện đã cài đặt; `FrameResult` nằm trong JSONL, không phải bảng SQLite."),
    ("| `GET /media/{source_id}` | Phát video của nguồn đã cấu hình trong bundle; chỉ nhận ID nguồn, không nhận path/URL tùy ý. |",
     "| `GET /media/{run_id}/{source_id}` | Phát video của nguồn đã cấu hình trong bundle; chỉ nhận ID, không nhận path/URL tùy ý. |\n| `GET /config_audit` | Nhật ký thay đổi cấu hình giữa các run (chỉ đọc). |"),
    ("    UI->>API: GET /media/{source_id}", "    UI->>API: GET /media/{run_id}/{source_id}"),
]


def fixed_text() -> str:
    md = DRAFT.read_text(encoding="utf-8")
    for old, new in FIX4:
        if md.count(old) != 1:
            raise SystemExit(f"ban nhap 4.1-4.2 da doi, kiem lai cho sua: {old[:70]}")
        md = md.replace(old, new)
    i = md.index("```mermaid\nerDiagram"); j = md.index("```", i + 10) + 3
    md = md[:i] + ERD_NEW + md[j:]
    return md


def mermaid_blocks(md: str) -> list[str]:
    out, parts = [], md.split("```mermaid\n")[1:]
    for p in parts:
        out.append(p.split("\n```", 1)[0])
    return out


def sections(md: str) -> tuple[str, str]:
    s41 = md.split("## 4.1.", 1)[1].split("## 4.2.", 1)[0].split("\n", 1)[1]
    s42 = md.split("## 4.2.", 1)[1].split("\n", 1)[1]
    return s41, s42
