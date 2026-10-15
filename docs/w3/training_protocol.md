# Giao thức Huấn luyện Baseline A (Training Protocol)
**Dự án:** Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu  
**Nhóm:** E1  

## 1. Mục tiêu thí nghiệm
Thiết lập và huấn luyện mô hình Object Detector cơ sở (Baseline A) trên tập dữ liệu Train v1 (912 chuỗi), đánh giá hiệu năng trên tập Validation v1 (195 chuỗi) nhằm thiết lập mốc đo lường (mAP baseline) trước khi tối ưu hóa vật thể nhỏ hoặc chuyển đổi sang mô hình đối chứng (RT-DETR). Tập Test v1 tiếp tục được giữ nguyên trạng thái đóng băng (frozen).

## 2. Thông số kỹ thuật & Môi trường
- **Framework:** Ultralytics YOLOv8 / PyTorch
- **Độ phân giải đầu vào:** 640x640 pixels
- **Batch size:** 16
- **Số lượng Epochs:** 50 epochs (có áp dụng Early Stopping patience = 10)
- **Seed cố định:** 20261014

## 3. Quy tắc chọn Checkpoint & Đánh giá
- **Checkpoint tốt nhất:** Lựa chọn `best.pt` dựa trên chỉ số **mAP@0.5:0.95** cao nhất trên tập Validation.
- **Metrics bắt buộc ghi nhận:** mAP@0.5, mAP@0.5:0.95, Precision, Recall, F1-score theo từng lớp (`Drone`, `Bird`, `Airplane`, `Helicopter`).
- **Tuyệt đối không sử dụng tập Test** trong quá trình huấn luyện và chọn checkpoint.