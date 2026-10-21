#!/usr/bin/env python3
"""Bao cao cong viec tuan W3 (1-2 trang) -> docx. python scripts/reporting/build_w3_work_report.py --out reports/w3/E1_W03_bao_cao_cong_viec.docx"""
import argparse
from pathlib import Path
import docx
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
d = docx.Document()
s = d.sections[0]; s.page_width, s.page_height = Cm(21), Cm(29.7)
for m in ("left_margin", "right_margin"): setattr(s, m, Cm(1.8))
s.top_margin = s.bottom_margin = Cm(1.1)
st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(10)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(2)

def para(text, bold=False, size=None, align=None, italic=False):
    p = d.add_paragraph(); r = p.add_run(text); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    if align: p.alignment = align
    return p

REPO = "https://github.com/itsmarcusduong/uav-airspace-monitoring"
def add_link(par, text, url, size=8.5):
    rid = d.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    h = OxmlElement("w:hyperlink"); h.set(qn("r:id"), rid)
    r = OxmlElement("w:r"); rp = OxmlElement("w:rPr")
    c = OxmlElement("w:color"); c.set(qn("w:val"), "0563C1"); rp.append(c)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rp.append(u)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size * 2))); rp.append(sz)
    r.append(rp); t = OxmlElement("w:t"); t.text = text; t.set(qn("xml:space"), "preserve"); r.append(t); h.append(r)
    par._p.append(h)
def plain(par, text, size=8.5):
    r = par.add_run(text); r.font.size = Pt(size)
def table(header, rows, widths, size=8.5):
    t = d.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size)
        sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "D9E2F3"); c._tc.get_or_add_tcPr().append(sh)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(v); r.font.size = Pt(size)
    for row in t.rows:
        for i, w in enumerate(widths): row.cells[i].width = Cm(w)
    d.add_paragraph().paragraph_format.space_after = Pt(0)


PRS = [(22, "0c42206", "0c42206249534dc07c73ffc2dd81b9829ee72af2", "job xuất YOLO, kiểm tra lệch nhãn, job train, ADR-0004 (#16)",
        [("d686117", "d6861170e18773e9afaf85a3f7725719f21fe2de"), ("bf1cfe1", "bf1cfe181bfbef3a9201f2a10d07e950c364449c")]),
       (23, "680043b", "680043bf9cfd43033a92688cdaabbd547049c6cc", "review nhãn v2, notebook Kaggle 03a/03b/04 (#10)",
        [("40dcdb2", "40dcdb2b24676b7bc817663dd5ec794404d31767"), ("8bd12a0", "8bd12a04eaf508db7d2c949b23442d5f9ac49e34"),
         ("edc7d79", "edc7d794598956020ca63fd26f9beeab2fc4ea5c"), ("d204db3", "d204db393b29cb33d19c9a864dde10d583b64cbf")]),
       (25, "e762257", "e762257", "bằng chứng review v2, lệch nhãn, dữ liệu e1-yolo-v1 (#10, #11, #16)",
        [("e143e66", "e143e66ec61522a02510f202fe60544d7491d1c9"), ("b619a2e", "b619a2ec6e476e9cf9c3e102e2f072ae23e05f61")]),
       (26, "220cd8a", "220cd8a", "job phân tích val, notebook run 05, khung model card (#19)",
        [("98f69c8", "98f69c8e681bf06e5360838c17ddc64eddb3448b")])]
PENDING = "[chờ run 04]"

para("BÁO CÁO CÔNG VIỆC TUẦN 3 — NHÓM E1", True, 13, WD_ALIGN_PARAGRAPH.CENTER)
para("Đề tài: Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu", False, 9.5, WD_ALIGN_PARAGRAPH.CENTER, True)
para("Tuần 3 (11/10–17/10/2026) — Milestone W3: Train baseline (config, weights, mAP/PR). GVHD: TS. Nguyễn Tất Thắng. Sinh viên: Lê Ngọc An, Dương Minh Quang.")
para("1. GitHub: Issue / PR / Commit", True)
t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, h in enumerate(["Hạng mục", "Liên kết"]):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8.5)
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "D9E2F3"); c._tc.get_or_add_tcPr().append(sh)
def row(label):
    cells = t.add_row().cells; cells[0].text = ""; r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(8.5)
    cells[1].text = ""; return cells[1].paragraphs[0]
