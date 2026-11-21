# Kết quả kịch bản E2E W8 (#118)

Kịch bản: `docs/w8/e2e_test_cases.md`, do Lê Ngọc An viết và chốt trước khi chạy (PR #122, #126).

| Tệp | Nguồn | Nội dung |
|---|---|---|
| `e2e_manual_An.csv` | Chép nguyên kết quả An ghi ở [#118, comment 7064084176](https://github.com/itsmarcusduong/uav-airspace-monitoring/issues/118#issuecomment-7064084176) (21/11/2026) | An chạy tay trên **bản sao** bundle demo `w8_demo` (run14 + run17, commit `5792ac6`): 6 PASS, 0 FAIL, 7 chưa kiểm được |
| `e2e_fixture_results.json` | `python scripts/pipeline/e2e_fixtures.py --out results/W08/e2e --commit <sha>` | Quang chạy tự động trên fixture tổng hợp theo đúng mô tả của từng ca, trên dashboard thật (Chromium headless). E2E-01…07, 09: 8 PASS, 0 FAIL |

Bundle fixture dựng bằng chính `build_bundle.py`, nên luật R1 trong fixture là luật thật. Video của fixture là mẫu thử `testsrc` của ffmpeg, không phải dữ liệu.

Lần chạy tự động đầu tiên báo E2E-04 FAIL do lỗi của bộ đo, không phải lỗi của dashboard. Bộ đo đóng WebSocket để giữ frame, nhưng dashboard xóa lớp vẽ khi mất kết nối (hành vi đúng), nên canvas trống. Bộ đo đã sửa: đặt `S.playing = false` trước khi đóng. Tiêu chí của ca không đổi.
