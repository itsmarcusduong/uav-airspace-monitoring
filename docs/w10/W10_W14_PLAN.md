# Kế hoạch W10–W14 rút gọn (30/11–09/12/2026), ADR-0017

Viết 29/11/2026, trước khi mở test và trước khi có danh sách ứng viên mới. Quang quyết định không cắt nội dung (ADR-0017 bối cảnh). Mọi luật chọn ghi ở đây hoặc trong giao thức riêng được commit **trước** khi chạy phần tương ứng.

## 1. Hiện trạng đầu W10 (nguồn: `docs/status/W09_planned_done_evidence.md`)
- Detector YOLO11n `s20261030`, NMS cùng lớp IoU 0,5 (V2), ByteTrack-e1, luật R1, cấu hình suy luận theo luật C của W9.
- Âm tính đã đo: FBD-SV-2024 19,13 phút; val Svanström không Drone 3,7 phút.
- Commons: 83 ứng viên (133,3 phút trước sàng lọc), Quang đã sàng lọc, chờ An.
- Điều kiện hard negative ADR-0011 mục 3 đã đạt (W9).

## 2. Ước lượng thời lượng âm tính (mục tiêu ADR-0011: `neg_eval` ≥ 120 phút) [INFERENCE]

| Nguồn | neg_eval dự kiến | Căn cứ |
|---|---|---|
| FBD-SV-2024 | 19,1 phút | đã đo (run 19b3) |
| Svanström val không Drone | 3,7 phút | W6 |
| Svanström test không Drone (26 video khả kiến) | khoảng 4,5 phút | 8165 frame / 30 fps trong `data/splits/video_split_v1.csv`; cộng ở W10 (ADR-0011 mục 2) |
| Wikimedia Commons | chưa biết, khoảng 20–33 phút | 133,3 phút ứng viên; nếu giữ 1/5–1/3 và 3/4 thời lượng vào neg_eval; chốt sau khi gộp |
| **Còn thiếu** | **khoảng 60–70 phút** | mở rộng Commons (mục 2b) |

- Để có khoảng 70 phút neg_eval cần khoảng 95 phút clip được cả hai người giữ. Với tỷ lệ giữ khoảng 1/3, danh sách ứng viên mới cần **≥ 300 phút**.
- Sàng lọc 300 phút clip mất khoảng 4–5 giờ mỗi người. Đây là việc trên đường găng của W10.

## 2b. Pixabay và Pexels không dùng được (kiểm 29/11) [WEB SOURCE]
- Terms of Service của Pixabay và Pexels (cùng cập nhật 20/10/2026), mục 8: cấm thu thập tự động và scraping cho mục đích không được phép, nêu rõ gồm học máy; cấm sao chép hàng loạt hoặc có hệ thống. Tài liệu API của Pixabay cũng cấm tải hàng loạt có hệ thống. Bằng chứng: `data/manifests/license_evidence/pixabay_pexels_terms_2026-11-29.md`.
- Dùng clip làm `neg_train` hoặc `neg_eval` cho mô hình là mục đích học máy, nên hai nguồn chuyển sang `needs_review` trong `license_matrix.csv` và không dùng nếu chưa có cho phép bằng văn bản.
- Quang chốt 29/11 (ADR-0018, giao thức `docs/w10/neg_sources_v2_protocol.md`): **AirBirds** (camera đường băng sân bay, chỉ `neg_eval`) + **Commons v2**; DVIDS dự phòng; Pixabay chờ email cho phép.
- Chi tiết Commons v2: **Wikimedia Commons v2**, thêm category (chim, đàn chim, mòng biển, ngỗng, máy bay dân dụng, trực thăng, bầu trời; gồm subcategory một cấp), cùng bộ lọc và cùng giao thức sàng lọc; danh sách category commit trước khi chạy. Giấy phép CC0/CC BY/CC BY-SA cho phép dùng cho học máy khi ghi công.
- Nếu Commons v2 không đủ: báo đúng thời lượng thực có (ADR-0011 mục 2), không hạ tiêu chí.

## 3. Việc theo thứ tự phụ thuộc

