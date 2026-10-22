# Hướng dẫn cho An — W4 (hạn 24/10/2026)

Người soạn: Quang · 22/10/2026 · Kế hoạch tuần: `docs/w4/W4_PLAN.md` · Quy trình GitHub: `docs/governance/github_workflow.md`

Mỗi việc làm trên **một nhánh tạo mới từ `main`** (GitHub Desktop: main → Fetch/Pull → New Branch). Tạo PR xong thì chọn reviewer `itsmarcusduong`; merge sau khi Quang approve.

## Thứ tự ưu tiên
| # | Issue | Việc | Hạn đề xuất | Chặn việc khác? |
|---|---|---|---|---|
| 1 | #38 W4-04 | Giao thức + config detector B và biến thể augmentation | 22/10 tối | **Có** — Quang chưa train B được nếu chưa có config |
| 2 | #5 W2-04 | Review ADR-0002, ADR-0003 → Accepted/Rejected | 23/10 | Có — split phải đóng băng trước khi train lại |
| 3 | #24 W4-01 | Vẽ tập chuẩn CVAT (khi Quang gửi gói ảnh) + kiểm tra 40 video review v2 | 23/10 | Không (kiểm chứng thứ hai) |
| 4 | #41 W4-07 | Version v0.4: mục 2.1, 2.2 (hạn nháp 24/10 theo template) | 24/10 | Không |
| 5 | #40 W4-06 | Phân tích bảng so sánh A/B/aug + model card B | sau run 09/10 | — |

---

## 1. #38 — Giao thức và config detector B + augmentation
Nhánh `issue-38-detector-b-config`. Tạo 3 file:

**a) `configs/detector_B.yaml`**: copy `configs/baseline_A.yaml`, chỉ đổi:
- `experiment: detector_B`
- `model: yolov8s.pt` (Thuyết minh 7.2: YOLOv8s @960)
- `train.imgsz: 960`, `val.imgsz: 960`
- `train.batch`: T4 15 GB với YOLOv8s @960 có thể không đủ bộ nhớ ở batch 32 → đề xuất `16` và ghi lý do. Không để `-1` (auto) vì làm khó tái lập.
- Giữ nguyên `epochs: 50`, `patience: 15`, `seed: 20261013`, `deterministic: true`, `optimizer: auto`.

**b) `configs/baseline_A_aug.yaml`**: copy baseline A, `experiment: baseline_A_aug`, chỉ đổi **tham số augmentation**, còn lại giữ nguyên để so sánh công bằng. Gợi ý cho vật thể nhỏ (chọn tối đa 2–3 thay đổi, mỗi thay đổi có lý do):
- `scale` (mặc định 0.5): giảm xuống 0.3 để ít thu nhỏ vật đã nhỏ, hoặc giữ nguyên;
- `mosaic` (mặc định 1.0) giữ nguyên, `close_mosaic: 10` giữ nguyên;
- `degrees`, `translate`, `fliplr`: giữ mặc định nếu không có lý do;
- Không dùng `copy_paste` (cần nhãn segmentation, dữ liệu chỉ có hộp).
Tham khảo danh sách tham số: https://docs.ultralytics.com/usage/cfg/#augmentation-settings-and-hyperparameters

**c) `docs/w4/training_protocol_w4.md`**: bảng 3 cấu hình (A, A_aug, B): model, imgsz, batch, tham số đổi so với A, lý do. Ghi rõ:
- dữ liệu dùng chung (e1-yolo-v1 hoặc v2 tùy ADR-0006, Quang điền sau run 06);
- chỉ báo cáo trên val, số liệu lạc quan;
- chọn ngưỡng vận hành theo mục 7 giao thức W3 (F1 Drone);
- nếu đủ GPU: thêm `YOLOv8n @960` để tách ảnh hưởng độ phân giải khỏi kiến trúc (Thuyết minh 7.2).

Commit: `docs(w4): add detector B and augmentation configs with protocol (#38)`. PR title: `W4-04: config detector B (YOLOv8s@960) và biến thể augmentation (#38)`, cuối mô tả ghi `Closes #38`.

## 2. #5 — Review ADR-0002 và ADR-0003
Nhánh `issue-5-adr-review`. Đọc `docs/decisions/ADR-0002-*.md`, `ADR-0003-*.md`, `docs/w2/split_protocol.md`.
- ADR-0002: phần thứ tự tuần và tracker đã được ADR-0005 thay thế → đổi trạng thái thành `Superseded by ADR-0005 (mục 1–2)`, phần còn lại (SQLite cho MVP, modality) ghi `Accepted` nếu đồng ý.
- ADR-0003: mục 2 (loại video dư 1 mục) đã được ADR-0004 thay thế; phần split theo video 70/15/15, seed 20261217, test khóa → `Accepted` nếu đồng ý. Ghi ngày, người duyệt, lý do; không đồng ý điểm nào thì ghi rõ và đề xuất sửa.
- Thêm dòng vào cuối mỗi ADR: `Duyệt: Lê Ngọc An, <ngày>`.
Commit: `docs(adr): review ADR-0002 and ADR-0003 (#5)`. PR ghi `Closes #5`.

