# W6-05 — Phân tích lỗi cảnh báo run 14 (#78)

## Phạm vi và cách đối chiếu

Đánh giá trên validation, ROI chính `center_hex`, điểm đại diện `center`, theo cấu hình đã khóa trong ADR-0009. Nguồn số liệu là `results/W06/alert_eval/alert_log.csv`, `per_video_alerts.csv`, `gt_events.csv`, các detection/track/GT của run 14 và `results/W06/duplicate_boxes.json`.

Quang cung cấp `V_VIDS_3.zip`, gồm ba MP4 gốc và ba file MATLAB MCOS `*_LABELS.mat`. SHA-256 của ZIP là `e227e65b1d7c9119405964b6c06ea00279350aec72bf0bedf0e4f74dd0c61288`. Dùng `mcos_decoder` để giải mã nhãn; đối chiếu với GT CSV của run 14 cho thấy mọi hộp nhãn trong khung hình MP4 đều trùng chính xác (IoU 1,0). Hai file MAT Drone có thêm một phần tử nhãn cuối so với số frame MP4; phần tử ngoài phạm vi video không được dùng.

Các hình dưới đây lấy mẫu frame có ghi số frame, vẽ ROI vàng, GT trắng, detection Drone màu tím, detection lớp khác màu xanh lá và track màu cam:

![V_HELICOPTER_031, các frame trong cảnh báo R0 sai](figures/V_HELICOPTER_031_alert_review.jpg)

![V_DRONE_025, các frame trong hai cảnh báo R1](figures/V_DRONE_025_alert_review.jpg)

![V_DRONE_060, các frame trong hai cảnh báo R1](figures/V_DRONE_060_alert_review.jpg)

## Kết quả tổng thể và giới hạn phép đo

Theo `alert_summary.json`, ở ROI/điểm chính:

| Luật | Sự kiện GT | Được phát hiện | Event recall | Tổng cảnh báo | Sai trên video không Drone | Sai trên video Drone | Cảnh báo lặp | Độ trễ trung vị |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R0 | 23 | 23 | 1,0 | 31 | 7 | 1 | 0 | −0,033 s |
| R1 | 23 | 23 | 1,0 | 25 | 0 | 0 | 2 | 0,233 s |

- R1 không có cảnh báo sai hoặc sự kiện bỏ sót theo quy tắc ghép đã đăng ký trước (giao khoảng cảnh báo với GT mở rộng ±1 giây). Do đó, không có sự kiện sai/bỏ sót R1 để gán nguyên nhân.
- Tuy nhiên, bộ ghép cho phép nhiều cảnh báo cùng khớp một GT. Hai cảnh báo R1 dư là `V_DRONE_078` frame 141–146 (cùng GT frame 126–299 với cảnh báo frame 204–299) và `V_DRONE_096` frame 285–295 (cùng GT frame 21–296 với cảnh báo frame 48–223). Chúng là cảnh báo lặp, không phải sự kiện GT bị bỏ sót; ID của hai đoạn lần lượt là 6→13 và 6→22. Vì vậy event precision 1,0 theo cách tính hiện tại không đồng nghĩa ghép một-một; số cảnh báo lặp phải được đọc kèm.
- 21 video không Drone chỉ cung cấp 0,0611 giờ (khoảng 3,7 phút). Kết quả hỗ trợ phát biểu hẹp “0 cảnh báo sai R1 quan sát được trên mẫu val này”, không chứng minh tỷ lệ sai vận hành bằng 0. Mốc Poisson xấp xỉ 3/0,0611 ≈ 49 cảnh báo/giờ là giới hạn trên 95% minh họa nếu giả sử sự kiện độc lập, đồng nhất; giả định độc lập theo thời gian/video không được bảo đảm nên đây không phải ước lượng triển khai. Mức 114,6 cảnh báo/giờ của R0 cũng chỉ là ngoại suy từ 7 sự kiện trong mẫu ngắn.
- Dữ liệu một nhãn mục tiêu mỗi video và ROI mô phỏng cũng hạn chế việc phân biệt vật thể thật không được gán nhãn với cảnh báo sai.

## Từng cảnh báo sai R0 trên video không Drone

Các frame trong bảng là khoảng alert ghi trong log; số detection là các detection Drone `conf ≥ 0,25` có tâm trong `center_hex` tại các frame của khoảng đó. “Chồng lớp khác” đếm frame có ít nhất một detection lớp khác chồng IoU ≥ 0,5 với detection Drone trong cùng frame. Overlap là bằng chứng hình học, không tự nó chứng minh hai hộp cùng một vật.

