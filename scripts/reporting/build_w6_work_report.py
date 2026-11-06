#!/usr/bin/env python3
"""Bao cao cong viec tuan W6 (1-2 trang) -> docx. So lieu doc tu file ket qua trong repo, khong nhap tay.

    python scripts/reporting/build_w5_work_report.py --out reports/w6/E1_W06_bao_cao_cong_viec.docx
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



AL = rj("results/W06/alert_eval/alert_summary.json")
R0, R1 = AL["summary"]["center_hex|center|R0"], AL["summary"]["center_hex|center|R1"]
TS = rj("results/W06/kaggle_run_14/w6_run14/track_summary.json")["summary"]["tracker_bytetrack_e1@0.5"]
SW = list(csv.DictReader((ROOT / "results/W06/detector_swap_tracking/summary.csv").open(encoding="utf-8")))
DUP = rj("results/W06/duplicate_boxes.json")["tracks"]["yolo11n"]
COV = rj("results/W06/dataset_coverage.json")["visible"]
VN = rj("results/W06/val_negative_frames/val_negative_summary.json")
MR = list(csv.DictReader((ROOT / "results/W06/val_negative_frames/manual_review_classification.csv").open(encoding="utf-8-sig")))
DEMO14 = rj("results/W06/kaggle_run_14/w6_run14/demo/demo_index.json")
DEMO15 = rj("results/W06/kaggle_run_15/w6_alert_demo/demo_index.json")
EV = rj("Evidence/W06/test-results.json")
N_PYTEST = sum(1 for c in EV["checks"] if c["check"].startswith("pytest::"))
GS = (ROOT / "docs/status/W06_github_structure.md").read_text(encoding="utf-8")
GS_SUM = next(l for l in GS.splitlines() if l.startswith("FAIL:")).split(". Tạo")[0]
GS_COMMIT = next(l for l in GS.splitlines() if "Commit cuoi tuan" in l).split("|")[4].strip().split(" (")[0]


def sw(det, cls="all"):
    return next(r for r in SW if r["detector"] == det and r["class"] == cls)


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
PRS = [(80, "Quang", "job run 14, mô-đun cảnh báo, bộ đánh giá, ADR-0009 (#74, #76)", ["3792c088bf787d44ee7e58d5b4d5853141d6f074"], "7193cc6435901eb0d56f0f17b962df221ecba16f"),
       (81, "An", "duyệt ADR-0009, ca kiểm thử ROI (#75)", ["4ca6002d126ccd860cc723079f665b20c0f3577e"], "a607ba8e354af61fb8989d8415d96d6518b0e4bd"),
       (82, "An", "model card YOLO11n (#77)", ["93afffb25810fb56085fae6a785dd5d485b43195"], "bedb3552ec65911c364b1e7c363bc623ccdc46a6"),
       (83, "Quang", "kết quả run 14, đánh giá cảnh báo, job run 15 (#74, #76)", ["e4d231ad27095da518f979f683f4bae9f0a88ff5"], "20bdea2469d8324c1562b4e8b0f3fcb6f66aec53"),
       (86, "Quang", "cấu trúc GitHub/Evidence theo mẫu GVHD, script kiểm tra (#79)", ["97752f96db9d1742657a1cff5ccfe375940ef9d4"], "9e0564a5c1c4a70040fab77cb8d14a71fb32cb34"),
       (87, "Quang", "demo run 15, phân tích hộp trùng, quy định tag (#76, #79)", ["bea720347a949c957fa79159ac3e43517e24e8ce"], "80acac22adec7d6fc2120c4221e4a7799f6aa8c5"),
       (89, "Quang", "khảo sát dữ liệu bổ sung, ADR-0011 (#88)", ["074822c83473a1e2438f3d8a1256af6f8e1e4081"], "a023b6fb4f941f817c5f0e95a0d7a515a56ad7f7"),
       (90, "An", "phân tích lỗi cảnh báo run 14 (#78)", ["3f5958c190b91a3aa4635e36f29c476196ad0ac6", "caafb96c74b9c0775a018addfbe249cca3cbdb4e"], "d26aa90445024ca16f736dcc766f586071522b95"),
       (91, "Quang", "sửa theo review của An, 40 ảnh âm tính, job run 16 (#76, #79, #88)", ["5fdd7042cfc3c88737fe63374ee100ecd8830d0c"], "234adcc9e466e24ba2256d109d80441b18e6d43f"),
       (92, "Quang", "link Drive video run 15 (#76)", ["95852aabb8fb8f484d514e3aff1fdd111498ecd9"], "7e1bbdb36cab289434c13256f0607154a309adac"),
       (93, "Quang", "precision một-một bằng ghép cặp lớn nhất (#76)", ["7badfc99e47fe794ccc0f38308fb3f41c7766abf"], "bb7e89afd3406d58c4f0c1fe8029c47d8c25a772"),
       (94, "An", "phân loại 40 ảnh val âm tính (#78)", ["6a15b42ddf98c188fc2c9a688ca4ad94cfdb3b57", "e626ae85b50f3fae070fdfd4c43b841fb4b1c2f1"], "d76d10585ee8edd628f9fda3c03fe82596111c91"),
       (95, "Quang", "lịch quay W7, kết quả xem ảnh của An (#88)", ["824c7cd6aa7b0ba68601ac10c90ea1f9a1c43a76"], "1afba4b3d9ebefc2468f60b03154a235ff25f19a")]

para("BÁO CÁO CÔNG VIỆC TUẦN 6 — NHÓM E1", True, 13, WD_ALIGN_PARAGRAPH.CENTER)
para("Đề tài: Nghiên cứu và phát triển hệ thống phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay dựa trên học sâu", False, 9.5, WD_ALIGN_PARAGRAPH.CENTER, True)
para("Tuần 6 (01/11–07/11/2026) — Milestone Tuan6: geofence + cảnh báo theo trajectory. GVHD: TS. Nguyễn Tất Thắng. Sinh viên: Lê Ngọc An, Dương Minh Quang.")
para("1. GitHub: Issue / PR / Commit cuối tuần (theo mẫu GVHD, ADR-0010)", True)
t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, h in enumerate(["Hạng mục", "Liên kết"]):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8); shade(c)


def row(label):
    cells = t.add_row().cells; cells[0].text = ""; r = cells[0].paragraphs[0].add_run(label); r.font.size = Pt(8)
    cells[1].text = ""; return cells[1].paragraphs[0]


p = row("Milestone / Issues")
add_link(p, "Milestone Tuan6", REPO + "/milestone/6", 8); plain(p, " · Issues #74–#79, #88 (mỗi issue một sinh viên, một kết quả, đúng 1 assignee)", 8)
for num, who, desc, commits, merge in PRS:
    p = row(f"PR #{num} ({who})")
    add_link(p, f"#{num}", f"{REPO}/pull/{num}", 8); plain(p, f" {desc}. Commit ", 8)
    for i, full in enumerate(commits):
        add_link(p, full[:7], f"{REPO}/commit/{full}", 8)
        if i < len(commits) - 1:
            plain(p, ", ", 8)
    plain(p, "; merge ", 8); add_link(p, merge[:7], f"{REPO}/commit/{merge}", 8)
p = row("Review chéo")
plain(p, "An review 8 PR của Quang: Approve #89, #92, #93; Comment #80, #83, #87, #91; Request changes #86 (đã sửa ở #91). Mọi nhận xét của An đều được kiểm bằng code và đúng; đã sửa kèm test. Quang approve #81, #82, #90, #94 của An. #95 chờ An review.", 8)
p = row("Kaggle (COMMIT)")
add_link(p, "7193cc6", REPO + "/commit/7193cc6435901eb0d56f0f17b962df221ecba16f", 8); plain(p, " run 14 (GPU); ", 8)
add_link(p, "9e0564a", REPO + "/commit/9e0564a5c1c4a70040fab77cb8d14a71fb32cb34", 8); plain(p, " run 15 (video demo); ", 8)
add_link(p, "d26aa90", REPO + "/commit/d26aa90445024ca16f736dcc766f586071522b95", 8); plain(p, " run 16 (40 ảnh âm tính). Quang chạy cả ba.", 8)
p = row("Commit cuối tuần")
plain(p, f"W6 không bắt buộc tag (Đề cương mục 10: W4, W8, W11, W14). Commit nội dung cuối trước báo cáo: ", 8)
add_link(p, GS_COMMIT.split()[0], f"{REPO}/commit/1afba4b3d9ebefc2468f60b03154a235ff25f19a", 8)
plain(p, "; commit cuối tuần = merge PR báo cáo, ghi ở ", 8); add_link(p, "issue #79", f"{REPO}/issues/79", 8)
p = row("check_structure.py --weeks 6")
plain(p, f"{GS_SUM} (WARN: PR #95 chờ An review). File: docs/status/W06_github_structure.md", 8)
widths(t, [3.4, 14.0])
d.add_paragraph().paragraph_format.space_after = Pt(0)

para("2. Phân chia công việc", True)
table(["Issue", "Nội dung", "Phụ trách", "Review", "Trạng thái"],
      [["#74 W6-01", "Run 14: YOLO11n + ByteTrack-e1, lưu detection thô, GT, ghép theo frame", "Quang", "An", "Xong (PR #80, #83)"],
       ["#75 W6-02", "Duyệt ADR-0009 trước khi đánh giá, ca kiểm thử ROI", "An", "Quang", "Đóng (PR #81)"],
       ["#76 W6-03", "Mô-đun geofence + cảnh báo R0/R1, đánh giá sự kiện, video demo", "Quang", "An", "Xong (PR #80, #83, #87, #91–#93)"],
       ["#77 W6-04", "Model card YOLO11n s20261030", "An", "Quang", "Đóng (PR #82)"],
       ["#78 W6-05", "Phân tích lỗi cảnh báo; phân loại 40 ảnh val âm tính", "An", "Quang", "Đóng (PR #90, #94)"],
       ["#88 W6-07", "Khảo sát dữ liệu bổ sung, ADR-0011, lịch quay W7", "Quang", "An", "Đóng (PR #89, #95)"],
       ["#79 W6-06", "Báo cáo W6, v0.6, Evidence/W06, cấu trúc GitHub", "Quang", "An", "Bản nộp"]],
      [1.7, 8.0, 1.8, 1.3, 4.6], size=8)

para("3. Planned – Done – Evidence – Problems – Next", True)
table(["Planned", "Done", "Evidence", "Problems", "Next week"],
      [["Geofence + cảnh báo theo quỹ đạo, luật đặt trước; tracking với YOLO11n; model card; phân tích lỗi",
        "Run 14 trên 38 video val; ADR-0009 Accepted trước khi đánh giá; luật → PASS; 3 video demo cảnh báo; phân tích lỗi; ADR-0011 kế hoạch dữ liệu; Evidence/W06",
        "results/W06/ (kaggle_run_14–15, alert_eval, detector_swap_tracking, val_negative_frames); ADR-0009/0010/0011; Evidence/W06/",
        "Chỉ 3,7 phút video không Drone; ID switch tăng gấp đôi khi đổi detector; ảnh val âm tính đều lỗi nhãn",
        "W7: tập âm tính tự quay ≥ 2 giờ, hard negative có điều kiện, phân tích nhầm lẫn, giao thức NMS"]],
      [3.0, 4.3, 3.8, 3.6, 2.7], size=8)

para("4. Kết quả đo (validation; ROI center_hex, điểm tâm; nguồn: CSV/JSON + script)", True)
mins = vn(R0["hours_nondrone"] * 60, 1)
n_pass = sum(c["status"] == "PASS" for c in EV["checks"])
cm = {k: sum(r["conclusion"] == k for r in MR) for k in {r["conclusion"] for r in MR}}
table(["Chỉ số", "Giá trị", "Nguồn"],
      [["Luật ADR-0009: R1 so với R0 (giảm ≥ 30% cảnh báo sai, recall giảm ≤ 5 điểm)", f"{AL['decision']['verdict']}: cảnh báo sai trên video không Drone {R0['false_alerts_nondrone']} → {R1['false_alerts_nondrone']}; event recall {R0['detected']}/{R0['events']} → {R1['detected']}/{R1['events']}", "results/W06/alert_eval/alert_summary.json"],
       [f"Cận trên 95% cảnh báo sai/giờ R0 / R1 (Poisson, {mins} phút)", f"{vn(R0['false_alerts_per_hour_nondrone_upper95'], 1)} / {vn(R1['false_alerts_per_hour_nondrone_upper95'], 1)} (chỉ báo, mẫu quá nhỏ)", "alert_summary.json"],
       ["Event precision một-một; cảnh báo lặp; độ trễ trung vị: R0 / R1", f"{vn(R0['event_precision_1to1'])} / {vn(R1['event_precision_1to1'])}; {R0['duplicates']} / {R1['duplicates']}; {vn(R0['latency_median_s'])} / {vn(R1['latency_median_s'])} s", "alert_summary.json"],
       ["ID switch / 1000 frame GT, ByteTrack-e1: baseline A → YOLO11n (Drone)", f"{vn(sw('baseline_A')['idsw_per_1000_gt_frames'], 2)} → {vn(sw('yolo11n_s20261030')['idsw_per_1000_gt_frames'], 2)} ({vn(sw('baseline_A', 'Drone')['idsw_per_1000_gt_frames'], 2)} → {vn(sw('yolo11n_s20261030', 'Drone')['idsw_per_1000_gt_frames'], 2)})", "results/W06/detector_swap_tracking/summary.csv"],
       ["Cặp ID track chồng nhau của YOLO11n: cùng lớp / tổng", f"{DUP['same_class_id_pairs']}/{DUP['same_class_id_pairs'] + DUP['cross_class_id_pairs']}", "results/W06/duplicate_boxes.json"],
       ["Video khả kiến không có Drone trong Svanström (cả 3 split)", f"{vn(COV['non_drone_minutes_all_splits'], 1)} phút / mục tiêu {COV['target_negative_minutes']:.0f} phút", "results/W06/dataset_coverage.json"],
       ["40 ảnh val \"âm tính\" (An xem bằng mắt)", f"{VN['with_det']}/{VN['negative_frames']} có dự đoán; {cm.get('vat_that_thieu_nhan', 0)}/40 là vật thật thiếu nhãn", "results/W06/val_negative_frames/"],
       ["Kiểm tra Evidence/W06", f"{n_pass}/{len(EV['checks'])} PASS; pytest {N_PYTEST} test", "Evidence/W06/test-results.json"]],
      [6.2, 6.4, 4.8], size=8)

para("5. Dataset card / model card", True)
para("Dataset e1-yolo-v1 không đổi (fingerprint d0ac7e23…). Model card YOLO11n s20261030: docs/w6/model_card_yolo11n.md (An). Kế hoạch dữ liệu W7–W12 (ADR-0011): Svanström vẫn là nguồn chính; tập âm tính tự quay + FBD-SV-2024 chỉ để đánh giá; OOD ở W11 (Anti-UAV300 RGB). Mọi nguồn mới đang needs_review trong data/manifests/license_matrix.csv.")
para("6. Demo/video (Drive demo/W06)", True)
p = d.add_paragraph(); plain(p, "Cảnh báo ROI + R0/R1 (run 15): ", 9)
for i, x in enumerate(DEMO15):
    add_link(p, x["video_id"], x["drive_link"], 9); plain(p, ", " if i < len(DEMO15) - 1 else ". ", 9)
plain(p, "Tracking YOLO11n + ByteTrack-e1 (run 14): ", 9)
for i, x in enumerate(DEMO14):
    add_link(p, x["video_id"], x["drive_link"], 9); plain(p, ", " if i < len(DEMO14) - 1 else ". ", 9)
plain(p, "SHA-256 trong demo_index.json của từng run.", 9)
para("7. Vấn đề và rủi ro (trung thực)", True)
for t_ in [f"Video không có Drone trên val chỉ {mins} phút. \"R1 có 0 cảnh báo sai\" chỉ đúng trên mẫu này; cận trên 95% vẫn khoảng {vn(R1['false_alerts_per_hour_nondrone_upper95'], 0)} cảnh báo/giờ. Svanström không đủ để đạt ≥ 2 giờ, nên W7 tự quay video bầu trời (ADR-0011). ROI là vùng mô phỏng, không phải vùng cấm bay thật.",
           "Đổi sang YOLO11n làm ID switch tăng gấp đôi, chủ yếu do track trùng cùng lớp; mAP không phản ánh độ ổn định ID. Cần giao thức đặt trước cho NMS ở W7.",
           "Ảnh val âm tính đều là vật thật thiếu nhãn (frame 0 có mục nhãn rỗng, V_BIRD_041 hết nhãn sớm), nên chưa đo được FP nền. Precision lớp Bird (0,548) có thể bị kéo xuống bởi một video; ảnh âm tính trong train có thể cùng lỗi, chưa kiểm.",
           "Phần lớn PR được review sau merge để kịp chạy Kaggle. Mọi số đo trên val (lạc quan); test vẫn khóa tới W10."]:
    d.add_paragraph(t_, style="List Bullet")
a.out.parent.mkdir(parents=True, exist_ok=True); d.save(a.out); print("saved", a.out)
