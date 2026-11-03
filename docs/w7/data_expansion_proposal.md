# Đề xuất bổ sung dữ liệu W7–W12 (issue #88)

- Người soạn: Dương Minh Quang, 03/11/2026. Reviewer: Lê Ngọc An.
- Trạng thái: An đã trả lời trên PR #89 (03/11). Quyết định chốt ở `docs/decisions/ADR-0011-external-data-plan.md` (**Accepted**, đã đưa hai sửa đổi của An vào). Chưa tải hay train gì.
- Số liệu Svanström: `results/W06/dataset_coverage.json`, tạo bằng `scripts/reporting/dataset_coverage_stats.py` từ `data/splits/video_split_v1.csv`, run 13 (`analysis_yolo11n_640_s20261030`) và run 14 (`meta.csv`).

## 1. Kết luận
1. **Giữ Svanström làm dữ liệu chính.** Đây vẫn là bộ duy nhất đã kiểm có đúng góc nhìn (camera mặt đất nhìn lên trời), đủ 4 lớp Drone/Bird/Airplane/Helicopter và giấy phép rõ (CC0-1.0). Không thay, không trộn lớn dữ liệu Drone ngoài vào tập train lúc này.
2. **Svanström thiếu ở ba điểm, và chỉ dữ liệu ngoài mới bù được:**
   - G1. Video âm tính để đo cảnh báo sai/giờ. Toàn bộ phần khả kiến không có Drone, cộng cả ba split, chỉ có **29,9 phút**. Thuyết minh mục 13 đặt mục tiêu ≥ 2 giờ, nên không thể đạt chỉ với Svanström.
   - G2. Tập bền vững đêm/độ phân giải thấp. Đề cương W13 yêu cầu "Night/low-resolution subset", nhưng Svanström chỉ quay ban ngày.
   - G3. Khả năng tổng quát sang loại drone và cảnh khác. Svanström chỉ có 3 drone, quay ở 3 sân bay Thụy Điển, nên val/test cùng phân phối với train và lạc quan.
3. **Thêm theo mục đích, ở đúng tuần của thang chấm, ưu tiên dữ liệu chỉ để đánh giá:**
   - W7 (hard negatives + phân tích nhầm lẫn): xây tập âm tính `e1-neg-v1` ≥ 2 giờ để đo cảnh báo sai/giờ, không train lại. Chỉ chạy **một** thí nghiệm train với hard negative nếu điều kiện kích hoạt đặt trước bị chạm.
   - W11 (bền vững + feature freeze): đánh giá ngoài phân phối (OOD) trên DUT Anti-UAV / Anti-UAV300 RGB, cùng biến đổi tổng hợp của test Svanström; chỉ đánh giá.
   - W12: chốt manifest cuối, gồm mọi nguồn ngoài và license.
4. **Chi phí chấp nhận được** nếu giữ đúng phạm vi trên:
   - Các tập chỉ để đánh giá không đổi mô hình nên không phải so sánh lại W3–W6.
   - Thí nghiệm train duy nhất chỉ đổi một yếu tố (dữ liệu), dùng lại script so sánh nhiều seed và đánh giá tracking/cảnh báo đã có.
   - Nếu không đạt luật đặt trước thì giữ mô hình hiện tại và báo cáo là kết quả âm. Việc này vẫn là sản phẩm hợp lệ của W7.

## 2. Svanström đang có gì (ảnh khả kiến)
| Mục | Số liệu | Nguồn |
|---|---|---|
| Video khả kiến theo split | train 199, val 43, test 43 | split v1 |
| Thời lượng (30 fps, 640×512) | train 34,6 phút; val 7,5; test 7,5 | split v1, `meta.csv` run 14 |
| Ảnh huấn luyện `e1-yolo-v1` (stride 10) | train 178 video / 5.667 ảnh; val 38 video / 1.202 ảnh | ADR-0004 |
| Video không có Drone | train 20,8 phút; val 4,6; test 4,5; **tổng 29,9 phút** | `dataset_coverage.json` |
| Val dùng cho cảnh báo (run 14) | 38 video; 21 không có Drone = 3,66 phút | `dataset_coverage.json` |
| Video Drone trong val | 17 | split v1 |
| Điều kiện quay | 3 drone, 3 sân bay Thụy Điển, ban ngày, drone xa nhất 200 m | [WEB SOURCE] Svanström et al., arXiv:2111.01888 |