| Video | Frame cảnh báo | Detection Drone trong ROI | Frame có overlap lớp khác | Đánh giá nguyên nhân |
|---|---:|---:|---:|---|
| `V_AIRPLANE_007` | 96–96 | 1 | 1 | Phù hợp với nhầm lớp/hộp trùng khác lớp; không có video trong ZIP để xác nhận trực quan. |
| `V_AIRPLANE_007` | 220–223 | 3 | 3 | Phù hợp với nhầm lớp/hộp trùng khác lớp; khoảng gộp có một frame không có detection Drone. |
| `V_AIRPLANE_037` | 143–269 | 44 | 44 | Hộp Drone chồng lớp khác ở cả 44 frame có detection; phù hợp với nhầm lớp kéo dài, chưa kiểm tra video. |
| `V_AIRPLANE_052` | 73–91 | 5 | 1 | Có overlap ở một frame, nhưng bốn frame còn lại không; nguyên nhân hỗn hợp/chưa xác định nếu không xem clip. |
| `V_AIRPLANE_052` | 132–132 | 1 | 0 | Detection Drone đơn lẻ, không có overlap lớp khác. Chưa đủ bằng chứng để kết luận nhầm lớp hay vật không gán nhãn. |
| `V_HELICOPTER_031` | 73–302 | 40 | 29 | Đã xem video: cả 40 hộp Drone có IoU ≥ 0,5 với GT trực thăng (IoU trung vị 0,807). Đây là nhầm lớp Drone trên trực thăng; cảnh báo kéo dài do R0 gộp các đoạn theo cửa sổ 1 giây. Track ID 1 mang lớp Helicopter nên R1 không cảnh báo. |
| `V_HELICOPTER_039` | 197–269 | 26 | 26 | Phù hợp với nhầm lớp/hộp trùng khác lớp; chưa có video trong ZIP để xác nhận trực quan. |

Trong bảy cảnh báo sai R0 trên video không Drone, sáu khoảng có ít nhất một overlap lớp khác. Tổng cộng có 120 frame chứa detection Drone trong các khoảng này; 104 frame có overlap IoU ≥ 0,5. Riêng `V_HELICOPTER_031`, bằng chứng GT và video xác nhận trực tiếp lỗi lớp. Không quy 15 detection Drone không overlap còn lại cho cùng một nguyên nhân nếu chưa xem video tương ứng.

R0 còn một cảnh báo không khớp trên video Drone `V_DRONE_080`, frame 0. Sự kiện GT trong ROI bắt đầu frame 83; alert đơn frame này nằm ngoài dung sai ghép ±30 frame. Video không có trong ZIP, nên đây là sai khác thời điểm giữa detection và GT theo benchmark, chưa thể kết luận đó là detection giả hay một UAV thật bị thiếu nhãn.

## Video demo R1

| Video | GT trong `center_hex` | Cảnh báo R1 | Đối chiếu hình ảnh |
|---|---|---|---|
| `V_DRONE_060` | 5–187 và 234–307 | 12–186 và 242–307 | Hai cảnh báo theo đúng hai sự kiện; trễ lần lượt 7 frame (0,233 s) và 8 frame (0,267 s), phù hợp với xác nhận và dwell đã chốt. Không thấy cảnh báo sai/bỏ sót trong clip. |
| `V_DRONE_025` | 12–169 và 255–269 | 19–167 và 262–267 | Hai cảnh báo khớp hai sự kiện, mỗi cảnh báo bắt đầu trễ 7 frame (0,233 s). Cảnh báo thứ hai ngắn (6 frame) và dừng trước cuối GT 2 frame; vẫn khớp theo tiêu chí ±1 giây. Không thấy cảnh báo sai/bỏ sót trong clip; việc chọn video vì nhiều ID switch không chứng minh mọi switch đã được xử lý. |
| `V_HELICOPTER_031` | Không có sự kiện Drone | R1 không cảnh báo | GT và video là trực thăng xuyên suốt cảnh báo sai R0; detection Drone chồng lên hộp GT trong 40 frame. R1 loại trường hợp này nhờ track lớp Helicopter. |

## Đề xuất W7 (chưa thay ngưỡng)

1. Thu thêm video âm tính/hard negative độc lập đến ít nhất 2 giờ; báo số sự kiện theo video và độ bất định ở cấp video. Không dùng 3,7 phút val để tuyên bố tỷ lệ cảnh báo sai triển khai.
2. Với `V_AIRPLANE_052` frame 132 và `V_DRONE_080` frame 0, xem video gốc/đối chiếu nhãn trước khi gán nguyên nhân; bổ sung cảnh báo theo video, frame, lớp và trạng thái overlap vào log phân tích.
3. Thử riêng biệt NMS không phân lớp và giảm NMS IoU như ghi ở PR #87, trên protocol mới có đối chứng. Tách chỉ số detection/classification khỏi theo dõi và cảnh báo; giữ nguyên ngưỡng ADR-0009 trong báo cáo W6.
4. Báo cả event recall, tổng cảnh báo, cảnh báo lặp và ghép sự kiện một-một (hoặc nêu rõ chính sách nhiều-cảnh-báo/một-sự-kiện), cùng độ trễ. Không suy diễn độ chính xác theo sự kiện chỉ từ `event_precision=1,0` hiện tại.

## Nguồn

- `results/W06/alert_eval/alert_log.csv`, `per_video_alerts.csv`, `gt_events.csv`, `alert_summary.json`, `README.md`.
- `results/W06/kaggle_run_14/w6_run14/dets/`, `tracks/tracker_bytetrack_e1/`, `gt/`, `inputs.json`.
- `results/W06/duplicate_boxes.json`; `scripts/reporting/duplicate_box_stats.py`.
- Video/nhãn người dùng cung cấp trong `V_VIDS_3.zip` (SHA-256 ở trên); ảnh đối chiếu mẫu trong `docs/w6/figures/`.
- ADR-0009 mục 6–7; giới hạn dữ liệu val và ngưỡng giữ nguyên theo protocol.
