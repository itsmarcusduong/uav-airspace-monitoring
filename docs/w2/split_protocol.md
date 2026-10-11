# Giao thức chia dữ liệu v1 (đề xuất, chưa đóng băng)

Tạo bằng `scripts/dataset/make_video_split.py` (đọc metadata, không giải mã video). Kết quả: `data/splits/video_split_v1.csv`, `video_split_v1_summary.csv`, `video_split_v1_manifest.json` (SHA-256 đầu vào/đầu ra, seed). Seed cơ sở 20261011, tìm 3.000 seed, chọn **20261217** (độ lệch cân bằng 0,0718).

## Nguyên tắc
- Đơn vị chia = **video** (mp4 + `_LABELS.mat` luôn cùng split). Không chia theo frame hay theo file.
- Phân tầng `modality × class` (8 tầng); tỷ lệ 70/15/15; tầng có < 4 video không có val/test (không xảy ra ở dữ liệu này).
- Seed được chọn để cân bằng thêm: số frame và frame có bbox theo lớp, số video/frame theo **distance bin** (CLOSE/MEDIUM/DISTANT từ workbook), và theo modality. Bản chia của Kaggle (seed 20261092) chỉ cân bằng theo lớp và làm test thiếu video DISTANT (27,6% so với 37,0% ở train); bản này sửa điều đó (test DISTANT 33,7% so với train 34,8%).
- Tăng cường dữ liệu chỉ trên train; ngưỡng chọn trên val; test khóa tới W11.

## Kết quả
| Split | Video | Frame | Frame có bbox |
|---|---|---|---|
| train | 454 | 142.187 | 136.013 |
| val | 98 | 30.545 | 28.943 |
| test | 98 | 30.596 | 29.596 |
Theo lớp (train/val/test video): Airplane 93/20/20, Bird 90/20/20, Drone 189/41/41, Helicopter 82/17/17. IR 255/55/55, Visible 199/43/43.

## Rò rỉ — mức bảo đảm hạn chế (phải nói thẳng trong báo cáo)
1. **Cặp IR/V cùng class+number**: 279 cặp; 123 cặp rơi vào split khác nhau. Chưa có bằng chứng là cùng sự kiện: số `INTER BIN NUMBER` trùng chỉ 23/279 cặp và số frame trùng 16/279. Do đó mặc định **không** gom cặp (`NEEDS_REVIEW`).
2. **Trùng cảnh**: sàng lọc dHash (Hamming ≤ 4, cùng modality) tìm thấy 562 cặp video khác split (437 cặp cùng lớp). Dữ liệu thu ở số ít vị trí cố định nên cảnh/nền lặp lại; split theo video **không** bảo đảm test là "cảnh chưa thấy". dHash chỉ là sàng lọc thô, chưa phải bằng chứng đầy đủ.
3. Workbook không có thông tin phiên quay/địa điểm → không thể giữ nguyên một nguồn/phiên cho kiểm thử khác miền (Thuyết minh 8.3). Cần đối chiếu README của dataset hoặc xem tay ở W3–W4; hiện tại ghi là giới hạn.
4. 12 video không bbox nằm trong split (9 train, 2 val, 1 test theo bản Kaggle; bản v1 xem cột `all_absent`).

## Điều kiện đóng băng
An và Quang cùng duyệt → tag commit → ghi SHA-256 `video_split_v1.csv` vào manifest/báo cáo. Thay đổi sau đó phải có ADR và tăng phiên bản (v1.1).
