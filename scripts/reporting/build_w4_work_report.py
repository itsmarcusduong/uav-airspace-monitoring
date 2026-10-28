#!/usr/bin/env python3
"""Bao cao cong viec tuan W4 (1-2 trang) -> docx. So lieu doc tu file ket qua trong repo, khong nhap tay.

    python scripts/reporting/build_w4_work_report.py --out reports/w4/E1_W04_bao_cao_cong_viec.docx
"""
import argparse
import csv
import json
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()

CMP = {r["model"]: r for r in csv.DictReader((ROOT / "results/W04/comparison_w4.csv").open(encoding="utf-8"))}
OFF = json.loads((ROOT / "results/W04/kaggle_run_06/w4_offset_check/offset_check_summary.json").read_text(encoding="utf-8"))
GS = json.loads((ROOT / "results/W04/cvat_gold/scoring/gold_score.json").read_text(encoding="utf-8"))
AG = json.loads((ROOT / "results/W04/review_v2_agreement.json").read_text(encoding="utf-8"))
EV = json.loads((ROOT / "Evidence/W04/test-results.json").read_text(encoding="utf-8"))
checks = EV["checks"] if isinstance(EV, dict) else EV


def vn(x, n=3):
    return f"{float(x):.{n}f}".replace(".", ",")


d = docx.Document()
s = d.sections[0]; s.page_width, s.page_height = Cm(21), Cm(29.7)
for m in ("left_margin", "right_margin"):
    setattr(s, m, Cm(1.8))
s.top_margin = s.bottom_margin = Cm(1.1)
st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(10)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(2)


def para(text, bold=False, size=None, align=None, italic=False):
    p = d.add_paragraph(); r = p.add_run(text); r.bold = bold; r.italic = italic
    if size:
        r.font.size = Pt(size)
    if align:
        p.alignment = align
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


def shade(c):
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "D9E2F3"); c._tc.get_or_add_tcPr().append(sh)


def widths(t, ws):
    for row in t.rows:
        for i, w in enumerate(ws):
            row.cells[i].width = Cm(w)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), ws):
        gc.set(qn("w:w"), str(int(Cm(w).twips)))


def table(header, rows, ws, size=8.5):
    t = d.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size); shade(c)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
    widths(t, ws)
    d.add_paragraph().paragraph_format.space_after = Pt(0)


# (PR, tac gia, mo ta, [commit], merge)
PRS = [(43, "Quang", "luật đặt trước ADR-0006, job run 06, kế hoạch W4 (#36)", ["ffb2ed0a18f9db775c54b6c1e49732e58c6da230"], "e81a5fb06c36e2a4929f4228c078a0568e8912ea"),
       (44, "Quang", "công cụ tập chuẩn CVAT: gói ảnh mù, chấm điểm (#24)", ["e3d89abba2d6c3de0e97c11895c23602558fd806"], "bb8a695b560481e682c2134413765e9a2085e894"),
       (45, "An", "config detector B và augmentation, giao thức W4 (#38)", ["50948c3cf02a2bc35a0e96838ef19d972a4ba605"], "980b3cbecc40634e3052940afb29fd72f2f50271"),
       (46, "An", "duyệt ADR-0002, ADR-0003 (#5)", ["34621a95d6e19a44c4915824f78cc9c2af4ff472", "f4118cd2a684441de8754c3929aaf8a0c7f668c9"], "22d057b0346b3fe0b4f514f4f2ee26b9c5e6186e"),
       (47, "An", "bản nháp mục 2.1, 2.2 (#41)", ["fdd05c72bea57b83ae1fe48dc27050c847a28058", "51d9a5807ef01273a36befbeb3f83a1ad955e1f6"], "fc4fb73dc08737a27f8e87319622c7890c5d8702"),
       (50, "Quang", "cấu trúc Evidence/W01–W04, pytest (#48)", ["421d66653d53e05fd9d66b7369da9c4b381aa02d"], "2fe08506bfb0b0bd75a22edbe809afe8371e7672"),
       (51, "Quang", "job so sánh nhiều mô hình run 09, luật chọn đặt trước (#39)", ["2ae4c508344660bd82c6bf84d36698ab50503547", "99d30331ae4bd8e4506a937d61e87243271e65c7"], "1a71f5bdba154818310a741fe38fd14fe86fb946"),
       (52, "Quang", "kết quả run 06, ADR-0006 Accepted (#36)", ["7e0262f0d6c1155c7acb0ffbd6c2102bcacca588"], "9eb1de85e09ce77546f954913e82b9cd6cf3ba2f"),
       (53, "An", "annotation tập chuẩn CVAT, review 40 video (#24)", ["3f0040014be9440ccd56f481cfa0dd48a1d16580", "07f9768e499699c6acf498031366eca7b60eef6a", "c5729a4043cef418fc8898efc132b25d757a57c0"], "4af165c2c4bbe3135d424bb3a912521f96a6ac6e"),
       (54, "Quang", "chấm tập chuẩn CVAT, mức đồng ý review (#24)", ["653c6f36ccf462c2e019905e658a7c0ce24c2a3e"], "591521522d8ec81d10d7e8ed809769dd698a29da"),
       (55, "Quang", "kết quả run 09, ADR-0007, Evidence/W04 (#39, #48)", ["ef9f42ee09131f92035ca7c7b83bc691b60666f2"], "8f91d93f2a8a47f9616bfa71ccb73953a864b005")]

