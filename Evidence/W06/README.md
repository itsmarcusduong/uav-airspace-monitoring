# Evidence W06 — Geofence + cảnh báo theo trajectory

Milestone **Tuan6** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `1afba4b` · 2026-11-06

**Phạm vi:** Run 14: YOLO11n s20261030 + ByteTrack-e1 trên 38 video val, lưu detection thô, GT, ghép theo frame; mô-đun ROI/cảnh báo R0 (chỉ detector) và R1 (theo track) theo giao thức đặt trước ADR-0009; video demo cảnh báo (run 15); phân tích lỗi cảnh báo, hộp trùng, 40 ảnh val âm tính (run 16); kế hoạch dữ liệu W7–W12 (ADR-0011).

**Liên kết:** Issue #74–#79, #88; PR #80–#83, #86, #87, #89–#95. Báo cáo: reports/w6/ (báo cáo công việc, v0.6). Trạng thái: docs/status/W06_planned_done_evidence.md. Kế hoạch: docs/w6/W6_PLAN.md. ADR-0009, ADR-0010, ADR-0011. Phân tích: docs/w6/alert_error_review.md, docs/w6/val_negative_frames.md, docs/w7/data_expansion_proposal.md. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 56 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 86 kiểm tra chạy lại lúc tạo Evidence: **86 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w6_alerts.png` | R0 và R1, ROI center_hex, điểm tâm: cảnh báo sai, lặp, bỏ sót (val, run 14) |
| `figures/fig_w6_detector_swap.png` | ID switch / 1000 frame GT theo lớp khi đổi detector, cùng ByteTrack-e1 (val) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| demo/W06/V_DRONE_096_tracker_bytetrack_e1.mp4 | https://drive.google.com/file/d/1IiL7iFlHkgjTE4-iZmo7NNGnkF8i9JjV/view | `2d87c58269321cd1…` |
| demo/W06/V_BIRD_037_tracker_bytetrack_e1.mp4 | https://drive.google.com/file/d/18uLGu_3nzyslT3LSq9pt5H7UjU5RLU9P/view | `1c85be2f4d952a4e…` |
| demo/W06/V_DRONE_025_tracker_bytetrack_e1.mp4 | https://drive.google.com/file/d/1kUlHcRCg-FCzgKFrmUqc-vsvffrQhWZQ/view | `63364f4e52018153…` |
| demo/W06/V_DRONE_060_alert.mp4 | https://drive.google.com/file/d/1XM4HFSUL0eFf7ko5V_4rhDdHzXgq6lnW/view | `e3f821a1d9f5bd19…` |
| demo/W06/V_HELICOPTER_031_alert.mp4 | https://drive.google.com/file/d/1Jm4GNnm2cidimVK-_mbFvcD4sLzxQPA2/view | `ea28922b6d1a01ac…` |
| demo/W06/V_DRONE_025_alert.mp4 | https://drive.google.com/file/d/1gfQP90KMLPznmy6IdS1vN7qGyNj8t9xc/view | `126b325da86464b3…` |
| kaggle_run_16/w6_negframes.zip (gui An, khong len Drive) | — | `67ec70c18fafe290…` |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W06
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
