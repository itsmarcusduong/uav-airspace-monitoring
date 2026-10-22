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

## Kết quả thực hiện (21/10/2026) [Kết quả đo]
Nguồn: `results/W03/kaggle_run_03a/`, `results/W03/kaggle_run_03b/`, `results/W03/review/` (commit script `680043b`).

1. **Độ nhạy lệch 1 frame** (`offset_sensitivity_summary.json`, ngưỡng IoU 0,5, yêu cầu ≥ 90%): V-Drone plus1 98,6% (95 video), V-Bird plus1 95,3% (34 video), đối chứng V-Airplane 99,7%, V-Helicopter 99,6% → **đạt**, giữ video plus1 với offset 0. V-Bird thiếu nhãn (minus) 87,5% → không đạt, vẫn bị loại theo mục 7.
2. **Thăm dò offset bằng mắt** (72 ô, `offset_review_score.json`; *không phải review mù độc lập*, xem mục Giới hạn): nhóm đối chứng chọn đúng nhãn i chỉ 53% (8/15 lựa chọn rõ ràng) < 80% → theo luật mục 6, phương pháp xem không đủ tin cậy; **offset chưa xác định, dùng offset0**. Ghi nhận (không dùng để quyết định): ở nhóm plus1, 26/34 lựa chọn rõ ràng nghiêng về nhãn i+1 → kiểm chứng ở W4 bằng tập chuẩn CVAT (#24).
3. **Review nhãn v2** (#10, 358 video, 8 frame/video, có hỗ trợ công cụ): OK 283 / SAI_NHAN 60 / KHONG_RO 15 (`review_v2_summary.json`). 10 video "không có nhãn" có vật thể bay trong hình (IR_DRONE_143–147, V_DRONE_106/107, V_HELICOPTER_040, IR_BIRD_038, V_BIRD_005) → không dùng làm âm tính (sửa mục 9: chỉ video không bbox **đã xem và không thấy vật thể** mới là âm tính).
4. **Dữ liệu xuất `e1-yolo-v1`** (`dataset_card.json`, fingerprint `d0ac7e23…`): train 178 video / 5.667 ảnh (123 âm tính), val 38 video / 1.202 ảnh (40 âm tính); bbox nhỏ (< 32×32 px) chiếm 3.041/5.544 (train) và 475/1.162 (val). Loại 21 video train, 5 val.

## Giới hạn ghi nhận
- Val chỉ còn 3 video Bird (73 ảnh có hộp) → AP lớp Bird trên val dao động lớn, chỉ để tham khảo.
- 77/242 video V train+val chưa được xem bằng mắt (ngoài danh sách 358); giữ theo audit tự động.
- Review v2 chỉ xem 8 frame/video; lỗi ở frame không được chọn không phát hiện được.
- Thăm dò offset (mục 2 ở trên) không đạt điều kiện review mù: khóa đáp án `offset_review_KEY_do_not_open_before_review.csv` nằm trong cùng gói kết quả run 03a với bảng xem, và không có bằng chứng lựa chọn đã được chốt (commit) trước khi khóa có thể truy cập; khóa sau đó được đưa vào cùng PR #25 với kết quả. Vì vậy kết quả chỉ là thăm dò, không phải bằng chứng độc lập (review An, PR #25). Kết luận không đổi vì đối chứng không đạt và quyết định vẫn là offset0.
- Quy tắc cho các lần review mù sau (W4 CVAT, #24): job tách khóa đáp án ra file riêng không đưa vào gói tải về cho người xem; người xem commit câu trả lời trước; khóa chỉ được thêm vào repo trong commit sau đó.
- Lỗi xử lý nhãn trong script review/phân tích được sửa ở PR sửa theo review (#19): nhãn lỗi không còn bị hiển thị như frame không có nhãn; video không mở được hoặc ghi ảnh thất bại làm job báo lỗi; dòng nhãn YOLO sai định dạng dừng phân tích. Bằng chứng run 03a/03b không bị ảnh hưởng: audit W2 không có hộp NaN hoặc w, h ≤ 0 (`annotation_audit_summary.json`); run 03a dựng đủ 358/358 video, `failed` rỗng (`review_v2/stage_status.json`); run 03b `frames_skipped` rỗng (`dataset_card.json`).
- Ghi nhận sau run 05 (22/10/2026) [Kết quả đo + INFERENCE]: ở video dư 1 mục, mục nhãn rỗng duy nhất nằm ở **đầu** (frame 0) — 111/114 video Drone khả kiến có đúng 1 mục rỗng (`annotation_audit.csv`), cả 92/92 video Drone trong `e1-yolo-v1` có frame 0 không nhãn (`yolo_manifest.csv.gz`), trong khi review v2 thấy drone ở frame 0. Điều này nghiêng về offset1 (mục 0 thừa), cùng chiều thăm dò 26/34, nhưng chưa thay quyết định offset0; kiểm chứng ở W4 (#24) rồi mới ghi ADR mới.
