# Evidence W08 — Pipeline E2E + dashboard/log

Milestone **Tuan8** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `122552a` · 2026-11-21

**Phạm vi:** Kaggle run 17: V2 (NMS cùng lớp IoU 0,5) trong detector, áp luật đặt trước W8_PLAN mục B → áp dụng V2; chẩn đoán hộp trùng video so với ảnh val (mục C, trường hợp 3). Pipeline phát lại: kho sự kiện SQLite chỉ thêm, API FastAPI + WebSocket, dashboard, nhật ký review và cấu hình (ADR-0015). 13 kịch bản E2E của An: 9 đạt, 0 trượt, 4 không kiểm được ở chế độ phát lại. Tập âm tính e1-neg-v1 chưa xong (chuyển W9).

**Liên kết:** Issue #113, #115–#119; PR #114, #120–#127 và PR chốt tuần. Báo cáo: reports/w8/ (báo cáo công việc, v0.8). Trạng thái: docs/status/W08_planned_done_evidence.md. Kế hoạch: docs/w8/W8_PLAN.md. ADR-0014, ADR-0015. Kết quả: docs/w8/v2_verify_results.md, results/W08/e2e/README.md. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 35 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 113 kiểm tra chạy lại lúc tạo Evidence: **113 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w8_v2_verify.png` | Luật áp dụng V2: run 14 so với run 17 (val) |
| `figures/fig_w8_dup.png` | Tỷ lệ hộp trùng theo đầu vào và độ chính xác số |
| `figures/fig_w8_arch.png` | Kiến trúc tổng thể (mục 4.1, bản nháp của An) |
| `figures/fig_w8_erd.png` | ERD kho sự kiện (mục 4.2) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| bundle w8_demo/bundle.json (run14 + run17, 38 video H.264; Drive w8, khong vao Git) | — | `491974f8ba43380c…` |
| demo/W08/V_DRONE_096_tracker_bytetrack_e1.mp4 | — | `1c5b37ff8d67acf1…` |
| demo/W08/V_BIRD_037_tracker_bytetrack_e1.mp4 | — | `1c85be2f4d952a4e…` |
| demo/W08/V_DRONE_078_tracker_bytetrack_e1.mp4 | — | `e000c1f90966d8c2…` |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W08
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