Detector đang dùng (YOLO11n `s20261030`, val, lạc quan vì val dùng để chọn):
- Drone: P 0,816, R 0,828, AP@0.5 0,804. Mục tiêu trên test là P ≥ 0,85, R ≥ 0,85, mAP@0.5 ≥ 0,80 (ADR-0005).
- Bird: precision thấp nhất, 0,549.
- Nhầm sang Drone: Airplane 15/289 hộp GT; Bird 0/73; Helicopter 0/285.
- Ảnh val không có nhãn: 38/40 ảnh có FP ở conf 0,25.
- Cảnh báo sai của R0 chủ yếu do hộp Drone khác lớp chồng lên Airplane/Helicopter (109/126 frame, `results/W06/duplicate_boxes.json`).

**[INFERENCE] Đọc số liệu một cách phản biện:**
- *Chưa có bằng chứng thiếu dữ liệu train là nút thắt.* AP@0.5:0.95 của Drone thấp (0,26–0,28) có nguyên nhân đã biết: 60,5% hộp Drone < 32×32 px và nhãn lệch 1 frame (ADR-0006). Thêm ảnh Drone từ nguồn khác không sửa hai nguyên nhân này, lại đổi quy ước nhãn.
- *Chưa có bằng chứng chim bị nhầm thành Drone.* Bird→Drone = 0/73 hộp, nhưng 73 hộp này chỉ đến từ 3 video Bird trong val, nên bằng chứng rất yếu theo cả hai chiều. Không thêm dữ liệu chim vào train chỉ vì "drone vs bird nghe hợp lý". Cần tập âm tính lớn hơn để đo.
- *38/40 ảnh "âm tính" có FP không phải FP nền* (đã kiểm sau, `docs/w6/val_negative_frames.md`). 20 ảnh là frame 0 trước frame có nhãn đầu tiên: 18/18 detection chồng hộp GT frame 1. 20 ảnh còn lại là `V_BIRD_041` sau frame 107, khi nhãn hết nhưng track chim vẫn liên tục tới frame 304. Svanström vì vậy không có ảnh nền trống đáng tin để đo FP, nên tập âm tính ngoài càng cần.
- *Thống kê yếu.* 17 video Drone val và 23 sự kiện GT cảnh báo cho khoảng tin cậy rộng. Kết quả "0 cảnh báo sai" của R1 trên 3,66 phút không chứng minh R1 không báo sai (Thuyết minh mục 13 nói rõ điều này).

## 3. Nguồn đã khảo sát
Giấy phép: chỉ ghi điều trang chính thức nói. "Không thấy" nghĩa là chưa tìm thấy, không phải không có.

