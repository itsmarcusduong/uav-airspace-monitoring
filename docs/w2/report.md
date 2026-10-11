# Báo cáo Kết quả Tuần 2 (W2: EDA + Annotation Audit + Baseline Setup)
**Dự án:** Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu  
**Nhóm:** E1 (Lê Ngọc An, Dương Minh Quang)[cite: 1]  

## 1. Mục tiêu Tuần 2
Thực hiện khám phá dữ liệu (EDA), kiểm định chất lượng nhãn (Annotation Audit) và xây dựng kịch bản chia tập huấn luyện/kiểm thử (Train/Val/Test Split v1) chống rò rỉ dữ liệu (Data Leakage).

## 2. Kết quả Khám phá Dữ liệu (EDA)
- **Tổng số bản ghi/video khảo sát:** 1,303 chuỗi từ archive Svanstrom.
- **Phân bố lớp đối tượng (Classes Distribution):**
  - `Drone`: 271 chuỗi
  - `Airplane`: 133 chuỗi
  - `Bird`: 130 chuỗi
  - `Helicopter`: 116 chuỗi
- **Đặc thù dữ liệu:** Dữ liệu bao gồm cả phổ Hồng ngoại (IR) và khả kiến (Visible); đa số mục tiêu ở dạng vật thể nhỏ (Small Objects) quan sát từ mặt đất.

## 3. Kiểm định Chất lượng Nhãn (Annotation Audit)
- Kiểm tra toàn vẹn metadata: 1,303/1,303 bản ghi hợp lệ, không có bản ghi nào bị thiếu đường dẫn tệp (`missing paths = 0`).
- Đảm bảo tính nhất quán của cấu trúc thư mục và sẵn sàng cho pipeline chuyển đổi định dạng sang YOLO cho Tuần 3.

## 4. Kịch bản Phân chia Dữ liệu (Split v1 - Group-based Split)
Nhằm triệt tiêu hiện tượng Data Leakage (tránh việc các frame liền kề của cùng một video bị lọt vào cả tập train và test), nhóm thực hiện chia theo nhóm video (Video-based Group Split) với tỷ lệ chuẩn:
- **Tập Train (70%):** 912 chuỗi (Dùng để huấn luyện mô hình ở W3-W5).
- **Tập Validation (15%):** 195 chuỗi (Dùng để tinh chỉnh siêu tham số và chọn ngưỡng).
- **Tập Test - Frozen (15%):** 196 chuỗi (Đã khóa cứng, lưu tại `data/splits/test_v1.csv`, tuyệt đối không chạm vào đến mốc đánh giá cuối kỳ W11)[cite: 2, 3].

## 5. Kế hoạch tiếp theo (Tuần 3)
- Tiến hành chuyển đổi định dạng nhãn sang chuẩn YOLO.
- Huấn luyện Detector Baseline A (YOLOv8/YOLOv11) trên tập Train v1.
- Lưu trữ weights, đường cong học tập (learning curves) và đo lường baseline mAP đầu tiên trên tập Validation[cite: 2, 3].