p = row("Milestone W3 / Issues W3-01…W3-08")
add_link(p, "Milestones", REPO + "/milestones"); plain(p, " · "); add_link(p, "Issues #10, #11, #16–#21", REPO + "/issues?q=milestone%3A%22W3+%E2%80%93+Train+baseline+%28config%2C+weights%2C+mAP%2FPR%29%22")
for num, m7, mfull, desc, commits in PRS:
    p = row(f"PR #{num}")
    add_link(p, f"PR #{num}", f"{REPO}/pull/{num}"); plain(p, f" — {desc}. Commit: ")
    for i, (sh7, full) in enumerate(commits):
        add_link(p, sh7, f"{REPO}/commit/{full}")
        if i < len(commits) - 1: plain(p, ", ")
    plain(p, "; merge "); add_link(p, m7, f"{REPO}/commit/{mfull}")
p = row("Review chéo")
plain(p, "An review PR #22 (approve bằng comment), #23, #25, #26 sau khi merge, nêu 3 lỗi kỹ thuật; đã sửa trong "); add_link(p, "PR #28", REPO + "/pull/28"); plain(p, " (gửi An review trước khi merge). Từ W4: mọi PR đều gửi yêu cầu review tới An trước khi merge.")
p = row("Kaggle (COMMIT dùng cho run)"); add_link(p, "680043b", REPO + "/commit/680043bf9cfd43033a92688cdaabbd547049c6cc"); plain(p, " — run 03a, 03b, 04")
p = row("Tag release"); plain(p, "Chưa có (tag đầu tiên tại W4)")
for r_ in t.rows:
    r_.cells[0].width = Cm(4.6); r_.cells[1].width = Cm(12.8)
d.add_paragraph().paragraph_format.space_after = Pt(0)
para("2. Phân chia công việc", True)
table(["Issue", "Nội dung", "Phụ trách", "Review", "Trạng thái"],
      [["#10 W3-01", "Review nhãn v2: 358 video, 8 frame/video + ảnh phóng to", "Quang", "An", "Hoàn thành (PR #23, #25)"],
       ["#11 W3-02", "Chính sách căn nhãn: độ nhạy IoU + thăm dò bằng mắt có đối chứng", "Quang", "An", "Hoàn thành; chiều lệch chưa xác định → W4 (#24)"],
       ["#16 W3-03", "ADR-0004 + xuất dữ liệu YOLO e1-yolo-v1", "Quang", "An", "Hoàn thành (PR #22, #25)"],
       ["#17 W3-04", "Giao thức train + config baseline A", "An", "Quang", "Bản nháp; phần của An chưa merge vào main"],
       ["#18 W3-05", "Train YOLOv8n@640 trên Kaggle GPU", "Quang", "An", "Đang chạy (run 04)"],
       ["#19 W3-06", "Phân tích val + model card", "An, Quang", "Nhau", "Job + khung model card xong (PR #26); chờ run 04"],
       ["#20 W3-07", "License Ultralytics/YOLOv8n", "An", "Quang", "An đã kiểm (nhánh code-lna), chưa merge"],
       ["#21 W3-08", "Báo cáo tuần + version v0.3 (1.4, 1.5)", "Quang, An", "Nhau", "Bản nháp"],
       ["#7 W2-06", "Chỉ tiêu, modality, tracker (họp GVHD)", "Cả hai", "—", "Chưa chốt"]],
      [1.9, 6.0, 1.9, 1.3, 6.3])
