#!/usr/bin/env python3
"""Bao cao cong viec tuan W5 (1-2 trang) -> docx. So lieu doc tu file ket qua trong repo, khong nhap tay.

    python scripts/reporting/build_w5_work_report.py --out reports/w5/E1_W05_bao_cao_cong_viec.docx
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

def rj(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


SD = rj("results/W05/seed_decision.json")
TC = list(csv.DictReader((ROOT / "results/W05/track_comparison.csv").open(encoding="utf-8")))
TD = rj("results/W05/track_decision.json")
TG = rj("results/W05/track_gaps.json")
DEMO = rj("results/W05/kaggle_run_12/w5_track/demo/demo_index.json")
EV = rj("Evidence/W05/test-results.json")
N_PYTEST = sum(1 for c in EV["checks"] if c["check"].startswith("pytest::"))


def tc(tracker, iou="0.5", cls="all"):
    return next(r for r in TC if r["tracker"] == tracker and r["iou_thr"] == iou and r["class"] == cls)

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
PRS = [(63, "Quang", "job tracking run 12, độ đo liên kết ADR-0008, job 3 seed run 13 (#57, #59)", ["5f846501fb196c620e5a3c2835ff22f5e2badab7"], "26c94626db6f325befad039be8a654a7488656d2"),
       (64, "An", "phân tích so sánh W4, model card detector B, duyệt ADR-0007 (#40)", ["ce90e197c39af2df4e4ea5029d95cb7d4b6118cc"], "a40b9864443557f14aa5559d6318e6a0e28fdd7f"),
       (65, "An", "cấu hình tracker e1, giao thức so sánh, duyệt ADR-0008 (#58)", ["80c543a670d89e069d0a0536cbfabda9d14991e7"], "03e43a881c41d515b1236c84f51915422953fdc7"),
       (66, "An", "bản nháp mục 2.3 (#60)", ["ed91be956bac838f8fd411d2274d327fd006def1", "e34997925e7e7ed144f2ad27a2f06223b5600b58"], "93e7fa77d10212a36feff54d07410d99dc34d464"),
       (67, "Quang", "kết quả 3 seed run 13, ADR-0007 cập nhật (#59)", ["09815006e5ce1d4a84fd0a49c2d24167b8ffea77"], "89093677a371fb7b8dc8e341dfd7dcc5d0a10669"),
       (68, "Quang", "kết quả tracking run 12 (#57)", ["40c4a76fa768dd38e47e240c41d17840d55b7d10"], "2c6de1b531f67edd387927960ffee20782647a21"),
       (69, "Quang", "chốt 5 video bất đồng review v2 (#24)", ["cef70ca4d94c916d250add218464cf472c8fb126"], "46d0f3a148b6e5d40982c9700c11d4645fce0ea0"),
       (70, "Quang", "kết quả run 12b, chọn tracker theo ADR-0008 (#57)", ["0e3035c39f41dd5bbec1411d4c5c77abfd1e37ff"], "b0a93069189eda806af14725bf0b58d3385d9498")]

para("BÁO CÁO CÔNG VIỆC TUẦN 5 — NHÓM E1", True, 13, WD_ALIGN_PARAGRAPH.CENTER)
para("Đề tài: Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu", False, 9.5, WD_ALIGN_PARAGRAPH.CENTER, True)
para("Tuần 5 (25/10–31/10/2026) — Milestone Tuan5: tích hợp tracker, video test ID ổn định. GVHD: TS. Nguyễn Tất Thắng. Sinh viên: Lê Ngọc An, Dương Minh Quang.")
para("1. GitHub: Issue / PR / Commit / Tag", True)
t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, h in enumerate(["Hạng mục", "Liên kết"]):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8.5); shade(c)


def row(label):
    cells = t.add_row().cells; cells[0].text = ""; r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(8.5)
    cells[1].text = ""; return cells[1].paragraphs[0]


p = row("Milestone Tuan5 / Issues")
add_link(p, "Milestone Tuan5", REPO + "/milestone/5"); plain(p, " · Issues #57–#62; #24 (W4) đóng tuần này")
for num, who, desc, commits, merge in PRS:
    p = row(f"PR #{num} ({who})")
    add_link(p, f"PR #{num}", f"{REPO}/pull/{num}"); plain(p, f" — {desc}. Commit: ")
    for i, full in enumerate(commits):
        add_link(p, full[:7], f"{REPO}/commit/{full}")
        if i < len(commits) - 1:
            plain(p, ", ")
    plain(p, "; merge "); add_link(p, merge[:7], f"{REPO}/commit/{merge}")
p = row("Review chéo")
plain(p, "Quang review và approve #64, #65, #66 của An (có góp ý sửa mục 2.3; Quang cập nhật số liệu W5 vào bản nháp, chờ An xác nhận). Các PR của Quang (#63, #67–#70) đã gửi yêu cầu review cho An nhưng được merge trước để kịp chạy Kaggle; An chưa review, gồm phần cập nhật ADR-0007 sau 3 seed.")
p = row("Kaggle (COMMIT dùng cho run)")
add_link(p, "26c9462", REPO + "/commit/26c94626db6f325befad039be8a654a7488656d2"); plain(p, " run 12 (tracker mặc định), run 13 (2 seed mới); ")
add_link(p, "46d0f3a", REPO + "/commit/46d0f3a148b6e5d40982c9700c11d4645fce0ea0"); plain(p, " run 12b (tracker e1). Cả ba do Quang chạy.")
p = row("Tag W5")
add_link(p, "w05", REPO + "/releases/tag/w05"); plain(p, " (gắn cuối tuần sau khi merge báo cáo)")
widths(t, [4.0, 13.4])
d.add_paragraph().paragraph_format.space_after = Pt(0)

para("2. Phân chia công việc", True)
table(["Issue", "Nội dung", "Phụ trách", "Review", "Trạng thái"],
      [["#57 W5-01", "Pipeline video → detector → tracker, track log, độ đo liên kết (run 12, 12b)", "Quang", "An", "Đóng (PR #63, #68, #70)"],
       ["#58 W5-02", "Cấu hình tracker e1, giao thức so sánh, duyệt ADR-0008", "An", "Quang", "Đóng (PR #65)"],
       ["#59 W5-03", "2 seed mới cho baseline A và YOLO11n (run 13), chọn lại theo luật", "Quang", "An", "Đóng (PR #63, #67)"],
       ["#60 W5-04", "Mục 2.3 Công nghệ và lý do lựa chọn", "An", "Quang", "Đóng (PR #66), đã đưa vào v0.5"],
       ["#61 W5-05", "Phân tích lỗi liên kết trên video demo", "An", "Quang", "Đang làm"],
       ["#62 W5-06", "Báo cáo W5, v0.5, Evidence/W05, tag w05", "Quang", "An", "Bản nộp"],
       ["#40 W4-06", "Phân tích so sánh W4, model card detector B", "An", "Quang", "Đóng (PR #64)"],
       ["#24 W4-01", "Chốt 5 video review bất đồng: An xem lại, cả 5 SAI_NHAN", "An, Quang", "Nhau", "Đóng (PR #69)"]],
      [1.7, 7.0, 2.2, 1.3, 5.2], size=8)

para("3. Planned – Done – Evidence – Problems – Next", True)
table(["Planned", "Done", "Evidence (đường dẫn trong repo)", "Problems", "Next week"],
      [["Tích hợp ByteTrack (BoT-SORT đối chiếu) với detector đã chọn, video test ID ổn định; 3 seed A và YOLO11n; mục 2.3",
        "Tracking trên 38 video val, 2 tracker × 2 cấu hình, luật đặt trước → giữ ByteTrack-e1. 3 seed → đổi detector sang YOLO11n theo luật. 3 video demo. Mục 2.3, Chương II bản 1, v0.5",
        "results/W05/kaggle_run_12/, kaggle_run_12b/, kaggle_run_13/; track_comparison.csv, seed_comparison.csv; ADR-0007, ADR-0008; Evidence/W05/",
        "Không có track ID thật (GT dẫn xuất, không phải HOTA/IDF1); ID switch do track trùng; bằng chứng đổi detector yếu; #61 chưa xong",
        "W6: tracking với YOLO11n + ByteTrack-e1; xử lý track trùng (giao thức đặt trước); geofence + cảnh báo theo quỹ đạo"]],
      [3.0, 4.4, 3.8, 3.6, 2.6], size=8)

para("4. Kết quả đo (validation; nguồn: CSV/JSON + script)", True)
S = SD["summary"]; bt, bs, b3 = tc("tracker_bytetrack_e1"), tc("tracker_botsort_e1"), tc("tracker_bytetrack_e1", "0.3")
pb = next(p for p in TG["pairs"] if p["b"]["dir"].endswith("tracker_bytetrack_e1"))
n_pass = sum(c["status"] == "PASS" for c in EV["checks"])
table(["Chỉ số", "Giá trị", "Nguồn"],
      [["mAP@0.5:0.95 trung bình ± SD, 3 seed: baseline A / YOLO11n", f"{vn(S['baseline_A']['map']['mean'], 4)} ± {vn(S['baseline_A']['map']['sd'], 4)} / {vn(S['yolo11n_640']['map']['mean'], 4)} ± {vn(S['yolo11n_640']['map']['sd'], 4)} → hòa", "results/W05/seed_comparison.csv"],
       ["F1 Drone trung bình; ms/ảnh: A / YOLO11n", f"{vn(S['baseline_A']['f1']['mean'])} / {vn(S['yolo11n_640']['f1']['mean'])}; {vn(S['baseline_A']['ms']['mean'], 2)} / {vn(S['yolo11n_640']['ms']['mean'], 2)} → chọn YOLO11n", "results/W05/seed_decision.json"],
       ["ID switch / 1000 frame GT (IoU 0,5): ByteTrack-e1 / BoT-SORT-e1", f"{vn(bt['idsw_per_1000_gt_frames'], 2)} / {vn(bs['idsw_per_1000_gt_frames'], 2)} (chênh {vn(100 * TD['decision']['rel_diff'], 1)}% → hòa → ByteTrack)", "results/W05/track_decision.json"],
       ["Track recall; trung vị độ phủ ID chính (ByteTrack-e1)", f"{vn(bt['track_recall_pooled'])}; {vn(bt['median_dominant_id_coverage'])}; {bt['videos_single_id']}/{bt['videos']} video chỉ 1 ID", "results/W05/track_comparison.csv"],
       ["Đứt track IoU 0,5 → 0,3 (ByteTrack-e1)", f"{bt['fragments']} → {b3['fragments']} (hộp nhãn rộng)", "track_comparison.csv"],
       ["Track log e1 trùng cấu hình mặc định", f"{pb['identical']}/{pb['files']} video (track_buffer không tác dụng)", "results/W05/track_gaps.json"],
       ["FPS trung vị (giải mã + detect + track, T4): ByteTrack-e1 / BoT-SORT-e1", f"{vn(TD['fps_median']['tracker_bytetrack_e1'], 1)} / {vn(TD['fps_median']['tracker_botsort_e1'], 1)} (tham khảo)", "track_decision.json"],
       ["Kiểm tra Evidence/W05", f"{n_pass}/{len(EV['checks'])} PASS; pytest {N_PYTEST} test", "Evidence/W05/test-results.json"]],
      [6.0, 6.2, 5.2], size=8)

para("5. Dataset card / model card", True)
para("Dataset: e1-yolo-v1 không đổi (fingerprint d0ac7e23…). Weights 8 tệp của run 13: Google Drive weights/W05/<cấu hình>/, SHA-256 và link trong results/W05/kaggle_run_13/train_*/weights_manifest.json. Model card detector B: docs/w4/model_card_detector_B.md (An). Model card YOLO11n: làm ở W6 trước khi dùng.")
para("6. Demo/video", True)
p = d.add_paragraph(); plain(p, "3 video demo ByteTrack có vẽ ID (val, chọn theo luật đặt trước trong job): ", 9.5)
for i, x in enumerate(DEMO):
    add_link(p, x["video_id"], x["drive_link"], 9.5)
    if i < len(DEMO) - 1:
        plain(p, ", ", 9.5)
plain(p, ". SHA-256 trong results/W05/kaggle_run_12/w5_track/demo/demo_index.json.", 9.5)
para("7. Vấn đề và rủi ro (trung thực)", True)
for t_ in ["Svanström không có track ID: độ đo liên kết dùng GT dẫn xuất \"1 track/video\", không phải MOTA/IDF1/HOTA; vật thể khác trong khung hình không có nhãn. Mọi số đo trên val (lạc quan); test vẫn khóa.",
           "Đổi detector sang YOLO11n dựa trên tiêu chí phụ (F1 Drone +0,014) nhỏ hơn độ lệch chuẩn giữa các seed; luật nhiều seed viết sau khi biết seed đầu (đã ghi rõ trong giao thức).",
           "ID switch tập trung ở video có hai track trùng trên cùng vật; tăng track_buffer gần như không có tác dụng. Xử lý ở W6 cần giao thức đặt trước.",
           "An chưa review các PR của Quang (#63, #67–#70) và phần cập nhật ADR-0007; #61 chưa xong. FPS chỉ tham khảo (dao động khoảng 11% giữa hai lần chạy)."]:
    d.add_paragraph(t_, style="List Bullet")
a.out.parent.mkdir(parents=True, exist_ok=True); d.save(a.out); print("saved", a.out)
