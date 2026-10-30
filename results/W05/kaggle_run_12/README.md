# Kaggle run 12 — tracking trên video val, cấu hình tracker mặc định (issue #57, ADR-0008)

## Nguồn gốc
- Notebook `scripts/kaggle/notebooks/w5_run12_track.ipynb`, job `scripts/kaggle/w5_track_videos.py`, commit `26c94626db6f325befad039be8a654a7488656d2`. Ultralytics 8.4.183, Tesla T4 (`w5_track/env.json`).
- Detector: baseline A best.pt, SHA `65dd67fb…` (`w5_track/inputs.json`). conf 0,1, NMS IoU 0,7, imgsz 640.
- Tracker `tracker_bytetrack_default`, `tracker_botsort_default`. Khác biệt so với bản Ultralytics đang chạy: `{}` cho cả hai.
- Dữ liệu: 38 video khả kiến tập val của `e1-yolo-v1`, 11.604 frame GT. `test_used = false`.
- Gói gốc: `w5_track_evidence.zip` SHA `5d456c45…`, `w5_track_demo.zip` SHA `1198894c…`. Gói demo chỉ lưu trên Drive.
- Tất cả 6 stage `OK` (`w5_track/stage_status.json`).

## File
| File | Nội dung |
|---|---|
| `w5_track/per_video_metrics.csv` | độ đo theo video × tracker × IoU (0,5 / 0,3) |
| `w5_track/track_summary.json` | tổng hợp theo tracker × IoU × lớp |
| `w5_track/tracks/<tracker>/<video>.csv` | track log: frame, id, cls, conf, x, y, w, h (pixel) |
| `w5_track/timing.csv` | FPS theo video (giải mã + detector + tracker) |
| `w5_track/demo/demo_index.json` | 3 video demo, SHA-256 và link Drive |
| `track_comparison.{csv,md}`, `track_decision.json` | tạo bằng `scripts/reporting/build_track_comparison.py` |

Lệnh tạo bảng:
```
python scripts/reporting/build_track_comparison.py --evidence results/W05/kaggle_run_12/w5_track \
    --pair tracker_bytetrack_default tracker_botsort_default --reference-only --out results/W05/kaggle_run_12
```

## Kết quả
Bảng đầy đủ nằm trong `track_comparison.md`.

Các độ đo tính trên GT dẫn xuất "1 track/video". Đây **không** phải MOTA/IDF1/HOTA. "Track giả" có thể là vật thể thật không được gán nhãn.

- **[Kết quả đo] Cặp default chỉ để tham khảo.**
  - ID switch / 1000 frame GT ở IoU 0,5: ByteTrack 8,96, BoT-SORT 7,76. Chênh tương đối 13,5%, nằm trong vùng hòa theo luật mục 7.
  - Theo video: BoT-SORT tốt hơn ở 6 video, ByteTrack ở 3, bằng nhau ở 29.
  - Luật quyết định chỉ áp cho cặp `e1` ở run 12b (`docs/w5/tracking_protocol_w5.md`).
- **[Kết quả đo] Tốc độ.** FPS trung vị: ByteTrack 106, BoT-SORT 74. BoT-SORT chậm hơn vì GMC `sparseOptFlow`.
- **[Kết quả đo] Đứt track phần lớn do ngưỡng IoU 0,5.**
  - Hạ IoU từ 0,5 xuống 0,3 thì fragment của ByteTrack giảm từ 340 xuống 58, và track recall gộp tăng từ 0,858 lên 0,950.
  - [INFERENCE] Hộp nhãn rộng hơn vật khoảng 3 lần (ADR-0006, tập chuẩn CVAT), nên IoU giữa hộp track và hộp nhãn dao động quanh 0,5. Nhiều "đứt track" ở IoU 0,5 là do cách đo, không phải tracker mất vật.
- **[Kết quả đo] Airplane có ID switch cao nhất.** ByteTrack: 20,0 / 1000 frame GT, trung vị độ phủ ID chính 0,505.
  - V_AIRPLANE_047 (ByteTrack) có 28 ID switch nhưng chỉ 2 ID.
  - 81/325 frame có 2 track chồng nhau, trung vị IoU giữa hai track là 0,66, nhỏ hơn ngưỡng NMS 0,7.
  - [INFERENCE] Đây là hai track trùng trên cùng một máy bay. Cách ghép "IoU lớn nhất" chuyển qua lại giữa hai track, nên mỗi lần chuyển bị tính là ID switch. W6 cần xử lý track trùng (NMS chặt hơn hoặc gộp track) trước khi dùng track cho cảnh báo. Bất kỳ thay đổi nào cũng phải ghi vào giao thức trước khi chạy.
- **[Kết quả đo] Bird:** gần như không có ID switch (ByteTrack 0; BoT-SORT 2,67 / 1000). Mẫu nhỏ: 3 video.

## Video demo (Drive, ByteTrack default)
Luật chọn đặt trước trong job: video Drone và Bird có nhiều frame GT nhất, cộng video Drone có nhiều ID switch nhất. Link nằm trong `w5_track/demo/demo_index.json`.
- V_DRONE_096: https://drive.google.com/file/d/1Qz-etgvoJsK5Jyk6VjPNIIkN4LbLTbmD/view
- V_BIRD_037: https://drive.google.com/file/d/1-kZZgVR-M6Y_8lsHH2u-wff8kYJkmrFS/view
- V_DRONE_080: https://drive.google.com/file/d/1L_enuzQ-C3N6D7xi2rgC9m5vBcdrI2Nh/view

## Giới hạn
- Chỉ đo trên val. Val cũng là tập dùng để chọn detector, nên số liệu lạc quan.
- Mỗi video có 1 vật thể được gán nhãn. Các vật thể khác không có GT.
- FPS đo trên một lần chạy Kaggle T4, có cả thời gian giải mã video. Đây không phải benchmark tốc độ W9.
