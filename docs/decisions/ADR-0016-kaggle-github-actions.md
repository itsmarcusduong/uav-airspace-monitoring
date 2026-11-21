# ADR-0016: Chạy job Kaggle qua GitHub Actions (bấm tay)

- Trạng thái: **Proposed** (Quang 22/11/2026). Chuyển **Accepted** khi An duyệt trên PR. Chưa Accepted thì không dùng workflow cho run có số liệu đưa vào báo cáo.
- Liên quan: W9-02, W9-03, `docs/w9/W9_PLAN.md` mục E, ADR-0010 (quy trình GitHub).

## Bối cảnh
- Từ W2, mọi job dữ liệu thật chạy trên Kaggle do Quang thao tác tay theo `docs/wN/kaggle_guide_wN_LOCAL.md`:
  - cập nhật dataset tools;
  - mở notebook, thêm input, sửa `COMMIT`, chạy;
  - tải zip về, giải nén.
- W9 cần chạy cùng job nhiều lần: benchmark 3 lần mỗi cấu hình (Thuyết minh mục 13) và chạy lại khi có clip âm tính mới. Làm tay dễ sai bước (W8: notebook đọc sai khóa, phải sửa ô).
- [WEB SOURCE] Kaggle CLI có các lệnh cần dùng:
  - `kaggle datasets version`;
  - `kaggle kernels push`, `status`, `output`;
  - `kernel-metadata.json` khai báo `dataset_sources`, `kernel_sources`, `enable_gpu`, `enable_internet`, `machine_shape`.
- Môi trường cloud của Claude không gọi được Kaggle API (proxy chặn); runner của GitHub Actions thì gọi được.

## Quyết định [DECISION]
1. Thêm workflow `.github/workflows/kaggle_run.yml`, **chỉ chạy khi bấm tay** (`workflow_dispatch`), không chạy theo lịch hay theo push.
2. Đầu vào của workflow:
   - tên job (ánh xạ tới notebook trong `scripts/kaggle/notebooks/`);
   - commit;
   - nhãn run (vd. `run20_c1_rep2`).
3. Các bước:
   1. checkout đúng commit;
   2. dựng thư mục dataset tools từ repo (script và cấu hình) → `kaggle datasets version` với ghi chú chứa commit;
   3. chép notebook, điền `COMMIT` và `RUN_TAG` bằng script (không sửa tay) → `kaggle kernels push`;
   4. chờ trạng thái `complete` hoặc `error`, thời gian tối đa 5 giờ;
   5. `kaggle kernels output` → tính SHA-256 từng tệp → tải lên làm artifact của Actions (giữ 30 ngày).
4. Kết quả **không tự commit** vào repo. Quang tải artifact, đặt vào thư mục `results/` như hiện nay, mở PR có review.
5. Token Kaggle do Quang tự thêm vào GitHub Secrets. Claude không nhập, không xem token.
6. Truy vết:
   - mỗi run ghi `runner` (`manual` hoặc `github-actions`), commit, phiên bản dataset tools và ID run của Actions vào `env.json`;
   - báo cáo nêu run nào chạy qua Actions.
7. **Lần chạy đầu của mỗi job vẫn chạy tay**, rồi chạy lại qua Actions với cùng commit. Kết quả phải khớp: cùng `stage_status`, cùng số liệu không phụ thuộc thời gian. Chỉ khi khớp mới dùng Actions cho các lần sau của job đó.
8. Dataset dữ liệu (Svanström, FBD-SV) **không** đi qua Actions. Workflow chỉ tham chiếu dataset Kaggle đã có, dữ liệu không ra ngoài Kaggle.

## Hệ quả
- Giảm thao tác tay và lỗi bước khi chạy lặp; mọi run có commit và log của Actions.
- Phụ thuộc thêm GitHub Actions và Kaggle API. Khi workflow lỗi thì quay về chạy tay; hướng dẫn `*_LOCAL.md` vẫn được giữ.
- Hạn mức GPU Kaggle vẫn tính như chạy tay; workflow không tự chạy lại khi lỗi.
- Claude không chạy thử được workflow từ môi trường của mình. Lần chạy đầu do Quang bấm và theo dõi.
