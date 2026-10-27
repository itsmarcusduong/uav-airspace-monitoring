# Evidence W01 — Phạm vi, lớp, metric, dataset, quy tắc nhãn, split

Milestone **Tuan1** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `980b3cb` · 2026-10-27

**Phạm vi:** Khảo sát dataset và license, manifest v1, 100 frame mẫu có truy nguồn, kiểm tra sơ bộ nhãn.

**Liên kết:** Báo cáo: reports/w1/. Tài liệu: docs/w1/. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 5 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 6 kiểm tra chạy lại lúc tạo Evidence: **6 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w01_sample_classes.png` | Số frame mẫu theo lớp (index_100_frames.csv) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| — | — | — |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W01
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
