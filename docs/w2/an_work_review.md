# Đánh giá phần việc của An (W2) và đối chiếu với kết quả Kaggle

Ngày rà: 11/10/2026. Phạm vi: `docs/w2/report.md`, `scripts/{eda_analysis,annotation_audit,make_split}.py`, `data/splits/{train,val,test}_v1.csv`, `split_v1_manifest.json`, `An_Work/w1/Thuyet_minh_de_tai_UAV_Drone_san_bay.docx`. Nguồn đối chiếu: `results/W02/kaggle_run_01/` (Quang chạy, `stage_status.json` toàn OK).

## Kết luận ngắn
Phần của An **chưa dùng được làm evidence W2** (đặc biệt split), nhưng ý định và khung báo cáo đúng hướng. Phải thay bằng kết quả Kaggle + `video_split_v1`. Thuyết minh trong `An_Work/w1/` **giống hệt từng byte** file trong `docs/reference/briefs/` (đã `cmp`), không phải báo cáo W1 riêng; nó là nguồn nội dung rất tốt để điền template.

## Vấn đề cụ thể (có bằng chứng)
| # | Phát hiện | Bằng chứng | Hệ quả |
|---|---|---|---|
| 1 | "1.303 chuỗi/video" sai: 1.303 là số **bản ghi file** trong `svanstrom_files.csv` (650 mp4 + 650 `_LABELS.mat` + 1 xlsx + 2 demo mp4). Số video thật = **650**. | `stage_status.json`: videos=650; tổng 4 lớp trong chính report của An = 271+133+130+116 = 650 | Báo cáo tự mâu thuẫn |
| 2 | Split 912/195/196 được tạo trên **file**, không phải video; do CSV không có cột class nên script rơi vào nhánh "random toàn bộ" (không phân tầng) | Header `train_v1.csv` = `relative_path,suffix,bytes,sha256`; `make_split.py` cần cột class/label | Không phải stratified theo lớp |
| 3 | **Rò rỉ trực tiếp**: mp4 và `_LABELS.mat` của cùng video nằm ở split khác nhau (316/650 video); file xlsx lọt vào test | Đối chiếu tên file giữa 3 CSV | Vi phạm nguyên tắc split theo video (Đề cương mục 8, Thuyết minh 8.3). Tuyên bố "Test frozen" không đúng |
| 4 | `annotation_audit.py` không kiểm tra nhãn: chỉ đếm null của cột `file_path` (cột này không tồn tại → luôn 0). Câu "1.303/1.303 bản ghi hợp lệ" không có căn cứ | Mã nguồn; kết quả audit thật: **276/650 video** có cảnh báo | Chưa có annotation audit thực sự |
| 5 | `eda_analysis.py` gán cứng `class_stats` (comment "dựa trên W1") thay vì tính | Mã nguồn | Số đúng nhưng không tái lập được |
| 6 | Mô tả "đa số mục tiêu là vật thể nhỏ" không có số; còn sót chuỗi `[cite: 1]` trong report | `report.md` | Cần số liệu và làm sạch |
| 7 | Script đặt ở `scripts/` (không phải `scripts/dataset/`), không argparse/logging; seed 20261010 khác quy ước | — | Nhỏ; cần chuẩn hóa nếu muốn giữ |

## Phần dùng lại được
- Mục tiêu W2 và khung báo cáo (EDA → audit → split → kế hoạch W3).
- Tỷ lệ 70/15/15, seed cố định, ý tưởng chuẩn bị chuyển YOLO ở W3.
- Con số theo lớp (271/133/130/116) đúng với kết quả Kaggle — nay có nguồn tính toán.
- Thuyết minh: nguồn chính cho Mở đầu, 1.1–1.5, và các chương sau trong template.

## Việc đề nghị cho An (không mang tính phê bình cá nhân — mọi người đều làm trong điều kiện thiếu dữ liệu hợp lệ)
1. Lưu bản gốc vào `An_Work/w2_original/` (không xóa) và dùng `data/splits/video_split_v1.*` làm split chính.
2. Cùng Quang xem `review_sheets` (180 video/người, `review_assignment.csv`) và điền `verdict`.
3. Soạn tiêu chí audit (W2-03) và duyệt ADR-0002/0003; viết/duyệt Mở đầu + Chương I trong `E1_DoAn_v0.2_W02.docx`.
4. Mọi PR đưa vào repo sạch cần review chéo (Quang review An và ngược lại).
