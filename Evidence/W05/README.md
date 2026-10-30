# Evidence W05 — Tích hợp tracker, video test ID ổn định

Milestone **Tuan5** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `b0a9306` · 2026-10-30

**Phạm vi:** Pipeline video → detector → tracker trên 38 video val (run 12, 12b), độ đo liên kết trên GT dẫn xuất (ADR-0008), chọn tracker theo luật đặt trước; 3 seed cho baseline A và YOLO11n (run 13), chọn lại detector (ADR-0007 cập nhật).

**Liên kết:** Issue #57–#62; PR #63–#70. Báo cáo: reports/w5/ (báo cáo công việc, v0.5). Trạng thái: docs/status/W05_planned_done_evidence.md. Kế hoạch: docs/w5/W5_PLAN.md. ADR-0007 (cập nhật), ADR-0008. Giao thức: docs/w5/tracking_protocol_w5.md, docs/w4/training_protocol_w4.md mục 6. Repo: https://github.com/itsmarcusduong/uav-airspace-monitoring

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | 340 chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | 61 kiểm tra chạy lại lúc tạo Evidence: **61 PASS / 0 FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
| `figures/fig_w5_tracking_by_class.png` | ID switch / 1000 frame GT theo lớp, ByteTrack-e1 và BoT-SORT-e1 (val, IoU 0,5) |
| `figures/fig_w5_seeds.png` | mAP@0.5:0.95 và F1 Drone theo seed, baseline A và YOLO11n (val) |

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
| demo/V_DRONE_096_tracker_bytetrack_default.mp4 | https://drive.google.com/file/d/1Qz-etgvoJsK5Jyk6VjPNIIkN4LbLTbmD/view | `29aa4f83df9c5f26…` |
| demo/V_BIRD_037_tracker_bytetrack_default.mp4 | https://drive.google.com/file/d/1-kZZgVR-M6Y_8lsHH2u-wff8kYJkmrFS/view | `19905117a5994eb2…` |
| demo/V_DRONE_080_tracker_bytetrack_default.mp4 | https://drive.google.com/file/d/1L_enuzQ-C3N6D7xi2rgC9m5vBcdrI2Nh/view | `2b8074746a0c172e…` |
| baseline_A_s20261029/best.pt | https://drive.google.com/file/d/1A2Ex__eSBOvuPj0LGY1I6DtbX1deZDzD/view | `7bf592c878f21334…` |
| baseline_A_s20261029/last.pt | https://drive.google.com/file/d/19vmRmo0XcSNO49deLANO-x1iQFGkXqUL/view | `8461eacddc95ded2…` |
| baseline_A_s20261030/best.pt | https://drive.google.com/file/d/1urKFrChLJqRzT4M8Bvyxu9T3K5fLkBxz/view | `b80e11e39c1d0bbe…` |
| baseline_A_s20261030/last.pt | https://drive.google.com/file/d/1pCc7SoM44t8zwSrrV2TbxJtJuy8J_PFN/view | `b38e7f2e94ad15fd…` |
| yolo11n_640_s20261029/best.pt | https://drive.google.com/file/d/1Jo5KwGopdWLlLBXOXEqoJMUarzsRsDjK/view | `e54ec659e342259a…` |
| yolo11n_640_s20261029/last.pt | https://drive.google.com/file/d/1tNFJtUeL68TdGAi1U-mmkHnMDvmUDl6e/view | `015c82320da34c76…` |
| yolo11n_640_s20261030/best.pt | https://drive.google.com/file/d/12nwiAizDxphbciMc7ogYzV-FWI6CYzp5/view | `a3de1e0195e4380a…` |
| yolo11n_640_s20261030/last.pt | https://drive.google.com/file/d/140Ok2xbPBEzkW2l_Ts9C5oylydT17D8x/view | `0cfc4474e56f74d0…` |

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks W05
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
