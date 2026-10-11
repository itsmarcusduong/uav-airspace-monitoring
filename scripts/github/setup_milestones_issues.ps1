<#
Tạo milestones W1–W14 và issues W2/W3 cho repo hiện tại.
Yêu cầu: GitHub CLI (gh) đã cài và đã đăng nhập (gh auth login); chạy trong thư mục repo đã clone.
    cd D:\code_source\e1-uav-airspace-monitoring
    powershell -ExecutionPolicy Bypass -File scripts\github\setup_milestones_issues.ps1 [-DryRun]
Script chỉ tạo mới; chạy lần 2 sẽ báo trùng milestone (không xóa gì).
#>
param([switch]$DryRun)
$ErrorActionPreference = "Stop"
$milestones = @(
  @{ title = "W1 – Phạm vi, lớp, metric, dataset, quy tắc nhãn, split"; due = "2026-10-03T23:59:59+07:00" },
  @{ title = "W2 – Chuẩn hóa dataset, thống kê lớp và chất lượng nhãn"; due = "2026-10-10T23:59:59+07:00" },
  @{ title = "W3 – Train baseline (config, weights, mAP/PR)"; due = "2026-10-17T23:59:59+07:00" },
  @{ title = "W4 – Tuning + augmentation, so sánh baseline (tag release)"; due = "2026-10-24T23:59:59+07:00" },
  @{ title = "W5 – Tích hợp tracker, video test ID ổn định"; due = "2026-10-31T23:59:59+07:00" },
  @{ title = "W6 – Geofence + cảnh báo theo trajectory"; due = "2026-11-07T23:59:59+07:00" },
  @{ title = "W7 – Hard negatives + confusion analysis"; due = "2026-11-14T23:59:59+07:00" },
  @{ title = "W8 – Pipeline E2E + dashboard/log (tag release)"; due = "2026-11-21T23:59:59+07:00" },
  @{ title = "W9 – Tối ưu inference, FPS/latency"; due = "2026-11-28T23:59:59+07:00" },
  @{ title = "W10 – Đánh giá detection + tracking trên test"; due = "2026-12-05T23:59:59+07:00" },
  @{ title = "W11 – Robustness + feature freeze + benchmark cố định (tag release)"; due = "2026-12-12T23:59:59+07:00" },
  @{ title = "W12 – Hoàn thiện thực nghiệm/ablation"; due = "2026-12-19T23:59:59+07:00" },
  @{ title = "W13 – Demo rehearsal + báo cáo"; due = "2026-12-26T23:59:59+07:00" },
  @{ title = "W14 – Release cuối (tag release)"; due = "2026-12-31T23:59:59+07:00" }
)
$issues = @(
  @{ ms = "W2"; title = "W2-00 Nền tảng GitHub: milestones, nhãn, template báo cáo"; body = "Phụ trách: Quang`nReview chéo: An`n`nTạo milestones W1–W14, issues W2, bật branch protection cho main, thêm docs/templates, docs/status, docs/project_versions.`n`nEvidence: link milestone/issue; cấu hình branch protection (đường dẫn trong báo cáo, không dùng ảnh chụp màn hình làm minh chứng duy nhất)." },
  @{ ms = "W2"; title = "W2-01 Kaggle: xác minh SHA-256 và chạy job EDA/audit"; body = "Phụ trách: Quang`nReview chéo: An`n`nChạy scripts/kaggle/w2_eda_audit_split.py.`n`nEvidence: results/W02/kaggle_run_01/.../stage_status.json (toàn OK), checksum_verification.csv, env.json." },
  @{ ms = "W2"; title = "W2-02 Inventory + EDA (lớp, cỡ bbox)"; body = "Phụ trách: Quang`nReview chéo: An`n`nEvidence: video_inventory.csv, class_stats.csv, fig_*.png; mục 3.2 của E1_DoAn_v0.2_W02." },
  @{ ms = "W2"; title = "W2-03 Tiêu chí audit nhãn + kiểm tra chéo bằng mắt"; body = "Phụ trách: An (tiêu chí), cả hai (xem)`nReview chéo: Nhau`n`nAudit tự động: docs/w2/annotation_audit_w2.md. Kiểm tra bằng mắt: cột review_quang đã điền sơ bộ cho 358 video (204 OK / 144 KHONG_RO / 10 SAI_NHAN); An xác nhận/sửa chuyển sang W3 (issue W3-01)." },
  @{ ms = "W2"; title = "W2-04 Giao thức split + ADR-0002/0003"; body = "Phụ trách: An`nReview chéo: Quang`n`nEvidence: docs/decisions/ADR-0002..0003 (Proposed), docs/w2/split_protocol.md." },
  @{ ms = "W2"; title = "W2-05 Split v1 theo video + báo cáo rò rỉ"; body = "Phụ trách: Quang`nReview chéo: An`n`nEvidence: data/splits/video_split_v1*.{csv,json}; scripts/dataset/make_video_split.py (seed 20261217)." },
  @{ ms = "W2"; title = "W2-06 Phần cứng tham chiếu + protocol + chỉ tiêu (họp GVHD)"; body = "Phụ trách: Cả hai`nReview chéo: —`n`nPhần cứng W2 = Kaggle CPU (env.json). Chỉ tiêu và kế hoạch tuần cần GVHD xác nhận (ADR-0002)." },
  @{ ms = "W2"; title = "W2-07 Version đồ án v0.2 (Mở đầu, 1.1–1.3, 3.2)"; body = "Phụ trách: An (khung), Quang (số liệu)`nReview chéo: Nhau`n`nEvidence: reports/w2/E1_DoAn_v0.2_W02.docx/.pdf." },
  @{ ms = "W2"; title = "W2-08 Báo cáo công việc W2 + PR evidence"; body = "Phụ trách: Quang`nReview chéo: An`n`nEvidence: reports/w2/E1_W02_bao_cao_cong_viec.docx/.pdf; PR có review chéo." },
  @{ ms = "W3"; title = "W3-01 An xác nhận/sửa cột review_quang trong review_assignment.csv"; body = "Phụ trách: An`nReview chéo: Quang`n`nCột review_quang được điền trước (có hỗ trợ công cụ, 3 frame/video) tại results/W02/review/review_assignment_w2.csv. An xem lại, ưu tiên 10 video SAI_NHAN, 144 KHONG_RO và toàn bộ video test;, điền verdict cuối (OK / SAI_NHAN / KHONG_RO) và ghi chú; thống kê tỷ lệ đồng ý.`n`nEvidence: results/W03/review_assignment_confirmed.csv." },
  @{ ms = "W3"; title = "W3-02 Chốt chính sách căn nhãn (253 video lệch số mục)"; body = "Phụ trách: Quang`nReview chéo: An`n`nChẩn đoán contrast (kaggle_run_02) không kết luận được (nhóm đối chứng không chọn offset 0); xem tay: 7/51 V-Bird có chim ngoài box. Đề xuất: loại 231 video dư 1 mục khỏi train/eval hoặc đo ảnh hưởng 1-frame bằng IoU liên frame; cập nhật ADR-0003." }
)
foreach ($m in $milestones) {
  if ($DryRun) { Write-Host "[dry] milestone: $($m.title) due $($m.due)"; continue }
  gh api "repos/{owner}/{repo}/milestones" -f title="$($m.title)" -f due_on="$($m.due)" | Out-Null
  Write-Host "milestone: $($m.title)"
}
foreach ($i in $issues) {
  $ms = ($milestones | Where-Object { $_.title -like "$($i.ms) *" }).title
  if ($DryRun) { Write-Host "[dry] issue: $($i.title) -> $ms"; continue }
  gh issue create --title $i.title --body $i.body --milestone $ms
}
