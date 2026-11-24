# W9 (22/11–28/11/2026): Tối ưu suy luận, FPS/độ trễ; tập âm tính

Mốc tuần:
- Thang chấm cột E1, W9: "tối ưu inference, FPS/latency".
- Đề cương: "Optimization FPS/latency", sản phẩm "Benchmark GPU/CPU/TensorRT if possible", dữ liệu "Fixed benchmark videos".
- Thuyết minh mục 12 (NFR1): GPU tham chiếu, batch 1, một luồng; ≥ 15 FPS toàn pipeline, độ trễ p95 ≤ 500 ms; đo ≥ 3 lần, báo trung vị và p95; chạy ổn định 60 phút, ghi lỗi và RAM.
- Template: mục 4.3, 4.4 hạn 28/11.
- W9 không bắt buộc tag; ghi SHA commit cuối tuần. Test vẫn khóa: mọi số đo trên **val**.

**Mọi luật ở mục B–E được viết và merge trước khi chạy job tương ứng. Không sửa luật sau khi có kết quả.**

## A. Issue và phân công (milestone Tuan9)
| Issue | Việc | Phụ trách | Review | Evidence |
|---|---|---|---|---|
| #129 W9-01 | Pipeline `e1pipe` chạy từng frame, có `stage_latency_ms`; cổng tái tạo so với run 17 (mục B) | Quang | An | `scripts/pipeline/e1pipe.py`, pytest, `results/W09/` |
| #130 W9-02 | Benchmark FPS/độ trễ: C0, C1, C2, CPU; chạy ổn định 60 phút; chọn cấu hình theo luật C | Quang | An | `results/W09/benchmark/`, CSV phần cứng |
| #131 W9-03 | Tập âm tính `e1-neg-v1` (tiếp #113): chuẩn hóa FBD-SV-2024; manifest Wikimedia/Pixabay; đo cảnh báo sai/giờ (mục D) | Quang | An | `data/manifests/`, `results/W09/neg_eval/` |
| #132 W9-04 | Duyệt W9_PLAN (luật B–E) và ADR-0016 **trước khi chạy**; sàng lọc độc lập clip âm tính | An | Quang | review PR, bảng sàng lọc |
| #133 W9-05 | Chương IV: cập nhật 4.3 (mô-đun AI), viết 4.4 (bảo mật, riêng tư, rủi ro) | An | Quang | `docs/w9/chuong4_4.3_4.4_nhap_An.md` |
| #134 W9-06 | Báo cáo W9, v0.9, Evidence/W09, commit cuối tuần | Quang | An | `reports/w9/`, `Evidence/W09/` |

## B. Pipeline từng frame và cổng tái tạo
`e1pipe` xử lý tuần tự từng frame:

| Bước | Nội dung |
|---|---|
| decode | `cv2.VideoCapture.read()` |
| detect | Ultralytics `predict`: YOLO11n s20261030 (SHA `a3de1e01…`), conf 0,1, NMS cùng lớp IoU 0,5 (V2, mục 5.3.8), imgsz 640, batch 1; gồm tiền xử lý, hậu xử lý và chép kết quả về CPU |
| track | `BYTETracker` của Ultralytics 8.4.183 với `configs/tracker_bytetrack_e1.yaml` |
| alert | R1 chạy trực tuyến; cùng mã với `alert_engine.r1_alerts` (ADR-0009, `configs/alert_e1.yaml`, ROI `center_hex`, điểm tâm) |
| persist | ghi `FrameResult` (JSONL nén) và sự kiện đã chốt vào SQLite (`e1store`) |

- Mỗi `FrameResult` ghi `stage_latency_ms` của 5 bước và `total`. `total` tính từ trước lúc đọc frame tới sau lúc ghi xong.
- **Cổng tái tạo** chạy trên 38 video val với cấu hình C0, phải đạt cả ba điều kiện:
  1. track log khớp run 17 ở ≥ 99% dòng (cùng frame, ID, lớp; mỗi tọa độ lệch ≤ 0,05 px);
  2. sự kiện R1 trùng từng khung frame với bundle run 17 (25 sự kiện);
  3. R1 trực tuyến cho đúng kết quả của `r1_alerts` khi chạy cùng track log (pytest).
