# Chương IV. Thiết kế hệ thống — bản nháp mục 4.3–4.4

**Trạng thái:** Bản nháp cập nhật ngày 28/11/2026. Mục 4.3 mô tả pipeline và luật đã có, kèm kết quả benchmark run 18; kết quả C2 sau sửa, chạy ổn định 60 phút và số đo tập âm tính chưa được cập nhật. Không dùng số liệu dự kiến thay cho kết quả đo.

## 4.3. Các mô-đun trí tuệ nhân tạo

Hệ thống xử lý video theo từng frame, theo thứ tự: giải mã, phát hiện đối tượng, theo vết, phát hiện sự kiện và lưu kết quả. Các mô-đun được ghép thành pipeline `e1pipe`; cùng một luồng dữ liệu được dùng cho suy luận trên Kaggle và cho phép đo thời gian từng công đoạn. Mỗi run gắn với commit, SHA-256 của weights và cấu hình để có thể truy nguyên đầu vào.

| Mô-đun | Chức năng | Đầu vào và đầu ra |
|---|---|---|
| Giải mã và tiền xử lý | Đọc tuần tự các frame từ video, giữ thứ tự và thời gian nguồn. Bộ benchmark dùng đầu vào cố định từ manifest; phép đo tập âm tính chuẩn hóa video theo ADR-0013. | Video và metadata → frame BGR, chỉ số frame, thời gian nguồn. |
| Phát hiện đối tượng | YOLO11n nhận diện Airplane, Bird, Drone và Helicopter. Cấu hình mốc C0 dùng PyTorch fp32, batch 1, `imgsz=640`, ngưỡng phát hiện 0,1 và NMS cùng lớp IoU 0,5. Ngưỡng 0,25 được dùng riêng cho phép đánh giá detection, không thay cho ngưỡng suy luận. | Frame → hộp giới hạn, lớp và độ tin cậy. |
| Theo vết | BYTETracker gán và duy trì ID cho các đối tượng qua các frame, theo `configs/tracker_bytetrack_e1.yaml`. | Detection theo frame → track có ID, lớp và hộp giới hạn. |
| Cảnh báo | AlertEngine áp dụng luật R1 theo track: tích lũy bằng chứng để xác nhận đối tượng, kiểm tra vùng quan tâm và thời gian hiện diện, sau đó mở, nối lại hoặc đóng sự kiện. Engine xử lý trực tuyến từng frame; hàm đánh giá dữ liệu đã lưu gọi cùng engine để giữ nhất quán giữa hai cách chạy. | Track theo frame và ROI → sự kiện R1 cùng các chuyển trạng thái. |
| Lưu trữ và đo lường | Mỗi `FrameResult` ghi thời gian nguồn, track, chuyển trạng thái và độ trễ theo công đoạn. Sự kiện đã chốt được ghi vào SQLite; dữ liệu frame lưu dạng JSONL nén. | Kết quả từng frame → bundle có thể kiểm tra và phát lại. |

### Giao diện mô-đun và xử lý lỗi

| Giao diện | Đầu vào | Đầu ra và hành vi |
|---|---|---|
| `detector(frame)` | Một frame BGR. | Mảng `float32` kích thước N×6, mỗi dòng `[x1, y1, x2, y2, conf, cls]`; không có detection thì trả mảng rỗng kích thước 0×6. |
| `track_step(tracker, det, w, h)` | Tracker, mảng detection và chiều rộng/chiều cao frame. | Danh sách track có `id`, `cls`, `conf`, `x`, `y`, `w`, `h`; hộp được chặn trong khung ảnh. |
| `R1Engine.step(f, rows)` | Chỉ số frame liên tiếp `f` và danh sách track của frame đó, có thể rỗng. | Danh sách chuyển trạng thái `open`, `reopen` hoặc `close`; gọi thiếu hoặc sai thứ tự frame sẽ báo lỗi. |
| `Sink.write_line(line)` | Một dòng JSON đã serialize. | Ghi dòng vào JSONL nén và thêm ký tự xuống dòng. |

