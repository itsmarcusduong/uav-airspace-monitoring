# W2 — Kế hoạch và hướng dẫn chạy Kaggle

Mốc chuyên môn (thang chấm E1): *thu thập/chuẩn hóa dataset; thống kê lớp và chất lượng nhãn.* Đề cương thêm: EDA + annotation audit + split train/val/test + baseline setup. Thuyết minh thêm: chốt phần cứng/protocol/chỉ tiêu với GVHD.
**Lưu ý thời gian:** hạn W2 là 10/10, hôm nay 11/10. Nên hỏi thầy cách nộp muộn; trong báo cáo ghi đúng ngày làm, không ghi "đúng hạn".

## A. Việc cần làm (mỗi dòng = 1 GitHub Issue, milestone W2)
| # | Việc | Chủ trì | Review | Evidence |
|---|---|---|---|---|
| W2-01 | Upload dataset lên Kaggle + chạy job, xác minh SHA-256 | Quang | An | `checksum_verification.csv`, `stage_status.json`, `env.json` |
| W2-02 | Inventory + thống kê lớp/chất lượng (EDA) | Quang | An | `video_inventory.csv`, `class_stats.csv`, 3 hình `fig_*.png` |
| W2-03 | Tiêu chí audit nhãn + kiểm tra chéo bằng mắt (toàn bộ test + 10% train + video bị flag) | An (tiêu chí), cả hai (kiểm) | nhau | `annotation_audit*.csv`, `review_assignment.csv` đã điền `verdict` |
| W2-04 | Giao thức split (đơn vị nhóm, tỉ lệ, quy tắc rò rỉ) → ADR-0002/0003 | An | Quang | `docs/decisions/ADR-0002..` |
| W2-05 | Split v1 + báo cáo rò rỉ | Quang | An | `split_v1.csv`, `split_summary.csv`, `split_report.json`, `leakage_*.csv` |
| W2-06 | Phần cứng tham chiếu + protocol + chỉ tiêu (họp GVHD) | cả hai | — | ADR + biên bản ngắn |
| W2-07 | Viết Mở đầu + 1.1–1.3 (+1.4–1.5 hạn 17/10) và mục 3.2 (dữ liệu) vào template | An viết khung, Quang điền số liệu 3.2 | nhau | `E1_DoAn_v0.2_W02.docx` |
| W2-08 | Báo cáo công việc W2 (docx→pdf) + PR + bảng Planned–Done–Evidence | Quang | An | `E1_W02_bao_cao_cong_viec.pdf` |
| W2-00 | **Nền tảng GitHub** (nếu chưa): milestones W1–W14, issues W2, branch protection, template báo cáo `docs/templates/`, thư mục `docs/status|project_versions`, Issue hồi tố W1 (ghi rõ là hồi tố) | Quang | An | link repo/milestone |

## B. Quyết định cần chốt (không tự quyết im lặng)
Modality · đơn vị nhóm split · xử lý 12 chuỗi không bbox · GT tracking · stride lấy mẫu frame · GPU tham chiếu · chỉ tiêu · mâu thuẫn kế hoạch tuần. Chi tiết: `PROJECT_CONTEXT.md` mục 5 và 8. Job Kaggle cung cấp dữ kiện để quyết (đặc biệt `leakage_ir_v_same_number.csv`, `workbook_columns.json`, `annotation_audit_summary.json`).

## C. Hướng dẫn chạy trên Kaggle (làm một lần ~30–40 phút; job chạy vài phút)
Dữ liệu chỉ ≈ 0,2 GB nên CPU là đủ; Kaggle dùng để giữ mọi xử lý dữ liệu ngoài máy local và để từ W3 có GPU.

**Bước 1 — Chuẩn bị file (máy local, chỉ nén/copy, không xử lý):**
1. Thư mục dataset Svanström đã tải về (`Drone-detection-dataset-master`) (có `Data\Video_IR`, `Data\Video_V`, `Data\Video_dataset_description.xlsx`).
2. Hai file công cụ: `scripts\kaggle\w2_eda_audit_split.py` và `resources\metadata\svanstrom_files.csv`.

**Bước 2 — Tạo 2 Kaggle Dataset (Private):** kaggle.com → Datasets → New Dataset.
- `e1-svanstrom-raw`: kéo cả thư mục `Drone-detection-dataset-master` vào (ưu tiên upload thư mục; nếu nén zip thì cell bên dưới sẽ giải nén nếu cần).
- `e1-w2-tools`: 2 file ở bước 1.2.

