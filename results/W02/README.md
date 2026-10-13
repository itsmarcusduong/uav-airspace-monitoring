# results/W02

`kaggle_run_01/w2_outputs_bundle/` — Quang chạy `scripts/kaggle/w2_eda_audit_split.py` (CPU, Kaggle; xem `env.json`). `stage_status.json` toàn OK.

| Vào Git (nhỏ) | Lên Drive/Kaggle, chỉ ghi SHA-256 |
|---|---|
| checksum_verification.csv, video_inventory.csv, annotation_audit.csv, annotation_audit_summary.json, class_stats.csv, stage_status.json, env.json, review_assignment.csv, fig_*.png (nhỏ) | annotations_per_frame.csv.gz, review_sheets/, w2_outputs_bundle.zip |

Split chính thức là `data/splits/video_split_v1.*` (tạo từ metadata bởi `scripts/dataset/make_video_split.py`), **không** phải `split_v1.csv` của Kaggle (chỉ cân bằng theo lớp). Tính SHA-256: `Get-FileHash <file> -Algorithm SHA256`.