| Nguồn | Sự kiện [WEB SOURCE] | Giấy phép / truy cập | Đề xuất |
|---|---|---|---|
| **Video tự quay** bầu trời không có UAV | Đề cương mục 8 cho phép "tập video tự thu hoặc sưu tầm hợp pháp"; Thuyết minh 8.1: nguồn bổ sung phải có ghi xuất xứ | Nhóm sở hữu. Cần kiểm quy định nơi quay; không bay drone; tránh quay rõ mặt người | **Chính cho G1** (đánh giá; một phần có thể làm hard negative train nếu kích hoạt) |
| **FBD-SV-2024** (chim bay trong video giám sát) | 483 clip, 28.694 frame (23.833 frame có chim), 1280×720, 25 fps; bbox + track ID; ~50% chim < 32×32 px; split 400/83 video (arXiv:2409.00317) | figshare 1,67 GB; không ghi tên license, chỉ ghi "for learning and research purposes only, not for commercial use" → `needs_review` | **G1, chỉ đánh giá** (cả 483 clip ≈ 19,1 phút; chim khó, nhiều chim nhỏ). Không bao giờ vào train, để không phải chia lại |
| **DUT Anti-UAV** | 10.000 ảnh phát hiện (5.200/2.600/2.200), 20 chuỗi tracking 1080p/720p; khả kiến; > 35 loại UAV; ngày/đêm/bình minh/hoàng hôn; nhiều cảnh (arXiv:2205.10851) | Repo ghi Apache-2.0, không nói phần dữ liệu → `needs_review` | **G2 + G3 ở W11** (chỉ đánh giá, kể cả tập con đêm/hoàng hôn) |
| **Anti-UAV** (phần RGB của Anti-UAV300) | RGB + IR, bbox, thuộc tính, cờ có/không có mục tiêu theo frame; 410/600 chỉ IR | MIT cho mã dự án, dữ liệu không ghi điều khoản → `needs_review` (như W1) | **G3 ở W11** (chỉ RGB, chỉ đánh giá). Một mục tiêu mỗi chuỗi nên có danh tính thật, dùng để kiểm chéo cách đo GT dẫn xuất của ADR-0008 |
| **Drone-vs-Bird** (WOSDETC) | Drone xuất hiện cùng chim; nhãn theo frame có trường lớp; khảo sát 2025 ghi 77 chuỗi | Phải gửi email `wosdetc@googlegroups.com` và ký thỏa thuận sử dụng, chỉ cho nghiên cứu | **Gửi yêu cầu ngay** vì cần thời gian chờ; có trước W10 thì dùng đánh giá OOD ở W11, không có thì bỏ |
| MAV-VID | 64 video (benchmark Isaac-Medina et al.) | Nguồn Kaggle đã hỏng theo repo benchmark | Dự phòng |
| Anti-UAV410/600, AOT | Hồng ngoại / quay từ máy bay | — | Ngoài phạm vi (ADR-0005: khả kiến là nhánh chính) |
| Det-Fly, NPS-Drones, FL-Drones | Không đối không, hoặc góc nhìn khác | — | Chỉ tham khảo |
| VisDrone, UAVDT | Camera đặt trên UAV nhìn xuống | — | Chỉ tham khảo (giữ quyết định W1) |
| Bộ gộp Roboflow/Kaggle, clip YouTube | Không rõ xuất xứ, có thể chứa chính frame Svanström (rò rỉ test) | Không rõ | **Loại** |
| Dữ liệu tổng hợp (vd. SynDroneVision) | Ảnh render | — | Chỉ tham khảo. Nếu dùng thì báo tách riêng (Thuyết minh 8.1) |

Biến đổi tổng hợp của test Svanström (giảm độ phân giải, làm tối, nhiễu, mờ) không cần license. Đây là cách rẻ nhất cho tập "low-resolution" của W13 và phải báo tách riêng khỏi kết quả video thật.

## 4. Khớp với kế hoạch của thầy
Thứ tự tuần theo thang chấm cột E1 (ADR-0005, 4A). Đề cương và Thuyết minh xếp hard negative ở W10. Thang chấm xếp ở W7, nên làm ở W7 khớp cả hai: W10 vẫn có phân tích lỗi cuối.

| Tuần | Thang chấm | Việc dữ liệu đề xuất | Đổi mô hình? |
|---|---|---|---|
| W6 (tới 07/11) | geofence + cảnh báo | Tài liệu này, ADR-0011 Proposed, An duyệt; gửi yêu cầu Drone-vs-Bird; đọc điều khoản FBD-SV, DUT, Anti-UAV. Chưa tải. | Không |
| **W7** (08–14/11) | **hard negatives + phân tích nhầm lẫn** | An: phân tích nhầm lẫn trên val, xem tận mắt 38 ảnh âm tính có FP. Quang: quay và lập manifest `e1-neg-v1`, job Kaggle đo cảnh báo sai/giờ (R0, R1) bằng mô hình hiện tại. Thí nghiệm train `e1-yolo-v1-hn` chỉ chạy khi điều kiện kích hoạt bị chạm. | Chỉ khi kích hoạt và đạt luật |
| W8–W9 | E2E/dashboard, FPS | Không đổi dữ liệu. Nếu W7 chọn v2 thì chạy lại tracking và cảnh báo một lần (script có sẵn). | Không |
| W10 | test detection + tracking | Test Svanström mở một lần. Cảnh báo sai/giờ cuối trên phần đánh giá của `e1-neg-v1`. | Không |
| W11 | bền vững, freeze, benchmark cố định | Đánh giá OOD: DUT (gồm tập con đêm/hoàng hôn), Anti-UAV300 RGB, Drone-vs-Bird nếu có; biến đổi tổng hợp của test. | Không (đã freeze) |
| W12 | thực nghiệm/ablation | Manifest cuối + license matrix. Có thể thêm một ablation thăm dò, báo tách riêng, không đổi mô hình cuối. | Không |

