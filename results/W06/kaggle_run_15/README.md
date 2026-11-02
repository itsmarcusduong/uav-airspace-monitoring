# Kaggle run 15 — video demo có vẽ ROI và cảnh báo (issue #76, ADR-0009)

## Nguồn gốc
- Notebook `scripts/kaggle/notebooks/w6_run15_alert_demo.ipynb`; job `scripts/kaggle/w6_alert_demo.py`, commit `9e0564a5c1c4a70040fab77cb8d14a71fb32cb34`. Chạy trên CPU (cv2 4.14.0).
- Đầu vào:
  - bằng chứng run 14 (weights `a3de1e01…`);
  - `configs/roi_w6.yaml` và `configs/alert_e1.yaml`. SHA ghi trong `stage_status.json` (`d34a2ccc…`, `547ceebf…`) là SHA của bản CRLF do file đi qua Windows. Bản LF trong repo có SHA `b8babbbc…`, `2d4cee9f…`; nội dung giống nhau (notebook kiểm tra SHA sau khi chuẩn hóa xuống dòng).
- Các stage env, inputs, select, render đều `OK`.
- Gói bằng chứng `w6_alert_demo_evidence.zip`, SHA `9f2c257886d35f5a685a46f28cc5cfd224a3b9e55e25eb602211bd4637f3ec5e`.
- Gói video `w6_alert_demo_videos.zip` (SHA `84a8fa87…`, 3 mp4) chỉ lưu trên Drive `demo/W06`, không đưa vào Git.

## Kiểm tra chéo
- `w6_alert_demo/demo_alerts.csv` (56 cảnh báo R0 + R1, ROI `center_hex`, điểm tâm) trùng từng dòng với `results/W06/alert_eval/alert_log.csv` (cùng ROI và điểm). Cảnh báo vẽ trên video đúng là cảnh báo đã được chấm điểm.
- SHA của 3 mp4 khớp `demo_index.json`.

## Video demo (luật chọn đặt trước trong job)
| Video | Luật chọn | Nội dung |
|---|---|---|
| V_DRONE_060 | Drone, cảnh báo R1 `vao_vung` dài nhất | R1 cảnh báo ở frame 12–186 và 242–307 |
| V_HELICOPTER_031 | Không phải Drone, cảnh báo sai R0 dài nhất, R1 không cảnh báo | R0 cảnh báo sai liên tục frame 73–302; track mang lớp Helicopter nên R1 không báo |
| V_DRONE_025 | Drone, nhiều ID switch nhất ở run 14 | kiểm tra việc gộp track trùng |

## Phát hiện khi xem lại [Kết quả đo]
Nguồn: `results/W06/duplicate_boxes.json`, tạo bằng `scripts/reporting/duplicate_box_stats.py`. Đây là phân tích thăm dò làm sau khi xem kết quả, không đổi luật nào.
- **Nguồn cảnh báo sai của R0:** trên 5 video không có Drone có cảnh báo sai, 109/126 frame có detection Drone (conf ≥ 0,25) nằm chồng (IoU ≥ 0,5) lên một detection lớp khác trên cùng vật.
  - [INFERENCE] Đây là hộp trùng **khác lớp**: NMS của Ultralytics chạy riêng từng lớp nên giữ cả hai hộp.
  - Track mang lớp đúng, nên R1 lọc được.
- **Track trùng của YOLO11n:** 2.000/2.050 cặp track chồng nhau (IoU ≥ 0,3) là **cùng lớp**. Baseline A có 354/424.
  - [INFERENCE] Đây là cơ chế khác: NMS IoU 0,7 để lọt hộp cùng lớp.
- Hệ quả cho W7 (cần giao thức đặt trước): thử NMS không phân lớp, và thử hạ NMS IoU. Đánh giá từng thay đổi riêng, có đối chứng.
- Giới hạn của video demo: lớp phủ chỉ vẽ track, không vẽ detection thô, nên người xem không thấy hộp Drone làm R0 báo sai. Lần dựng demo sau nên vẽ thêm detection Drone thô.
