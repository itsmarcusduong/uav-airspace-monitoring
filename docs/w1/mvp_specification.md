# Đặc tả MVP W1

## Mục đích

MVP của đồ án là nguyên mẫu phần mềm xử lý video từ camera mặt đất hoặc tệp video để hỗ trợ người quan sát phát hiện UAV trong vùng trời sân bay mô phỏng. Hệ thống không đưa ra quyết định điều hành bay, không can thiệp UAV và không xác nhận danh tính người điều khiển.

## Phạm vi chức năng đã chốt

| Thành phần | Đầu vào | Đầu ra kiểm chứng ở các tuần sau |
|---|---|---|
| Tiếp nhận video | Tệp video hoặc camera thử nghiệm | Frame, timestamp, trạng thái nguồn |
| Detector | Frame | Bounding box, lớp, confidence, thời gian xử lý |
| Lớp đối tượng | Drone, Bird, Airplane, Helicopter khi đủ nhãn | Nhãn lớp và hộp bao |
| Tracker | Chuỗi detection | Track ID, quỹ đạo ảnh 2D, trạng thái track |
| ROI và cảnh báo | Track, polygon trên ảnh, quy tắc thời gian | Sự kiện, ảnh/video bằng chứng, trạng thái xác minh |
| Giao diện và lưu vết | Kết quả pipeline và thao tác người dùng | Hiển thị video, nhật ký, tìm kiếm/xuất sự kiện |

## Quy tắc cảnh báo dự kiến

1. Một detection lớp Drone vượt ngưỡng là đối tượng ứng viên.
2. Cần ít nhất 3 detection hợp lệ trong 5 frame xử lý liên tiếp để xác nhận track.
3. Chỉ tạo cảnh báo khi track đã xác nhận ở trong ROI liên tục tối thiểu 0,3 giây theo timestamp.
4. Một cảnh báo lưu bằng chứng và chờ người quan sát xác minh là đúng hoặc báo sai.

Các ngưỡng này là giả thuyết thiết kế. Chúng sẽ được chọn/điều chỉnh trên validation ở các tuần sau; không dùng test để chọn ngưỡng.

## Mốc đo lường và giới hạn

- Detection: precision, recall, F1, mAP@0.5 và mAP@0.5:0.95 theo lớp; phân tầng theo kích thước bbox.
- Tracking: HOTA, IDF1 và ID switches chỉ khi có nhãn track ID hợp lệ.
- Cảnh báo: event precision/recall và cảnh báo sai trên giờ video không UAV.
- Hiệu năng: FPS toàn pipeline và độ trễ p95 trên phần cứng công bố.
- Dữ liệu chính dự kiến là Svanstrom nhìn từ mặt đất; split theo video/nguồn sẽ được khóa ở W2.

## Ngoài phạm vi

Không định vị 3D/độ cao thực, không sử dụng radar/RF, không bay thử hay lắp đặt ở sân bay, và không suy luận ý định của UAV. Polygon demo là vùng trên ảnh, không phải khu vực cấm bay pháp lý.
