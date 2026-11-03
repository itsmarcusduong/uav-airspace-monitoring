# results/W06/val_negative_frames

40 ảnh val "âm tính" của `e1-yolo-v1` và dự đoán trên từng ảnh. Đây là phân tích thăm dò làm sau khi xem kết quả; giải thích và hệ quả ở `docs/w6/val_negative_frames.md`.

```
python scripts/reporting/val_negative_frames.py --evidence results/W06/kaggle_run_14/w6_run14 \
    --check results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030/negatives_fp.json \
    --run13-predictions results/W05/kaggle_run_13/train_yolo11n_640_s20261030/val/predictions.json.gz \
    --out results/W06/val_negative_frames
```

| File | Nội dung |
|---|---|
| `val_negative_frames.csv` | Mỗi ảnh một dòng: video, frame, đường dẫn ảnh trong `e1-yolo-v1`, nhóm nguyên nhân, khoảng frame có nhãn, hộp GT gần nhất, detection run 14 (`det_*`), dự đoán run 13 (`run13_*`, dùng cho metric), IoU với hộp GT gần nhất. Đây cũng là input `--index` của Kaggle run 16. |
| `val_negative_summary.json` | Đếm theo nhóm; đối chiếu với `negatives_fp.json` (40/38, `match: true`). |

Ảnh gốc và ảnh vẽ hộp không có trong Git: chạy Kaggle run 16 (`scripts/kaggle/notebooks/w6_run16_negframes.ipynb`) để lấy `w6_negframes.zip`.
