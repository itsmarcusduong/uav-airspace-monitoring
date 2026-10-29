# Giao thức đánh giá tracker W5 (#58)

Giao thức này chốt trước run 12b theo ADR-0008. Mục tiêu là so độ ổn định ID của vật thể mục tiêu được gán nhãn, không suy rộng thành đánh giá tracking đa đối tượng.

## Cấu hình chạy

| Tracker | Biến thể | Tệp cấu hình | Tham số khác default | Vai trò |
|---|---|---|---|---|
| ByteTrack | default | `configs/tracker_bytetrack_default.yaml` | Không | Mốc run 12; ghi khác biệt với bản Ultralytics đang cài |
| BoT-SORT | default | `configs/tracker_botsort_default.yaml` | Không | Mốc run 12; ghi khác biệt với bản Ultralytics đang cài |
| ByteTrack | e1 | `configs/tracker_bytetrack_e1.yaml` | `track_buffer: 30 → 45` — giữ ID thêm 0,5 giây (tổng 1,5 giây ở 30 fps) qua mất dấu ngắn; cùng một thay đổi áp dụng cho cả hai tracker để so sánh có kiểm soát | Cấu hình chốt trước run 12b |
| BoT-SORT | e1 | `configs/tracker_botsort_e1.yaml` | `track_buffer: 30 → 45` — giữ ID thêm 0,5 giây (tổng 1,5 giây ở 30 fps) qua mất dấu ngắn; `gmc_method: sparseOptFlow` giữ nguyên vì tập dữ liệu có chuyển động pan/tilt và thay đổi camera | Cấu hình chốt trước run 12b |

Không đổi `new_track_thresh`, `match_thresh`, ngưỡng điểm, `fuse_score`, ReID hoặc GMC so với default. Thay đổi buffer có thể duy trì ID lỗi lâu hơn; ghi nhận rủi ro này khi diễn giải kết quả. Không thử thêm bộ tham số hoặc chọn cấu hình dựa trên kết quả run 12b.

## Tập dữ liệu và điều kiện cố định

- Dùng toàn bộ video thuộc `val` trong manifest `e1-yolo-v1`; không dùng split `test`.
- Với mỗi video, dùng cùng baseline A `best.pt` (SHA-256 bắt đầu `65dd67fb`), `imgsz=640`, detector `conf=0.1`, NMS IoU `0.7`, cùng manifest, nhãn, thứ tự frame và phiên bản Ultralytics trên toàn bộ các run. Ghi SHA weights, commit, phiên bản Ultralytics, thiết bị và cấu hình thực chạy vào evidence.
- Run 12 là mốc với hai cấu hình `default`; run 12b chạy đúng một lần với hai cấu hình `e1` trên cùng các video/frame và tracker khởi tạo riêng cho từng video. Nếu stage thất bại, số frame giải mã không khớp audit, hoặc SHA weights sai, dừng và không diễn giải so sánh đó.
- Báo cáo đủ bốn tổ hợp tracker × biến thể, lấy `default` từ run 12 và `e1` từ run 12b. Luật chọn tracker chỉ so cặp `ByteTrack-e1` và `BoT-SORT-e1`; không chạy lại để chọn hậu nghiệm một cấu hình có số đẹp nhất.

## GT dẫn xuất và ghép

Svanström không cung cấp track ID và chỉ gán nhãn tối đa một vật thể mục tiêu mỗi frame. Trong từng video, gán cùng một ID GT dẫn xuất cho mọi frame có hộp nhãn; căn frame video `i` với mục nhãn `i` theo offset 0. Frame không có hộp nhãn không phải frame GT. Với mỗi frame GT, chọn track có IoU cao nhất không xét lớp; khớp khi IoU ≥ 0,5. Báo thêm IoU ≥ 0,3 như phân tích độ nhạy.

## Chỉ số và luật chọn đặt trước

| Vai trò | Chỉ số / luật |
|---|---|
| Chính | ID switch / 1.000 frame GT tại IoU 0,5, gộp theo tổng ID switch chia tổng frame GT |
| Phụ | Trung vị độ phủ ID chính theo video; độ phủ là số frame khớp với ID xuất hiện nhiều nhất chia số frame GT |
| Báo cáo bổ sung | Track recall, số ID khớp mục tiêu, số video chỉ có một ID, fragment, độ nhất quán lớp và track giả theo từng video; tổng hợp theo lớp và tại IoU 0,3 / 0,5 |
| So sánh | So ID switch / 1.000 frame GT của `ByteTrack-e1` và `BoT-SORT-e1`. Chênh lệch tương đối `|A-B| / max(A,B)` dưới 20% (0 nếu cả hai bằng 0), **hoặc** chênh lệch tuyệt đối dưới 1 ID switch / 1.000 frame GT, được coi là hòa. |
| Quyết định | Ngoài vùng hòa, tracker có ID switch thấp hơn thắng. Khi hòa, giữ ByteTrack theo ADR-0005; độ phủ ID chính được báo để diễn giải, không thay đổi quy tắc hòa. Báo số video mà mỗi tracker tốt hơn. |

Đơn vị phân tích là video. Kết quả độ ổn định này chỉ áp dụng cho vật thể mục tiêu được gán nhãn; các đối tượng thật khác không được gán nhãn. Không gọi các chỉ số này là MOTA, IDF1 hoặc HOTA, không dùng track giả làm tỷ lệ cảnh báo giả. HOTA/IDF1 cần GT ID cho mọi đối tượng; cảnh báo giả được đánh giá bằng video âm tính ở W6–W7.
