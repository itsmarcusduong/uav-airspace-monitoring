# Evidence W07 — Hard negatives + confusion analysis

Milestone **Tuan7** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `dcd0555` · 2026-11-17

**Phạm vi:** Cổng tái tạo tracker offline trên detection của run 14; thí nghiệm hậu xử lý detection V0/V1/V2 theo luật đặt trước ADR-0012 (chọn V2, NMS cùng lớp IoU 0,5); phân tích nhầm lẫn và hard negative trên val (An, #98); nguồn video âm tính công khai có giấy phép thay video tự quay (ADR-0013, thu thập W8); Chương III bản 1.

**Liên kết:** Issue #97–#101; PR #102–#109 và PR chốt tuần. Báo cáo: reports/w7/ (báo cáo công việc, v0.7). Trạng thái: docs/status/W07_planned_done_evidence.md. Kế hoạch: docs/w7/W7_PLAN.md. ADR-0012, ADR-0013. Phân tích: docs/w7/postproc_results.md, docs/w7/confusion_analysis.md. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 66 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 88 kiểm tra chạy lại lúc tạo Evidence: **88 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w7_postproc.png` | ID switch / 1000 frame GT theo lớp của V0/V1/V2 (val, offline) |
| `figures/fig_w7_idsw_by_video.png` | ID switch theo video, V0 và V2 |
| `figures/fig_w7_confusion.png` | Ma trận nhầm V0, conf 0,25, val bỏ 40 ảnh lỗi nhãn |
| `figures/fig_w7_pipeline.png` | Pipeline mục 3.3 (bản nháp của An) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| — | — | — |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W07
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
