#!/usr/bin/env python3
"""Bao cao cong viec tuan W7 (1-2 trang) -> docx. So lieu doc tu file ket qua trong repo, khong nhap tay.

    python scripts/reporting/build_w7_work_report.py --out reports/w7/E1_W07_bao_cao_cong_viec.docx
"""
import argparse
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


P = "results/W07/postproc"
PPS = rj(f"{P}/postproc_summary.json")
if PPS["decision"]["choice"] != "nms_iou":
    raise SystemExit("quyet dinh ADR-0012 khac noi dung bao cao - cap nhat builder")
VS = {t: rj(f"{P}/{d}/summary.json") for t, d in (("V0", "V0_none"), ("V1", "V1_agnostic_nms"), ("V2", "V2_nms_iou"))}
EXP = rj(f"{P}/exploratory.json")
REPRO = rj(f"{P}/repro_check.json")
CA = rj("results/W07/confusion_analysis.json")
EV = rj("Evidence/W07/test-results.json")
N_PYTEST = sum(1 for c in EV["checks"] if c["check"].startswith("pytest::"))
GS = (ROOT / "docs/status/W07_github_structure.md").read_text(encoding="utf-8")
GS_SUM = next(l for l in GS.splitlines() if l.startswith("FAIL:")).split(". Tạo")[0]
GS_WARN = [l.split("|")[2].strip() for l in GS.splitlines() if "| WARN |" in l]


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
PRS = [(102, "Quang", "tracker offline, cổng tái tạo run 14, ADR-0012 (#97)", ["3d57c45735f0065b495567ae599cc188f989587f"], "53bb81e8ee26435404eee6ef6abab4821ce3afa8"),
       (103, "Quang", "nguồn video công khai, ADR-0013 (#99)", ["9516010910e071352def0ddacbf6361020353cb9"], "51088db3b6a7288f4caddaa1b2b6d4bdd898b031"),
       (104, "Quang", "kết quả kiểm license Pixabay (#99)", ["5c72fc31e1b3e6a7f208cea7ced855fdf3beb1ab"], "f6386861b0216b875c0eb4b80bc890d9411f52fc"),
       (105, "An", "duyệt ADR-0012 → Accepted (#98)", ["64d82a0036ad29401a085e1e768ebfd68961d75c"], "7237dd6424062f06f0d3fa4db8399ba9f19b1a97"),
       (106, "An", "tạm loại FBD-SV-2024 chờ rà license (#99)", ["f88a5467ac3cf21b809d90743f1efa9efa630b78"], "23bdd412da689cac3dcbe9929f36bcdcbc62e0ac"),
       (107, "An", "Chương III bản 1, mục 3.3–3.4 (#100)", ["912bd179d7a862cfeeb726b479ee210daec5fba1"], "a61fd776e1081f4cfd38477111afcce44b9e96be"),
       (108, "An", "phân tích nhầm lẫn trên val (#98)", ["2563b8f768b85b2dd5e2446682aeccfefd9437fb", "cfda7e920ef2531f12433a537adf44bac48ed49a"], "65ecfe7a46938fed87e49ecae76d26878dea60a3"),
       (109, "Quang", "thí nghiệm V0/V1/V2, chọn V2 (#97)", ["50188121fcdaaa3eb35f9ff95211f80586efb4e0"], "7060d67c4322dcd1c99bc401b832410b3e29dfec")]

para("BÁO CÁO CÔNG VIỆC TUẦN 7 — NHÓM E1", True, 13, WD_ALIGN_PARAGRAPH.CENTER)
para("Đề tài: Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu", False, 9.5, WD_ALIGN_PARAGRAPH.CENTER, True)
para("Tuần 7 (08/11–14/11/2026, hoàn thành 17/11) — Milestone Tuan7: hard negatives + confusion analysis. GVHD: TS. Nguyễn Tất Thắng. Sinh viên: Lê Ngọc An, Dương Minh Quang.")
para("1. GitHub: Issue / PR / Commit cuối tuần (theo mẫu GVHD, ADR-0010)", True)
t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, h in enumerate(["Hạng mục", "Liên kết"]):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8); shade(c)


def row(label):
    cells = t.add_row().cells; cells[0].text = ""; r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(8)
    cells[1].text = ""; return cells[1].paragraphs[0]


p = row("Milestone / Issues")
add_link(p, "Milestone Tuan7", REPO + "/milestone/7", 8); plain(p, " · Issues #97–#101 (mỗi issue một sinh viên, một kết quả, đúng 1 assignee)", 8)
for num, who, desc, commits, merge in PRS:
    p = row(f"PR #{num} ({who})")
    add_link(p, f"#{num}", f"{REPO}/pull/{num}", 8); plain(p, f" {desc}. Commit ", 8)
    for i, full in enumerate(commits):
        add_link(p, full[:7], f"{REPO}/commit/{full}", 8)
        if i < len(commits) - 1:
            plain(p, ", ", 8)
    plain(p, "; merge ", 8); add_link(p, merge[:7], f"{REPO}/commit/{merge}", 8)