## 5. Chi phí và cách giữ gọn
| Loại bổ sung | Việc phải làm | Có phải so sánh lại W3–W6? | Ước lượng |
|---|---|---|---|
| Tập âm tính chỉ để đánh giá (G1) | Quay, cắt, manifest + SHA-256; một job Kaggle chạy detector + ByteTrack-e1 + `evaluate_alerts` (không cần GT hộp) | Không | Khoảng 2 giờ video ≈ 216 nghìn frame. Detector 3,3 ms/ảnh → khoảng 15–30 phút GPU. Phần tốn là công quay: 8 buổi × ≥ 20 phút (2 buổi `neg_train`, 6 buổi `neg_eval` ≈ 120 phút) |
| Thí nghiệm hard negative (chỉ khi kích hoạt) | `e1-yolo-v1-hn` = v1 + frame âm tính của các buổi train; YOLO11n cùng cấu hình, 3 seed; `build_seed_comparison.py`; chạy lại tracking/cảnh báo như run 14 | Chỉ so v2 với v1 trên cùng val (một yếu tố) | Run 13: YOLO11n mất 19–22 phút/seed trên 5.667 ảnh. Thêm 2–3 nghìn ảnh → khoảng 30 phút/seed, 3 seed ≈ 1,5 giờ GPU |
| Đánh giá OOD W11 | Script chuyển nhãn DUT/Anti-UAV sang định dạng GT của `w5_track_metrics`; một job Kaggle | Không | 1 job, chủ yếu tốn công viết bộ chuyển đổi và pytest |
| **Không đề xuất:** trộn ảnh Drone ngoài vào train trước W11 | Kiểm nhãn bộ mới, cân bằng lớp, đổi fingerprint, train lại mọi cấu hình, so sánh lại tracker và cảnh báo | **Có, toàn bộ** | Cao, lợi ích chưa có bằng chứng |

Rủi ro chính và cách giảm:
- Rò rỉ: buổi quay dùng để train và buổi dùng để đánh giá tách theo buổi, gán trước khi chạy detector. Nguồn ngoài (FBD-SV, DUT, Anti-UAV, Drone-vs-Bird) không bao giờ vào train.
- Ngân sách thời lượng G1: FBD-SV 19,1 phút + val Svanström 3,66 phút ≈ 23 phút, nên phần đánh giá của video tự quay cần **≥ 97 phút** để đạt 2 giờ. Test Svanström (4,5 phút) chỉ cộng vào ở W10.
- Lệch miền: điện thoại hoặc camera khác cảm biến Svanström. Với tập âm tính, lệch miền là thực tế chứ không phải lỗi; ghi rõ thiết bị, độ phân giải và cách resize trong manifest.
- License chưa rõ: nguồn `needs_review` chỉ dùng đánh giá nội bộ, không đưa frame vào Git hay báo cáo công khai, chỉ ghi manifest + SHA-256 + trích dẫn.
- Thời gian W7: nếu tới thứ Tư 11/11 chưa đủ ≥ 2 giờ âm tính thì báo thời lượng thực có (Thuyết minh mục 13 cho phép) và bỏ thí nghiệm train.

## 6. Cần An cho ý kiến (trả lời trên PR)
1. Đồng ý giữ Svanström làm nguồn chính và **không** trộn ảnh Drone ngoài vào train trước W11?
2. Điều kiện kích hoạt và luật chọn v2 ở ADR-0011 mục 3–4: đồng ý, hoặc đề xuất ngưỡng khác **trước** khi có dữ liệu âm tính.
3. Lịch quay video: mỗi người ít nhất 4 buổi × 20 phút (điện thoại cố định trên chân máy), ở nơi công cộng được phép quay, khác ngày/giờ/hướng trời. Ai quay buổi nào?
4. W11 dùng DUT hay Anti-UAV300 RGB làm tập OOD chính, nếu chỉ kịp một bộ?
