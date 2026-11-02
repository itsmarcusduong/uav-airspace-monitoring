# ADR-0009: Giao thức cảnh báo theo vùng (geofence) và quỹ đạo, tuần 6

- Trạng thái: **Accepted** (Quang 01/11/2026, An 01/11/2026).
  - Luật, ngưỡng và ROI được chốt trước khi chạy `evaluate_alerts.py` trên run 14 (PR #81 merge 02/11 17:03 UTC, đánh giá chạy sau đó). Sau khi đã xem kết quả, không sửa luật, ngưỡng hay ROI của ADR này. Thay đổi nào cũng phải viết thành ADR mới.
- Liên quan:
  - ADR-0005: chỉ tiêu cảnh báo, W6 = geofence + cảnh báo theo trajectory.
  - ADR-0007 (bản cập nhật): detector YOLO11n `s20261030`.
  - ADR-0008: tracker ByteTrack-e1.
  - Thuyết minh mục 10 (trạng thái cảnh báo) và mục 12 (chỉ tiêu).
  - `docs/w5/tracking_error_review.md` (#61): track trùng, đề xuất persistence ở tầng cảnh báo.

## Bối cảnh
- [DOCUMENT] Thuyết minh mục 10.2 quy định:
  - ROI là polygon theo tọa độ ảnh chuẩn hóa; điểm đại diện là tâm hộp; thêm tiêu chí hộp giao polygon để phân tích độ nhạy.
  - Trạng thái: ứng viên → xác nhận (≥ 3 detection hợp lệ trong 5 frame) → cảnh báo (track xác nhận ở trong ROI liên tục ≥ 0,3 giây) → kết thúc (ra khỏi ROI hoặc mất bằng chứng quá thời gian chờ).
  - Gộp cảnh báo lặp theo track và vùng; nối sự kiện khi đổi track ID.
- [DOCUMENT] Thuyết minh mục 12: giảm ≥ 30% cảnh báo sai so với luật detector-only, trong khi event recall không giảm quá 5 điểm %. Cảnh báo sai đo trên video không có UAV, mục tiêu ≥ 2 giờ video.
- [Kết quả đo] Svanström không có cấu hình camera hay vùng thật, và không có video trời trống. Tập val có 38 video khả kiến: Drone 17, Airplane 9, Bird 3, Helicopter 9. Mỗi video khoảng 10 giây.
- [Kết quả đo] #61: lỗi đổi ID chủ yếu do hai track trùng trên cùng vật; `track_buffer` gần như không có tác dụng.

## Quyết định [DECISION]
1. **Dữ liệu và mô hình.**
   - Dùng bằng chứng Kaggle run 14 (#74): YOLO11n `s20261030` (SHA `a3de1e01…`), ByteTrack-e1, detector conf 0,1, NMS 0,7, imgsz 640, 38 video val.
   - Test vẫn khóa tới W10.
2. **ROI** (`configs/roi_w6.yaml`, `roi_w6_v1`). Ba polygon chuẩn hóa, dùng chung cho mọi video; đây là vùng mô phỏng, không phải vùng cấm bay pháp lý:
   - `full_frame`: toàn khung, chỉ để kiểm tra logic xác nhận theo thời gian;
   - `center_hex`: **ROI chính**, lục giác giữa khung;
   - `lower_half`: nửa dưới khung.
   - Điểm đại diện chính là tâm hộp. Biến thể `box` (hộp giao polygon) chỉ để phân tích độ nhạy.
3. **Sự kiện GT.**
   - Chỉ có ở video lớp Drone: tâm hộp nhãn nằm trong ROI liên tục ≥ 0,3 giây.
   - Hai sự kiện cách nhau ≤ 1 giây được gộp.
   - Căn nhãn theo offset0 (ADR-0006).
   - Video Airplane, Bird, Helicopter không có sự kiện GT: mọi cảnh báo trên các video này là cảnh báo sai.
4. **Hai luật** (`configs/alert_e1.yaml`, `alert_e1_v1`; `scripts/alert/alert_engine.py`):
   - **R0, detector-only (mốc):** frame có detection Drone với conf ≥ 0,25 và tâm hộp trong ROI thì đang cảnh báo. Các đoạn cách nhau ≤ 1 giây gộp thành một cảnh báo.
     - 0,25 là ngưỡng vận hành của `yolo11n_640_s20261030` (`results/W05/seed_comparison.csv`, cột `conf_op`).
   - **R1, theo track:** chạy tuần tự từng frame, mỗi frame chỉ dùng dữ liệu đến frame đó.
     - **Bằng chứng:** một dòng track có lớp Drone và conf ≥ 0,25.
     - **Xác nhận:** track có ≥ 3 bằng chứng trong 5 frame gần nhất. Lớp xuất hiện nhiều nhất của track (tính từ đầu track) phải là Drone; nếu đồng hạng thì chưa đạt điều kiện này.
     - **Cảnh báo:** track đã xác nhận có bằng chứng trong ROI liên tục ≥ 0,3 giây (9 frame ở 30 fps).
     - **Kết thúc:** không còn bằng chứng trong ROI quá 1 giây.
     - **Chống lặp và nối sự kiện:**
       - track mới có hộp chồng (IoU ≥ 0,3) với hộp cuối của một cảnh báo đang mở, hoặc vừa đóng trong 1 giây, được gắn vào cùng cảnh báo (xử lý track trùng và đổi ID);
       - cùng track quay lại trong 1 giây thì mở lại cảnh báo cũ.
     - **Nguyên tắc:** cảnh báo chỉ sinh từ frame có detection thật, không từ vị trí tracker dự đoán.
   - **Quỹ đạo:**
     - mỗi cảnh báo R1 ghi `vao_vung` nếu track đã được thấy ngoài ROI trước đó, hoặc `xuat_hien_trong_vung` nếu không;
     - **cảnh báo sớm** (thăm dò, không dùng để quyết định): ngoại suy tâm hộp theo vận tốc trung bình của 10 dòng gần nhất, 1 giây tới; nếu điểm ngoại suy vào ROI thì ghi một cảnh báo sớm cho track đó.
   - Các ngưỡng 3/5, 0,3 giây và 1 giây là giá trị khởi điểm của Thuyết minh. **W6 không hiệu chỉnh** chúng trên run 14. Hiệu chỉnh, nếu cần, làm ở W7 với hard negative và giao thức đặt trước.
5. **Độ đo** (`scripts/alert/evaluate_alerts.py`). Tính theo ROI × luật × điểm đại diện:
   - **Ghép:** cảnh báo khớp sự kiện GT nếu khoảng thời gian của nó giao [bắt đầu − 1 s, kết thúc + 1 s] của sự kiện.
   - **Các chỉ số:**
     - event recall = sự kiện có ít nhất 1 cảnh báo khớp / số sự kiện;
     - event precision = cảnh báo khớp / tổng cảnh báo;
     - số cảnh báo sai, và số cảnh báo sai trên mỗi giờ video không có Drone;
     - số cảnh báo sai trên video Drone;
     - số cảnh báo lặp trên mỗi sự kiện;
     - độ trễ trung vị = bắt đầu cảnh báo − bắt đầu sự kiện, tính bằng giây.
   - Đơn vị phân tích là video. File theo video: `per_video_alerts.csv`.
6. **Luật đạt, đặt trước** (ROI `center_hex`, điểm `center`):
   - R1 **PASS** nếu cảnh báo sai trên video không có Drone giảm ≥ 30% so với R0, **và** event recall của R1 ≥ recall R0 − 0,05.
   - Nếu R0 không có cảnh báo sai nào → **UNDETERMINED**: không đo được mức giảm.
   - Các ROI và điểm đại diện khác chỉ để báo cáo, không đổi kết luận.
7. **Giới hạn bắt buộc phải ghi cùng số liệu:**
   - chỉ đo trên val;
   - video không có Drone chỉ khoảng 3–4 phút, xa mức ≥ 2 giờ, nên kết quả chỉ mang tính chỉ báo;
   - ROI là mô phỏng;
   - mỗi video chỉ có một vật được gán nhãn, nên cảnh báo trên một drone thứ hai không có nhãn sẽ bị tính là sai (#61 thấy điều này ở V_DRONE_080). An xem lại các trường hợp này bằng mắt trong #78.

## Hệ quả
- W6: run 14 (#74), An duyệt ADR này và viết ca kiểm thử (#75), đánh giá cảnh báo và video demo có vẽ ROI và cảnh báo (#76), An phân tích lỗi cảnh báo (#78).
- W7: bổ sung video âm tính hoặc hard negative để tiến tới ≥ 2 giờ; mọi hiệu chỉnh ngưỡng phải có giao thức mới.
- W8: mô-đun `alert_engine` được dùng lại trong pipeline đầu-cuối (API, dashboard, nhật ký sự kiện).

## Kết quả áp luật (run 14, 02/11/2026)
Nguồn: `results/W06/alert_eval/alert_summary.{json,md}`, tạo bằng `scripts/alert/evaluate_alerts.py`, với `roi_w6_v1` (SHA `b8babbbc…`) và `alert_e1_v1` (SHA `2d4cee9f…`). Bằng chứng run 14: `results/W06/kaggle_run_14/`.

| ROI chính `center_hex`, điểm tâm | Sự kiện GT | Event recall | Cảnh báo | Event precision | Cảnh báo sai (21 video không có Drone) | Cảnh báo sai (video Drone) | Độ trễ trung vị |
|---|---|---|---|---|---|---|---|
| R0 detector-only | 23 | 1,0 | 31 | 0,742 | 7 | 1 | −0,033 s |
| R1 theo track | 23 | 1,0 | 25 | 1,0 | 0 | 0 | 0,233 s |

- **[DECISION] Theo luật mục 6: PASS.** Cảnh báo sai trên video không có Drone giảm 100% (7 → 0); event recall không giảm (1,0 → 1,0).
- Cái giá của R1:
  - trễ hơn khoảng 0,27 s (đúng bằng thời gian xác nhận 3/5 frame cộng thời gian ở trong vùng 0,3 s);
  - có 2 cảnh báo lặp trên 23 sự kiện.
- Kết quả ở các ROI phụ và biến thể điểm `box` cùng chiều: R1 không có cảnh báo sai nào trên video không có Drone.
  - Ngoại lệ: ở `lower_half`/`box`, R1 có 4 cảnh báo không khớp trên video Drone.
- 7 cảnh báo sai của R0 nằm ở V_AIRPLANE_007, _037, _052, V_HELICOPTER_031, _039. Đây là detection lớp Drone ngắn hạn trên máy bay hoặc trực thăng, mà R1 loại nhờ điều kiện xác nhận và lớp đa số.
- Quỹ đạo: 25 cảnh báo R1 gồm 9 `vao_vung` và 16 `xuat_hien_trong_vung` ([INFERENCE] nhiều video bắt đầu khi vật đã ở trong ROI). Có 8 cảnh báo sớm (thăm dò, không dùng để quyết định).
- **Giới hạn** (mục 7):
  - 21 video không có Drone chỉ khoảng 3,7 phút, nên con số 114,6 cảnh báo sai/giờ của R0 là ngoại suy từ 7 cảnh báo;
  - 0 cảnh báo sai của R1 không chứng minh R1 không bao giờ báo sai;
  - cần ≥ 2 giờ video âm tính (W7) mới so được với chỉ tiêu.

