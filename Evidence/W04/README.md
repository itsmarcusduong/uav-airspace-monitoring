# Evidence W04 — Tuning + augmentation, so sánh baseline

Milestone **Tuan4** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `1a71f5b` · 2026-10-27

**Phạm vi:** Kiểm chứng chiều lệch nhãn (run 06, ADR-0006), tập chuẩn CVAT, config và train các mô hình so sánh (A+aug, A@960, B), bảng so sánh.

**Liên kết:** Issue #24, #36–#42, #48, #49; PR #43–#47. Kế hoạch: docs/w4/W4_PLAN.md. ADR-0006. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 12 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 27 kiểm tra chạy lại lúc tạo Evidence: **27 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| — | (chưa có) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| — | — | — |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W04
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
