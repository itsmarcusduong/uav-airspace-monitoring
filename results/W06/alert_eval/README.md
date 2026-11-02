# Đánh giá cảnh báo theo vùng trên run 14 (issue #76, ADR-0009)

Lệnh (chạy sau khi ADR-0009 Accepted, PR #81):
```
python scripts/alert/evaluate_alerts.py --evidence results/W06/kaggle_run_14/w6_run14 --tracker tracker_bytetrack_e1 \
    --roi configs/roi_w6.yaml --alert configs/alert_e1.yaml \
    --weights-sha a3de1e0195e4380aac497612296ed57f67e41ceb5ae3314e82a5ad66b125ef8a --out results/W06/alert_eval
```

| File | Nội dung |
|---|---|
| `alert_summary.json`, `alert_summary.md` | bảng ROI × điểm đại diện × luật, quyết định theo luật đặt trước, SHA của 2 file cấu hình |
| `alert_log.csv` | từng cảnh báo: video, ROI, luật, khung thời gian, track, loại (`vao_vung` / `xuat_hien_trong_vung`), có khớp sự kiện GT không |
| `gt_events.csv` | sự kiện GT (Drone trong ROI ≥ 0,3 s) |
| `per_video_alerts.csv` | số đếm theo video |
| `prewarn.csv` | cảnh báo sớm theo ngoại suy quỹ đạo (thăm dò) |

Kết quả ROI chính `center_hex`, điểm tâm:
- R1 PASS: cảnh báo sai trên 21 video không có Drone giảm từ 7 (R0) xuống 0;
- event recall 1,0 ở cả hai luật (23 sự kiện);
- độ trễ trung vị 0,233 s so với −0,033 s.

Giới hạn:
- chỉ đo trên val;
- video không có Drone chỉ khoảng 3,7 phút;
- ROI là mô phỏng.

Xem ADR-0009 mục "Kết quả áp luật".
