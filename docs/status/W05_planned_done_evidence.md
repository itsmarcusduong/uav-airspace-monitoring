# W5 (25/10–31/10/2026) — Planned / Done / Evidence / Problems / Next

Milestone `Tuan5`. Kế hoạch: `docs/w5/W5_PLAN.md`. Evidence: `Evidence/W05/`, tạo bằng `scripts/reporting/build_evidence.py`.

| Issue | Planned | Done | Evidence | Trạng thái |
|---|---|---|---|---|
| #57 W5-01 (Quang) | Pipeline video → detector → tracker, track log, độ đo liên kết | Run 12 (tracker mặc định) và run 12b (e1) trên 38 video val; luật ADR-0008: hòa → giữ ByteTrack-e1; 3 video demo | `results/W05/kaggle_run_12/`, `kaggle_run_12b/`, `track_comparison.*`, `track_decision.json`, `track_gaps.json`; PR #63, #68, #70 | DONE |
| #58 W5-02 (An) | Cấu hình tracker e1, giao thức, duyệt ADR-0008 | `tracker_*_e1.yaml` (`track_buffer` 30 → 45), `docs/w5/tracking_protocol_w5.md`; ADR-0008 Accepted | PR #65 | DONE |
| #59 W5-03 (Quang) | 2 seed mới cho A và YOLO11n, chọn lại theo luật mục 6 | Run 13: 4 run OK; luật → YOLO11n (hòa mAP và tốc độ, F1 Drone +0,014) | `results/W05/kaggle_run_13/`, `seed_comparison.*`, `seed_decision.json`; ADR-0007 bản cập nhật; PR #63, #67 | DONE (ADR-0007 cập nhật chờ An duyệt) |
| #60 W5-04 (An) | Mục 2.3 | Bản nháp. Quang cập nhật số liệu W5 theo review và đưa vào v0.5 | `docs/w5/muc_2_3_nhap_An.md`; PR #66 | DONE (An xác nhận phần Quang sửa) |
| #61 W5-05 (An) | Phân tích lỗi liên kết trên video demo | Chưa | — | IN PROGRESS → W6 |
| #62 W5-06 (Quang) | Báo cáo W5, v0.5, Evidence/W05, tag w05 | `E1_W05_bao_cao_cong_viec`, `E1_DoAn_v0.5_W05` (docx và pdf), Evidence/W05 | `reports/w5/`, `Evidence/W05/` | DONE (bản nộp) |
| #40 W4-06 (An) | Phân tích so sánh W4 + model card B | Xong; ADR-0007 (bản W4) Accepted | PR #64 | DONE |
| #24 W4-01 (An, Quang) | Thống nhất 5 video review bất đồng | Cả 5 chốt SAI_NHAN (đều thuộc train) | `results/W04/review_v2_adjudication.csv`; PR #69 | DONE |

## Problems
1. Svanström không có track ID. Độ đo liên kết dùng GT dẫn xuất "1 track/video", không phải MOTA/IDF1/HOTA. Các vật thể khác trong khung hình không có nhãn.
2. Đổi detector sang YOLO11n dựa trên tiêu chí phụ (F1 Drone). Mức chênh nhỏ hơn độ lệch chuẩn giữa các seed. Luật nhiều seed được viết sau khi biết kết quả seed 1 (đã ghi trong giao thức).
3. ID switch tập trung ở các video có hai track trùng trên cùng vật thể. `track_buffer` gần như không có tác dụng: track log của run 12 và 12b trùng nhau ở 75/76 cặp video.
4. An chưa review các PR #63, #67–#70, chưa duyệt ADR-0007 bản cập nhật và luật chọn weights YOLO11n; #61 chưa xong.
5. FPS chỉ để tham khảo: cùng một cấu hình ByteTrack nhưng hai lần chạy chênh nhau khoảng 11%.

## Next (W6)
- Chạy tracking với YOLO11n (`s20261030`) và ByteTrack-e1.
- Làm model card YOLO11n.
- Viết giao thức xử lý track trùng (luật đặt trước) rồi mới chạy.
- Geofence và cảnh báo theo quỹ đạo; chọn thời gian xác nhận dựa trên #61.