| Tình huống lỗi/biên | Hành vi hoặc fallback đã xác minh |
|---|---|
| Không mở được video hoặc lệch số frame | `read_frames` báo lỗi nếu không mở được video. Benchmark cố định so số frame đọc với metadata và đánh dấu run thất bại nếu lệch; không dùng run thiếu frame như kết quả hợp lệ. |
| SHA weights/tools không khớp | Job dừng nếu SHA-256 weights khác giá trị kỳ vọng. GitHub Actions cũng dừng nếu commit checkout không khớp `--commit`; tools được dựng từ commit đó. Không thấy kiểm tra SHA-256 độc lập cho gói tools trên Kaggle, nên không khẳng định có cổng riêng như vậy. |
| TensorRT export thất bại | Ghi `export.status=FAILED` và thông báo lỗi vào `stage_status.json`, rồi kết thúc job với mã 2; W9_PLAN yêu cầu ghi log, đánh dấu “không khả thi” và không thử cấu hình thay thế. Run 18 lần đầu gặp lỗi do bộ đo ghi `best.onnx` vào `/kaggle/input` chỉ đọc; theo cập nhật được báo cùng PR #141, đường dẫn xuất đã được sửa, nhưng chưa có số đo C2 sau sửa. |
| EOS khi còn event mở | `R1Engine.close()` đặt `end=last_in` và trả chuyển trạng thái `close`; sau vòng lặp, `run_source` lưu các event đã đóng vào SQLite. Không có frame JSONL mới để mang chuyển trạng thái EOS này. |
| Frame không có detection | Detector trả mảng 0×6; pipeline vẫn gọi tracker và R1 cho frame đó, ghi frame result với dữ liệu track mà tracker trả về và tiếp tục xử lý. |

`FrameResult` tổng hợp dưới đây chỉ là **ví dụ tổng hợp**, không phải số đo hay dữ liệu của một run:

```json
{
  "run_id": "synthetic-run",
  "source_id": "synthetic-video",
  "model_version": "synthetic-sha256",
  "frame_index": 42,
  "source_time_ms": 1400.0,
  "tracks": [
    {"id": 7, "cls": 2, "cls_name": "Drone", "conf": 0.91, "box": [300.0, 160.0, 360.0, 220.0]}
  ],
  "events": [
    {"event_id": "synthetic-run:synthetic-video:0", "transition": "open"}
  ],
  "stage_latency_ms": {
    "decode": 1.2,
    "detect": 12.4,
    "track": 0.5,
    "alert": 0.2,
    "persist": 0.8,
    "total": 15.1
  }
}
```

Artifacts theo dõi run benchmark gồm `stage_status.json`, `env.json` và `latency.csv.gz` (CSV độ trễ được nén). `config_audit` là bảng audit append-only trong bundle SQLite W8, đọc được qua `GET /config_audit`; đây không phải tệp đầu ra riêng của job benchmark W9.

Trong implementation hiện tại, các giá trị `stage_latency_ms` được chụp trước `Sink.write_line`; `latency.csv.gz` được dựng từ cùng các giá trị đó nên cũng chưa tính thời gian ghi dòng JSONL nén. Đây khác với mô tả trong W9_PLAN mục B rằng `total` tính đến sau khi ghi xong. Vì vậy `total`/`persist` hiện chưa bao gồm thao tác ghi dòng JSONL; cần giữ rõ khác biệt này khi diễn giải p95 và NFR1, không mô tả chúng như số đo sau khi ghi.

W9 so sánh bốn cấu hình: C0 (PyTorch fp32), C1 (PyTorch fp16), C2 (TensorRT fp16) và CPU (PyTorch fp32). C0 là mốc đối chiếu; CPU chỉ dùng để báo cáo. Cấu hình vận hành chỉ được chọn nếu đạt ngưỡng hiệu năng đã định trước và không vượt các giới hạn suy giảm độ chính xác trong W9_PLAN. Nếu C2 cần đệm đầu vào 640×640 khác với PyTorch, khác biệt tiền xử lý này được ghi nhận; vì vậy chênh lệch C2–C1 không được diễn giải như tác động thuần túy của runtime.

**Kết quả benchmark run 18 (cập nhật 28/11/2026):** Cổng B đạt: 11.474/11.474 dòng track khớp và sự kiện R1 25/25; độ chính xác C0 trùng run 17. Trong run 18, C0 đạt 89,3 FPS, p95 `total` 12,1 ms; C1 đạt 78,5 FPS và chậm hơn C0. Kết quả hiện chọn C0 theo luật C. C2 chưa có kết quả hợp lệ: lần export đầu thất bại do bộ đo cố ghi `best.onnx` vào `/kaggle/input` chỉ đọc; theo cập nhật được báo cùng PR #141, đường dẫn xuất đã được sửa. Chưa có số đo C2 sau sửa nên lựa chọn này chưa phải kết luận cuối nếu C2 được chạy lại. Kết quả chạy ổn định 60 phút và tập âm tính chưa được cập nhật ở đây. Mọi kết quả được báo theo tập dữ liệu và cấu hình; tập val dùng để đánh giá không đồng nghĩa với dữ liệu triển khai thực tế.

### Quy tắc R0/R1 của v0.8, ROI và nguồn ngưỡng