- Không đạt cổng thì không báo FPS là "FPS pipeline". Tìm nguyên nhân trước khi chạy mục C.

## C. Benchmark và luật chọn cấu hình vận hành
**Bộ video cố định:** 38 video khả kiến tập val (11.821 frame, 6,57 phút), theo `results/W08/kaggle_run_17/w8_run17/meta.csv`, đọc theo thứ tự `video_id`. Mỗi video được kiểm SHA-256 trước khi chạy.

**Phần cứng:** Kaggle, 1 × Tesla T4, batch 1, một luồng. Ghi `nvidia-smi`, CPU, RAM, phiên bản thư viện vào `env.json`.

**Cấu hình** (mỗi cấu hình chỉ đổi một yếu tố so với cấu hình liền trước: C1 so với C0 đổi độ chính xác số; C2 so với C1 đổi runtime):

| Mã | Runtime | Độ chính xác số | Ghi chú |
|---|---|---|---|
| C0 | PyTorch (Ultralytics) | fp32 | như run 17 |
| C1 | PyTorch | fp16 (`quantize=16`) | |
| C2 | TensorRT (engine xuất từ cùng weights, imgsz 640, batch 1) | fp16 | engine có kích thước đầu vào cố định 640×640, nên ảnh 640×512 được đệm thành hình vuông thay vì đệm theo chữ nhật như PyTorch; khác biệt này đi kèm runtime và được ghi nhận, không tách riêng. Nếu xuất engine thất bại: ghi "không khả thi" kèm log, không thử lại bằng cấu hình khác |
| CPU | PyTorch trên CPU Kaggle | fp32 | chỉ báo cáo, không tham gia chọn |

**Cách đo:**
- Mỗi cấu hình chạy **3 lần**, mỗi lần một tiến trình mới. 30 frame đầu của video đầu tiên là khởi động, không tính.
- FPS của một lần chạy = số frame / tổng thời gian tường.
- Độ trễ: p50 và p95 của `total` qua mọi frame; p50 và p95 của từng bước.
- Báo trung vị của 3 lần chạy, kèm min và max. Ghi bộ nhớ GPU đỉnh và RSS.
- CPU chạy 1 lần trên 5 video đầu, vì chỉ để báo cáo.

**Luật chọn cấu hình vận hành:**
1. **Đạt NFR1:** trung vị FPS ≥ 15 **và** trung vị p95 `total` ≤ 500 ms.
2. **Không xấu đi về độ chính xác so với C0**, cùng 38 video, đánh giá bằng `scripts/experiments/w8_v2_verify.py` (đường `predict`, theo luật C của W8):
   - recall Drone mức ảnh giảm ≤ 0,01;
   - event recall R1 không giảm, cảnh báo sai R1 trên video không Drone không tăng;
   - track recall gộp giảm ≤ 0,01;
   - ID switch / 1000 frame GT không tăng quá 10%.
3. Trong các cấu hình đạt (1) và (2), chọn cấu hình có trung vị FPS cao nhất. Nếu FPS chênh < 5% thì coi là hòa, chọn cấu hình đơn giản hơn theo thứ tự C0 > C1 > C2.
4. Không cấu hình nào đạt (2) thì giữ C0. Nếu C0 cũng không đạt (1) thì ghi NFR1 **không đạt**. Không đổi ngưỡng.

**Chạy ổn định 60 phút:** cấu hình được chọn chạy liên tục 60 phút, lặp lại bộ video.
- Ghi RSS và bộ nhớ GPU mỗi 60 giây, cùng mọi lỗi gặp phải.
- Đạt khi: không dừng do lỗi, và RSS ở phút 60 không quá 1,10 × RSS ở phút 10.

