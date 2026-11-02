# ADR-0011: Dữ liệu bổ sung W7–W12: tập âm tính, hard negative có điều kiện, đánh giá ngoài phân phối

- Trạng thái: **Proposed** (Quang 03/11/2026). Chuyển **Accepted** khi An duyệt trên PR. Luật ở mục 3–4 phải Accepted **trước** khi chạy detector trên bất kỳ dữ liệu bổ sung nào.
- Liên quan:
  - #88 (W6-07), `docs/w7/data_expansion_proposal.md`, `results/W06/dataset_coverage.json`;
  - ADR-0003 (split theo video), ADR-0005 (chỉ tiêu, khả kiến là nhánh chính, test khóa tới W10), ADR-0007 (YOLO11n `s20261030`), ADR-0009 (luật cảnh báo R0/R1).

## Bối cảnh
- [DOCUMENT] Đề cương mục 8: "Ưu tiên bộ dữ liệu drone công khai (Anti-UAV/Drone-vs-Bird/VisDrone để tham khảo kỹ thuật) và tập video tự thu hoặc sưu tầm hợp pháp".
- [DOCUMENT] Đề cương: W12 "Dataset manifest final"; W13 "Night/low-resolution subset". Đề cương và Thuyết minh xếp hard negative ở W10; thang chấm cột E1 xếp ở W7.
- [DOCUMENT] Thuyết minh mục 13: cảnh báo giả/giờ tính trên video âm tính, "dự kiến tích lũy ít nhất 2 giờ video âm tính từ nhiều chuỗi hợp lệ; nếu không đủ, công bố thời lượng thực có và giới hạn thống kê".
- [DOCUMENT] Thuyết minh 8.1: video tự thu hoặc mô phỏng là nguồn bổ sung có ghi xuất xứ; kết quả trên dữ liệu tổng hợp trình bày tách khỏi video thật.
- [Kết quả đo] Svanström, ảnh khả kiến, không có Drone: tổng 29,9 phút cho cả ba split (val 4,6; test 4,5). Run 14 dùng 21 video không có Drone, tổng 3,66 phút.
- [WEB SOURCE] Svanström chỉ quay ban ngày, 3 drone, 3 sân bay Thụy Điển (arXiv:2111.01888).

## Quyết định [DECISION]
1. **Svanström vẫn là nguồn chính** cho train, val, chọn mô hình, chọn ngưỡng và test cuối. Không trộn ảnh Drone từ nguồn ngoài vào train trước W11.

2. **Tập âm tính `e1-neg-v1`** (W7), chỉ để đánh giá cảnh báo sai/giờ:
   - nguồn:
     - phần đánh giá của video tự quay bầu trời không có UAV;
     - FBD-SV-2024, toàn bộ 483 clip, chỉ đánh giá;
     - 21 video val không có Drone của Svanström;
     - test Svanström chỉ cộng vào ở W10;
   - mục tiêu ≥ 120 phút; nếu thiếu thì báo thời lượng thực có;
   - quy trình quay và ghi manifest:
     - mỗi buổi quay một `session_id`; ghi thiết bị, ngày giờ, nơi quay (mức quận/huyện), độ phân giải, fps, thời lượng, SHA-256;
     - frame được resize về 640×512, cùng tiền xử lý với Svanström (cắt giữa 5:4 rồi resize);
     - không bay drone; nếu thấy vật lạ nghi là UAV thì loại cả buổi khỏi tập âm tính;
   - gán buổi vào `neg_train` / `neg_eval` **trước khi chạy detector**:
     - mỗi người quay ≥ 4 buổi, mỗi buổi ≥ 20 phút, khác ngày/giờ/hướng trời;
     - buổi cuối cùng của mỗi người vào `neg_train`, các buổi còn lại vào `neg_eval`.

3. **Điều kiện kích hoạt thí nghiệm hard negative** (đo bằng YOLO11n `s20261030`, ByteTrack-e1, luật ADR-0009 không đổi, ROI `center_hex`, điểm tâm):
   - chạy `e1-yolo-v2` nếu trên `neg_eval` (không gồm test Svanström) xảy ra một trong hai:
     - R1 có ≥ 1 cảnh báo sai;
     - có detection Drone (conf ≥ 0,25) ở ≥ 1% số frame;
   - nếu không xảy ra cả hai thì ghi kết quả và không train.

4. **Luật chọn `e1-yolo-v2`** (= `e1-yolo-v1` + frame stride 10 của `neg_train`, nhãn rỗng; cùng cấu hình YOLO11n, 3 seed như run 13). Chọn v2 khi đạt **đủ cả** các điều kiện sau:
   - trên val Svanström:
     - mAP@0.5:0.95 trung bình 3 seed không thấp hơn v1 quá 0,01 (ngưỡng hòa ADR-0007);
     - recall Drone ở conf 0,25 không giảm quá 0,02;
     - event recall R1 (`center_hex`, điểm tâm) không giảm quá 5 điểm %;
   - trên `neg_eval`: số frame có detection Drone (conf ≥ 0,25) giảm ≥ 30% so với v1 (seed trung vị của mỗi bên, chọn như ADR-0007).
   - Nếu không đạt thì giữ v1 và báo cáo là kết quả âm.
   - Thí nghiệm phải xong trước 14/11 (hết W7); không kịp thì bỏ và ghi lý do.

5. **Đánh giá ngoài phân phối (OOD)** (W11), chỉ đánh giá và báo cáo trong bảng riêng:
   - nguồn: DUT Anti-UAV (gồm tập con đêm/hoàng hôn), phần RGB của Anti-UAV300, Drone-vs-Bird nếu được cấp trước W10;
   - thêm biến đổi tổng hợp của test Svanström (giảm độ phân giải, làm tối), báo tách riêng;
   - không dùng các tập OOD để chọn mô hình hay ngưỡng.

6. **License:**
   - chỉ dùng nguồn có trạng thái `usable`, hoặc `needs_review` đã được cả hai thành viên ghi nhận là đủ cho đánh giá nghiên cứu nội bộ;
   - không đưa frame hay video nguồn ngoài vào Git hoặc báo cáo công khai;
   - Git chỉ giữ manifest, SHA-256 và trích dẫn;
   - cập nhật `data/manifests/license_matrix.csv` trước khi tải.

## Hệ quả
- Không thay đổi chỉ tiêu ADR-0005, luật cảnh báo ADR-0009 hay detector ADR-0007, trừ khi luật mục 4 chọn v2.
  - Nếu chọn v2: ghi bản cập nhật ADR-0007 và chạy lại tracking/cảnh báo một lần trên val.
- Cảnh báo sai/giờ trong báo cáo luôn ghi kèm tổng thời lượng âm tính và nguồn của từng phần.
- W12: manifest cuối liệt kê mọi nguồn trên cùng trạng thái license.

## Còn mở
- [ ] An duyệt mục 2–4 (hoặc đề xuất ngưỡng khác) trước khi có video âm tính.
- [ ] Kết quả yêu cầu dữ liệu Drone-vs-Bird (ngày gửi, ngày trả lời).
- [ ] Điều khoản dữ liệu của FBD-SV-2024, DUT Anti-UAV và Anti-UAV300 (đọc trang tải; hỏi tác giả nếu cần).
