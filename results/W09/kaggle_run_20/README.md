# Kaggle run 20 — chạy ổn định 60 phút, cấu hình C0 (W9_PLAN mục C)

- Chạy qua GitHub Actions run `46148190658`, notebook `e1-w9-run20-stability`, COMMIT `98bc37938b74dd207dab844df3849249cdb725dd`, ngày 28/11/2026, GPU Tesla T4. Ô cuối in `PASS`.
- Phát lặp 38 video val trong 60 phút: 1059 lượt video, 329430 frame, FPS 91,735 (bỏ khởi động), p95 total 11,826 ms.
- Luật ổn định (W9_PLAN mục C): RSS phút 60 ≤ 1,10 × RSS phút 10. Kết quả: 1467,9 MB → 1550,6 MB, tỷ lệ 1,0563, không lỗi. Bộ nhớ GPU cấp phát giữ 42 MB.
- Tệp `w9_C0_rep1_stab_evidence.zip`: SHA-256 `dcb6bf77554c5f5340152835622e26d6d808496ba2a593f50ed1f2ce2770cc4a`. Tệp zip không đưa vào Git; `w9_C0_rep1_stab/` là nội dung đã giải nén. SHA-256 từng tệp ghi trong `ACTIONS_OUTPUT_MANIFEST.json` (đã đối chiếu khi đưa vào repo).
- Các lần dispatch trước run này dừng trước bước đo (lỗi cấu hình workflow, sửa ở #142–#149), không có kết quả.
- `inputs.json` có `actions_run_id` để trống, vì biến môi trường của GitHub không truyền vào phiên Kaggle. ID run nằm trong `ACTIONS_OUTPUT_MANIFEST.json`.
- Dùng cho luật C: `python scripts/experiments/w9_bench_select.py --runs results/W09/kaggle_run_18 [results/W09/kaggle_run_18b] --stability results/W09/kaggle_run_20/w9_C0_rep1_stab --out results/W09/benchmark`.
