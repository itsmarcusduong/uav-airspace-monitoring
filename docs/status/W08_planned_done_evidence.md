# W8 (15/11–21/11/2026, chốt 22/11) — Planned / Done / Evidence / Problems / Next

Milestone `Tuan8`. Kế hoạch: `docs/w8/W8_PLAN.md`. Evidence: `Evidence/W08/`, tạo bằng `scripts/reporting/build_evidence.py`. Mọi số đo trên **val**; test vẫn khóa tới W10. **Tag `w08` bắt buộc** (Đề cương mục 10).

W8 bắt đầu 17/11 vì W7 làm bù.

| Issue | Planned | Done | Evidence | Trạng thái |
|---|---|---|---|---|
| #113 W8-01 (Quang) | Tập âm tính `e1-neg-v1`: manifest, license, sàng lọc, job chuẩn hóa | ADR-0014: FBD-SV-2024 chỉ dùng cho neg_eval, An duyệt (PR #114). Đã lưu bằng chứng license (JSON metadata Figshare). **Chưa** lập manifest clip Wikimedia/Pixabay, chưa sàng lọc, chưa chuẩn hóa | ADR-0014, `data/manifests/license_evidence/`, `license_matrix.csv` | CHƯA XONG → chuyển W9 |
| #115 W8-02 (Quang) | Run 17: V2 trong detector, chẩn đoán hộp trùng; áp luật B, C | Run 17 OK. **Luật B: áp dụng V2**, đạt 5/5 điều kiện. **Luật C: trường hợp 3**. Thêm 38 video H.264 cho dashboard | `results/W08/kaggle_run_17/`, `results/W08/v2_verify/`, `docs/w8/v2_verify_results.md`; PR #120, #123, #125, #127 | DONE |
| #116 W8-03 (Quang) | Pipeline lõi, SQLite, FastAPI + WebSocket, dashboard, nhật ký (ADR-0015) | ADR-0015 Accepted (#121). Pipeline phát lại (#124): kho sự kiện chỉ thêm, API, dashboard, `config_audit`. Sửa 4 lỗi An tìm ra. Fixture E2E tự động | `scripts/pipeline/`, `docs/w8/openapi_w8.json`, `tests/test_w8_pipeline.py`, `results/W08/e2e/` | DONE (chế độ phát lại) |
| #117 W8-04 (An) | Duyệt ADR-0014, ADR-0015, luật B–C; nháp 4.1–4.2 | Duyệt #114, #121, #124; sửa luật C trước run 17; nháp 4.1–4.2 (đã vào v0.8) | PR #122; `docs/w8/chuong4_4.1_4.2_nhap_An.md` | DONE |
| #118 W8-05 (An) | Kịch bản E2E viết trước rồi chạy trên dashboard | 13 ca viết trước (#122, #126). An chạy tay: 6 PASS, 0 FAIL, 7 chưa kiểm được. Fixture tự động: 8/8 PASS | `docs/w8/e2e_test_cases.md`, `results/W08/e2e/` | DONE |
| #119 W8-06 (Quang) | Báo cáo W8, v0.8, Evidence/W08, tag `w08` | Báo cáo 2 trang, v0.8 (mục 4.1, 4.2, 5.2, 5.3.8, 5.4.7), Evidence/W08 | `reports/w8/`, `Evidence/W08/` | Bản nộp; tag do Quang tạo |

## Kết quả chính
Nguồn: `results/W08/v2_verify/v2_verify.json`, `results/W08/e2e/`.

| Chỉ số (val, 38 video) | Run 14 (NMS 0,7) | Run 17 (NMS 0,5, V2) |
|---|---|---|
| ID switch / 1000 frame GT | 18,011 | 1,982 |
| Track recall gộp | 0,8425 | 0,8379 |
| Recall Drone mức ảnh (từ detection video, conf 0,25) | 0,8718 | 0,8718 |
| R1: sự kiện / cảnh báo sai trên video không Drone | 23/23 / 0 | 23/23 / 0 |
| R0: cảnh báo sai trên video không Drone | 7 | 7 |

- Chẩn đoán hộp trùng: tỷ lệ 10,8–11,7% ở cả 4 điều kiện, so với 0,6% của `model.val`. Đầu vào và fp16 đều không phải yếu tố (chênh dưới 3 điểm).
- E2E: 13 ca, 9 ca đạt, 0 ca trượt, 4 ca không kiểm được ở chế độ phát lại (camera, tải đầu vào, đổi cấu hình giữa phiên, phân quyền).

## Problems
1. #113 chưa xong: chưa có clip âm tính công khai nào được lập manifest hay chuẩn hóa. Cảnh báo sai/giờ vẫn chỉ đo trên 3,7 phút. Chuyển W9; vẫn giữ mục tiêu ≥ 120 phút.
2. Một số ca E2E An chạy tay dùng video val thay cho fixture đã mô tả; E2E-05 chỉ có khoảng vắng 1 frame. Đã bù bằng fixture đúng mô tả, chạy tự động. Lần đầu E2E-04 báo FAIL do lỗi của bộ đo (`results/W08/e2e/README.md`).
3. Demo là đầu-cuối về luồng dữ liệu, không phải thời gian thực. `stage_latency_ms` để trống; FPS và độ trễ đo ở W9.
4. Track recall giảm hơn 0,02 ở 4 video khi dùng V2, mạnh nhất V_HELICOPTER_012 (−0,194). Cần theo dõi khi đánh giá trên test ở W10.
5. Quy trình:
   - #120, #123, #125, #127 merge chưa có review GitHub của An. An có đọc #120 qua #122 (sửa luật C), nhưng chưa có review chính thức;
   - SQLite không ghi được trên ổ dùng chung của máy ảo (lỗi I/O), nên bundle được dựng ở chỗ khác rồi chép sang.

## Next (W9: tối ưu suy luận, FPS/độ trễ)
- `e1pipe` chạy từng frame trên Kaggle, có `stage_latency_ms`. Benchmark FPS/p95 đo ≥ 3 lần (NFR1).
- Hoàn tất `e1-neg-v1`: manifest, sàng lọc hai người, chuẩn hóa, đo cảnh báo sai/giờ. Thí nghiệm hard negative nếu đạt điều kiện kích hoạt (ADR-0011).
- Số đo mức ảnh tính từ đầu ra `predict` (luật C).
- ADR riêng cho đổi cấu hình giữa phiên và phân quyền (mục 4.4).