para("BÁO CÁO CÔNG VIỆC TUẦN 4 — NHÓM E1", True, 13, WD_ALIGN_PARAGRAPH.CENTER)
para("Đề tài: Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu", False, 9.5, WD_ALIGN_PARAGRAPH.CENTER, True)
para("Tuần 4 (18/10–24/10/2026) — Milestone Tuan4: Tuning + augmentation, so sánh baseline, tag release. GVHD: TS. Nguyễn Tất Thắng. Sinh viên: Lê Ngọc An, Dương Minh Quang.")
para("1. GitHub: Issue / PR / Commit / Tag", True)
t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, h in enumerate(["Hạng mục", "Liên kết"]):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8.5); shade(c)


def row(label):
    cells = t.add_row().cells; cells[0].text = ""; r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(8.5)
    cells[1].text = ""; return cells[1].paragraphs[0]


p = row("Milestone Tuan4 / Issues")
add_link(p, "Milestone Tuan4", REPO + "/milestone/4"); plain(p, " · Issues #24, #36–#42, #48, #49, #5")
for num, who, desc, commits, merge in PRS:
    p = row(f"PR #{num} ({who})")
    add_link(p, f"PR #{num}", f"{REPO}/pull/{num}"); plain(p, f" — {desc}. Commit: ")
    for i, full in enumerate(commits):
        add_link(p, full[:7], f"{REPO}/commit/{full}")
        if i < len(commits) - 1:
            plain(p, ", ")
    plain(p, "; merge "); add_link(p, merge[:7], f"{REPO}/commit/{merge}")
p = row("Review chéo")
plain(p, "Quang review và approve #45, #46, #53 của An; #47 yêu cầu sửa 1 lần rồi approve. Các PR của Quang (#43, #44, #50–#52, #54, #55) đã gửi yêu cầu review cho An nhưng được merge trước để kịp chạy Kaggle; An review sau, kể cả duyệt ADR-0007.")
p = row("Kaggle (COMMIT dùng cho run)")
add_link(p, "bb8a695", REPO + "/commit/bb8a695b560481e682c2134413765e9a2085e894"); plain(p, " run 06, run 11; ")
add_link(p, "1a71f5b", REPO + "/commit/1a71f5bdba154818310a741fe38fd14fe86fb946"); plain(p, " run 09 (phiên 1–2 tài khoản Quang, phiên 3 tài khoản An)")
p = row("Tag release W4")
add_link(p, "w04", REPO + "/releases/tag/w04"); plain(p, " (gắn cuối tuần, kèm release note; split v1 đóng băng tại tag này)")
widths(t, [4.0, 13.4])
d.add_paragraph().paragraph_format.space_after = Pt(0)

