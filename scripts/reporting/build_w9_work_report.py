#!/usr/bin/env python3
"""Bao cao cong viec tuan W9 (1-2 trang) -> docx. So lieu doc tu file ket qua trong repo, khong nhap tay.

    python scripts/reporting/build_w9_work_report.py --out reports/w9/E1_W09_bao_cao_cong_viec.docx [--draft]
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
ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--draft", action="store_true"); a = ap.parse_args()


def rj(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


import csv
BS = rj("results/W09/benchmark/benchmark_summary.json")
NEG = rj("results/W09/kaggle_run_19/w9_neg_fbdsv/neg_summary.json")
ST20 = rj("results/W09/kaggle_run_20/w9_C0_rep1_stab/summary.json")
RGC = rj("results/W09/benchmark/rss_growth_check.json")
PC19 = list(csv.DictReader((ROOT / "results/W09/kaggle_run_19/w9_neg_fbdsv/per_clip.csv").open(encoding="utf-8")))
CAND = list(csv.DictReader((ROOT / "data/manifests/neg_commons_candidates.csv").open(encoding="utf-8")))
if not BS["gate_b"]["pass"] or not BS["stability"] or not BS["stability"]["pass"]:
    raise SystemExit("ket qua W9 khac noi dung bao cao - cap nhat builder")
CHOICE = BS["rule_c"]["choice"]; TM = BS["timing"]; C2R = BS["rule_c"]["candidates"].get("C2", {})
C2OK = C2R.get("available", False)
if not C2OK and C2R.get("reason") == "khong co ket qua" and not a.draft:
    raise SystemExit("chua co ket qua run 18b (C2); dung --draft")
EV = rj("Evidence/W09/test-results.json")
N_PYTEST = sum(1 for c in EV["checks"] if c["check"].startswith("pytest::"))
GS = (ROOT / "docs/status/W09_github_structure.md").read_text(encoding="utf-8")
GS_SUM = next(l for l in GS.splitlines() if l.startswith("FAIL:")).split(". Tạo")[0]
GS_WARN = [l.split("|")[2].strip() for l in GS.splitlines() if "| WARN |" in l]


def th(n):
    return f"{int(n):,}".replace(",", ".")


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
PRS = [(135, "Quang", "kế hoạch W9, luật đặt trước B–E, ADR-0016 (#130)", ["68399e0f434f2cf843cb5d61c9ca13a29e1db2c8", "52fe7cfc24537e56f513abf6800814b0308f9e32", "3f3d58f8e97416e1a1bdc114662dbdce316c6533", "ff2dc32c4dc9f5612604dbd440f14bbfa8ebcb76"], "497b37a855335fc4233b648d51ff6596fd2aba19"),
       (136, "Quang", "e1pipe từng frame, R1 trực tuyến, job benchmark và FBD-SV, bộ áp luật B/C (#129)", ["04d0c6111636342ff9c4ee5ca3798ecba6c01b64"], "f36add123862b3532a51f523a37b057de3b269ff"),
       (137, "Quang", "sửa theo review #136: close cuối video, phạm vi đo total (#129)", ["438ddab629deb20162fd277ff66e6a0a33e68073"], "7833289a92cf97077179ce62a60f7e51d52eaa6d"),
       (138, "Quang", "manifest ứng viên Commons từ API gốc, luật sàng lọc và chia split viết trước (#131)", ["3c2f30c93f0bc27943975833aec82c47f490fb3d", "017c173a8f3b40503b243a4bf879f589a7ff070f", "5dd4e7871ad0ce05c56fd775fc12e64439427da6"], "ad4cfddf85b489e85cb2dc5edc1c3a5e0021fffe"),
       (140, "An", "nháp Chương IV mục 4.3–4.4 (#133)", ["e9ee17ca2a9cb2911d18e299fcef450a801882a4", "f04a5d5a86646feabcb3bc7802d7dcf2731968e0"], "785d8b76dfd375138bf8551c019994d34eb4b9b1"),
       (141, "Quang", "log tiến độ run 19; C2 xuất TensorRT từ bản sao weights (#131, #130)", ["9f0271681b1f5d30520b7535eb626e6d29768f1f"], "3ea87d9c80dcfcdef64f0907e71b69b27d901980"),
       (148, "Quang", "kết quả run 18, áp luật B/C (#130, #129)", ["ecc0e6cb138e1d472759777aeedef4c98af04c3f"], "811f4d9d3a4a5a8092bfcbd2d53536fb37d6f529"),
       (150, "Quang", "poisson_upper tính trong log (tràn số ở run 19) (#131)", ["01c502540b159a329f4bdfd6be975aa9dce6b607"], "98bc37938b74dd207dab844df3849249cdb725dd"),
       (151, "Quang", "run 19 chép clip một lần, chuẩn hóa song song (#131)", ["004e128ed02a481cf50d585e73b57f7deb5f1471"], "f18a4d38b9dd01aaaf8e5aa3f54612398b8c71a8"),
       (153, "Quang", "author_key chỉ đọc tài khoản từ href (#131)", ["977dae2ea1f7423e65af1d3a215de847a1f229cf"], "cbb6f30357b523f34908aad9a708da20aa8b10d7"),
       (154, "Quang", "kết quả run 19b3 FBD-SV + danh sách ứng viên Commons (#131)", ["c57750f2c85912e94335c694b0a599fa8d564a8a"], "239ca975e31501450ccf838581775ba73b854c4a"),
       (155, "Quang", "run 18b: chỉ chạy lại C2 ×3 (#130)", ["8c3d2db4c9636e002ac07f16676f7b6400eb582a"], "834dc3feda6f9c16413ed430ba6a35a49f15ba69")]
SMALL = [(139, "README theo trạng thái W1–W9"), (142, ""), (143, ""), (144, ""), (145, ""), (146, ""), (147, ""), (149, ""), (152, "ADR-0014 dòng trạng thái Accepted")]

para("BÁO CÁO CÔNG VIỆC TUẦN 9 — NHÓM E1", True, 13, WD_ALIGN_PARAGRAPH.CENTER)
para("Đề tài: Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu", False, 9.5, WD_ALIGN_PARAGRAPH.CENTER, True)
para("Tuần 9 (22/11–28/11/2026, chốt 29/11) — Milestone Tuan9: tối ưu inference, FPS/latency; tuần không bắt buộc tag (ghi commit cuối tuần). GVHD: TS. Nguyễn Tất Thắng. Sinh viên: Lê Ngọc An, Dương Minh Quang.")
para("1. GitHub: Issue / PR / Commit cuối tuần (theo mẫu GVHD, ADR-0010)", True)
t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, h in enumerate(["Hạng mục", "Liên kết"]):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8); shade(c)


def row(label):
    cells = t.add_row().cells; cells[0].text = ""; r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(8)
    cells[1].text = ""; return cells[1].paragraphs[0]


p = row("Milestone / Issues")
add_link(p, "Milestone Tuan9", REPO + "/milestone/9", 8); plain(p, " · Issues #129–#134 (mỗi issue một sinh viên, một kết quả, đúng 1 assignee)", 8)
for num, who, desc, commits, merge in PRS:
    p = row(f"PR #{num} ({who})")
    add_link(p, f"#{num}", f"{REPO}/pull/{num}", 8); plain(p, f" {desc}. Commit ", 8)
    for i, full in enumerate(commits):
        add_link(p, full[:7], f"{REPO}/commit/{full}", 8)
        if i < len(commits) - 1:
            plain(p, ", ", 8)
    plain(p, "; merge ", 8); add_link(p, merge[:7], f"{REPO}/commit/{merge}", 8)
p = row("PR nhỏ (Quang)")
for i, (num, desc) in enumerate(SMALL):
    add_link(p, f"#{num}", f"{REPO}/pull/{num}", 8)
    plain(p, (f" ({desc})" if desc else "") + (", " if i < len(SMALL) - 1 else ""), 8)
plain(p, ": sửa script chạy job Kaggle và tài liệu.", 8)
p = row("Review chéo")
plain(p, "An: approve #135 (luật W9, ADR-0016) trước khi chạy; review #136 tìm 2 lỗi đo (sửa ở #137); request changes 2 lần rồi approve #138 (luật sàng lọc); approve #137, #139, #141, #148, #152. Quang: request changes 2 lần rồi approve #140 (sửa các nhận định sai về EOS, độ trễ, secret). " + (f"{', '.join(GS_WARN)}: An review sau merge bằng comment trên PR ngày 28/11, chưa phải review chính thức nên check_structure còn WARN." if GS_WARN else ""), 8)
p = row("Commit cuối tuần")
plain(p, "W9 không bắt buộc tag (Đề cương mục 10); commit cuối tuần là commit merge PR chốt tuần, SHA ghi ở ", 8); add_link(p, "issue #134", f"{REPO}/issues/134", 8)
p = row("check_structure.py --weeks 9")
plain(p, f"{GS_SUM}. File: docs/status/W09_github_structure.md", 8)
widths(t, [3.4, 14.0])
d.add_paragraph().paragraph_format.space_after = Pt(0)

para("2. Phân chia công việc", True)
table(["Issue", "Nội dung", "Phụ trách", "Review", "Trạng thái"],
      [["#129 W9-01", "e1pipe chạy từng frame có độ trễ từng bước, qua cổng tái tạo so với run 17", "Quang", "An", "Xong (PR #136, #137, #148)"],
       ["#130 W9-02", "Benchmark C0/C1/C2/CPU ≥ 3 lần, chạy ổn định 60 phút, chọn cấu hình theo luật C", "Quang", "An", "Xong (PR #135, #141, #148, #155; run 18, 18b, 20)" if C2OK else "Xong C0/C1/CPU và chạy ổn định; C2 chạy lại ở run 18b, chưa có kết quả"],
       ["#131 W9-03", "Tập âm tính: chuẩn hóa FBD-SV-2024, manifest nguồn công khai, cảnh báo sai/giờ", "Quang", "An", f"FBD-SV xong (run 19b3); Commons: {len(CAND)} ứng viên, chờ sàng lọc; tổng âm tính < 2 giờ"],
       ["#132 W9-04", "Duyệt luật W9 và ADR-0016 trước khi chạy; sàng lọc độc lập clip âm tính", "An", "Quang", "Duyệt xong (#135, #138); sàng lọc: Quang xong, An đang làm → W10"],
       ["#133 W9-05", "Chương IV: cập nhật 4.3, viết 4.4", "An", "Quang", "Đóng (PR #140), đã vào v0.9"],
       ["#134 W9-06", "Báo cáo W9, v0.9, Evidence/W09, commit cuối tuần", "Quang", "An", "Bản nộp"]],
      [1.7, 7.0, 1.5, 1.3, 5.9], size=8)

para("3. Planned – Done – Evidence – Problems – Next", True)
table(["Planned", "Done", "Evidence", "Problems", "Next week"],
      [["e1pipe từng frame; FPS/p95 ≥ 3 lần (NFR1); chọn cấu hình suy luận; chạy 60 phút; tập âm tính và cảnh báo sai/giờ; Chương IV 4.3–4.4",
        f"Cổng B đạt. C0 {vn(TM['C0']['fps_median'], 1)} FPS, p95 {vn(TM['C0']['p95_total_median'], 1)} ms → chọn {CHOICE}. 60 phút đạt. FBD-SV: R1 {vn(NEG['R1']['per_hour'], 1)} cảnh báo sai/giờ → kích hoạt ADR-0011. Mục 4.3–4.4 (An)",
        "results/W09/ (benchmark, kaggle_run_18, 19, 20); scripts/pipeline/e1pipe.py; docs/w9/; Evidence/W09/; reports/w9/",
        "Cảnh báo sai trên chim nhỏ rất cao; âm tính mới 19 phút; sàng lọc Commons chưa xong; 5 PR chưa review",
        "W10: hard negative (ADR-0011); sàng lọc + đo Commons; đánh giá detection+tracking trên test"]],
      [3.1, 4.6, 3.6, 3.4, 2.7], size=8)

para("4. Kết quả đo (val 38 video và FBD-SV-2024; nguồn: CSV/JSON + script)", True)
n_pass = sum(c["status"] == "PASS" for c in EV["checks"])
g = BS["gate_b"]; st_ = BS["stability"]
c2 = f"C2 {vn(TM['C2']['fps_median'], 1)} FPS, p95 {vn(TM['C2']['p95_total_median'], 1)} ms" if C2OK else ("C2: chưa có kết quả (run 18b)" if C2R.get("reason") == "khong co ket qua" else f"C2 không khả thi ({C2R.get('reason')})")
table(["Chỉ số", "Giá trị", "Nguồn"],
      [["Cổng tái tạo e1pipe (luật B)", f"{g['matched']}/{g['track_rows_run17']} dòng track, sự kiện R1 {g['events_e1pipe']}/{g['events_run17']} khớp run 17 → đạt", "results/W09/benchmark/benchmark_summary.json"],
       ["FPS / p95 total (trung vị 3 lần, T4)", f"C0 {vn(TM['C0']['fps_median'], 1)} FPS, {vn(TM['C0']['p95_total_median'], 1)} ms; C1 {vn(TM['C1']['fps_median'], 1)} FPS, {vn(TM['C1']['p95_total_median'], 1)} ms; {c2}; CPU {vn(TM['CPU']['fps_median'], 1)} FPS (5 video)", "results/W09/benchmark/benchmark.csv"],
       ["Luật C (viết trước)", f"chọn {CHOICE}; NFR1 đạt trên GPU, không đạt trên CPU", "results/W09/benchmark/benchmark_summary.json"],
       ["Chạy 60 phút, C0 (run 20)", f"{th(ST20['frames'])} frame, {vn(ST20['fps_excl_warmup'], 1)} FPS; RSS phút 60/phút 10 = {vn(st_['rss_ratio'], 3)} ≤ 1,10 → đạt; khoảng {vn(100 * RGC['share_explained'], 0)}% mức tăng RSS do bộ đo giữ latency trong RAM (thăm dò)", "results/W09/kaggle_run_20/, benchmark/rss_growth_check.json"],
       ["FBD-SV-2024 (run 19b3)", f"{NEG['clips']} clip, {vn(NEG['minutes'], 2)} phút: R0 {NEG['R0']['false_alerts']} ({vn(NEG['R0']['per_hour'], 1)}/giờ), R1 {NEG['R1']['false_alerts']} ({vn(NEG['R1']['per_hour'], 1)}/giờ, cận trên {vn(NEG['R1']['per_hour_upper95'], 1)}); {vn(100 * NEG['frac_frames_drone_det'], 1)}% frame có detection Drone → ADR-0011 kích hoạt", "results/W09/kaggle_run_19/w9_neg_fbdsv/"],
       ["Kiểm tra Evidence/W09", f"{n_pass}/{len(EV['checks'])} PASS; pytest {N_PYTEST} test", "Evidence/W09/test-results.json"]],
      [4.2, 9.0, 4.2], size=8)

para("5. Dataset card / model card", True)
para(f"Dataset e1-yolo-v1 và detector YOLO11n s20261030 (NMS cùng lớp IoU 0,5) không đổi. Cấu hình suy luận vận hành: {CHOICE}. FBD-SV-2024 chỉ dùng làm neg_eval, chỉ có số tổng hợp và ID clip trong repo (ADR-0014). Ứng viên Wikimedia Commons: data/manifests/neg_commons_candidates.csv ({len(CAND)} clip, chưa sàng lọc).")
para("6. Demo/video", True)
para("Tuần 9 không thêm video demo mới; demo dashboard phát lại của tuần 8 vẫn dùng được. Kết quả tuần này là số đo tốc độ và cảnh báo sai, xem mục 4 và v0.9 mục 5.3.9, 5.4.8.")
para("7. Vấn đề và rủi ro (trung thực)", True)
risks = [f"Detector nhận gần như mọi chim nhỏ trong FBD-SV là Drone ({sum(int(r['tracks_majority_drone']) for r in PC19)}/{sum(int(r['tracks']) for r in PC19)} track, thăm dò): R1 vẫn {vn(NEG['R1']['per_hour'], 1)} cảnh báo sai/giờ. Cần dữ liệu hard negative (W10, ADR-0011).",
         "Tổng âm tính mới 19 phút (mục tiêu NFR3: 2 giờ); clip FBD-SV ngắn (trung vị 2 giây) nên tần suất có thể khác video giám sát liên tục. Commons chờ An sàng lọc xong; Pixabay chưa làm.",
         "Run 19 lần đầu lỗi tràn số ở bước tổng hợp sau khoảng 4 giờ chạy, lần 2 chuẩn hóa quá chậm và bị hủy; đã sửa (#150, #151), lần 3 (19b3) chạy xong.",
         "Số đo tốc độ chỉ trên Tesla T4 và video đọc từ tệp; chưa đo trên test (W10–W11)."]
if not C2OK:
    risks.insert(0, "C2 (TensorRT): lần chạy đầu lỗi do bộ đo ghi vào thư mục chỉ đọc; run 18b chạy lại ×3 " + ("đang chờ kết quả." if C2R.get("reason") == "khong co ket qua" else "vẫn không có kết quả hợp lệ."))
if GS_WARN:
    risks.append(f"Quy trình: {', '.join(GS_WARN)} merge khi An chưa review; An đã review sau merge bằng comment, cần thêm review chính thức trên GitHub.")
for t_ in risks:
    d.add_paragraph(t_, style="List Bullet")
a.out.parent.mkdir(parents=True, exist_ok=True); d.save(a.out); print("saved", a.out)
