# W2 (04/10–10/10/2026) — Planned / Done / Evidence / Problems / Next

| Issue | Planned | Done | Evidence | Trạng thái |
|---|---|---|---|---|
| W2-01 | Chạy Kaggle, xác minh SHA-256 | Done (CPU) | `results/W02/kaggle_run_01/.../checksum_verification.csv`, `stage_status.json`, `env.json` | DONE |
| W2-02 | Inventory + EDA | 650 video / 203.328 frame, thống kê lớp, bbox | `video_inventory.csv`, `class_stats.csv`, `fig_*.png` | DONE |
| W2-03 | Audit nhãn + xem chéo | Audit tự động xong; review sơ bộ 358/358 (có hỗ trợ công cụ, An xác nhận ở W3-01) | `annotation_audit*.csv/json`, `results/W02/review/review_assignment_w2.csv`, `docs/w2/annotation_audit_w2.md` | PARTIAL |
| W2-04 | Giao thức split → ADR | Soạn ADR-0002/0003 (Proposed) | `docs/decisions/`, `docs/w2/split_protocol.md` | PARTIAL (chờ duyệt) |
| W2-05 | Split v1 + rò rỉ | Split video-level 454/98/98 + sàng lọc rò rỉ | `data/splits/video_split_v1*.{csv,json}` | DONE (PROPOSED, chưa freeze) |
| W2-06 | Phần cứng/protocol/chỉ tiêu | Chưa họp GVHD; phần cứng W2 = CPU Kaggle | `env.json` | MISSING |
| W2-07 | Template v0.2 (Mở đầu, 1.1–1.3, 3.2) | Bản nháp `E1_DoAn_v0.2_W02` | file docx | PARTIAL |
| W2-08 | Báo cáo W2 | `E1_W02_bao_cao_cong_viec` (đã điền link Issue/PR/commit) | `reports/w2/*.docx/pdf`; PR #13: https://github.com/itsmarcusduong/uav-airspace-monitoring/pull/13 | PARTIAL (chờ review chéo của An + merge PR #13) |

## Problems
1. Phần của An (split file-level, audit không kiểm nhãn) không dùng được → `docs/w2/an_work_review.md`.
2. Lệch nhãn/frame 253 video; chẩn đoán run 02 không kết luận được (nhóm đối chứng không đạt) → chính sách loại tạm trong ADR-0003.
3. Review sơ bộ chưa có xác nhận của người thứ hai; chưa họp GVHD.
4. Rò rỉ cảnh/địa điểm không kiểm soát được.

## Next (W3)
An xác nhận/sửa review (W3-01); chốt chính sách căn nhãn (W3-02); export YOLO (train/val) → train baseline YOLOv8n trên Kaggle GPU; chốt ADR.

## GitHub
PR #13, 8 commit: 1fd337f, ceb77c4, b609888, 08647d1, 499f101, 20287b2, 2e10c2a, 48c8a04 (SHA đầy đủ trong báo cáo). SHA merge vào `main`: chưa có.
