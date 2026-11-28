# Kaggle run 18b — chạy lại C2 (TensorRT fp16) × 3 sau khi sửa bộ đo

- Notebook `e1-w9-run18-bench-c2` (run 18 với `ONLY = "C2"`, không chạy CPU; #155). COMMIT `834dc3feda6f9c16413ed430ba6a35a49f15ba69`; mã đo trùng 7833289 và 3ea87d9 (thay đổi sau đó chỉ ở notebook, workflow và tài liệu). Ngày 28–29/11/2026, GPU Tesla T4. Ô cuối in `PASS`.
- Lý do chạy lại: run 18 lần đầu xuất engine thất bại vì bộ đo ghi `best.onnx` cạnh weights trong `/kaggle/input` (chỉ đọc); PR #141 sửa bằng cách sao chép weights sang thư mục ghi được.
- Xuất engine thành công (224 giây ở lần 1); lần 2 và 3 dùng lại engine trong `/tmp/e1_engine_cache`, cùng SHA-256 `5448aac8…18928c` (`stage_status.json`).
- Tệp tổng `w9_run18_all.zip`: SHA-256 `00ccca85ccbc9089321a48adfec6d1c779c05a52b4935317505c6104978b65d3`. Zip không đưa vào Git; ba thư mục `w9_C2_rep*/` là nội dung đã giải nén, SHA-256 từng tệp khớp `ACTIONS_OUTPUT_MANIFEST.json` (137/137 tệp, đã kiểm khi đưa vào repo).
- Kết quả: FPS trung vị 198,8 (198,6–199,1), p95 total 5,44 ms. Luật C: **C2 không đạt giới hạn độ chính xác** (recall Drone 0,8291 so với C0 0,8718, giảm 0,043 > 0,01; thêm 1 cảnh báo sai R1 trên video không Drone) → cấu hình vận hành vẫn là C0 (`results/W09/benchmark/benchmark_summary.json`).
- Áp luật: `python scripts/experiments/w9_bench_select.py --runs results/W09/kaggle_run_18 results/W09/kaggle_run_18b --stability results/W09/kaggle_run_20/w9_C0_rep1_stab --out results/W09/benchmark`.
