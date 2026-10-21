# W3 (11/10–17/10/2026) — Train detector baseline A

Mốc: Đề cương W3 "Train detector baseline A" → *Weights A; learning curves; mAP baseline* (input: train split). Thang chấm E1: config, weights, mAP/PR curve. Thuyết minh: chuẩn hóa nhãn + baseline detector. Template: mục 1.4, 1.5 hạn 17/10. Quyết định dữ liệu: `docs/decisions/ADR-0004-w3-baseline-a-data.md` (Proposed).

## A. Issue và phân công (milestone W3)
| Issue | Việc | Phụ trách | Review | Evidence |
|---|---|---|---|---|
| #10 W3-01 | Review nhãn v2 cho 358 video (8 frame/video, có ảnh phóng to; có hỗ trợ công cụ) → cột `review_quang_v2` | Quang | An | `results/W03/review/review_assignment_w3.csv` |
| #11 W3-02 | Chính sách căn nhãn: chạy run 03 (độ nhạy IoU + bảng xem mù), chấm theo luật ADR-0004 mục 6 | Quang (chạy), cả hai (xem) | An | `offset_sensitivity_summary.json`, `offset_review_score.json` |
| #5 W2-04 | Duyệt ADR-0003 (+ ADR-0004), đóng băng split v1 | An duyệt | Quang | ADR trạng thái Accepted; tag/commit split |
| #7 W2-06 | Họp GVHD: chỉ tiêu, modality, tracker, kế hoạch tuần | Cả hai | — | Biên bản/ADR |
| W3-03 | ADR-0004 + xuất dữ liệu YOLO (Kaggle run 03) | Quang | An | `results/W03/kaggle_run_03/` |
| W3-04 | Giao thức + config baseline A | An | Quang | `configs/baseline_A.yaml`, `docs/w3/training_protocol.md` |
| W3-05 | Train baseline A (Kaggle run 04) + weights lên Drive | Quang | An | `results/W03/kaggle_run_04/`, `weights_manifest.json` |
| W3-06 | Đánh giá val + model card | An (phân tích), Quang (số liệu) | Nhau | `docs/w3/model_card_baseline_A.md` |
| W3-07 | License Ultralytics / yolov8n.pt | An | Quang | dòng mới trong `license_matrix.csv` |
| W3-08 | Báo cáo W3 + version đồ án v0.3 (1.4, 1.5) | Quang (báo cáo), An (1.4, 1.5) | Nhau | `reports/w3/` |
| (W4) | An kiểm tra thủ công mẫu review v2 → cột `verdict` | An | Quang | tỷ lệ đồng ý với `review_quang_v2` |

Từ W3: mọi PR cần approve của người còn lại trước khi merge (main đã bảo vệ).

## B. Thứ tự và điều kiện dừng
1. PR chứa script W3 (nhánh `issue-<W3-03>-w3-export`) → lấy SHA commit làm `COMMIT` cho Kaggle.
2. **Run 03** (CPU) → tải bằng chứng → Quang và An xem bảng mù **độc lập** → chấm (`score_offset_review.py`).
   - **Dừng, không train** nếu: một stage FAILED; `dataset_card.problems` khác rỗng; nhóm `V|Drone|plus1` hoặc `V|Bird|plus1` có `passes: false` (baseline sẽ thiếu lớp).
   - Nếu chấm ra `offset1`: chạy lại run 03 với `--plus1-policy offset1` (vài phút).
3. An review `configs/baseline_A.yaml` (W3-04) **trước** run 04.
4. **Run 04** (GPU) → tải bằng chứng + weights → Drive.
5. Phân tích, model card, báo cáo.


