# Kaggle run 18 — benchmark W9 (C0, C1, C2, CPU)

- Notebook `e1-w9-run18-bench`, version `run18 commit 7833289`. COMMIT `7833289a92cf97077179ce62a60f7e51d52eaa6d`, chạy tay ngày 28/11/2026 trên GPU T4 x2 (dùng GPU 0), thời gian 18 phút 15 giây, ô cuối in `PASS`.
- Tệp tổng `w9_run18_all.zip`, SHA-256 `69b538b78648c27c0b9f64ceeafdc656a91a32866a1c223448ce7e17ebd56a89`. Tệp zip không đưa vào Git; thư mục này là các evidence zip đã giải nén.
- C2 (TensorRT) xuất engine thất bại cả 3 lần, mã thoát 2: `[Errno 30] Read-only file system: …/weights/best.onnx`. Ultralytics ghi tệp ONNX cạnh weights, mà weights nằm trong `/kaggle/input`, là thư mục chỉ đọc. Lỗi nằm ở bộ đo, đã sửa ở PR #141. Theo W9_PLAN mục C, C2 được ghi là "không khả thi". Có chạy lại C2 hay không do An quyết (#130).
- Áp luật B và C: `python scripts/experiments/w9_bench_select.py --runs results/W09/kaggle_run_18 --out results/W09/benchmark`.