para("3. Planned – Done – Evidence – Problems – Next", True)
table(["Planned", "Done", "Evidence (đường dẫn trong repo)", "Problems", "Next week"],
      [["Chốt nhãn, xuất dữ liệu YOLO, train baseline A, đánh giá val, model card",
        "Review v2 358 video (OK 283 / SAI_NHAN 60 / KHONG_RO 15); giữ video dư 1 mục với offset 0; e1-yolo-v1: 216 video, 6.869 ảnh; job train + phân tích sẵn sàng",
        "results/W03/review/review_v2_summary.json; results/W03/kaggle_run_03a/export_evidence/offset_sensitivity_summary.json; results/W03/kaggle_run_03b/export_evidence/dataset_card.json; docs/decisions/ADR-0004*; docs/w3/model_card_baseline_A.md",
        "mAP/PR chưa có (run 04 đang chạy); thăm dò bằng mắt: đối chứng chỉ 53% → không xác định chiều lệch; val chỉ 3 video Bird; 77/242 video chưa xem bằng mắt; #7 chưa chốt với GVHD",
        "Điền model card, chạy run 05; W4: cấu hình đối chứng B + augmentation, tập chuẩn CVAT (#24), tag release W4"]],
      [3.0, 3.8, 4.4, 3.8, 2.4], size=8)
para("4. Kết quả đo (nguồn: CSV/JSON + script)", True)
table(["Chỉ số", "Giá trị", "Nguồn"],
      [["Review nhãn v2 (358 video)", "OK 283 / SAI_NHAN 60 / KHONG_RO 15", "results/W03/review/review_v2_summary.json"],
       ["IoU frame liên tiếp ≥ 0,5 (V, dư 1 mục)", "Drone 98,6% (95 video); Bird 95,3% (34 video)", "…/kaggle_run_03a/export_evidence/offset_sensitivity_summary.json"],
       ["Thăm dò offset bằng mắt (không phải review mù độc lập)", "Đối chứng 53% (8/15) < ngưỡng 80% → không kết luận", "results/W03/review/offset_review_score.json"],
       ["e1-yolo-v1 train / val", "178 video, 5.667 ảnh / 38 video, 1.202 ảnh (stride 10)", "…/kaggle_run_03b/export_evidence/dataset_card.json"],
       ["Baseline A: mAP@0.5, P, R (val)", PENDING, "results/W03/kaggle_run_04/ (chờ)"],
       ["Phần cứng train", PENDING, "kaggle_run_04/env.json (chờ)"]], [5.0, 5.8, 6.6])
para("5. Dataset card / model card", True)
para("Dataset card: results/W03/kaggle_run_03b/export_evidence/dataset_card.json (fingerprint d0ac7e23…). Model card baseline A: docs/w3/model_card_baseline_A.md (khung, điền sau run 04/05). Weights lưu Google Drive, ghi SHA-256 trong weights_manifest.json.")
para("6. Demo/video", True); para("Chưa có (tuần này không có sản phẩm demo).")
para("7. Vấn đề và rủi ro (trung thực)", True)
for t_ in ["Chiều lệch nhãn của video dư 1 mục chưa xác định; kết quả mAP@0.5 ít bị ảnh hưởng (IoU frame liên tiếp ≥ 95%) nhưng mAP@0.5:0.95 có thể bị kéo xuống. Kiểm chứng bằng tập chuẩn CVAT ở W4.",
           "Val dùng cả để dừng sớm lẫn báo cáo → số liệu val lạc quan; không so trực tiếp với chỉ tiêu trên test.",
           "Phần việc của An (#17, #20) mới ở nhánh code-lna, chưa qua PR; chỉ tiêu và tracker (#7) chưa được GVHD xác nhận."]:
    d.add_paragraph(t_, style="List Bullet")
a.out.parent.mkdir(parents=True, exist_ok=True); d.save(a.out); print("saved")
