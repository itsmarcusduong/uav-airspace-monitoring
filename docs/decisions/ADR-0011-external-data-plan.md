# ADR-0011: Dữ liệu bổ sung W7–W12: tập âm tính, hard negative có điều kiện, đánh giá ngoài phân phối

- Trạng thái: **Accepted** (Quang 03/11/2026; An 03/11/2026, comment trên PR #89, kèm hai sửa đổi đã đưa vào mục 4 và mục 7).
  - Luật ở mục 3–4 được chốt **trước** khi có bất kỳ video âm tính nào; chưa chạy detector trên dữ liệu bổ sung. Sau khi xem kết quả không sửa luật; thay đổi nào cũng phải viết thành ADR mới.
  - Đổi tên dữ liệu thí nghiệm từ `e1-yolo-v2` thành `e1-yolo-v1-hn`, vì tên `e1-yolo-v2` đã dành cho bản xuất offset1 ở ADR-0006.
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
- [Kết quả đo, thăm dò] 40 ảnh val "âm tính" của `e1-yolo-v1` không phải nền trống (`results/W06/val_negative_frames/`). 20 ảnh là frame 0, trước frame có nhãn đầu tiên; 18/18 detection ở đó chồng IoU ≥ 0,3 với hộp GT frame 1. 20 ảnh còn lại là `V_BIRD_041` sau frame 107, khi nhãn đã hết nhưng track chim vẫn liên tục. Vì vậy ảnh âm tính trong Svanström không dùng được để đo FP nền.

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
   - chạy `e1-yolo-v1-hn` nếu trên `neg_eval` (không gồm test Svanström) xảy ra một trong hai:
     - R1 có ≥ 1 cảnh báo sai;
     - có detection Drone (conf ≥ 0,25) ở ≥ 1% số frame;
   - nếu không xảy ra cả hai thì ghi kết quả và không train.

4. **Luật chọn `e1-yolo-v1-hn`** (= `e1-yolo-v1` + frame stride 10 của `neg_train`, nhãn rỗng; cùng cấu hình YOLO11n, 3 seed như run 13). Chỉ đổi một yếu tố là thêm `neg_train`; không đụng tới nhãn Svanström. Chọn `-hn` khi đạt **đủ cả** các điều kiện sau:
   - trên val Svanström:
     - mAP@0.5:0.95 trung bình 3 seed không thấp hơn v1 quá 0,01 (ngưỡng hòa ADR-0007);
     - recall Drone ở conf 0,25 không giảm quá 0,02;
     - event recall R1 (`center_hex`, điểm tâm) **không giảm**: không mất sự kiện nào so với v1 trên cùng 38 video val (hiện 23/23). Sửa theo An: với 23 sự kiện, mất 1 sự kiện = −4,35 điểm, vẫn lọt ngưỡng 5 điểm cũ;
   - trên `neg_eval`: số frame có detection Drone (conf ≥ 0,25) giảm ≥ 30% so với v1 (seed trung vị của mỗi bên, chọn như ADR-0007).
   - Mọi số frame và cảnh báo dùng cùng pipeline đã khóa: conf 0,25 cho detection, detector conf 0,1 / NMS 0,7 / imgsz 640 cho tracking, ByteTrack-e1, luật ADR-0009.
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

7. **Báo cáo theo nguồn** (sửa theo An): cảnh báo sai/giờ, cận trên Poisson 95% và tỷ lệ frame có detection Drone báo **riêng** cho từng nguồn (video tự quay theo `session_id`, FBD-SV, Svanström val) kèm thời lượng. Không gộp thành một ước lượng vận hành duy nhất; nếu có dòng "tổng" thì ghi rõ là cộng dồn.

8. **Lịch quay W7** (An đề xuất trên PR #89; Quang xác nhận 03/11; An xác nhận 07/11, kèm dời buổi `neg_train` của An từ 13/11 sang chiều 12/11; chưa tính thời tiết):

   | Ngày | Quang | An |
   |---|---|---|
   | CN 08/11 | 08:00 `neg_eval` #1 | — |
   | T2 09/11 | — | 09:00 `neg_eval` #1 |
   | T3 10/11 | 07:30 `neg_eval` #2 | 16:30 `neg_eval` #2 |
   | T4 11/11 | 08:00 `neg_eval` #3 | 16:00 `neg_eval` #3 |
   | T5 12/11 | sáng `neg_train` | chiều `neg_train` |

   - Mốc kiểm tra thời lượng: 11/11.
   - Hai buổi `neg_train` vẫn là buổi cuối của mỗi người, nên luật ở mục 2 không đổi.
   - Dời sang 12/11 để nếu điều kiện mục 3 bị chạm vẫn còn 13–14/11 để train 3 seed và chạy lại tracking/cảnh báo.
   - Buổi bị hủy (thời tiết, có vật nghi UAV) được quay bù ở ngày gần nhất và giữ đúng vai trò; ghi ngày thực tế vào manifest.

## Hệ quả
- Không thay đổi chỉ tiêu ADR-0005, luật cảnh báo ADR-0009 hay detector ADR-0007, trừ khi luật mục 4 chọn v2.
  - Nếu chọn v2: ghi bản cập nhật ADR-0007 và chạy lại tracking/cảnh báo một lần trên val.
- Cảnh báo sai/giờ trong báo cáo luôn ghi kèm tổng thời lượng âm tính và nguồn của từng phần.
- W12: manifest cuối liệt kê mọi nguồn trên cùng trạng thái license.

## Còn mở
- [x] An duyệt mục 2–4 (03/11, PR #89), kèm hai sửa đổi đã đưa vào mục 4 và mục 7.
- [ ] Nhãn rỗng ở frame 0 và sau khi nhãn hết trong **train** (123 ảnh âm tính của `e1-yolo-v1`) có thể cũng là nhãn thiếu. Đây là một yếu tố dữ liệu khác, nên chỉ xử lý bằng giao thức riêng đặt trước ở W7 (issue W7 của An), không trộn vào thí nghiệm `-hn`.
- [ ] Kết quả yêu cầu dữ liệu Drone-vs-Bird (ngày gửi, ngày trả lời).
- [ ] Điều khoản dữ liệu của FBD-SV-2024, DUT Anti-UAV và Anti-UAV300 (đọc trang tải; hỏi tác giả nếu cần). Tập OOD chính ở W11: Anti-UAV300 RGB (theo An; có cờ có/không mục tiêu theo frame); DUT là tập bổ sung.