| Luật | Tóm tắt |
|---|---|
| R0 (detector-only) | Mỗi frame có detection lớp Drone, confidence đạt `conf_min` và điểm tâm hộp nằm trong ROI được tính là frame kích hoạt; các đoạn được gộp theo `merge_gap_s`. Không dùng track. |
| R1 (theo track) | Bằng chứng Drone đạt `confirm_k=3` trong `confirm_n=5` frame gần nhất, lớp Drone chiếm đa số của track, confidence đạt ngưỡng và điểm tâm ở trong ROI liên tục đủ `dwell_s=0.3`; event đóng sau `end_timeout_s=1.0` thiếu bằng chứng trong ROI. |

ROI chính là `center_hex`, lục giác giữa khung trong `configs/roi_w6.yaml`; phép thử dùng điểm `center` của hộp. Đây là ROI mô phỏng, không phải vùng cấm bay pháp lý. `conf_min=0.25` có nguồn là `results/W05/seed_comparison.csv` (`conf_op`); `confirm_k`, `confirm_n`, `dwell_s` và các giá trị khởi điểm luật cảnh báo lấy từ Thuyết minh mục 10.2, theo chú thích trong `configs/alert_e1.yaml`. Ngưỡng phát hiện suy luận 0.1 và NMS cùng lớp IoU 0.5 là cấu hình W9_PLAN mục B (V2, mục 5.3.8), tách biệt với `conf_min` của luật cảnh báo.

## 4.4. Bảo mật, quyền riêng tư và rủi ro

### Ranh giới dữ liệu và quyền truy cập

Video nguồn và weights được xử lý trong môi trường Kaggle theo quy trình của dự án. Không đưa video, frame hoặc nhãn của FBD-SV-2024 vào Git hay artifact công khai; bằng chứng dùng cho báo cáo chỉ gồm số liệu tổng hợp và mã định danh clip. Nguồn Wikimedia Commons phải được ghi nhận theo giấy phép của từng tệp. Với FBD-SV-2024, nhóm áp dụng điều kiện thận trọng đã nêu trong ADR-0014: chỉ đánh giá trong phạm vi đồ án, không thương mại và không phân phối lại video, frame hoặc nhãn.

API phát lại W8 chỉ bind vào `127.0.0.1`, và media được phân giải từ danh sách nguồn trong bundle thay vì nhận đường dẫn hoặc URL tùy ý từ client. Đây là giới hạn phạm vi truy cập cho bản demo cục bộ, không phải cơ chế xác thực. Hệ thống hiện chưa có tài khoản, xác thực người dùng hay phân quyền; `reviewer_id` do người dùng nhập chỉ là định danh cục bộ, không chứng minh danh tính. Vì vậy không triển khai API ra mạng dùng chung hoặc xem nhật ký review là bằng chứng kiểm toán danh tính.

ADR-0014 trong repository hiện vẫn ghi trạng thái **Proposed**. Vì vậy các điều kiện bảo vệ FBD-SV nêu ở đây là ràng buộc chính sách dự kiến, không phải bằng chứng rằng trạng thái phê duyệt hoặc quyền truy cập dataset bên ngoài đã được xác minh.

Đối với các clip công khai, hai screener cần sàng lọc độc lập và lưu kết quả vào **hai tệp riêng**, không cùng sửa một tệp. W9_PLAN hiện phân công An sàng lọc độc lập; repository không nêu người sàng lọc thứ hai và không có hai tệp kết quả để xác nhận việc này đã hoàn tất.

### Tính toàn vẹn và lưu vết

Manifest, SHA-256 của video/weights/cấu hình và commit được dùng để phát hiện đầu vào hoặc mã nguồn không khớp. Sự kiện pipeline là bản ghi bất biến; thao tác xác nhận hoặc báo sai được lưu thành bản ghi review mới, không ghi đè sự kiện gốc. Bundle có thể chứa đường dẫn media cục bộ nên chỉ chia sẻ theo quy trình có kiểm soát và không đưa lên nơi công khai nếu còn dữ liệu bị giới hạn.

### Mô hình đe dọa

