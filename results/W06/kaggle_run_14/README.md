# Kaggle run 14 — YOLO11n + ByteTrack-e1 trên video val, kèm detection thô, GT và ghép theo frame (issue #74)

## Nguồn gốc
- Notebook `scripts/kaggle/notebooks/w6_run14_track_dump.ipynb`.
- Job `scripts/kaggle/w5_track_videos.py --tag w6_run14 --save-detections --save-gt --save-matches`, commit `7193cc6435901eb0d56f0f17b962df221ecba16f`.
- Ultralytics 8.4.183, Tesla T4 (`w6_run14/env.json`).
- Detector YOLO11n `yolo11n_640_s20261030`, `best.pt` SHA `a3de1e0195e4380a…` (ADR-0007 bản cập nhật). conf 0,1, NMS 0,7, imgsz 640.
- Tracker `tracker_bytetrack_e1`: chỉ khác mặc định ở `track_buffer` 30 → 45 (ADR-0008).
- Dữ liệu: 38 video khả kiến tập val, 11.604 frame GT; `split = val`, `test_used = false`.
- Các stage env, inputs, track, metrics, detect (19.567 detection), dump (38 GT, 38 file ghép), demo đều `OK`.
- Gói gốc `w6_run14_evidence.zip`, SHA `ed5bd1c98f4286b1f8fb63a0506e4176a908cfa2fa90fba9fc71978ad21432ab`. Gói `w6_run14_demo.zip` (3 mp4) chỉ lưu trên Drive `demo/W06`.

## File trong `w6_run14/`
| File | Nội dung |
|---|---|
| `tracks/tracker_bytetrack_e1/<video>.csv` | track log: frame, id, cls, conf, x, y, w, h |
| `dets/<video>.csv` | detection thô mỗi frame (không tracker), cho luật R0 |
| `gt/<video>.csv`, `meta.csv` | hộp nhãn theo frame (offset0); fps, kích thước, số frame |
| `matches/tracker_bytetrack_e1/<video>.csv` | ghép GT–track từng frame (IoU 0,5): định vị từng ID switch |
| `per_video_metrics.csv`, `track_summary.json`, `timing.csv` | độ đo liên kết (ADR-0008), FPS tham khảo |

## Dùng ở đâu
- So sánh đổi detector (cùng ByteTrack-e1, so với run 12b): `results/W06/detector_swap_tracking/`, ghi ở ADR-0007 mục "Phát hiện sau khi đổi detector".
  - ID switch / 1000 frame GT tăng từ 8,96 lên 18,01.
  - Frame có track chồng nhau tăng từ 416 lên 2.012.
- Đánh giá cảnh báo: `results/W06/alert_eval/` (ADR-0009).
