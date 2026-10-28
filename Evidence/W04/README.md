# Evidence W04 — Tuning + augmentation, so sánh baseline

Milestone **Tuan4** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `5915215` · 2026-10-28

**Phạm vi:** Kiểm chứng chiều lệch nhãn (run 06 và tập chuẩn CVAT, ADR-0006), train và so sánh 6 mô hình trên cùng dữ liệu (run 09), áp luật chọn đặt trước (ADR-0007).

**Liên kết:** Issue #24, #36–#42, #48, #49; PR #43–#47, #50–#55. Kế hoạch: docs/w4/W4_PLAN.md. ADR-0006, ADR-0007. Giao thức: docs/w4/training_protocol_w4.md. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 184 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 54 kiểm tra chạy lại lúc tạo Evidence: **54 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w4_accuracy_vs_latency.png` | mAP@0.5:0.95 và thời gian suy luận (val, T4) |
| `figures/fig_w4_ap_by_class.png` | AP@0.5 theo lớp, 6 mô hình (val) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| baseline_A_aug/best.pt | https://drive.google.com/file/d/1TU-aqFP2ACZOhlPqzkXDEwYH2Mzv0oyK/view | `32a6f453fd0320cc…` |
| baseline_A_aug/last.pt | https://drive.google.com/file/d/1276oshbnhtfIF6j_EsQke2mcDLK_8o9A/view | `5f16b4010dea214f…` |
| baseline_A_960/best.pt | https://drive.google.com/file/d/1argQENmJI_ZS8sTFZ-nze93P3OZaAm2T/view | `9fafd566fc372b2b…` |
| baseline_A_960/last.pt | https://drive.google.com/file/d/1Z6w683s1wu1RjeHxi_3M4EfpS7KexQT7/view | `b354eb640e0a9b21…` |
| yolo11n_640/best.pt | https://drive.google.com/file/d/1lbHwnnPsEKFg_9vudnbHOm7PInp4Lm0M/view | `80ff77c7b4340efc…` |
| yolo11n_640/last.pt | https://drive.google.com/file/d/16Osh6Ex-GFbONSjV6ao8FW8_cPMbgIL8/view | `02da011021ef3b6f…` |
| detector_B/best.pt | https://drive.google.com/file/d/1BfJQlurjwIOAs8kxf6oR3pXrRKxItuMt/view | `04f320964b63a3df…` |
| detector_B/last.pt | https://drive.google.com/file/d/1g9IUlzP-ydLqolw_7xiK3soLWy5IWzsl/view | `3578b6fe6a9f285c…` |
| rtdetr_l_640/best.pt | https://drive.google.com/file/d/1QrIXDpR738QRTqHBaRMwh0NngS7DppRS/view | `fd031079701678d2…` |
| rtdetr_l_640/last.pt | https://drive.google.com/file/d/1CP97pJInfSjHOFi94aORbK_UPDomzZac/view | `706f92e78663e2df…` |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W04
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