p = row("Review chéo")
plain(p, "Quang approve #105–#108 của An sau khi chạy lại script và test (góp ý ghi trong từng review). An duyệt nội dung #102 qua #105 (ADR-0012) và #103 qua #106 (FBD-SV), nhưng chưa có review GitHub trên #102, #103, #104, #109; ADR-0013 chờ An duyệt.", 8)
p = row("Commit cuối tuần")
plain(p, "W7 không bắt buộc tag (Đề cương mục 10: W4, W8, W11, W14). Commit nội dung cuối trước báo cáo: ", 8)
add_link(p, "7060d67", f"{REPO}/commit/7060d67c4322dcd1c99bc401b832410b3e29dfec", 8)
plain(p, " (merge #109); commit cuối tuần = merge PR báo cáo, ghi ở ", 8); add_link(p, "issue #101", f"{REPO}/issues/101", 8)
p = row("check_structure.py --weeks 7")
plain(p, f"{GS_SUM} (WARN: {', '.join(GS_WARN)} chưa có review GitHub của An). File: docs/status/W07_github_structure.md", 8)
widths(t, [3.4, 14.0])
d.add_paragraph().paragraph_format.space_after = Pt(0)

para("2. Phân chia công việc", True)
table(["Issue", "Nội dung", "Phụ trách", "Review", "Trạng thái"],
      [["#97 W7-01", "Tracker offline, cổng tái tạo; thí nghiệm hậu xử lý V0/V1/V2 theo ADR-0012", "Quang", "An", "Xong (PR #102, #109)"],
       ["#98 W7-02", "Duyệt ADR-0012 trước khi chạy V1/V2; phân tích nhầm lẫn, hard negative trên val", "An", "Quang", "Đóng (PR #105, #108)"],
       ["#99 W7-03", "Nguồn video công khai có giấy phép thay video tự quay (ADR-0013)", "Quang", "An", "Chờ An duyệt ADR-0013 (PR #103, #104, #106)"],
       ["#100 W7-04", "Chương III bản 1: mục 3.3–3.4", "An", "Quang", "Đóng (PR #107), đã vào v0.7"],
       ["#101 W7-05", "Mục 3.1, báo cáo W7, v0.7, Evidence/W07", "Quang", "An", "Bản nộp"]],
      [1.7, 8.0, 1.8, 1.3, 4.6], size=8)

para("3. Planned – Done – Evidence – Problems – Next", True)
table(["Planned", "Done", "Evidence", "Problems", "Next week"],
      [["Hard negative + phân tích nhầm lẫn; tập âm tính tự quay; giao thức NMS; Chương III bản 1",
        "Tự quay không khả thi → ADR-0013 (nguồn công khai, thu ở W8). Thí nghiệm NMS theo luật đặt trước: chọn V2. Phân tích nhầm lẫn (An). Mục 3.1, 3.3, 3.4",
        "results/W07/ (postproc, confusion_analysis.json); docs/w7/; ADR-0012, ADR-0013; Evidence/W07/",
        "Kết quả V2 mới đo offline; chưa có video âm tính ngoài; hộp trùng ở video gấp ~20 lần ảnh val",
        "W8: đo lại V2 trên Kaggle; thu video âm tính công khai; pipeline đầu-cuối, API, dashboard; tag w08"]],
      [3.0, 4.3, 3.8, 3.6, 2.7], size=8)

