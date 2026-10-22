# ADR-0005: Chỉ tiêu, modality, tracker và thứ tự tuần W4–W6

- Trạng thái: **Proposed – áp dụng tạm** (Quang soạn 21/10/2026 theo lựa chọn của An trên #7). Chuyển **Accepted** khi GVHD xác nhận; nếu GVHD sửa thì ghi bản mới của ADR này.
- Liên quan: #7 (W2-06), ADR-0002 (modality), ADR-0004 (baseline A).

## Bối cảnh
- [DOCUMENT] Ba tài liệu kế hoạch lệch nhau: Đề cương W5 = augmentation vật thể nhỏ, W6 = tích hợp tracker; Thuyết minh W5 = ByteTrack, W6 = đối chiếu tracker; thang chấm cột E1: W5 = "tích hợp tracker, video test ID ổn định", W6 = "geofence + cảnh báo theo trajectory", tracker ghi "ByteTrack/DeepSORT".
- [DOCUMENT] Ngưỡng định lượng đề xuất: Thuyết minh mục 12.
- [Kết quả đo] Ảnh khả kiến: 60,5% hộp Drone nhỏ hơn 32×32 px; ảnh IR: 98,9% (`results/W02/kaggle_run_01/class_stats.csv`). 58 video có bước nhảy tâm hộp lớn, một phần do camera xoay/zoom (`docs/w2/annotation_audit_w2.md`).
- [WEB SOURCE] Cảm biến của bộ Svanström đặt trên đế pan-tilt (Svanström et al., arXiv:2111.01888). Ultralytics hỗ trợ sẵn `bytetrack.yaml` và `botsort.yaml` (docs.ultralytics.com/modes/track); DeepSORT không có sẵn.
- Tài liệu so sánh phương án: `docs/w3/E1_issue7_chot_chi_tieu_modality_tracker.docx`. Lựa chọn của An: comment trên #7 ngày 21/10/2026 (1A, 2A, 3A, 4A); Quang đồng ý.

## Quyết định [DECISION]
1. **Chỉ tiêu (1A)** — là *mục tiêu*, chưa phải cam kết:
   - Phát hiện, lớp Drone, tập test: Precision ≥ 0,85, Recall ≥ 0,85, mAP@0.5 ≥ 0,80.
   - Cảnh báo: giảm ≥ 30% cảnh báo giả so với chỉ dùng detector; event recall giảm ≤ 5 điểm %.
   - Thời gian thực: ≥ 15 FPS toàn pipeline, p95 ≤ 500 ms, đo ≥ 3 lần trên GPU tham chiếu.
   - GPU tham chiếu = GPU Kaggle ghi trong `env.json` của lần đo cuối; báo tên GPU cùng số đo.
   - W3–W4 chỉ báo cáo trên validation; test khóa tới đánh giá cuối (W10). Sau baseline được điều chỉnh ngưỡng **một lần** qua bản mới của ADR này, kèm lý do và số liệu.
2. **Modality (2A)**: ảnh khả kiến là nhánh chính cho mọi chỉ tiêu. IR là thí nghiệm phụ, báo cáo riêng ở giai đoạn sau, không gộp vào con số chính.
3. **Tracker (3A)**: ByteTrack là tracker chính; BoT-SORT đối chiếu trên cùng tập detection. Svanström không có track ID: chỉ đo ID switch / độ ổn định trên "1 track/video" dẫn xuất và ghi rõ đây **không phải ground truth**; không báo HOTA/IDF1 như kết quả chính.
4. **Thứ tự tuần (4A)**, theo thang chấm của GVHD:
   - W4: tuning + augmentation, gồm augmentation vật thể nhỏ (chuyển từ W5 của Đề cương).
   - W5: tích hợp tracker.
   - W6: geofence + cảnh báo theo trajectory.

## Hệ quả
- W4 (#24 và các issue W4) bao gồm augmentation vật thể nhỏ.
- Chênh lệch giữa chữ "DeepSORT" trong thang chấm và 3A cần GVHD đồng ý; nếu GVHD yêu cầu DeepSORT thì thêm như phương án đối chiếu thứ ba (3C).
- Khi GVHD sửa ngưỡng, sửa thứ tự tuần hoặc sửa tracker → ghi bản mới của ADR này, cập nhật v0.x của báo cáo (Bảng 1, Bảng 4) và W_PLAN của tuần liên quan.

## Còn mở (đóng #7 khi có)
- [ ] GVHD xác nhận ngưỡng 1A, GPU tham chiếu và thứ tự tuần 4A (ghi ngày, hình thức, kết luận vào #7).
- [ ] GVHD đồng ý ByteTrack + BoT-SORT thay cho "ByteTrack/DeepSORT".
