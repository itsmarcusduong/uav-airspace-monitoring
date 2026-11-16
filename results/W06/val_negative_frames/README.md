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
| `manual_review_classification.csv` | Kết luận xem ảnh bằng mắt. Riêng 20 frame `V_BIRD_041` sau frame nhãn cuối, ghi thêm số object, dự đoán khớp object theo ghép 1-1, dự đoán dư/duplicate tính FP theo phép ghép, FP trên nền trống, lớp dự đoán và số object bị bỏ sót. |

Ảnh gốc và ảnh vẽ hộp không có trong Git: chạy Kaggle run 16 (`scripts/kaggle/notebooks/w6_run16_negframes.ipynb`) để lấy `w6_negframes.zip`.

Ở 20 frame `V_BIRD_041` f110–300, xem chuỗi ảnh gốc theo thời gian cho thấy hai con chim thật. 42 hộp dự đoán run 13 gồm 36 lớp Bird và 6 lớp Airplane; cả 42 hộp nằm trên chim, nhưng 4 hộp dư trùng object đã được hộp khác ghép, nên là FP theo ghép object 1-1 chứ không phải FP nền. Còn 2 trong 40 object-frame không được phát hiện. Sáu dự đoán Airplane là nhầm lớp trên chim thật. Đây là phân loại thủ công thăm dò trên ảnh, không sửa nhãn GT hay metric.
