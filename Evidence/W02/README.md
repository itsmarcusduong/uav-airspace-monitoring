# Evidence W02 — Chuẩn hóa dataset, thống kê lớp và chất lượng nhãn

Milestone **Tuan2** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `980b3cb` · 2026-10-27

**Phạm vi:** Kiểm tra SHA-256 1.303 tệp, EDA 650 video, audit nhãn, split v1 theo video, sàng lọc rò rỉ.

**Liên kết:** PR #13, #14. Báo cáo: reports/w2/. Tài liệu: docs/w2/, ADR-0002, ADR-0003. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 17 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 5 kiểm tra chạy lại lúc tạo Evidence: **5 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_overview.png` | Sơ đồ tổng quan bài toán |
| `figures/fig_split_v1_by_class.png` | Số video theo lớp trong từng tập split v1 |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| — | — | — |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W02
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