## D. Tập âm tính: FBD-SV-2024 và nguồn công khai
**FBD-SV-2024** (ADR-0014; dataset Kaggle **Private** `minhquangdng/e1-fbd-sv-2024`):
- Kiểm từng mp4 theo `data/manifests/fbd_sv_2024_zip_contents_sha256.csv` (483 tệp; zip MD5 khớp Figshare).
- Chuẩn hóa theo ADR-0013 mục 2: cắt giữa tỉ lệ 5:4, resize 640×512, đưa về 30 fps (ffmpeg `fps=30`). Ghi `ffprobe` nguồn và đích cho từng clip.
- Toàn bộ 483 clip thuộc `neg_eval` (ADR-0014). Theo readme của bộ dữ liệu, tổng khoảng 19 phút.
- Hạn chế (An xác nhận khi duyệt, 23/11): FBD-SV quay 25 fps; đưa về 30 fps làm lặp khoảng 1/6 số frame. Luật cảnh báo tính theo frame ở 30 fps nên các khoảng thời gian vẫn đúng, nhưng tracker thấy các frame giống hệt nhau liên tiếp. Báo cáo ghi rõ hạn chế này.
- Không đưa video, frame hay nhãn ra khỏi Kaggle. Bằng chứng chỉ gồm số đo tổng hợp và ID clip.

**Đo** bằng `e1pipe` cấu hình C0. Cấu hình đo cố định ngay bây giờ, không phụ thuộc kết quả mục C.
- Báo riêng theo nguồn: số giờ; số cảnh báo sai R0 và R1; cảnh báo sai/giờ kèm cận trên Poisson 95%; tỷ lệ frame có detection Drone với conf ≥ 0,25.
- Mọi cảnh báo trên clip âm tính đều là cảnh báo sai. Clip có cảnh báo sai được liệt kê ID để An xem bằng mắt **trên Kaggle**.
- Điều kiện kích hoạt thí nghiệm hard negative giữ nguyên theo ADR-0011 mục 3: R1 có ≥ 1 cảnh báo sai, hoặc có detection Drone ở ≥ 1% số frame. Đề cương đặt hard negative ở W10.

**Wikimedia Commons, Pixabay** (ADR-0013):
- Quang lập manifest gồm URL, tác giả, giấy phép, SHA-256.
- An sàng lọc độc lập: không có drone, không có người hay logo.
- Chuẩn hóa và đo theo cùng cách với FBD-SV.
- Nếu tổng thời lượng < 120 phút thì báo đúng thời lượng thực có.

## E. Tự động hóa Kaggle bằng GitHub Actions (ADR-0016, Accepted)
- Workflow chỉ chạy khi bấm tay (`workflow_dispatch`).
- Các bước: tạo version mới cho dataset tools từ đúng commit → đẩy notebook (`kaggle kernels push`) → chờ chạy xong → tải đầu ra về thành artifact của Actions, kèm SHA-256.
- Kết quả vào repo qua PR có review như cũ.
- Token Kaggle do Quang tự thêm vào GitHub Secrets.
- Lần chạy đầu của mỗi job vẫn chạy tay trên Kaggle để đối chiếu. Mỗi run ghi `runner` = `manual` hoặc `github-actions` trong `env.json`.

## F. Thứ tự và hạn
1. 22–23/11:
   - merge W9_PLAN và ADR-0016 sau khi An duyệt;
   - code `e1pipe`, job benchmark, job FBD-SV kèm pytest;
   - Quang chạy run 18 (cổng tái tạo + C0) và run 19 (chuẩn hóa FBD-SV + đo).
2. 24–25/11: run 20 (C1, C2, CPU, 3 lần mỗi cấu hình) và chạy ổn định 60 phút; áp luật C; An sàng lọc clip âm tính.
3. 26–27/11: An viết 4.3, 4.4; đo nguồn công khai nếu đã có clip.
4. 28/11: báo cáo W9, v0.9, Evidence/W09, `check_structure --weeks 9`.

## G. Dừng nếu
- Cổng tái tạo mục B không đạt.
- Luật C hoặc D bị sửa sau khi đã có kết quả.
- Dataset FBD-SV trên Kaggle không còn ở chế độ Private.
- Bất kỳ mp4 nào lệch SHA-256 so với manifest.
