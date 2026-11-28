# W9 (22/11–28/11/2026, chốt 29/11) — Planned / Done / Evidence / Problems / Next

Milestone `Tuan9`. Kế hoạch và luật đặt trước: `docs/w9/W9_PLAN.md` (An duyệt PR #135 trước khi chạy). Evidence: `Evidence/W09/`, tạo bằng `scripts/reporting/build_evidence.py`. Mọi số đo của detector/tracker trên **val**; test vẫn khóa tới W10. W9 không bắt buộc tag (Đề cương mục 10): ghi commit cuối tuần ở issue #134.

| Issue | Planned | Done | Evidence | Trạng thái |
|---|---|---|---|---|
| #129 W9-01 (Quang) | `e1pipe` chạy từng frame, có `stage_latency_ms`; qua cổng tái tạo so với run 17 | `e1pipe` + engine R1 trực tuyến (#136); sửa 2 lỗi đo An tìm ra (#137). **Cổng B đạt**: 11474/11474 dòng track, 25/25 sự kiện R1 | `scripts/pipeline/e1pipe.py`, `tests/test_w9_e1pipe.py`, `results/W09/benchmark/` | DONE |
| #130 W9-02 (Quang) | Benchmark C0/C1/C2/CPU ≥ 3 lần; chạy 60 phút; chọn cấu hình theo luật C | Run 18: C0, C1 ×3, CPU ×1. **Luật C chọn C0.** Run 20: chạy 60 phút đạt. C2: lần đầu lỗi bộ đo (thư mục chỉ đọc), sửa ở #141, chạy lại ở run 18b | `results/W09/kaggle_run_18/`, `kaggle_run_20/`, `benchmark/` | C2_STATUS |
| #131 W9-03 (Quang) | Tập âm tính: chuẩn hóa FBD-SV-2024, manifest nguồn công khai, cảnh báo sai/giờ | FBD-SV-2024: 483 clip, 19,13 phút (run 19b3). Manifest 83 ứng viên Commons từ API gốc, giao thức sàng lọc viết trước (#138, #153) | `results/W09/kaggle_run_19/`, `data/manifests/neg_commons_candidates.csv`, `docs/w9/neg_screening_protocol.md` | FBD-SV DONE; Commons chờ sàng lọc → W10 |
| #132 W9-04 (An) | Duyệt luật W9 (B–E), ADR-0016 trước khi chạy; sàng lọc độc lập clip âm tính | Duyệt #135; review #136 (2 lỗi đo); yêu cầu sửa luật sàng lọc trước khi lập danh sách (#138). Sàng lọc: Quang đã điền tệp của mình, An đang làm | PR #135, #136, #138 | Duyệt DONE; sàng lọc → W10 |
| #133 W9-05 (An) | Chương IV: cập nhật 4.3, viết 4.4 | Nháp 4.3–4.4 (#140, Quang yêu cầu sửa 2 lần); đã vào v0.9 | `docs/w9/chuong4_4.3_4.4_nhap_An.md` | DONE |
| #134 W9-06 (Quang) | Báo cáo W9, v0.9, Evidence/W09, commit cuối tuần | Báo cáo công việc, v0.9 (4.3, 4.4, 5.2, 5.3.9, 5.4.8), Evidence/W09 | `reports/w9/`, `Evidence/W09/` | Bản nộp |

## Kết quả chính
Nguồn: `results/W09/benchmark/benchmark_summary.json`, `results/W09/kaggle_run_20/w9_C0_rep1_stab/summary.json`, `results/W09/kaggle_run_19/w9_neg_fbdsv/neg_summary.json`.

BENCH_TABLE

- Chạy 60 phút với C0 (run 20): 329430 frame, 91,7 FPS, p95 total 11,8 ms; RSS phút 60 / phút 10 = 1,0563 ≤ 1,10 → **đạt**. RSS tăng gần tuyến tính (1,76 MB/phút); khoảng 79% mức tăng do bộ đo giữ toàn bộ dòng latency trong RAM (thăm dò, `results/W09/benchmark/rss_growth_check.json`).
- FBD-SV-2024 (483 clip, 19,13 phút, C0, ROI center_hex):

| Luật | Cảnh báo sai | Mỗi giờ | Cận trên 95% | Clip có cảnh báo sai |
|---|---|---|---|---|
| R0 | 142 | 445,33 | 511,88 | 125 |
| R1 | 44 | 137,99 | 177,42 | 34 |

  26,9% frame có detection Drone (conf ≥ 0,25); 418/444 track có lớp đa số là Drone (thăm dò). **Điều kiện ADR-0011 mục 3 đạt** → thí nghiệm hard negative ở W10.

## Problems
1. Detector nhận gần như mọi chim nhỏ, xa trong FBD-SV là Drone. R1 giảm 69% cảnh báo sai so với R0 nhưng vẫn 138/giờ, không dùng được để vận hành.
2. Tổng âm tính mới 19 phút (mục tiêu ≥ 120 phút). Commons chờ An sàng lọc; Pixabay chưa làm. Clip FBD-SV ngắn (trung vị 2 giây), mỗi clip bắt đầu bằng track mới.
3. Run 19: lần 1 lỗi tràn số ở `poisson_upper` sau khoảng 4 giờ (#150); lần 2 chuẩn hóa chậm, hủy (#151); lần 3 (19b3) xong.
4. Số đo tốc độ chỉ trên Tesla T4, đọc video từ tệp; chưa đo trên test.
5. Quy trình: WARN_LIST

## Next (W10: đánh giá detection + tracking trên test)
- Thí nghiệm hard negative `e1-yolo-v1-hn` theo ADR-0011 (luật chọn đặt trước); dữ liệu train từ `neg_train` của Commons sau khi sàng lọc.
- Gộp hai tệp sàng lọc (`commons_manifest.py --finalize`), chuẩn hóa và đo Commons, báo riêng theo nguồn.
- Bộ đo ghi latency xuống đĩa theo từng video (bỏ nguồn tăng RSS do bộ đo).
- Mở khóa test theo giao thức: đánh giá detection + tracking + cảnh báo với cấu hình đã chọn.