**Bước 3 — Notebook:** New Notebook → Add data (2 dataset trên) → Settings: Accelerator **None**, **Internet ON** (cần số điện thoại xác minh; để `pip install mcos-decoder`). Dán lần lượt 3 cell:
```python
# Cell 1: cài decoder nhãn MATLAB và xem cấu trúc input
!pip -q install mcos-decoder
!ls /kaggle/input
```
```python
# Cell 2: (chỉ nếu Video_IR chưa thấy vì dataset còn là .zip) giải nén
import glob, zipfile, os
if not glob.glob('/kaggle/input/**/Video_IR', recursive=True):
    for z in glob.glob('/kaggle/input/**/*.zip', recursive=True):
        zipfile.ZipFile(z).extractall('/kaggle/working/raw'); print('extracted', z)
```
```python
# Cell 3: chạy job. Thay COMMIT bằng SHA commit repo (hoặc UNKNOWN)
import glob, subprocess, sys
script = glob.glob('/kaggle/input/**/w2_eda_audit_split.py', recursive=True)[0]
inv    = glob.glob('/kaggle/input/**/svanstrom_files.csv', recursive=True)[0]
root   = '/kaggle/working/raw' if glob.glob('/kaggle/working/raw/**/Video_IR', recursive=True) else '/kaggle/input'
r = subprocess.run([sys.executable, script, '--data-root', root, '--inventory', inv,
                    '--out', '/kaggle/working/w2_outputs', '--commit', 'COMMIT'])
print('exit code', r.returncode)
print(open('/kaggle/working/w2_outputs/stage_status.json').read())
```
**Bước 4 — Lưu bằng "Save Version → Save & Run All (Commit)"** để output được lưu vĩnh viễn. Mở tab **Output**, tải `w2_outputs_bundle.zip`.

**Bước 5 — Đặt kết quả về máy:** giải nén vào `results/W02/kaggle_run_01/` rồi nhắn mình ("đã có kết quả W2"). Mình sẽ đọc file, đối chiếu và cập nhật tài liệu/báo cáo.

**Cách tự kiểm tra thành công:** `stage_status.json` — mọi stage `OK`; `checksums.mismatch = 0` và `missing = 0`; `totals.videos = 650`; `totals.frames_decoded ≈ 203328` (khớp W1). Nếu lệch → dừng, gửi file đó cho mình, đừng sửa dữ liệu.
Nếu một stage `FAILED`: gửi `stage_status.json` + dòng log lỗi trong notebook; không chạy lại nhiều lần.

## D. Job tạo ra gì và dùng vào đâu
| File | Dùng cho |
|---|---|
| `checksum_verification.csv` | Chứng minh dữ liệu trên Kaggle y hệt W1 |
| `video_inventory.csv` | Dataset card/data dictionary (3.2); fps, độ phân giải, số frame, join workbook |
| `annotations_per_frame.csv.gz` | Nhãn đã giải mã, dùng cho W3 (đổi sang YOLO). **Không commit Git** → Drive/Kaggle, ghi SHA-256 |
| `annotation_audit.csv`, `annotation_audit_summary.json` | Thống kê chất lượng nhãn; danh sách video cần xem tay |
| `class_stats.csv`, `fig_*.png` | Biểu đồ EDA, phân bố bbox nhỏ/vừa/lớn |
| `split_v1.csv`, `split_summary.csv`, `split_report.json` | Split theo video (seed tìm cân bằng) |
| `leakage_near_duplicate_pairs.csv`, `leakage_ir_v_same_number.csv` | Rủi ro rò rỉ giữa split; căn cứ chọn đơn vị nhóm |
| `review_sheets/` + `review_assignment.csv` | An và Quang xem ảnh có bbox, điền `verdict`/`notes` (cross-check theo thuyết minh 8.2) |
| `env.json` | Phần cứng/phiên bản thư viện cho báo cáo |

Ghi chú kỹ thuật: kết quả near-duplicate dùng dHash khung đầu/giữa (ngưỡng Hamming ≤ 4) — chỉ là cảnh báo sàng lọc, không phải bằng chứng đầy đủ. `--group-by pair` (gom IR/V cùng class+number) chỉ dùng sau khi kiểm chứng chúng là cùng sự kiện. Script đã chạy thử thành công trên dữ liệu **tổng hợp** (phát hiện đúng 3 lỗi được cài sẵn); chưa chạy trên dữ liệu Svanström thật nên lần đầu có thể phát sinh lỗi định dạng workbook — stage đó được cô lập.

## E. Chia việc tay tuần này (sau khi có kết quả)
1. Cả hai xem `review_sheets` theo cột `reviewer`, điền `verdict` (OK / SAI_NHAN / KHONG_RO) + `notes`. Ghi cả quy tắc cho vật thể quá nhỏ/mờ.
2. Họp 20 phút chốt các quyết định mục B → viết ADR-0002 (kế hoạch tuần + modality), ADR-0003 (split + GT tracking + xử lý chuỗi không bbox).
3. Quang tạo PR "W2 evidence" (CSV/JSON nhỏ + docs), An review.
4. Mình soạn 2 file Word/PDF (báo cáo W2, version v0.2 theo template) khi đã có số liệu.

## F. Chuẩn bị W3 (train baseline — Kaggle GPU)
Mình sẽ soạn thêm job "export YOLO dataset" từ `split_v1.csv` + `annotations_per_frame.csv.gz` (trích frame với stride đã chốt, chỉ train/val; test khóa) và notebook train YOLOv8n@640 lưu `config`, `weights` (Drive/Kaggle, ghi SHA-256), PR curve, mAP theo lớp và theo kích thước bbox. Cần quyết trước: modality dùng để train và stride.
