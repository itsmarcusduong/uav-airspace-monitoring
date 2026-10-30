# Kaggle run 12b — tracking trên video val, cấu hình tracker e1 (ADR-0008, `docs/w5/tracking_protocol_w5.md`)

## Nguồn gốc
- Notebook `scripts/kaggle/notebooks/w5_run12_track.ipynb` với `TRACKERS = [tracker_bytetrack_e1.yaml, tracker_botsort_e1.yaml]`.
  - Job `scripts/kaggle/w5_track_videos.py`, commit `46d0f3a148b6e5d40982c9700c11d4645fce0ea0`.
  - Ultralytics 8.4.183, Tesla T4 (`w5_track/env.json`).
  - Chạy đúng một lần, theo giao thức.
- Detector giữ nguyên như run 12: baseline A best.pt SHA `65dd67fb…`, conf 0,1, NMS IoU 0,7, imgsz 640.
- Khác biệt so với Ultralytics mặc định (`w5_track/inputs.json`): chỉ `track_buffer` 30 → 45, ở cả hai tracker.
- Dữ liệu: 38 video val, 11.604 frame GT; `test_used = false`. Tất cả 6 stage `OK`.
- Gói gốc `w5_track_evidence.zip`, SHA `73e0a26a1997aab9038aff275bbc7cd6b61ce123c71488ac492191923ad2e96d`. Gói demo của run 12b không lưu, vì video demo của run 12 đã đủ.

## Áp luật (ADR-0008 mục 7)
Nguồn: `results/W05/track_comparison.{csv,md}` và `results/W05/track_decision.json`, tạo bằng `scripts/reporting/build_track_comparison.py`.
- ID switch / 1000 frame GT ở IoU 0,5:
  - ByteTrack-e1: 8,962;
  - BoT-SORT-e1: 7,756.
- Chênh tương đối 13,5%, dưới ngưỡng 20%, nên là **hòa**.
- **[DECISION] Giữ ByteTrack-e1** làm tracker cho W6, theo ADR-0005.
- So theo video: BoT-SORT tốt hơn ở 6 video, ByteTrack ở 3, bằng nhau ở 29.
- Trung vị độ phủ ID chính: ByteTrack 0,823, BoT-SORT 0,780.

## Phát hiện [Kết quả đo]: `track_buffer` gần như không có tác dụng
Nguồn: `results/W05/track_gaps.json`, tạo bằng `scripts/reporting/track_gap_stats.py`.
- Track log của run 12b **giống hệt** run 12:
  - ByteTrack: 38/38 video;
  - BoT-SORT: 37/38 video, chỉ khác V_HELICOPTER_011, ở đó track giả dài thêm 1 frame.
- Vì vậy mọi độ đo liên kết đều trùng run 12.
- Đây cũng là bằng chứng job **tất định**: cùng input thì cùng output.
- Lý do `track_buffer` không tác dụng: không có ID nào mất quá 30 frame rồi xuất hiện lại.
  - Khoảng mất của cùng một ID: ByteTrack 49 khoảng 1–5 frame, 16 khoảng 6–30 frame, 0 khoảng > 30 frame.
  - Chỉ có 1 khoảng 31–45 frame, ở BoT-SORT-e1 (V_HELICOPTER_011). Đây chính là chỗ tăng `track_buffer` có tác dụng.
- Khoảng không có track nào trong video: ByteTrack có 16 khoảng, tất cả ≤ 5 frame. Với conf 0,1, detector gần như luôn có hộp.
- [INFERENCE] ID switch trên tập này **không** đến từ mất phát hiện dài. Các nguyên nhân khả dĩ hơn:
  - track trùng trên cùng vật, ví dụ V_AIRPLANE_047, 81 frame có 2 track IoU 0,66 (xem `results/W05/kaggle_run_12/README.md`);
  - tạo track mới khi khớp thất bại.
- Tham số cần xem ở W6 là NMS / `match_thresh` / gộp track trùng, không phải `track_buffer`. Mọi thay đổi phải ghi vào giao thức trước khi chạy. An xác nhận nguyên nhân bằng video demo trong #61.

## FPS
- FPS trung vị: ByteTrack-e1 94,6, BoT-SORT-e1 76,8. Run 12 cùng tracker: 106,1 và 74,2.
- Track log gần như giống hệt, nên chênh lệch FPS giữa hai run (khoảng 11% ở ByteTrack) là **nhiễu đo** trên Kaggle.
- FPS ở đây chỉ để tham khảo. Benchmark tốc độ làm ở W9, với điều kiện cố định và nhiều lần đo.

## Giới hạn
Giống run 12:
- chỉ đo trên val;
- GT dẫn xuất "1 track/video", không phải MOTA/IDF1/HOTA;
- detector là baseline A.

Tracking với YOLO11n (ADR-0007 bản cập nhật) làm ở W6.
