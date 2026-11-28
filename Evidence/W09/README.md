# Evidence W09 — Tối ưu inference, FPS/latency

Milestone **Tuan9** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `d2e0f8e` · 2026-11-28

**Phạm vi:** Pipeline e1pipe chạy từng frame có độ trễ từng bước, qua cổng tái tạo so với run 17 (luật B). Benchmark C0/C1/C2/CPU trên 38 video val, chọn cấu hình vận hành theo luật C viết trước; chạy ổn định 60 phút (run 20). Tập âm tính: FBD-SV-2024 chuẩn hóa và đo cảnh báo sai/giờ (run 19b3), kích hoạt ADR-0011; danh sách ứng viên Wikimedia Commons lập từ API gốc, sàng lọc hai người chuyển W10.

**Liên kết:** Issue #129–#134; PR #135–#155 và PR chốt tuần. Báo cáo: reports/w9/ (báo cáo công việc, v0.9). Trạng thái: docs/status/W09_planned_done_evidence.md. Kế hoạch: docs/w9/W9_PLAN.md. ADR-0016. Kết quả: results/W09/benchmark/, results/W09/kaggle_run_18/README.md, results/W09/kaggle_run_19/README.md, results/W09/kaggle_run_20/README.md. Giao thức sàng lọc: docs/w9/neg_screening_protocol.md. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 84 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 162 kiểm tra chạy lại lúc tạo Evidence: **162 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w9_bench.png` | FPS và độ trễ p95 theo cấu hình (run 18, 18b) |
| `figures/fig_w9_stage.png` | Độ trễ p50 từng bước của pipeline |
| `figures/fig_w9_stability.png` | Chạy ổn định 60 phút với C0 (run 20) |
| `figures/fig_w9_neg.png` | Cảnh báo sai/giờ trên FBD-SV-2024 (run 19b3) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| — | — | — |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W09
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