### Tuan10 (30/11–02/12): tập âm tính, hard negative, test
| # | Việc | Người | Phụ thuộc | GPU |
|---|---|---|---|---|
| 10.1 | An sàng lọc Commons (tệp riêng), gửi Quang | An | — | — |
| 10.2 | Phụ lục giao thức Commons v2 (category mới, subcategory một cấp; loại trùng với v1) — commit **trước** khi lấy danh sách | Quang viết, An review ≤ 6 giờ | — | — |
| 10.3 | Chạy `commons_manifest.py` với category v2 trên máy có Internet → ứng viên mới ≥ 300 phút | Quang | 10.2 | — |
| 10.3b | AirBirds: Quang điền form; khi có link, kiểm LICENSE, tải theo thứ tự phần vào Kaggle; sàng lọc mẫu hai người (đầu/giữa/cuối mỗi chuỗi) | Quang, An | form | tùy link |
| 10.4 | Gộp Commons (`commons_manifest.py --finalize`) → `neg_commons_v1` | Quang | 10.1 | — |
| 10.5 | Sàng lọc Commons v2, hai tệp độc lập | Quang, An | 10.3 | — |
| 10.6 | Job Kaggle: tải, kiểm SHA, chuẩn hóa Commons v1 (+ v2 khi xong); đo C0 trên `neg_eval`; xuất frame stride 10 của `neg_train` | Quang | 10.4 (10.5) | khoảng 1 giờ |
| 10.7 | Train `e1-yolo-v1-hn` 3 seed (ADR-0011 mục 4: chỉ thêm `neg_train`, nhãn rỗng) + đánh giá val + đo `neg_eval` | Quang | 10.6 | khoảng 1,5 giờ (20 phút/seed) |
| 10.8 | Áp luật ADR-0011 mục 4 → chọn v1 hoặc `-hn` | Quang, An kiểm | 10.7 | — |
| 10.9 | Giao thức đánh giá test (metric, theo lớp/cỡ hộp/video, R0/R1, GT dẫn xuất ADR-0008, bootstrap theo video) — commit trước khi mở test | An viết, Quang review | — | — |
| 10.10 | **Mở test**: detection + tracking + cảnh báo với mô hình đã chọn; cộng test không Drone vào neg_eval | Quang | 10.8, 10.9 | khoảng 1 giờ |
| 10.11 | Phân tích lỗi trên test (lớp, cỡ hộp, video, ma trận nhầm) | An | 10.10 | — |
| 10.12 | Báo cáo W10, v0.10, Evidence/W10 | Quang | 10.10 | — |

### Tuan11 (03/12–05/12): độ bền, feature freeze, benchmark cố định, tag `w11`
- Biến đổi tổng hợp trên test (giảm độ phân giải, làm tối, mờ, nhiễu, nén JPEG), báo tách riêng (ADR-0011 mục 5).
- OOD: RGB của Anti-UAV300 và UAVDB (CC BY 4.0) sau khi kiểm license; chỉ báo cáo, không chọn mô hình.
- Feature freeze: khóa code, cấu hình, weights (SHA-256).
- Benchmark cố định trên test: FPS/p95 ≥ 3 lần với cấu hình đã chọn; chạy ổn định 60 phút lại với bộ đo ghi độ trễ xuống đĩa.
- Báo cáo W11, v0.11, Evidence/W11, **tag `w11`**.

### Tuan12 (06/12–07/12): ablation, thống kê
- Bảng ablation trên cùng dữ liệu: V0/V1/V2, ByteTrack và BoT-SORT, R0/R1, có/không hard negative, C0/C1/C2, imgsz.
- Mô hình cuối ≥ 3 seed; kiểm định có đối chứng (bootstrap theo video, ghép cặp); chênh < 0,01 mAP@0.5:0.95 với một seed coi là hòa.
- Nếu còn GPU và thời gian: một detector lớn hơn (vd. YOLO11s) với **đúng một yếu tố đổi** so với mô hình cuối, luật chọn commit trước.
- Báo cáo W12, v0.12.

### Tuan13 (08/12): demo, quyển
- Video demo với mô hình và cấu hình cuối (dashboard + cảnh báo), tập dượt.
- Hoàn thiện Chương V–VI, kết luận, tài liệu tham khảo; đọc soát toàn bộ.
- Báo cáo W13, v0.13.

### Tuan14 (09/12): release
- README, release `v1.0`, **tag `w14`**, PDF quyển đồ án và báo cáo cuối; Quang đính PDF vào release, Drive.

## 4. Nhịp làm việc
- Mỗi ngày 21:00: Quang và An cập nhật trạng thái theo bảng trên (issue comment), chốt việc ngày mai.
- Việc sau bắt đầu ngay khi việc trước có kết quả, không chờ hết ngày.
- Review của An theo ADR-0017 mục 5 (≤ 6 giờ cho luật/ADR; sàng lọc hai người không bỏ qua).

## 5. Ngân sách GPU
- 29/11: còn khoảng 24 giờ trong tuần.
- W10 dự kiến khoảng 4 giờ (10.6, 10.7, 10.10 và một lần chạy lại dự phòng).
- Mỗi job ghi thời gian thực vào README kết quả để cập nhật bảng này.

## 6. Rủi ro
| Rủi ro | Dấu hiệu | Ứng phó |
|---|---|---|
| Kaggle GPU xếp hàng lâu | QUEUED > 30 phút | Không chạy song song job phụ thuộc; chuẩn bị job kế tiếp trong lúc chờ |
| Sàng lọc Commons v2 chậm | 01/12 tối chưa xong | Đo Commons v1 trước; v2 vào neg_eval ở lần đo tiếp theo, vẫn trước W11 |
| `neg_train` quá nhỏ để hard negative có tác dụng | ít hơn 10 phút | Vẫn chạy theo luật; kết quả âm được báo cáo (ADR-0011 mục 4) |
| Không đủ 120 phút | sau 05/12 | Báo đúng thời lượng thực có, không hạ tiêu chí sàng lọc |