para("4. Kết quả đo (validation, 38 video; nguồn: CSV/JSON + script)", True)
n_pass = sum(c["status"] == "PASS" for c in EV["checks"])
tk = {t: VS[t]["tracking"]["all"] for t in VS}
al = lambda t, r: VS[t]["alerts"][f"center_hex|center|{r}"]
cd = PPS["decision"]["candidates"]
e2 = EXP["variants"]["V2_nms_iou"]; du = EXP["duplicates_on_same_val_frames"]
nd = CA["nen_to_drone_categories"]
table(["Chỉ số", "Giá trị", "Nguồn"],
      [["Cổng tái tạo offline so với run 14", f"track log trùng {REPRO['track_logs']['videos_identical']}/{REPRO['track_logs']['videos']} video; cảnh báo và P/R mức ảnh giống hệt", f"{P}/repro_check.json"],
       ["ID switch / 1000 frame GT: V0 / V1 / V2", f"{vn(tk['V0']['idsw_per_1000_gt_frames'], 2)} / {vn(tk['V1']['idsw_per_1000_gt_frames'], 2)} / {vn(tk['V2']['idsw_per_1000_gt_frames'], 2)} (giảm {vn(100 * cd['agnostic_nms']['idsw_reduction'], 1)}% / {vn(100 * cd['nms_iou']['idsw_reduction'], 1)}%)", f"{P}/V*/summary.json"],
       ["Luật ADR-0012 (recall Drone, R1 sự kiện và cảnh báo sai không xấu đi; giảm ID switch ≥ 20%)", f"cả hai đạt; chênh {vn(100 * (cd['agnostic_nms']['idsw_reduction'] - cd['nms_iou']['idsw_reduction']), 1)} điểm < 5 → chọn V2 (NMS cùng lớp IoU 0,5)", f"{P}/postproc_summary.json"],
       ["R1: sự kiện / sai trên video không Drone; R0 sai: V0 / V2", f"{al('V0', 'R1')['detected']}/{al('V0', 'R1')['events']} / {al('V0', 'R1')['false_alerts_nondrone']} → {al('V2', 'R1')['detected']}/{al('V2', 'R1')['events']} / {al('V2', 'R1')['false_alerts_nondrone']}; R0 {al('V0', 'R0')['false_alerts_nondrone']} → {al('V2', 'R0')['false_alerts_nondrone']}", f"{P}/V*/summary.json"],
       ["Kiểm \"quá đẹp\" (V2)", f"ID switch giảm ở {e2['idsw_by_video']['better']}/38 video, tăng ở {e2['idsw_by_video']['worse']}; bỏ video nhiều nhất vẫn giảm {vn(100 * e2['idsw_without_top1']['reduction'], 1)}%; track recall {vn(tk['V0']['track_recall_pooled'])} → {vn(tk['V2']['track_recall_pooled'])}", f"{P}/exploratory.json"],
       ["Dự đoán Drone không khớp nhãn (V0, conf 0,25)", f"{CA['confusion']['nen->Drone']} = {nd['duplicate']['count']} trùng + {nd['mislocalized']['count']} lệch vị trí + 0 nền; Airplane→Drone {CA['non_drone_gt_predicted_as_drone']['Airplane']['count']}", "results/W07/confusion_analysis.json (An)"],
       ["Hộp trùng cùng lớp trên cùng frame val (thăm dò)", f"video {vn(100 * du['video_predict']['dup_rate'], 1)}% so với ảnh val {vn(100 * du['image_val']['dup_rate'], 1)}%", f"{P}/exploratory.json"],
       ["Kiểm tra Evidence/W07", f"{n_pass}/{len(EV['checks'])} PASS; pytest {N_PYTEST} test", "Evidence/W07/test-results.json"]],
      [6.2, 6.4, 4.8], size=8)

para("5. Dataset card / model card", True)
para("Dataset e1-yolo-v1 và detector YOLO11n s20261030 không đổi. Tập âm tính e1-neg-v1 theo ADR-0013: Wikimedia Commons, Pixabay (license đã kiểm, usable cho đánh giá nội bộ), Pexels dự phòng; FBD-SV-2024 tạm loại (PR #106); UAVDB cho OOD ở W11. Trạng thái license: data/manifests/license_matrix.csv.")
para("6. Demo/video", True)
para("Tuần 7 không dựng video demo mới: thí nghiệm chạy offline trên detection đã lưu, không giải mã video. Video demo W6 vẫn ở Drive demo/W06.")
para("7. Vấn đề và rủi ro (trung thực)", True)
for t_ in ["Không thực hiện được lịch quay video âm tính (không chắc quy định quay gần sân bay); tuần 7 trễ hạn và không có tập âm tính ngoài. Cảnh báo sai/giờ vẫn chỉ đo trên 3,7 phút; thu video công khai ở W8, đo ở W9.",
           "Kết quả V2 là offline (NMS 0,5 áp sau NMS 0,7 của detection đã lưu). ADR-0012 mục 5 yêu cầu đo lại trên video thật ở W8; nếu ngược chiều thì giữ V0. Track recall giảm ở 4 video (mạnh nhất V_HELICOPTER_012).",
           "Không biến thể NMS nào giảm cảnh báo sai R0: hộp Drone trên máy bay là nhầm lớp, không phải hộp trùng. 63/74 dự đoán Drone không khớp nhãn là lỗi định vị trên drone nhỏ.",
           "Quy trình: PR #102, #103 merge trước review (An duyệt hậu kiểm qua #105, #106); #104, #109 chờ An review; ADR-0013 chờ An duyệt. v0.6 ghi ba câu hỏi nghiên cứu khác Thuyết minh 6.2, v0.7 đã sửa. Mọi số đo trên val; test khóa tới W10."]:
    d.add_paragraph(t_, style="List Bullet")
a.out.parent.mkdir(parents=True, exist_ok=True); d.save(a.out); print("saved", a.out)