| Tài sản | Đe dọa | Giảm thiểu | Rủi ro còn lại |
|---|---|---|
| Video và nhãn FBD-SV; thông tin giấy phép | Dữ liệu bị công khai hoặc dùng ngoài phạm vi đã nêu. | ADR-0014 quy định chỉ dùng cho đánh giá, không thương mại, không phân phối lại; W9_PLAN nói dữ liệu ở Kaggle Private và chỉ xuất số liệu tổng hợp. | ADR-0014 hiện còn Proposed; quyền truy cập thực tế trên Kaggle và các bản sao bên ngoài chưa được kiểm chứng từ repository. |
| Bundle và video phát lại | Client cục bộ cố truy cập media tùy ý hoặc gọi API từ máy khác. | API bind `127.0.0.1`; media chỉ tra theo `run_id`/`source_id` trong bundle, không nhận path/URL tùy ý. | Không có xác thực hay phân quyền; tiến trình hoặc người dùng cùng máy vẫn có thể gọi API. |
| Sự kiện và nhật ký review/audit | Sửa hoặc xóa lịch sử sự kiện để che dấu thao tác. | SQLite tạo trigger từ chối `UPDATE`/`DELETE` trên `events`, `event_reviews`, `config_audit`; review được ghi thêm thay vì sửa event. | Trigger không bảo vệ khỏi người có quyền ghi trực tiếp vào tệp DB hoặc thay schema/tệp. |
| Nội dung dashboard | Dữ liệu bundle/API độc hại được diễn giải như HTML/script. | Dashboard dựng text bằng `textContent`/text node, không ghép nội dung API thành HTML tại các đường hiển thị đã kiểm tra. | Đây không phải xác nhận bảo mật toàn bộ trình duyệt hay mọi mã frontend trong tương lai. |
| Kaggle API credentials | Token bị lộ qua log, artifact hoặc xử lý ngoài ý muốn. | Workflow đưa `KAGGLE_USERNAME`/`KAGGLE_KEY` vào môi trường riêng của bước chạy Kaggle; quyền workflow khai báo `contents: read`. | Mã chạy trong bước đó có thể sử dụng secrets; an toàn phụ thuộc vào quyền truy cập và tính tin cậy của workflow/commit được dispatch. |
| Dataset và job Kaggle | Job chạy ngoài ý muốn hoặc đưa dữ liệu nhạy cảm qua runner ngoài Kaggle. | ADR-0016 và workflow chỉ cho phép `workflow_dispatch`; job dùng dataset Kaggle có sẵn, không chuyển video/dataset qua Actions. | Người có quyền vẫn có thể dispatch job; cấu hình quyền người dùng GitHub/Kaggle nằm ngoài repository. |

### Checklist bảo mật và quyền riêng tư

| Kiểm soát | Đạt? | Bằng chứng / giới hạn xác minh |
|---|---|---|
| FBD-SV-2024: không đưa video/frame/nhãn vào Git hoặc artifact công khai; chỉ báo số liệu tổng hợp | No — chưa xác minh phê duyệt và thực thi | Điều kiện có trong ADR-0014 và W9_PLAN, nhưng ADR-0014 hiện là Proposed; không thể xác minh các bản sao ngoài repository. |
| Không đặt FBD-SV hoặc dữ liệu bị giới hạn lên Drive công khai | No — trạng thái ngoài repo chưa xác minh | ADR-0014 cấm Drive công khai; không có bằng chứng về ACL/trạng thái chia sẻ Drive thực tế trong repository. |
| API phát lại chỉ dùng loopback | Yes | `scripts/pipeline/api.py` khởi chạy Uvicorn trên `127.0.0.1`; API chưa có xác thực. |
| Trigger bảo vệ bảng sự kiện/audit khỏi UPDATE/DELETE | Yes | `scripts/pipeline/e1store.py` tạo trigger SQLite cho `events`, `event_reviews`, `config_audit`; test `tests/test_w8_pipeline.py` thử các thao tác bị chặn. |
| Dashboard hiển thị text không diễn giải nội dung dữ liệu thành HTML | Yes | `scripts/pipeline/static/index.html` dùng `textContent` trong helper `el` và khi cập nhật giao diện; phạm vi xác minh là các vị trí đã kiểm tra. |
| Kaggle secrets không đưa vào artifact và chỉ cấp cho bước chạy cần thiết | Yes, theo cấu hình | `.github/workflows/kaggle_run.yml` truyền secrets vào env của bước “Chạy job trên Kaggle”; repository không xác minh quyền GitHub/Kaggle bên ngoài. |
| Workflow Kaggle chỉ chạy thủ công | Yes | `.github/workflows/kaggle_run.yml` chỉ khai báo `workflow_dispatch`; ADR-0016 cũng cấm lịch/push trigger. |

Các biện pháp trên giảm rủi ro cho quy trình thí nghiệm và demo cục bộ, nhưng không biến hệ thống thành dịch vụ an ninh vận hành. Kết quả cảnh báo cần có người xem xét; các ngưỡng, dữ liệu và cấu hình được đánh giá trong W9 chưa chứng minh độ an toàn cho quyết định tự động hoặc môi trường thực tế. Rủi ro đo lường/hiệu năng được trình bày ở mục 4.3 và W9_PLAN, không xếp vào mô hình đe dọa.

### Tài liệu liên quan

- ADR-0013, *Thay video tự quay bằng nguồn video công khai có giấy phép; dời tập âm tính sang W8–W9*.
- ADR-0014, *Đưa lại FBD-SV-2024 vào tập âm tính, chỉ để đánh giá*.
- ADR-0015, *Kiến trúc đầu-cuối của MVP*.
- ADR-0016, *Chạy job Kaggle qua GitHub Actions (bấm tay)*.
- W9_PLAN, mục B–E.
