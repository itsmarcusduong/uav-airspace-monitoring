# Kaggle run 17 — V2 trong detector, chẩn đoán hộp trùng, video H.264 cho dashboard (#115)

## Nguồn gốc
- Notebook `scripts/kaggle/notebooks/w8_run17_v2_verify.ipynb`; script trên dataset tools tại commit `42fd7319bfa64c3aa87d7cc9a2e6c6b766931136` (ô fingerprint sửa ở PR #125, không đổi script).
- Ultralytics 8.4.183, torch 2.11.0+cu130, Tesla T4 (`w8_run17/env.json`).
- Detector YOLO11n `yolo11n_640_s20261030`, `best.pt` SHA `a3de1e0195e4380a…`. conf 0,1, **NMS cùng lớp IoU 0,5** (run 14: 0,7), imgsz 640.
- Tracker ByteTrack-e1, 38 video val, 11.604 frame GT; `split = val`, `test_used = false`.

| Gói (Quang tải 21/11/2026) | SHA-256 | Ở đâu |
|---|---|---|
| `w8_run17_evidence.zip` | `90d9c96f4b8398d8d7ea8e6e8d20c7106211dbb20b285046d9aa5793259533d5` | giải nén vào `w8_run17/` |
| `w8_dupdiag_evidence.zip` | `0aab8d493401377e1e038a322952780f78dc3205c75c5a270308b24112a2da9f` | giải nén vào `w8_dupdiag/` |
| `w8_media.zip` (38 mp4 H.264) | `2479b79aed420b4ff783d0da7e329d84b627858c7b24dae4a447ba37025396b1` | chỉ `media_manifest.json` vào repo; mp4 ở máy và Drive |
| `w8_run17_demo.zip` (3 mp4 có vẽ track) | `bb28fe818b26fbd48eb9a08c89434270b2c4c702881dffa371162798dc987732` | Drive `demo/W08` |

Mọi stage `OK`: track 38 tệp, FPS trung vị 85,03; detect 13.902 detection (run 14: 19.567); dump 38 GT; demo 3 video. Chẩn đoán: 1.202 ảnh, 296 s. Mã hóa lại: 38 video, 0 video lệch số frame, fps hay kích thước.

## File
| File | Nội dung |
|---|---|
| `w8_run17/` | cùng cấu trúc run 14: `tracks/`, `dets/`, `gt/`, `matches/`, `meta.csv`, `per_video_metrics.csv`, `track_summary.json`, `timing.csv` |
| `w8_dupdiag/dup_diagnostic.json` | tỷ lệ hộp trùng D theo 4 điều kiện, cổng tái tạo so với run 14 |
| `w8_dupdiag/per_image_dets.json.gz` | detection từng ảnh × điều kiện |
| `media_manifest.json` | SHA-256 nguồn và đích, số frame, fps, kích thước của 38 video H.264 |

Áp luật mục B, C: `scripts/experiments/w8_v2_verify.py` → `results/W08/v2_verify/`; diễn giải ở `docs/w8/v2_verify_results.md`.
