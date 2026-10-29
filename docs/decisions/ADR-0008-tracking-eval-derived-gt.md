# ADR-0008: Đánh giá liên kết của tracker bằng GT dẫn xuất "1 track/video"

- Trạng thái: **Proposed** (Quang soạn 29/10/2026, issue #57). An duyệt hoặc sửa trong #58 **trước** khi chạy run 12b. Run 12 (cấu hình mặc định) được phép chạy theo bản này.
- Liên quan: ADR-0005 mục 3 (ByteTrack chính, BoT-SORT đối chiếu; không báo HOTA/IDF1 làm kết quả chính), ADR-0006 (offset0), ADR-0007 (detector = baseline A).

## Bối cảnh
- [DOCUMENT] Thang chấm W5: "tích hợp tracker, video test ID ổn định". [DECISION] "Video test" được hiểu là video dùng để kiểm thử tracker, lấy từ tập **val**. Tập test của split v1 vẫn khóa tới W10 (ADR-0005).
- [Kết quả đo] Nhãn Svanström có tối đa 1 hộp/frame, không có track ID (W2 audit). Các vật thể khác trong khung hình (đàn chim, máy bay nền) không được gán nhãn.
- [WEB SOURCE] Ultralytics `model.track` hỗ trợ sẵn ByteTrack và BoT-SORT (docs.ultralytics.com/modes/track). HOTA [17], IDF1 [18] cần GT ID cho **mọi** đối tượng.

## Quyết định [DECISION]
1. **GT dẫn xuất.**
   - Mỗi video val có một vật thể mục tiêu. Mọi frame có hộp nhãn được gán cùng một ID.
   - Căn frame i ↔ mục nhãn i (offset0, ADR-0006).
   - Frame không có hộp nhãn không tính là GT.
2. **Ghép.**
   - Mỗi frame có GT: chọn hộp track có IoU lớn nhất với hộp GT, không xét lớp.
   - Khớp khi IoU ≥ 0,5 (chính). Báo thêm IoU ≥ 0,3 như phân tích độ nhạy, vì hộp nhãn rộng hơn vật khoảng 3 lần (ADR-0006).
3. **Độ đo theo video** (`scripts/kaggle/w5_track_metrics.py`):
   - track recall = frame khớp / frame GT;
   - **ID switch** = số lần ID khớp thay đổi giữa hai frame khớp liên tiếp (bỏ qua khoảng mất);
   - số ID khớp mục tiêu;
   - fragment = số lần từ "không khớp" chuyển sang "khớp" sau lần khớp đầu;
   - độ phủ ID chính = số frame khớp với ID xuất hiện nhiều nhất / frame GT;
   - độ nhất quán lớp;
   - track giả = ID không bao giờ khớp mục tiêu và dài ≥ 5 frame.
4. **Tổng hợp.** Đơn vị phân tích là video. Báo ID switch / 1000 frame GT (gộp), số video chỉ có 1 ID, trung vị độ phủ ID chính, trung vị track recall. Báo theo lớp.
5. **Giới hạn bắt buộc phải ghi cùng số liệu.**
   - Đây **không** phải MOTA/IDF1/HOTA. Không gọi tên các độ đo chuẩn cho các số này.
   - "Track giả" có thể là vật thể thật không được gán nhãn (chim, máy bay khác), nên không dùng làm tỷ lệ cảnh báo giả. Cảnh báo giả đo ở W6–W7 bằng video âm tính.
6. **Cấu hình chạy.**
   - Detector: baseline A best.pt (SHA `65dd67fb…`), imgsz 640, conf 0,1 đưa vào tracker (≤ `track_low_thresh`, để ByteTrack dùng được hộp điểm thấp), NMS IoU 0,7.
   - Tracker biến thể `default`: bản sao cấu hình mặc định Ultralytics (`configs/tracker_*_default.yaml`). Job ghi lại khác biệt so với bản Ultralytics đang chạy.
   - Biến thể `e1` do An chỉnh trong #58, chạy ở run 12b.
7. **So sánh ByteTrack và BoT-SORT** (đặt trước khi có kết quả).
   - Tiêu chí chính: ID switch / 1000 frame GT ở IoU 0,5.
   - Tiêu chí phụ: trung vị độ phủ ID chính.
   - Chênh lệch ID switch < 20% (tương đối), hoặc < 1 / 1000 frame (tuyệt đối), coi là **hòa**.
   - Khi hòa, giữ ByteTrack (tracker chính theo ADR-0005, rẻ hơn vì không cần GMC).
   - So sánh theo video: ghi số video mỗi tracker tốt hơn.

## Hệ quả
- W5 báo cáo: bảng độ đo theo tracker × ngưỡng IoU, 3 video demo (luật chọn đặt trước trong job: video Drone và Bird có nhiều frame GT nhất, cộng video Drone có nhiều ID switch nhất), FPS tham khảo.
- W6 (cảnh báo theo quỹ đạo) dùng track log của tracker được giữ.
- Nếu GVHD yêu cầu HOTA/IDF1: phải có GT nhiều đối tượng. Phương án: An gán nhãn ID cho một tập nhỏ video có nhiều vật thể. Cách làm này cần ADR mới.
