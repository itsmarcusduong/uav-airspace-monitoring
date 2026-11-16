# results/W07/postproc — hậu xử lý detection, tracking offline, cảnh báo (ADR-0012, #97)

```
python scripts/experiments/w7_postproc.py --variants none --out results/W07/postproc                        # cổng tái tạo
python scripts/experiments/w7_postproc.py --variants none agnostic_nms nms_iou --out results/W07/postproc  # sau khi ADR-0012 Accepted
```
Đầu vào: detection thô, GT và meta của Kaggle run 14 (`results/W06/kaggle_run_14/w6_run14/`); dự đoán ảnh val của run 13 (`results/W05/kaggle_run_13/train_yolo11n_640_s20261030/val/predictions.json.gz`). Không giải mã video. Tracker ByteTrack-e1 chạy offline bằng Ultralytics 8.4.183, cùng phiên bản với run 14.

| File | Nội dung |
|---|---|
| `repro_check.json` | Cổng tái tạo V0: track log so với run 14 (37/38 video giống, 99,84% dòng); cảnh báo R0/R1 `center_hex`/tâm giống hệt; P/R từng lớp ở conf 0,25 giống hệt `operating_points.csv` run 13 |
| `V0_none/` | `tracks/` (track log offline), `per_video_tracking.csv`, `summary.json` (độ đo liên kết, cảnh báo, P/R/F1 và ma trận nhầm mức ảnh, bỏ 40 ảnh lỗi nhãn) |
| `postproc_summary.json` | Tổng hợp các biến thể; có `decision` khi chạy cả V1, V2 |

ID switch / 1000 frame GT của V0 offline là 18,183, so với 18,011 của run 14; chênh do `V_AIRPLANE_037` (detection lưu được làm tròn 2 chữ số). Mọi so sánh biến thể dùng **V0 offline** làm mốc.
