### 2.3. Công nghệ sử dụng và lý do lựa chọn

Đồ án chọn Ultralytics YOLO, ByteTrack làm tracker chính, BoT-SORT làm đối chứng và Kaggle GPU làm môi trường chạy. Tiêu chí là tích hợp được, có thể so sánh trên cùng dữ liệu/phần cứng và lưu được evidence tái lập; lựa chọn này không khẳng định ưu thế phổ quát.

#### 2.3.1. Detector, framework và tracker

Ultralytics cung cấp API huấn luyện, suy luận và theo dõi thống nhất, với ByteTrack và BoT-SORT được hỗ trợ trực tiếp [1]. ByteTrack liên kết thêm hộp confidence thấp [2]; BoT-SORT có thể bù chuyển động camera và dùng ReID [3]. Vì vậy, nhóm dùng ByteTrack làm chính và so sánh BoT-SORT trên cùng detector/video. SORT là phương án ghép đơn giản hơn dựa trên Kalman và assignment [14], còn RT-DETR là đối chứng kiến trúc detector thời gian thực [6].

W4 đo trên **validation**: YOLOv8n (`baseline_A`) đạt mAP@0.5:0.95 **0,34213**, **3,257 ms/ảnh** và recall vật thể nhỏ **0,8632**; YOLO11n đạt lần lượt **0,34702**, **3,281 ms/ảnh** và F1 Drone **0,8802**. Chênh mAP 0,00489 nhỏ hơn ngưỡng hòa 0,01 đã đặt trước, nên giữ A theo luật chọn mô hình. RT-DETR-l đạt 42,742 ms/ảnh, vượt giới hạn 25 ms/ảnh; train lỗi loss NaN từ epoch 3, do đó kết quả được đánh dấu **không hợp lệ** và không dùng để kết luận RT-DETR kém hơn. Số validation có thể lạc quan vì dùng chọn checkpoint/ngưỡng.

**Bảng 2.2. Đánh đổi khi lựa chọn công nghệ**

| Tiêu chí | Phương án chọn | Phương án đối chiếu | Đánh đổi và căn cứ |
|---|---|---|---|
| Detector | YOLOv8n @640: mAP 0,34213; 3,257 ms/ảnh. | YOLO11n @640: 0,34702; 3,281 ms/ảnh. RT-DETR-l: 42,742 ms/ảnh, train lỗi. | A được giữ vì chênh mAP dưới 0,01 và nhanh hơn; run RT-DETR không hợp lệ [6]. |
| Tracker/tích hợp | ByteTrack qua API Ultralytics [1], [2]. | BoT-SORT tích hợp [1], [3] hoặc tracker từ repository gốc. | Tích hợp giảm công nối và giữ chung đầu vào; repository riêng tăng quyền kiểm soát nhưng cần xác minh cấu hình/phiên bản. Bù camera và ReID của BoT-SORT có thể tốn thêm tính toán; lợi ích với camera cố định cần đo. |
| Môi trường | Kaggle GPU; run W4 dùng Tesla T4, Ultralytics 8.4.183, cùng seed và fingerprint. | Colab hoặc máy cá nhân. | Kaggle giữ liên tục mốc đo và artifacts; môi trường khác cần ghi GPU, driver/runtime và phiên bản để kết quả so sánh được. |
| Giấy phép/dữ liệu | Ultralytics/weights YOLO được nhóm kiểm tra theo AGPL-3.0 [12]; Svanström CC0-1.0 [11]. | Thành phần có giấy phép phù hợp hoặc giấy phép thương mại. | Cần rà soát mã, weights và dependency riêng; CC0 của dữ liệu không thay đổi nghĩa vụ phần mềm. |

#### 2.3.2. Giấy phép và giảm phụ thuộc

Rủi ro chính là AGPL-3.0 của Ultralytics; W3 cũng ghi nhận mã nguồn và weights YOLOv8n theo giấy phép này [12]. AGPL có thể yêu cầu cung cấp mã nguồn tương ứng khi phân phối hoặc cung cấp qua mạng phiên bản đã sửa đổi trong các điều kiện của giấy phép. Cần rà soát trước khi phát hành/triển khai dịch vụ; đây không phải tư vấn pháp lý. Nhóm sẽ lưu phiên bản, nguồn và giấy phép riêng của thư viện, mã sửa đổi, weights và dependency, không suy ra giấy phép weights chỉ từ mã nguồn. Nếu không thể đáp ứng nghĩa vụ áp dụng, cần đánh giá giấy phép thương mại hoặc thay bằng stack phù hợp. Giấy phép CC0-1.0 của dữ liệu Svanström [11] không gỡ bỏ nghĩa vụ phần mềm.

Để giảm khóa chặt vào framework hoặc notebook, lưu dataset fingerprint, cấu hình, phiên bản, log và SHA-256 weights; duy trì adapter với đầu vào hộp/lớp/confidence và đầu ra track ID; giữ manifest ngoài phiên chạy. Khi chuyển môi trường, chạy lại validation và đối chiếu sai khác.

**Nguồn W4:** `results/W04/comparison_w4.csv`, `results/W04/comparison_w4.md`, `docs/decisions/ADR-0007-w4-model-selection.md`, `docs/w4/training_protocol_w4.md`; log môi trường run 09 tại `results/W04/kaggle_run_09/phien_*/train_*/env.json`. Trích dẫn [1]–[19] dùng danh mục v0.4; không thêm tài liệu tham khảo mới.
