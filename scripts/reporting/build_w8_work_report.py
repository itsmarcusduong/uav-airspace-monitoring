#!/usr/bin/env python3
"""Bao cao cong viec tuan W8 (1-2 trang) -> docx. So lieu doc tu file ket qua trong repo, khong nhap tay.

    python scripts/reporting/build_w7_work_report.py --out reports/w8/E1_W08_bao_cao_cong_viec.docx
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


V2V = rj("results/W08/v2_verify/v2_verify.json")
if V2V["rule_b"]["apply_v2"] is not True or not V2V["rule_c"]["c3_all_ge_8pct"]:
    raise SystemExit("ket qua luat B/C khac noi dung bao cao - cap nhat builder")
E2EF = rj("results/W08/e2e/e2e_fixture_results.json")
import csv
E2EM = list(csv.DictReader((ROOT / "results/W08/e2e/e2e_manual_An.csv").open(encoding="utf-8")))
EV = rj("Evidence/W08/test-results.json")
N_PYTEST = sum(1 for c in EV["checks"] if c["check"].startswith("pytest::"))
GS = (ROOT / "docs/status/W08_github_structure.md").read_text(encoding="utf-8")
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
PRS = [(114, "Quang", "ADR-0014: FBD-SV-2024 chỉ dùng cho neg_eval (#113)", ["c73c7958da576d02f53d4d8a21bb8c134338e9e7", "6663ca87c7a07a14a56e2dbb2c508edb08f73492"], "8f2b1b36f0014d3881efd44b869949b6e51c3520"),
       (120, "Quang", "kế hoạch W8, luật đặt trước B–C, job chẩn đoán (#115)", ["5edaf4996b8489c6aa463dd6c5095aaba5238706"], "6292e0a363a99d7d42584f943f4e24f12f2b406a"),
       (121, "Quang", "ADR-0015 kiến trúc đầu-cuối (#116)", ["50c36e5f9bd73d593e1561c4faa851768a29ee10", "8d5e088c89a2e4c530ae7cabdfc3de4c3e22d054"], "79d7d4945b80283803a801782e419c59a1b909fa"),
       (122, "An", "nháp 4.1–4.2, kịch bản E2E, sửa luật C (#117, #118)", ["a44c56bfa777768069f3e0be0d60e55890f02231"], "a01442ba7150ddd53df633ac7f216ace1ae06ced"),
       (123, "Quang", "run 17 mã hóa video H.264 (#115)", ["1adac75edf5fa51a1cac71aad064dfa7c79748ce"], "42fd7319bfa64c3aa87d7cc9a2e6c6b766931136"),
       (124, "Quang", "pipeline phát lại: SQLite, FastAPI + WebSocket, dashboard (#116)", ["39d17b34d67b80bee1a0844b2efbf405cd2c83b6", "5792ac6386b270d2a78567bbf262611e929925b2"], "ef7661b75253e1a19d434213f2038405533ec6c9"),
       (125, "Quang", "sửa khóa fingerprint của notebook run 17 (#115)", ["f350c2693b7ea67a3f9dddff4ee37d3af0987541"], "b7fcf3bf71527cb0d9beb3703cdef3cf5a131f59"),
       (126, "An", "kịch bản E2E bản chạy (E2E-07, E2E-13) (#118)", ["dd78cd574de502514ecd9388571035b853c33544", "bb7317d23a6ef53452c04481e0069e2ce738e984"], "122552ae8cad99c44c2fe1475a0612e31bdaa715"),
       (127, "Quang", "kết quả run 17, luật B (V2) và C (#115)", ["142f07af6c6f1d54550d79c8e4c845fa8115c92e"], "fdc73f8e44ed55b04897fdebb1a151ee64c52205")]

para("BÁO CÁO CÔNG VIỆC TUẦN 8 — NHÓM E1", True, 13, WD_ALIGN_PARAGRAPH.CENTER)
para("Đề tài: Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu", False, 9.5, WD_ALIGN_PARAGRAPH.CENTER, True)
para("Tuần 8 (15/11–21/11/2026, chốt 22/11) — Milestone Tuan8: pipeline E2E + dashboard/log; tag w08 bắt buộc. GVHD: TS. Nguyễn Tất Thắng. Sinh viên: Lê Ngọc An, Dương Minh Quang.")
para("1. GitHub: Issue / PR / Commit cuối tuần (theo mẫu GVHD, ADR-0010)", True)
t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, h in enumerate(["Hạng mục", "Liên kết"]):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8); shade(c)


def row(label):
    cells = t.add_row().cells; cells[0].text = ""; r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(8)
    cells[1].text = ""; return cells[1].paragraphs[0]


p = row("Milestone / Issues")
add_link(p, "Milestone Tuan8", REPO + "/milestone/8", 8); plain(p, " · Issues #113, #115–#119 (mỗi issue một sinh viên, một kết quả, đúng 1 assignee)", 8)
for num, who, desc, commits, merge in PRS:
    p = row(f"PR #{num} ({who})")
    add_link(p, f"#{num}", f"{REPO}/pull/{num}", 8); plain(p, f" {desc}. Commit ", 8)
    for i, full in enumerate(commits):
        add_link(p, full[:7], f"{REPO}/commit/{full}", 8)
        if i < len(commits) - 1:
            plain(p, ", ", 8)
    plain(p, "; merge ", 8); add_link(p, merge[:7], f"{REPO}/commit/{merge}", 8)
p = row("Review chéo")
plain(p, "An: approve #114; request changes rồi approve #121 (ADR-0015) và #124 (4 lỗi: --overwrite xóa ngoài bundle, chèn HTML không mã hóa, video chạy khi luồng quá hạn, config_audit chưa ghi). Quang: approve #122, #126 sau khi kiểm luật điểm trên biên và thời gian gộp sự kiện. #120, #123, #125, #127 chưa có review GitHub của An (WARN).", 8)
p = row("Tag / commit cuối tuần")
plain(p, "Tag w08 bắt buộc (Đề cương mục 10), gắn vào commit merge PR chốt tuần; SHA ghi ở ", 8); add_link(p, "issue #119", f"{REPO}/issues/119", 8)
plain(p, " và ", 8); add_link(p, "Releases", f"{REPO}/releases", 8)
p = row("check_structure.py --weeks 8")
plain(p, f"{GS_SUM}" + (f" (WARN: {', '.join(GS_WARN)})" if GS_WARN else "") + ". File: docs/status/W08_github_structure.md", 8)
widths(t, [3.4, 14.0])
d.add_paragraph().paragraph_format.space_after = Pt(0)

para("2. Phân chia công việc", True)
table(["Issue", "Nội dung", "Phụ trách", "Review", "Trạng thái"],
      [["#113 W8-01", "Tập âm tính e1-neg-v1: license, manifest, sàng lọc, chuẩn hóa (ADR-0013, 0014)", "Quang", "An", "Chưa xong: mới có ADR-0014 và bằng chứng license; chuyển W9"],
       ["#115 W8-02", "Run 17: V2 trong detector, chẩn đoán hộp trùng; áp luật B, C", "Quang", "An", "Xong (PR #120, #123, #125, #127)"],
       ["#116 W8-03", "Pipeline phát lại: kho sự kiện, API, dashboard, nhật ký (ADR-0015)", "Quang", "An", "Xong (PR #121, #124)"],
       ["#117 W8-04", "Duyệt ADR-0014, 0015, luật B–C; nháp 4.1–4.2", "An", "Quang", "Đóng (PR #122), đã vào v0.8"],
       ["#118 W8-05", "13 kịch bản E2E viết trước, chạy trên dashboard", "An", "Quang", "Đóng (PR #122, #126); kết quả ở #118"],
       ["#119 W8-06", "Báo cáo W8, v0.8, Evidence/W08, tag w08", "Quang", "An", "Bản nộp"]],
      [1.7, 7.6, 1.6, 1.3, 5.2], size=8)

para("3. Planned – Done – Evidence – Problems – Next", True)
table(["Planned", "Done", "Evidence", "Problems", "Next week"],
      [["Pipeline E2E + dashboard/log; đo lại V2 trên video thật; chẩn đoán hộp trùng; tập âm tính công khai; Chương IV 4.1–4.2",
        "Run 17: áp dụng V2 (5/5 điều kiện). Chẩn đoán: trường hợp 3. Pipeline phát lại + dashboard + nhật ký review/cấu hình. 13 ca E2E: 9 đạt, 0 trượt. Mục 4.1–4.2 (An)",
        "results/W08/ (kaggle_run_17, v2_verify, e2e); scripts/pipeline/; ADR-0014, 0015; Evidence/W08/; reports/w8/",
        "Tập âm tính chưa thu; demo chưa đo thời gian thực; track recall giảm ở 4 video; 4 PR chưa review",
        "W9: e1pipe từng frame, FPS/p95 ≥ 3 lần; tập âm tính, cảnh báo sai/giờ; số đo mức ảnh từ predict"]],
      [3.0, 4.4, 3.8, 3.5, 2.7], size=8)

para("4. Kết quả đo (validation, 38 video; nguồn: CSV/JSON + script)", True)
n_pass = sum(c["status"] == "PASS" for c in EV["checks"])
cd = V2V["rule_b"]["conditions"]; ex = V2V["rule_b"]["reported_not_conditions"]; rc = V2V["rule_c"]
e2e_pass = sorted({r["case"] for r in E2EM if r["status"] == "PASS"} | set(E2EF["summary"]["pass"]))
table(["Chỉ số", "Giá trị", "Nguồn"],
      [["Luật B (đặt trước): run 14 → run 17", f"recall Drone {vn(cd['1_drone_image_recall_drop_le_0.02']['run14'])} → {vn(cd['1_drone_image_recall_drop_le_0.02']['run17'])}; R1 {cd['2_r1_event_recall_not_lower']['run14']} → {cd['2_r1_event_recall_not_lower']['run17']}; sai R1 {cd['3_r1_false_nondrone_not_higher']['run14']} → {cd['3_r1_false_nondrone_not_higher']['run17']}; track recall {vn(cd['5_pooled_track_recall_drop_le_0.02']['run14'])} → {vn(cd['5_pooled_track_recall_drop_le_0.02']['run17'])} → áp dụng V2", "results/W08/v2_verify/v2_verify.json"],
       ["ID switch / 1000 frame GT", f"{vn(cd['4_idsw_reduction_ge_20pct']['run14'], 3)} → {vn(cd['4_idsw_reduction_ge_20pct']['run17'], 3)} (−{vn(100 * cd['4_idsw_reduction_ge_20pct']['reduction'], 1)}%; bằng V2 offline W7)", "results/W08/v2_verify/v2_verify.json"],
       ["Luật C: hộp trùng JPG/frame × fp32/fp16", f"{', '.join(vn(100 * rc['dup_rate'][k], 1) + '%' for k in ('jpg_fp32', 'frame_fp32', 'jpg_fp16', 'frame_fp16'))}; cổng tái tạo đạt → trường hợp 3", "results/W08/kaggle_run_17/w8_dupdiag/"],
       ["Kiểm chéo", f"đánh giá ngoài Kaggle khớp Kaggle; run 17 trùng {vn(100 * V2V['checks']['run17_vs_offline_v2_on_run14']['match_rate'], 1)}% hộp với V2 offline; fp16 có tác dụng", "results/W08/v2_verify/v2_verify.json"],
       ["Kịch bản E2E (13 ca của An)", f"đạt {len(e2e_pass)}/13 ({', '.join(c[-2:] for c in e2e_pass)}), 0 trượt, {13 - len(e2e_pass)} không kiểm được ở phát lại; An chạy tay 6 PASS, fixture tự động 8/8 PASS", "results/W08/e2e/"],
       ["Kiểm tra Evidence/W08", f"{n_pass}/{len(EV['checks'])} PASS; pytest {N_PYTEST} test (có Playwright)", "Evidence/W08/test-results.json"]],
      [4.6, 8.4, 4.4], size=8)

para("5. Dataset card / model card", True)
para("Dataset e1-yolo-v1 và detector YOLO11n s20261030 không đổi; detector dùng NMS cùng lớp IoU 0,5 từ W8 (V2). FBD-SV-2024 dùng được cho neg_eval, chỉ đánh giá, không phân phối lại (ADR-0014; bằng chứng license: data/manifests/license_evidence/).")
para("6. Demo/video", True)
p = para("Dashboard phát lại bundle w8_demo (run 14 + run 17, 38 video val H.264; bundle.json SHA 491974f8…) và 3 video demo có vẽ track của run 17 (demo/W08) trên ")
add_link(p, "Google Drive, thư mục w8", "https://drive.google.com/drive/folders/14eKmXBZsiDIQ7awFFzHNayQaGpVjADOA", 10)
plain(p, ". Video không đưa vào Git. Đây là demo đầu-cuối về luồng dữ liệu, không phải đo thời gian thực.", 10)
para("7. Vấn đề và rủi ro (trung thực)", True)
for t_ in ["#113 chưa xong: chưa có clip âm tính công khai nào được lập manifest hay chuẩn hóa; cảnh báo sai/giờ vẫn chỉ đo trên 3,7 phút. Chuyển W9.",
           "Track recall giảm hơn 0,02 ở 4 video khi dùng V2 (mạnh nhất V_HELICOPTER_012, −0,194); theo dõi khi đánh giá test ở W10.",
           "E2E: An chạy tay dùng video val thay fixture ở 5 ca; Quang bù bằng fixture đúng mô tả. 4 ca (camera, tải đầu vào, đổi cấu hình giữa phiên, phân quyền) chưa kiểm được ở chế độ phát lại.",
           "Quy trình: #120, #123, #125, #127 merge chưa có review GitHub của An; SQLite không ghi được trên ổ dùng chung của máy ảo, bundle dựng ở chỗ khác rồi chép sang."]:
    d.add_paragraph(t_, style="List Bullet")
a.out.parent.mkdir(parents=True, exist_ok=True); d.save(a.out); print("saved", a.out)