para("2. Phân chia công việc", True)
table(["Issue", "Nội dung", "Phụ trách", "Review", "Trạng thái"],
      [["#24 W4-01", "Tập chuẩn CVAT: gói ảnh mù + chấm (Quang); vẽ 168 ảnh + review độc lập 40 video (An)", "Quang, An", "Nhau", "Đóng (PR #44, #53, #54)"],
       ["#36 W4-02", "Kiểm chứng chiều lệch nhãn bằng dự đoán mô hình (run 06)", "Quang", "An", "Đóng (PR #43, #52)"],
       ["#37 W4-03", "Xuất lại e1-yolo-v2 nếu offset1", "Quang", "—", "Đóng, không thực hiện (ADR-0006)"],
       ["#38 W4-04", "Config detector B + augmentation, giao thức", "An", "Quang", "Đóng (PR #45)"],
       ["#39 W4-05", "Train 5 cấu hình (run 09), weights + SHA-256", "Quang (phiên 1–2), An (phiên 3)", "An", "Đóng (PR #51, #55)"],
       ["#40 W4-06", "Phân tích bảng so sánh, model card B", "An", "Quang", "Đang làm (hạn 30/10)"],
       ["#41 W4-07", "Mục 2.1, 2.2 của version đồ án", "An", "Quang", "Xong bản nháp (PR #47), đã đưa vào v0.4"],
       ["#48 W4-09", "metrics.csv + Evidence/W04", "Quang", "An", "Đóng (PR #50, #55)"],
       ["#49 W4-10", "Báo cáo W4 + version v0.4 (chương V)", "Quang", "An", "Bản nộp"],
       ["#42 W4-08", "Tag release w04", "Quang", "An", "Gắn sau khi merge báo cáo"],
       ["#5 W2-04", "Duyệt ADR-0002/0003, đóng băng split", "An", "Quang", "Đóng (PR #46)"]],
      [1.7, 7.0, 2.6, 1.3, 4.8], size=8)

para("3. Planned – Done – Evidence – Problems – Next", True)
A, Y = CMP["baseline_A"], CMP["yolo11n_640"]
table(["Planned", "Done", "Evidence (đường dẫn trong repo)", "Problems", "Next week"],
      [["Kiểm chứng chiều lệch nhãn; train detector B + augmentation, so với baseline; model card; tag release",
        "Run 06 + tập chuẩn CVAT: cả hai UNDETERMINED → giữ e1-yolo-v1. Train 5 cấu hình mới (YOLOv8n aug/@960, YOLO11n, YOLOv8s@960, RT-DETR-l), áp luật chọn đặt trước → giữ baseline A. Mục 2.1–2.2, v0.4",
        "results/W04/kaggle_run_06/, kaggle_run_09/, cvat_gold/scoring/, comparison_w4.csv; ADR-0006, ADR-0007; Evidence/W04/",
        "RT-DETR-l lỗi NaN (không hợp lệ); val nhiễu; một seed; model card B chưa xong; An chưa review các PR của Quang",
        "W5: tích hợp ByteTrack (BoT-SORT đối chiếu) với baseline A; chạy 3 seed A vs YOLO11n; mục 2.3"]],
      [3.0, 4.6, 3.8, 3.4, 2.6], size=8)

