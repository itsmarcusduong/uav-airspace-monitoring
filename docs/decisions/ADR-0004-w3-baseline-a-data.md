# ADR-0004: Dữ liệu và cấu hình baseline A (W3)

- Trạng thái: **Proposed** (Quang soạn 13/10/2026; chờ An review trong PR W3-03 và kết quả Kaggle run 03)
- Liên quan: ADR-0002 (modality), ADR-0003 (split, chính sách nhãn) — mục 2 của ADR-0003 được thay bằng ADR này.

## Bối cảnh
- [DOCUMENT] Đề cương mục 11, W3: "Train detector baseline A" → Weights A, learning curves, mAP baseline; input = train split. Thuyết minh 7.2: baseline dự kiến YOLOv8n @640.
- [Kết quả đo] `annotation_audit.csv` (Kaggle run 01) đối chiếu `data/splits/video_split_v1.csv`: video "dư đúng 1 mục nhãn" (plus1) **tập trung theo lớp**, không ngẫu nhiên:
  - Visible: Drone 114/114 plus1; Bird 40 plus1 + 11 thiếu nhãn; Airplane 58 khớp + 1 thiếu; Helicopter 59 khớp + 2 thiếu.
  - IR: Bird 77 plus1 + 2 thiếu; Drone 153 khớp + 1 thiếu + 3 dư nhiều; Airplane 74 khớp; Helicopter 53 khớp + 2 thiếu.
- Hệ quả: đề xuất cũ "loại 231 video plus1" (ADR-0003 mục 2) sẽ **loại toàn bộ Drone của ảnh khả kiến** → không thể làm baseline. [INFERENCE] Lệch tập trung theo lớp gợi ý một lỗi hệ thống của đợt gán nhãn (thừa một mục ở đầu hoặc cuối), tức offset cố định 0 hoặc +1, chưa biết là cái nào.
- Kaggle run 02 (đo tương phản) không kết luận được offset.

## Quyết định đề xuất [DECISION]
1. **Modality**: baseline A chỉ dùng ảnh khả kiến (V, 640×512). IR làm nhánh riêng ở tuần sau (ADR-0002 mục 4).
2. **Lớp**: 4 lớp Airplane=0, Bird=1, Drone=2, Helicopter=3 (Bird/Airplane/Helicopter là hard negative cho Drone).
3. **Split**: split video v1, chỉ xuất train và val. Test không được xuất ở W3.
4. **Lấy mẫu**: 1 frame mỗi 10 frame (stride 10, frame 0, 10, 20, …) trong mỗi video được chọn.
5. **Video plus1**: giữ lại với offset 0 (frame i ↔ nhãn i, bỏ mục cuối) **nếu** nhóm (modality, lớp) có ≥ 90% cặp frame liên tiếp với IoU(nhãn i, nhãn i+1) ≥ 0,5. Ý nghĩa: nếu điều này đúng, lệch 1 frame hiếm khi làm đổi kết quả khớp ở ngưỡng IoU 0,5 của mAP@0.5. Nhóm không đạt thì bị loại và **dừng trước khi train** để bàn lại.
6. **Kiểm tra bằng mắt có đối chứng (đặt luật trước)**: bảng xem mù vẽ nhãn i và nhãn i+1 lên frame i, gán màu ngẫu nhiên, đáp án để riêng. Quang và An xem độc lập. Nếu ở nhóm đối chứng (video khớp số nhãn) người xem chọn đúng nhãn i ≥ 80% số ô không ghi UNCLEAR, thì kết quả nhóm plus1 được dùng: ≥ 70% chọn nhãn i+1 → xuất lại với `--plus1-policy offset1`, ngược lại giữ offset 0. Đối chứng không đạt → giữ offset 0 và ghi là chưa xác định.
7. **Video thiếu nhãn hoặc dư > 1 mục**: loại khỏi baseline A (không biết căn nhãn).
8. **Video `review_quang = SAI_NHAN`**: loại (chờ An xác nhận ở W3-01; nếu An đổi thành OK thì xuất lại).
9. **Video không có bbox**: giữ làm ảnh âm tính. Frame có nhãn rỗng trong phạm vi nhãn = âm tính; frame ngoài phạm vi nhãn = không dùng.
10. **Cấu hình**: `configs/baseline_A.yaml` (YOLOv8n COCO-pretrained, 640, 50 epoch, patience 15, seed 20261013). An rà soát ở W3-04.
11. **Đánh giá W3**: chỉ trên val. Val đồng thời dùng để dừng sớm và chọn best.pt nên số liệu lạc quan; không so với chỉ tiêu mAP@0.5 ≥ 0,80 (chỉ tiêu tính trên test).

## Hệ quả
- Kết quả baseline A chỉ đại diện ảnh khả kiến, lấy mẫu stride 10, với rủi ro lệch nhãn ≤ 1 frame ở Drone/Bird được định lượng (run 03) và ghi trong báo cáo.
- Đổi offset (mục 6) chỉ cần chạy lại bước xuất dữ liệu, không đổi split.

## Còn mở
Kết quả run 03; review của An; xác nhận GVHD về modality và chỉ tiêu (issue W2-06, chuyển W3).