## 3. #24 — Tập chuẩn CVAT và kiểm tra review v2
- Quang chạy Kaggle run 11, gửi An **chỉ** file `cvat_package.zip`. Làm theo `docs/w4/cvat_gold_guide.md` (quy tắc mù, cách tạo task, quy tắc vẽ, xuất YOLO 1.1).
- Nộp: nhánh `issue-24-cvat-annotations`, file `results/W04/cvat_gold/cvat_gold_an_YYYYMMDD.zip` + `notes_an.md`; PR title `W4-01: annotation tập chuẩn CVAT (#24)`. Không mở bất kỳ kết quả run 06 nào trước khi PR này có trên GitHub.
- Kiểm tra review v2: trong `results/W03/review/review_assignment_w3.csv`, điền cột `verdict` (OK / SAI_NHAN / KHONG_RO) và `notes` cho **40 video** dưới đây (chọn ngẫu nhiên, seed 20261022), xem ít nhất 8 frame mỗi video trên review sheet của run 03a hoặc video gốc:

  IR_AIRPLANE_003, IR_AIRPLANE_009, IR_BIRD_005, IR_BIRD_010, IR_BIRD_011, IR_BIRD_012, IR_BIRD_014, IR_BIRD_035, IR_BIRD_036, IR_BIRD_039, IR_BIRD_040, IR_BIRD_048, IR_BIRD_053, IR_BIRD_056, IR_BIRD_057, IR_BIRD_069, IR_DRONE_005, IR_DRONE_013, IR_DRONE_047, IR_DRONE_074, IR_DRONE_094, IR_DRONE_101, IR_DRONE_155, IR_HELICOPTER_045, V_BIRD_002, V_BIRD_004, V_BIRD_012, V_DRONE_003, V_DRONE_007, V_DRONE_016, V_DRONE_033, V_DRONE_052, V_DRONE_069, V_DRONE_072, V_DRONE_074, V_DRONE_075, V_DRONE_091, V_DRONE_100, V_DRONE_109, V_HELICOPTER_037

  Điền **trước khi** xem cột `review_quang_v2` của video đó (che cột hoặc sắp xếp lại). Commit cùng nhánh #24: `data(w4): add An verdict for 40 review v2 videos (#24)`.

## 4. #41 — Version v0.4, mục 2.1 và 2.2
Viết vào file nháp `docs/w4/chuong2_nhap_An.md` (Quang chuyển vào template Word, giữ định dạng). Mỗi ý quan trọng có trích dẫn [n] theo danh mục tài liệu tham khảo hiện có (v0.3, [1]–[12]); tài liệu mới thì ghi đủ tác giả, tên, hội nghị/tạp chí, năm, link.
- **2.1 Kiến thức nền tảng** (2–3 trang): phát hiện vật thể một giai đoạn (YOLO: backbone–neck–head, anchor-free, NMS), DETR/RT-DETR [6]; theo dõi đa đối tượng tracking-by-detection: Kalman filter, Hungarian, ByteTrack [2] (liên kết cả hộp điểm thấp), BoT-SORT [3] (bù chuyển động camera, ReID); độ đo: IoU, P/R/F1, AP, mAP@0.5, mAP@0.5:0.95, HOTA, IDF1, ID switch. Chèn 1 hình sơ đồ tracking-by-detection (tự vẽ, có chú thích nguồn).
- **2.2 Công trình liên quan** (1–2 trang): bảng so sánh ≥ 5 công trình/bộ dữ liệu: Svanström [11], Anti-UAV, VisDrone [4][5], UAVDT [7], ByteTrack/BoT-SORT; cột: bài toán, dữ liệu, phương pháp, độ đo, hạn chế, khác biệt với đồ án. Không chép abstract.
Commit: `docs(w4): draft thesis sections 2.1 and 2.2 (#41)`.

## 5. #40 — Phân tích so sánh (sau khi Quang có run 09/10)
Quang gửi bảng số liệu `results/W04/comparison_w4.csv`. An viết phần phân tích: so sánh theo lớp, theo cỡ hộp, đánh đổi độ chính xác – thời gian suy luận, cấu hình nào làm baseline cho W5; điền `docs/w4/model_card_detector_B.md` theo mẫu `docs/w3/model_card_baseline_A.md` (chú ý cách đọc P/R mục 4).