## C0. Cập nhật 21/10/2026 — chạy bằng notebook có sẵn
Run 03 tách làm hai để review nhãn v2 (#10) và bảng xem mù offset (#11) xong **trước** khi xuất dữ liệu. Ba notebook upload thẳng lên Kaggle (`File → Import Notebook`), hướng dẫn từng bước trong `docs/w3/kaggle_guide_w3.md`:

| Lần chạy | Notebook | Máy | Kết quả tải về |
|---|---|---|---|
| 03a | `scripts/kaggle/notebooks/w3_run03a_review_offset.ipynb` | CPU | `w3_review_v2.zip`, `w3_export_evidence.zip` → `results/W03/kaggle_run_03a/` |
| — | Review nhãn v2 (`review_quang_v2`) + chấm bảng xem mù (`score_offset_review.py`) | — | `results/W03/review/` |
| 03b | `scripts/kaggle/notebooks/w3_run03b_export_yolo.ipynb` | CPU | `w3_export_evidence.zip` → `results/W03/kaggle_run_03b/` |
| 04 | `scripts/kaggle/notebooks/w3_run04_train_baseline_A.ipynb` | GPU | `w3_train_evidence.zip` → `results/W03/kaggle_run_04/`; weights → Drive |

Mỗi notebook có ô tự kiểm tra in `PASS`/`FAIL`. `w3_export_yolo.py` đọc kết quả review theo thứ tự ưu tiên `verdict` > `review_quang_v2` > `review_quang` và ghi cột đã dùng vào `inclusion_decisions.csv`. Mục C và D bên dưới là cách chạy bằng cell rời (giữ để tham khảo).

## C. Kaggle run 03 — xuất dữ liệu YOLO + kiểm tra lệch nhãn (CPU)
**Mục đích:** đo ảnh hưởng lệch nhãn 1 frame, tạo bảng xem mù, xuất ảnh/nhãn YOLO train+val (ảnh khả kiến, stride 10).

**Input cần add:**
- `e1-svanstrom-raw` (đã có từ W2).
- Dataset mới **`e1-w3-tools`** (Private), upload 6 file (đường dẫn tính từ gốc repo):
  `scripts\kaggle\w3_export_yolo.py`, `scripts\kaggle\w3_train_baseline.py`, `configs\baseline_A.yaml`,
  `data\splits\video_split_v1.csv`, `results\W02\kaggle_run_01\w2_outputs_bundle\annotation_audit.csv`, `results\W02\review\review_assignment_w2.csv`.

**Notebook:** New Notebook → Add Input 2 dataset trên → Settings: Accelerator **None**, **Internet ON**.
```python
# Cell 1
!pip -q install mcos-decoder
!ls /kaggle/input
```
```python
# Cell 2 (chỉ khi dataset thô còn dạng .zip)
import glob, zipfile
if not glob.glob('/kaggle/input/**/Video_V', recursive=True):
    for z in glob.glob('/kaggle/input/**/*.zip', recursive=True):
        zipfile.ZipFile(z).extractall('/kaggle/working/raw'); print('extracted', z)
```
```python
# Cell 3: chạy job. Thay COMMIT bằng SHA commit chứa script (GitHub Desktop → History)
import glob, subprocess, sys
f = lambda n: glob.glob(f'/kaggle/input/**/{n}', recursive=True)[0]
root = '/kaggle/working/raw' if glob.glob('/kaggle/working/raw/**/Video_V', recursive=True) else '/kaggle/input'
COMMIT = 'DIEN_SHA'
r = subprocess.run([sys.executable, f('w3_export_yolo.py'), '--data-root', root,
                    '--split-csv', f('video_split_v1.csv'), '--audit', f('annotation_audit.csv'),
                    '--review', f('review_assignment_w2.csv'), '--out', '/kaggle/working', '--commit', COMMIT])
print('exit code', r.returncode)
```
```python
# Cell 4: tự kiểm tra
import json, pandas as pd
ev = '/kaggle/working/w3_export_evidence'
print({k: v['status'] for k, v in json.load(open(f'{ev}/stage_status.json')).items()})
print(json.dumps(json.load(open(f'{ev}/offset_sensitivity_summary.json'))['groups'], indent=1))
card = json.load(open(f'{ev}/dataset_card.json'))
print(card['inputs']['split_counts'], card['videos_included'], card['images'], card['problems'])
print(pd.read_csv(f'{ev}/dataset_stats.csv'))
```
**Lưu:** Save Version → *Save & Run All (Commit)*. Tab Output: tải `w3_export_evidence.zip`. **Không tải** thư mục `e1-yolo-v1/` (để nguyên trên Kaggle, run 04 dùng trực tiếp).
**Đặt kết quả:** giải nén vào `results/W03/kaggle_run_03/`.
**Tự kiểm tra thành công:** mọi stage `OK`; `split_counts` = train 454 / val 98 / test 98; `problems` rỗng; không có `images/test`; hai nhóm `V|Drone|plus1`, `V|Bird|plus1` có `passes: true`.

**Xem bảng mù (W3-02):** mỗi người copy `offset_review.csv` thành `offset_review_quang.csv` / `offset_review_an.csv`, mở các ảnh `offset_review_sheets/*.jpg`, với mỗi ô ghi `A`, `B` hoặc `UNCLEAR` vào cột `choice_A_B_UNCLEAR` (hộp nào khớp vật thể trong ảnh). **Không mở file `..._KEY_...` trước khi cả hai xem xong.** Lưu vào `results\W03\review\` rồi báo mình; mình chạy `scripts/dataset/score_offset_review.py`.

## D. Kaggle run 04 — train baseline A (GPU)
**Mục đích:** train YOLOv8n theo `configs/baseline_A.yaml`, đánh giá best.pt trên val, thu config/weights/curves/metrics.

**Input cần add:** `e1-w3-tools` (bản mới nhất, có config An đã duyệt) + **output của notebook run 03** (Add Input → Your Work → Notebooks → chọn notebook run 03).
**Notebook:** Accelerator **GPU** (T4 hoặc P100), **Internet ON** (cài ultralytics, tải yolov8n.pt). Trước khi chạy, xem hạn mức GPU còn lại trong tài khoản Kaggle.
```python
# Cell 1
!pip -q install ultralytics
import ultralytics, torch; print(ultralytics.__version__, torch.__version__, torch.cuda.is_available())
```
```python
# Cell 2
import glob, os, subprocess, sys
f = lambda n: glob.glob(f'/kaggle/input/**/{n}', recursive=True)[0]
card = [p for p in glob.glob('/kaggle/input/**/dataset_card.json', recursive=True)
        if os.path.exists(os.path.join(os.path.dirname(p), 'data.yaml'))][0]
COMMIT = 'DIEN_SHA'
r = subprocess.run([sys.executable, f('w3_train_baseline.py'), '--data-dir', os.path.dirname(card),
                    '--config', f('baseline_A.yaml'), '--out', '/kaggle/working', '--commit', COMMIT])
print('exit code', r.returncode)
```
```python
# Cell 3: tự kiểm tra
import json
ev = '/kaggle/working/w3_train_evidence'
print({k: v['status'] for k, v in json.load(open(f'{ev}/stage_status.json')).items()})
print(json.load(open(f'{ev}/env.json'))['gpu'])
print(json.dumps(json.load(open(f'{ev}/baseline_A_val_metrics.json'))['overall'], indent=1))
```
**Lưu:** Save Version → *Save & Run All (Commit)* (chạy nền). Tab Output: tải `w3_train_evidence.zip` → giải nén vào `results/W03/kaggle_run_04/`; tải `runs/baseline_A/weights/best.pt` và `last.pt` → Drive (thư mục `E1/weights/W03/`, quyền xem), **không** đưa vào Git.
**Tự kiểm tra thành công:** mọi stage `OK`; `gpu` khác `none`; `train/results.csv` có một dòng mỗi epoch; có `val/BoxPR_curve.png` (hoặc `PR_curve.png`) và `baseline_A_val_metrics.json`. Gửi mình link Drive của 2 file weights để ghi vào `weights_manifest.json`.

## E. Script đã kiểm thử
Cả hai script chạy hết stage trên **dữ liệu tổng hợp** trong container (Ultralytics 8.4.176, CPU, 1 epoch). Số liệu thử nghiệm vô nghĩa, không dùng. Chưa chạy trên dữ liệu thật.
