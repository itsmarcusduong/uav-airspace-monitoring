# Evidence W03 — Train baseline (config, weights, mAP/PR)

Milestone **Tuan3** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `1a71f5b` · 2026-10-27

**Phạm vi:** Review nhãn v2, xuất e1-yolo-v1, train YOLOv8n@640 (baseline A), phân tích val, model card.

**Liên kết:** Issue #10, #11, #16–#21; PR #22, #23, #25, #26, #28, #31–#35. Báo cáo: reports/w3/. ADR-0004, ADR-0005. Model card: docs/w3/model_card_baseline_A.md. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 42 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 10 kiểm tra chạy lại lúc tạo Evidence: **10 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w3_data_funnel.png` | Từ video khả kiến tới e1-yolo-v1 |
| `figures/fig_w3_offset_sensitivity.png` | Độ nhạy với lệch 1 frame |
| `figures/fig_w3_learning_curves.png` | Learning curve baseline A |
| `figures/fig_w3_per_class_ap.png` | AP theo lớp baseline A (val) |
| `figures/fig_w3_recall_by_size.png` | Recall theo cỡ hộp (val, conf 0,25) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| baseline_A/best.pt | https://drive.google.com/file/d/1D_BcgNf37nBW9hMDkclLz4q9ViKFvfNB/view | `65dd67fb8968eb3d…` |
| baseline_A/last.pt | https://drive.google.com/file/d/1M33LPmTQ80sTF92HHAy060a849DfFCYg/view | `b5785db00f3a7d61…` |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W03
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