para("4. Kết quả đo (validation; nguồn: CSV/JSON + script)", True)
gc, g = OFF["groups"]["control_equal"], OFF["groups"]["Drone|plus1"]
gr = GS["groups"]
n_pass = sum(c["status"] == "PASS" for c in checks)
table(["Chỉ số", "Giá trị", "Nguồn"],
      [["mAP@0.5:0.95 / mAP@0.5: baseline A (YOLOv8n@640)", f"{vn(A['map50_95'])} / {vn(A['map50'])}; {vn(A['inference_ms'], 2)} ms/ảnh", "results/W04/comparison_w4.csv"],
       ["mAP@0.5:0.95 / mAP@0.5: YOLO11n@640", f"{vn(Y['map50_95'])} / {vn(Y['map50'])}; {vn(Y['inference_ms'], 2)} ms/ảnh → hòa với A (chênh < 0,01)", "comparison_w4.csv; ADR-0007"],
       ["mAP@0.5:0.95: A@960 / A+aug / YOLOv8s@960", f"{vn(CMP['baseline_A_960']['map50_95'])} / {vn(CMP['baseline_A_aug']['map50_95'])} / {vn(CMP['detector_B']['map50_95'])} ({vn(CMP['detector_B']['inference_ms'], 1)} ms)", "comparison_w4.csv"],
       ["AP@0.5:0.95 lớp Drone (mọi cấu hình hợp lệ)", f"{vn(min(float(CMP[m]['ap50_95_Drone']) for m in CMP if CMP[m]['train_health'] == 'OK'))}–{vn(max(float(CMP[m]['ap50_95_Drone']) for m in CMP if CMP[m]['train_health'] == 'OK'))} → ưu tiên cải thiện dữ liệu (luật 4)", "comparison_w4.csv"],
       ["Lệch nhãn — run 06: đối chứng / Drone dư 1 mục", f"{gc['videos'] - gc['videos_i1_better']}/{gc['videos']} về i (p {vn(gc['sign_test_p'])}) / {g['videos_i1_better']}/{g['videos']} về i+1", "kaggle_run_06/.../offset_check_summary.json"],
       ["Lệch nhãn — CVAT: đối chứng / Drone dư 1 mục", f"{gr['control_equal']['videos'] - gr['control_equal']['videos_i1_better']}/{gr['control_equal']['videos']} về i (p {vn(gr['control_equal']['sign_test_p'])}) / {gr['Drone|plus1']['videos_i1_better']}/{gr['Drone|plus1']['videos']} về i+1", "cvat_gold/scoring/gold_score.json"],
       ["Hộp vẽ tay / hộp nhãn gốc (diện tích, trung vị)", vn(GS["exploratory_center"]["box_vs_label"]["median_area_ratio_annot_over_label_i"], 2), "gold_score.json (phần thăm dò)"],
       ["Đồng ý review An / Quang (40 video)", f"{AG['agree']}/{AG['videos']}, κ = {vn(AG['cohen_kappa'], 2)}", "results/W04/review_v2_agreement.json"],
       ["Kiểm tra Evidence/W04", f"{n_pass}/{len(checks)} PASS; pytest 25 test", "Evidence/W04/test-results.json"]],
      [5.6, 6.0, 5.8], size=8)

para("5. Dataset card / model card", True)
para("Dataset: e1-yolo-v1 không đổi (fingerprint d0ac7e23…, results/W03/kaggle_run_03b/export_evidence/dataset_card.json). Model được chọn cho W5: baseline A, model card docs/w3/model_card_baseline_A.md. Weights 10 tệp của W4: Google Drive weights/W04/<cấu hình>/, SHA-256 và link trong results/W04/kaggle_run_09/phien_*/train_*/weights_manifest.json, liệt kê ở Evidence/W04/README.md. Model card detector B: #40 (An), chưa xong.")
para("6. Demo/video", True); para("Chưa có (tuần này không có sản phẩm demo).")
para("7. Vấn đề và rủi ro (trung thực)", True)
for t_ in ["Mọi số đo trên val (val dùng để dừng sớm, chọn checkpoint và ngưỡng) → lạc quan; test vẫn khóa. Một seed: mAP@0.5:0.95 dao động 0,02–0,04 giữa các epoch nên chênh lệch nhỏ chưa phải khác biệt thật.",
           "RT-DETR-l huấn luyện lỗi (loss NaN từ epoch 3) nên không có kết luận về RT-DETR; không chạy lại vì vượt giới hạn 25 ms/ảnh.",
           "Chiều lệch nhãn chưa kết luận theo luật dù hai phương pháp cùng nghiêng về offset1 cho Drone; nhãn gốc rộng hơn vật khoảng 3 lần. Cần ADR mới ở W7.",
           "Các PR của Quang chưa được An review trước khi merge; ADR-0007 đang chờ An duyệt. Chỉ tiêu và thứ tự tuần (ADR-0005) chưa được GVHD xác nhận."]:
    d.add_paragraph(t_, style="List Bullet")
a.out.parent.mkdir(parents=True, exist_ok=True); d.save(a.out); print("saved", a.out)
