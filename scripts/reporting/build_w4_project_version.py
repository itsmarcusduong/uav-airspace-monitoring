#!/usr/bin/env python3
"""Version do an v0.4 (tuan 4): dien E1_Template_QuyenDoAn_2026_v0.docx -> E1_DoAn_v0.4_W04.docx, giu style template.

Ke thua noi dung v0.3 (build_w3_project_version.py) va them:
- muc 2.1, 2.2 tu ban nhap cua Le Ngoc An (docs/w4/chuong2_nhap_An.md, PR #47): cong thuc va so do Mermaid duoc render
  thanh anh (make_w4_figures.py), bang 2.2, tai lieu [13]-[19];
- muc 3.2.3/3.2.4 cap nhat W4: kiem chung chieu lech nhan (run 06, tap chuan CVAT), dong bang split v1;
- muc 5.1, 5.3, 5.4 cap nhat W4: so sanh 6 cau hinh detector (run 09), ap luat chon dat truoc (ADR-0007).
So lieu W4 doc truc tiep tu file ket qua (comparison_w4.csv, offset_check_summary.json, gold_score.json,
review_v2_agreement.json), khong nhap tay. So hinh/bang trong cau van tham chieu bang khoa, dung lai hai luot de khop
voi truong SEQ cua chu thich.

    python scripts/reporting/make_w4_figures.py --out reports/w4/figures
    python scripts/reporting/build_w4_project_version.py --template <E1_Template_QuyenDoAn_2026_v0.docx> \
        --out reports/w4/E1_DoAn_v0.4_W04_raw.docx
    python scripts/reporting/update_docx_fields.py reports/w4/E1_DoAn_v0.4_W04_raw.docx \
        reports/w4/E1_DoAn_v0.4_W04.docx reports/w4/E1_DoAn_v0.4_W04.pdf
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import re
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--template", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--fig-w2", type=Path, default=ROOT / "reports/w2/figures")
ap.add_argument("--fig-w3", type=Path, default=ROOT / "reports/w3/figures")
ap.add_argument("--fig-w4", type=Path, default=ROOT / "reports/w4/figures")
ap.add_argument("--kaggle-w2", type=Path, default=ROOT / "results/W02/kaggle_run_01")
ap.add_argument("--chapter2", type=Path, default=ROOT / "docs/w4/chuong2_nhap_An.md")
a = ap.parse_args()
for p in (a.template, a.chapter2, a.fig_w2, a.fig_w3, a.fig_w4, a.kaggle_w2):
    if not p.exists():
        raise SystemExit(f"khong thay {p}")


def rj(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


CMP = {r["model"]: r for r in csv.DictReader((ROOT / "results/W04/comparison_w4.csv").open(encoding="utf-8"))}
OFF = rj("results/W04/kaggle_run_06/w4_offset_check/offset_check_summary.json")
GS = rj("results/W04/cvat_gold/scoring/gold_score.json")
AG = rj("results/W04/review_v2_agreement.json")
ORDER = ["baseline_A", "baseline_A_aug", "baseline_A_960", "yolo11n_640", "detector_B", "rtdetr_l_640"]
CHANGE = {"baseline_A": "mốc (tuần 3)", "baseline_A_aug": "A: scale 0,5 → 0,3", "baseline_A_960": "A: imgsz 640 → 960",
          "yolo11n_640": "A: kiến trúc YOLO11n", "detector_B": "A@960: YOLOv8n → YOLOv8s", "rtdetr_l_640": "A: họ RT-DETR-l"}
missing = [m for m in ORDER if m not in CMP]
if missing:
    raise SystemExit(f"comparison_w4.csv thieu {missing}")


def vn(x, n=3):
    """So kieu Viet Nam (dau phay thap phan)."""
    return f"{float(x):.{n}f}".replace(".", ",")


def pv(p):
    return f"{p:.1e}".replace(".", ",").replace("e-0", "·10⁻").replace("e-", "·10⁻") if p < 0.001 else vn(p, 3)


# ----------------------------------------------------------------------------- chương II từ bản nháp của An
MD = a.chapter2.read_text(encoding="utf-8")
part21 = MD.split("## 2.1.", 1)[1].split("## 2.2.", 1)[0].split("\n", 1)[1]
part22 = MD.split("## 2.2.", 1)[1].split("### Tài liệu tham khảo bổ sung", 1)[0].split("\n", 1)[1]
REFS_AN = [re.sub(r"\*(.+?)\*", r"\1", ln.strip()) for ln in MD.split("### Tài liệu tham khảo bổ sung", 1)[1].splitlines()
           if re.match(r"^\[\d+\]", ln.strip())]
if [int(re.match(r"\[(\d+)\]", r).group(1)) for r in REFS_AN] != list(range(13, 20)):
    raise SystemExit("tai lieu tham khao bo sung cua An phai la [13]-[19]")
EQ_LIST = [a.fig_w4 / "eq_w4_iou.png", a.fig_w4 / "eq_w4_prf1.png"]


def field_run(p, instr, placeholder=""):
    def r(child):
        run = OxmlElement("w:r"); run.append(child); p._p.append(run); return run
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r(b)
    t = OxmlElement("w:instrText"); t.set(qn("xml:space"), "preserve"); t.text = f" {instr} "; r(t)
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); r(s)
    x = OxmlElement("w:t"); x.set(qn("xml:space"), "preserve"); x.text = placeholder; r(x)
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r(e)


def build(refs: dict):
    d = docx.Document(a.template)
    P = list(d.paragraphs)
    EQ_FILES = iter(EQ_LIST)
    n = {"Hình": 0, "Bảng": 0}
    keys = {}

    def R(k):
        return str(refs.get(k, "?"))

    class Cursor:
        def __init__(self, anchor):
            self.el = anchor._p

        def _put(self, el):
            self.el.addnext(el); self.el = el

        def para(self, text="", style="Normal", bold=False, italic=False, align=None):
            p = d.add_paragraph(style=style)
            if text:
                r = p.add_run(text); r.bold = bold; r.italic = italic
            if align is not None:
                p.alignment = align
            self._put(p._p); return p

        def rich(self, parts, style="Normal"):
            p = d.add_paragraph(style=style)
            for t, b in parts:
                r = p.add_run(t); r.bold = b
            self._put(p._p); return p

        def md(self, text, style="Normal"):
            """Doan van markdown don gian: **dam**, *nghieng*, \\(toan inline\\) voi chi so duoi X_y."""
            p = d.add_paragraph(style=style)
            for tok in re.split(r"(\*\*.+?\*\*|\*[^*]+?\*|\\\(.+?\\\))", text):
                if not tok:
                    continue
                if tok.startswith("**"):
                    p.add_run(tok[2:-2]).bold = True
                elif tok.startswith("\\("):
                    for m in re.finditer(r"([A-Za-z]+)(?:_\{?([A-Za-z0-9]+)\}?)?", tok[2:-2]):
                        r = p.add_run(m.group(1)); r.italic = True
                        if m.group(2):
                            s = p.add_run(m.group(2)); s.italic = True; s.font.subscript = True
                elif tok.startswith("*"):
                    p.add_run(tok[1:-1]).italic = True
                else:
                    p.add_run(tok)
            self._put(p._p); return p

        def bullets(self, items):
            for t in items:
                self.para(t, style="List Bullet")

        def heading3(self, text):
            return self.para(text, style="Heading 3")

        def caption(self, kind, text, key=None):
            n[kind] += 1
            if key:
                if key in keys:
                    raise SystemExit(f"khoa trung {key}")
                keys[key] = n[kind]
            p = d.add_paragraph(style="Caption"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(f"{kind} ")
            field_run(p, f"SEQ {kind} \\* ARABIC", str(n[kind]))
            p.add_run(f". {text}")
            self._put(p._p); return p

        def picture(self, path, width_cm):
            p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(path), width=Cm(width_cm)); self._put(p._p); return p

        def image(self, path, width_cm, caption, key=None):
            self.picture(path, width_cm).paragraph_format.keep_with_next = True
            self.caption("Hình", caption, key)

        def table(self, caption, header, rows, widths=None, size=9, note=None, key=None):
            cp = self.caption("Bảng", caption, key); cp.paragraph_format.keep_with_next = True
            t = d.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
            for i, h in enumerate(header):
                c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size)
                sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "D9E2F3"); c._tc.get_or_add_tcPr().append(sh)
            trp = t.rows[0]._tr.get_or_add_trPr(); trp.append(OxmlElement("w:tblHeader"))
            for row in rows:
                cells = t.add_row().cells
                for i, v in enumerate(row):
                    cells[i].text = ""; rr = cells[i].paragraphs[0].add_run(str(v)); rr.font.size = Pt(size)
            if widths:
                for row in t.rows:
                    for i, w in enumerate(widths):
                        row.cells[i].width = Cm(w)
                # LibreOffice doc do rong cot tu tblGrid: ghi gridCol cho khop
                for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
                    gc.set(qn("w:w"), str(int(Cm(w).twips)))
            self._put(t._tbl)
            if note:
                q = self.para(note, italic=True); q.runs[0].font.size = Pt(8.5)
            else:
                self.para("")
            return t

    def fill(idx, builder):
        ph = P[idx]; assert "Nhóm điền" in ph.text, (idx, ph.text)
        ph.text = ""; cur = Cursor(ph); builder(cur); ph._p.getparent().remove(ph._p)

    def replace_with_field(idx, instr, hint):
        p = P[idx]; assert p.text.startswith("["), (idx, p.text)
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        field_run(p, instr, hint)

    # ======================================================================== MỞ ĐẦU
    def mo_dau(c):
        c.para("Phiên bản v0.4 (tuần 4). Số liệu dẫn từ các tệp kết quả trong kho mã nguồn (đường dẫn ghi kèm); các ngưỡng định lượng là đề xuất, chờ giảng viên hướng dẫn xác nhận. So với v0.3: thêm mục 2.1 và 2.2, cập nhật mục 3.2 (kiểm chứng chiều lệch nhãn, đóng băng split) và chương V (so sánh sáu cấu hình detector).", italic=True)
        c.para("Bài toán. Camera đặt trên mặt đất quan sát vùng trời quanh sân bay cần phát hiện UAV chỉ chiếm vài chục đến vài trăm điểm ảnh, phân biệt chúng với chim, máy bay và trực thăng, theo dõi qua nhiều khung hình và báo cho người vận hành khi UAV đi vào vùng giám sát. Khó khăn chính là vật thể nhỏ (trung vị diện tích hộp bao ở ảnh hồng ngoại khoảng 180–380 px², ở ảnh khả kiến khoảng 700–4.800 px², theo class_stats.csv) và các lớp có hình dạng dễ nhầm.")
        c.para("Điểm khác với một bài tập lớn thông thường là đề tài phải có quy trình dữ liệu tái lập được (manifest, checksum, chia dữ liệu theo video), so sánh mô hình trong cùng điều kiện, đánh giá phát hiện – theo dõi – cảnh báo bằng số liệu và lưu minh chứng theo từng tuần trên GitHub.")
        c.image(a.fig_w2 / "fig_overview.png", 15.5, "Sơ đồ tổng quan bài toán và chu trình xử lý đề xuất.", "f_overview")
        c.para(f"Mục tiêu định lượng đề xuất theo Thuyết minh mục 12 được tóm tắt trong Bảng {R('t_targets')}.")
        c.table("Mục tiêu định lượng đề xuất (chưa được giảng viên hướng dẫn xác nhận).",
                ["Mục tiêu", "Chỉ số", "Ngưỡng đề xuất", "Tập đo"],
                [["Phát hiện UAV", "Precision, Recall, mAP@0.5 lớp Drone", "P, R ≥ 0,85; mAP@0.5 ≥ 0,80", "Test (khóa tới đánh giá cuối)"],
                 ["Theo dõi", "HOTA, IDF1, ID switch", "Chỉ báo khi có nhãn track hợp lệ (Svanström không có track ID)", "Chưa xác định"],
                 ["Cảnh báo", "Tỷ lệ cảnh báo giả; event recall", "Giảm ≥ 30% so với chỉ dùng detector; recall giảm ≤ 5 điểm %", "Video âm tính ≥ 2 giờ"],
                 ["Thời gian thực", "FPS, độ trễ p95", "≥ 15 FPS; p95 ≤ 500 ms trên GPU tham chiếu, đo ≥ 3 lần", "Cùng phần cứng"]],
                [3.2, 4.2, 5.6, 3.2], key="t_targets")
        c.para(f"Phân chia công việc được ghi theo Issue trên GitHub; Bảng {R('t_alloc')} liệt kê phần đã có Issue hoặc commit tới hết tuần 4.")
        c.table("Phân chia công việc tới tuần 4 (chỉ liệt kê đóng góp đã có Issue/commit).",
                ["Thành viên", "Vai trò", "Đóng góp chính (Issue)", "Review chéo"],
                [["Dương Minh Quang", "Lead B: dữ liệu, tích hợp, kiểm thử",
                  "W2: Kaggle EDA/audit (#2, #3), split v1 (#6), báo cáo (#9). W3: review nhãn v2 (#10), kiểm tra lệch nhãn (#11), xuất dữ liệu YOLO (#16), huấn luyện baseline A (#18), báo cáo (#21). W4: kiểm chứng chiều lệch nhãn run 06 (#36), job tập chuẩn CVAT và chấm điểm (#24), huấn luyện và so sánh 5 cấu hình (run 09 phiên 1–2, #39), cấu trúc Evidence (#48), báo cáo và v0.4 (#49)", "An"],
                 ["Lê Ngọc An", "Lead A: phân tích, thiết kế, thí nghiệm",
                  "W2: tiêu chí audit (#4), giao thức split và ADR (#5), khung Mở đầu – Chương I (#8). W3: kiểm tra license Ultralytics/YOLOv8n (#20), giao thức huấn luyện (#17), phân tích kết quả và model card (#19). W4: duyệt ADR-0002/0003 (#5), config detector B và biến thể augmentation (#38), vẽ tập chuẩn CVAT 168 ảnh và review độc lập 40 video (#24), chạy run 09 phiên 3 RT-DETR-l (#39), bản nháp mục 2.1–2.2 (#41)", "Quang"]],
                [3.0, 3.6, 7.6, 2.0], key="t_alloc")
        c.para("Cấu trúc báo cáo gồm sáu chương, được tóm tắt ở mục 1.5.")

    # ======================================================================== 1.1 – 1.3
    def s11(c):
        c.para("UAV cỡ nhỏ xuất hiện trong ảnh với rất ít điểm ảnh, có hình dạng gần giống chim và chịu ảnh hưởng của nền trời, mây, ánh sáng ngược và nén video. Vì vậy một mô hình cho kết quả tốt trên ảnh thông thường chưa đủ để kết luận cho bài toán giám sát vùng trời sân bay; cần dữ liệu quan sát từ mặt đất và cách đánh giá theo video.")
        c.para("Các bộ dữ liệu công khai khác nhau về góc nhìn. Bộ dữ liệu của Svanström và cộng sự dùng camera đặt trên mặt đất, gồm UAV, chim, máy bay và trực thăng ở dạng video khả kiến và hồng ngoại [11]. VisDrone [4], [5] và UAVDT [7] dùng camera gắn trên UAV nhìn xuống nên chỉ phù hợp làm tham khảo về vật thể nhỏ và cách xây dựng benchmark. Về theo dõi, ByteTrack [2] và BoT-SORT [3] là hai phương pháp liên kết đa đối tượng làm cơ sở; RT-DETR [6] là hướng phát hiện thời gian thực để đối chiếu; Ultralytics [1], [12] cung cấp giao diện thống nhất giữa detector và tracker.")
        c.table("So sánh các nguồn dữ liệu (nguồn: tài liệu W1 và kiểm chứng Kaggle W2).",
                ["Dữ liệu", "Góc nhìn", "Mục tiêu UAV bay", "Vai trò trong đề tài"],
                [["Svanström [11]", "Camera mặt đất (kiểm chứng: 650 video, 203.328 frame)", "Có (Drone 271 video) + 3 lớp gây nhầm", "Dữ liệu chính (CC0-1.0 theo repository)"],
                 ["VisDrone [4], [5]", "Camera trên UAV nhìn xuống", "Không phải mục tiêu chính", "Chỉ tham khảo"],
                 ["UAVDT [7]", "Camera trên UAV", "Không phải mục tiêu chính", "Chỉ tham khảo"],
                 ["Anti-UAV [13]", "Camera mặt đất, theo dõi một mục tiêu", "Có (UAV, RGB/hồng ngoại)", "Tham khảo (mục 2.2); license dữ liệu chưa xác minh, chưa tải"]],
                [3.0, 5.0, 3.8, 4.4], key="t_sources")
        c.para("Giới hạn của dữ liệu chính: chỉ có điều kiện ban ngày, thu tại số ít vị trí ở Thụy Điển, không đại diện cho sân bay Việt Nam, mưa, sương hay ban đêm. Do đó kết quả của đồ án là kết quả trên benchmark công khai, không phải khẳng định về vận hành thực tế.")

    def s12(c):
        c.para("Mục tiêu tổng quát: xây dựng nguyên mẫu xử lý video từ camera mặt đất để phát hiện, phân loại và theo dõi UAV, kèm cảnh báo hỗ trợ người quan sát và bộ đánh giá tái lập được. Ba câu hỏi kỹ thuật: (Q1) cấu hình detector nào cân bằng tốt nhất giữa độ chính xác và tốc độ với vật thể nhỏ; (Q2) thông tin theo thời gian (tracking) giảm cảnh báo giả được bao nhiêu; (Q3) hiệu năng thay đổi thế nào theo cự ly và modality.")
        A = CMP["baseline_A"]
        c.table("Mục tiêu → chỉ số → ngưỡng đề xuất → minh chứng (cập nhật tới tuần 4).",
                ["Mục tiêu", "Chỉ số", "Ngưỡng đề xuất", "Tuần", "Minh chứng"],
                [["Dữ liệu sạch, tái lập", "Checksum 1.303 tệp; split theo video", "Không sai khác; không rò rỉ trực tiếp", "W2–W4", "checksum_verification.csv; video_split_v1.csv (đóng băng tại tag w04); dataset_card.json"],
                 ["Detector baseline", "mAP@0.5, P/R theo lớp, theo cỡ bbox", f"Như Bảng {R('t_targets')}", "W3–W4",
                  f"W3: mAP@0.5 = {vn(A['map50'])} trên val (run 04). W4: so sánh 6 cấu hình, giữ YOLOv8n @640 theo luật đặt trước (mục 5.3, ADR-0007); test chưa đánh giá"],
                 ["Tracker", "ID switch, độ ổn định ID", "Chưa có nhãn track hợp lệ", "W5", "Chưa có"],
                 ["Cảnh báo", "Cảnh báo giả / event recall", "−30% / ≤ 5 điểm %", "W6–W7", "Chưa có"],
                 ["Tốc độ", "FPS, độ trễ p95", "≥ 15 FPS; ≤ 500 ms", "W9", "W4: thời gian suy luận trong bước val (mục 5.3), chưa phải FPS pipeline"]],
                [3.2, 3.8, 3.6, 1.6, 4.2], size=8.5, key="t_goals")

    def s13(c):
        c.para("Đối tượng: UAV và ba lớp gây nhầm (chim, máy bay, trực thăng) trong video từ camera mặt đất. Phạm vi MVP: đọc video tệp, phát hiện và phân loại 4 lớp, theo dõi, vùng giám sát dạng đa giác trên ảnh và cảnh báo có xác nhận theo thời gian; đánh giá offline.")
        c.table("Phạm vi MVP và phần mở rộng.", ["MVP (bắt buộc)", "Mở rộng (nếu còn thời gian)"],
                [["Detector baseline + các cấu hình đối chứng; ByteTrack; ROI + cảnh báo; benchmark cố định",
                  "BoT-SORT đối chiếu, RT-DETR huấn luyện lại đúng cấu hình, tối ưu bằng TensorRT [10], luồng camera thử nghiệm, Docker, PostgreSQL"]],
                [8.2, 8.0], key="t_scope")
        c.para("Giới hạn: không đại diện điều kiện đêm, mưa, sương và sân bay Việt Nam; đa giác ROI là vùng trên ảnh, không phải vùng cấm bay pháp lý; hệ thống chỉ hỗ trợ quan sát, không suy đoán ý định của đối tượng; mọi số liệu trong báo cáo phải truy được tới tệp kết quả.")

    # ======================================================================== 1.4, 1.5
    def s14(c):
        c.para(f"Kết quả dự kiến của đồ án gồm bốn nhóm sản phẩm: dữ liệu, mô hình, phần mềm và tài liệu nghiên cứu. Mỗi sản phẩm có định danh phiên bản (commit, SHA-256 hoặc tag) để người khác có thể kiểm tra và chạy lại. Bảng {R('t_artifacts')} liệt kê các sản phẩm và trạng thái tại ngày 29/10/2026.")
        c.table("Danh sách sản phẩm (artifact) có phiên bản và trạng thái tại tuần 4.",
                ["Sản phẩm", "Loại", "Định danh / vị trí", "Trạng thái"],
                [["Manifest và checksum dữ liệu gốc", "Dữ liệu", "data/manifests/; checksum_verification.csv (1.303 tệp)", "Hoàn thành (W1–W2)"],
                 ["Split theo video v1 (454/98/98)", "Dữ liệu", "data/splits/video_split_v1.csv, SHA-256 7e3994…", "Đóng băng tại tag w04 (ADR-0003, An và Quang duyệt)"],
                 ["Review nhãn v2 (358 video)", "Dữ liệu", "results/W03/review/review_assignment_w3.csv", "Hoàn thành (W3); An kiểm tra độc lập 40 video (W4)"],
                 ["Tập huấn luyện YOLO e1-yolo-v1", "Dữ liệu", "dataset_card.json, fingerprint d0ac7e23…", "Hoàn thành (W3); giữ ở W4 (ADR-0006)"],
                 ["Tập chuẩn CVAT (168 ảnh, khóa đáp án tách riêng)", "Dữ liệu", "results/W04/cvat_gold/", "Hoàn thành (W4)"],
                 ["Detector baseline A (YOLOv8n @640)", "Mô hình", "best.pt SHA-256 65dd67fb… (Drive) + model card (docs/w3/model_card_baseline_A.md)", "Hoàn thành (W3); được chọn cho W5 (ADR-0007)"],
                 ["5 cấu hình detector đối chứng (gồm detector B YOLOv8s @960)", "Mô hình", "results/W04/kaggle_run_09/; weights Drive + SHA-256; results/W04/comparison_w4.csv", "Hoàn thành (W4), đánh giá trên val"],
                 ["Mô-đun theo dõi (ByteTrack, đối chiếu BoT-SORT)", "Phần mềm", "W5–W6", "Kế hoạch"],
                 ["Mô-đun ROI và cảnh báo theo quỹ đạo", "Phần mềm", "W6–W7", "Kế hoạch"],
                 ["Pipeline đầu-cuối, API, dashboard, nhật ký", "Phần mềm", "Tag release W8", "Kế hoạch"],
                 ["Benchmark FPS/độ trễ cố định", "Nghiên cứu", "Tag release W11", "Kế hoạch"],
                 ["Báo cáo, model card, dataset card, hướng dẫn tái lập", "Tài liệu", "Tag w04 (release W4); release W14", "Đang cập nhật hằng tuần"]],
                [5.0, 2.0, 6.2, 3.0], size=8.5, key="t_artifacts")
        c.para("Đóng góp của đồ án được xác định ở mức kỹ thuật, có thể kiểm chứng bằng số liệu:")
        c.bullets([
            "(C1) Quy trình chuẩn bị và đánh giá dữ liệu theo video cho bài toán phát hiện UAV từ mặt đất: chia dữ liệu theo video để tránh rò rỉ, sàng lọc cảnh gần trùng, kiểm chứng chiều lệch nhãn bằng hai phương pháp độc lập có nhóm đối chứng và luật quyết định đặt trước, và review nhãn có quy tắc ghi rõ.",
            "(C2) So sánh có kiểm soát nhiều cấu hình detector (YOLOv8n @640/@960, YOLO11n, YOLOv8s, RT-DETR-l) trên cùng split, cùng ngân sách huấn luyện, mỗi biến thể chỉ đổi một yếu tố, có phân tích theo lớp, theo cỡ vật thể và luật chọn mô hình đặt trước, dùng PyTorch [9] và Ultralytics [12].",
            "(C3) Đánh giá tác động của thông tin thời gian (tracking và xác nhận nhiều khung hình) lên tỷ lệ cảnh báo giả, trong giới hạn dữ liệu không có nhãn track ID.",
            "(C4) Nguyên mẫu phần mềm đầu-cuối và bộ minh chứng tái lập (mã nguồn, cấu hình, SHA-256, tag release, thư mục Evidence theo tuần)."])
        c.para(f"Đóng góp của từng thành viên được ghi theo Issue và commit trên GitHub, tổng hợp ở Bảng {R('t_alloc')} và cập nhật trong báo cáo công việc hằng tuần. Hai thành viên review chéo Pull Request của nhau; báo cáo ghi trung thực các tuần chưa có review.")

    def s15(c):
        c.para(f"Báo cáo gồm sáu chương. Bảng {R('t_chapters')} nêu câu hỏi mà mỗi chương trả lời; các đoạn dưới đây tóm tắt nội dung.")
        c.table("Câu hỏi mà mỗi chương trả lời.", ["Chương", "Câu hỏi trả lời"],
                [["I. Giới thiệu", "Bài toán là gì, vì sao cần giải quyết, mục tiêu và phạm vi đến đâu?"],
                 ["II. Cơ sở lý thuyết", "Những phương pháp phát hiện, theo dõi và đánh giá nào làm nền tảng cho giải pháp?"],
                 ["III. Yêu cầu, dữ liệu, phương pháp", "Hệ thống cần đáp ứng gì, dữ liệu được chuẩn bị và kiểm soát ra sao, thí nghiệm được thiết kế thế nào?"],
                 ["IV. Thiết kế hệ thống", "Các mô-đun được tổ chức và kết nối như thế nào?"],
                 ["V. Cài đặt và thực nghiệm", "Kết quả đo được là bao nhiêu, lỗi nằm ở đâu?"],
                 ["VI. Kết luận", "Đồ án đạt được gì, còn hạn chế gì, nên phát triển tiếp theo hướng nào?"]],
                [5.0, 11.2], key="t_chapters")
        for t in [
            "Chương I trình bày bối cảnh giám sát UAV quanh sân bay, các nguồn dữ liệu công khai và giới hạn của chúng, mục tiêu định lượng, phạm vi MVP, sản phẩm dự kiến và đóng góp.",
            "Chương II tóm tắt kiến thức nền về phát hiện vật thể một giai đoạn (YOLO) và dựa trên Transformer (RT-DETR), theo dõi đa đối tượng theo hướng tracking-by-detection (ByteTrack, BoT-SORT), các độ đo mAP, HOTA, IDF1, và so sánh các công trình liên quan.",
            "Chương III phân tích yêu cầu chức năng và phi chức năng, mô tả dữ liệu Svanström cùng quy trình kiểm định, chia dữ liệu theo video và xử lý lệch nhãn, phương pháp đề xuất và giao thức thí nghiệm.",
            "Chương IV trình bày kiến trúc hệ thống từ đọc video, phát hiện, theo dõi, cảnh báo theo ROI tới API, dashboard và nhật ký; thiết kế dữ liệu và các rủi ro bảo mật, riêng tư.",
            "Chương V mô tả môi trường cài đặt và kết quả thực nghiệm: detector baseline và các cấu hình đối chứng, tracker, cảnh báo, tốc độ xử lý, cùng phân tích lỗi theo lớp và cỡ vật thể.",
            "Chương VI tổng kết mức độ đạt mục tiêu, các hạn chế về dữ liệu và phương pháp, và đề xuất hướng phát triển."]:
            c.para(t)

    # ======================================================================== 2.1, 2.2 (bản nháp của An)
    def chapter2(c, text, intro=None):
        if intro:
            c.para(intro, italic=True)
        lines = text.splitlines()
        i, pend_table_cap = 0, None
        while i < len(lines):
            ln = lines[i].rstrip()
            s = ln.strip()
            if not s or s.startswith("<!--"):
                i += 1; continue
            if s.startswith("### "):
                h = re.sub(r"^(\d+\.\d+\.\d+)\.\s*", r"\1 ", s[4:])
                c.heading3(h); i += 1; continue
            if s == "$$":
                j = lines.index("$$", i + 1)
                eq = next(EQ_FILES)
                from PIL import Image
                with Image.open(eq) as im:
                    natural_cm = im.size[0] / 300 * 2.54          # anh render o 300 dpi, co chu 15 pt
                c.picture(eq, min(14.0, 0.8 * natural_cm)); i = j + 1; continue
            if s.startswith("```mermaid"):
                j = next(k for k in range(i + 1, len(lines)) if lines[k].strip() == "```")
                cap = next(lines[k] for k in range(j + 1, len(lines)) if lines[k].strip().startswith("**Hình"))
                cap = re.sub(r"^\*\*Hình [\d.]+\.?\*\*\s*", "", cap.strip())
                c.image(a.fig_w4 / "fig_w4_tracking_by_detection.png", 6.6, cap, "f_tbd")
                i = j + 1; continue
            if s.startswith("**Hình"):
                i += 1; continue                   # da dung lam chu thich o tren
            if re.match(r"^\*\*Bảng [\d.]+\.?", s):
                pend_table_cap = re.sub(r"^\*\*Bảng [\d.]+\.?\s*", "", s).rstrip("*").strip(); i += 1; continue
            if s.startswith("|"):
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                    if not all(re.fullmatch(r"-+", x) for x in cells):
                        rows.append([re.sub(r"\*\*(.+?)\*\*", r"\1", x) for x in cells])
                    i += 1
                c.table((pend_table_cap or "So sánh") + " (Lê Ngọc An tổng hợp).", rows[0], rows[1:],
                        [2.4, 1.9, 2.5, 2.4, 2.4, 2.4, 2.4], size=7.5, key="t_related")
                pend_table_cap = None; continue
            s = s.replace("Bảng 2.1", f"Bảng {R('t_related')}").replace("Hình 2.1", f"Hình {R('f_tbd')}")
            c.md(s); i += 1

    def s21(c):
        chapter2(c, part21)

    def s22(c):
        chapter2(c, part22)

    # ======================================================================== 3.2
    def s32(c):
        K = a.kaggle_w2
        c.heading3("3.2.1 Nguồn dữ liệu và dataset card")
        c.para("Dữ liệu chính là bộ Drone-detection-dataset của Svanström và cộng sự [11], tải thủ công ngày 04/10/2026, giấy phép CC0-1.0 theo repository. Toàn vẹn dữ liệu trên Kaggle được kiểm tra: 1.303/1.303 tệp khớp SHA-256 với bản W1 (checksum_verification.csv). Video được giải mã bằng OpenCV [8].")
        c.table("Dataset card tóm tắt.", ["Thông tin", "Giá trị (nguồn)"],
                [["Số video có nhãn", "650: hồng ngoại 365 (320×256), khả kiến 285 (640×512), 30 fps (video_inventory.csv)"],
                 ["Số frame giải mã", "203.328 (stage_status.json, Kaggle run 01)"],
                 ["Lớp (số video)", "Airplane 133, Bird 130, Drone 271, Helicopter 116"],
                 ["Nhãn", "MATLAB *_LABELS.mat đọc bằng mcos-decoder; mỗi frame tối đa 1 hộp (x, y, w, h); không có track ID"],
                 ["Metadata", "Video_dataset_description.xlsx: cảm biến, lớp, số thứ tự, khoảng cách (CLOSE 133 / MEDIUM 292 / DISTANT 225)"],
                 ["Phần cứng xử lý", "Kaggle CPU 4 lõi, Python 3.13, OpenCV 4.14 (env.json)"]],
                [3.8, 12.4], key="t_card")
        c.heading3("3.2.2 Thống kê lớp và kích thước vật thể")
        c.image(K / "fig_videos_by_modality_class.png", 12, "Số video theo modality và lớp (Kaggle run 01).", "f_videos")
        c.table("Thống kê kích thước hộp bao (diện tích px²; nhỏ: dưới 32×32 = 1.024 px²; class_stats.csv).",
                ["Modality", "Lớp", "Video", "Frame", "Tỷ lệ hộp nhỏ", "Diện tích trung vị"],
                [["IR", "Airplane", 74, "23.243", "96,4%", "197"], ["IR", "Bird", 79, "24.854", "100%", "178"],
                 ["IR", "Drone", 157, "49.043", "98,9%", "219"], ["IR", "Helicopter", 55, "16.955", "86,3%", "381"],
                 ["V", "Airplane", 59, "18.585", "45,2%", "1.269"], ["V", "Bird", 51, "16.118", "82,3%", "702"],
                 ["V", "Drone", 114, "35.496", "60,5%", "900"], ["V", "Helicopter", 61, "19.034", "22,7%", "4.804"]],
                [2.4, 3.0, 2.2, 2.6, 3.2, 3.2], key="t_bbox")
        c.image(K / "fig_bbox_area_by_class.png", 14, "Phân bố diện tích hộp bao theo lớp và modality (Kaggle run 01).", "f_bbox")
        c.heading3("3.2.3 Chất lượng nhãn")
        c.para("Audit tự động trên toàn bộ 650 video (docs/w2/annotation_audit_w2.md) cho kết quả:")
        c.bullets(["Không có hộp nằm ngoài ảnh, có chiều rộng/cao ≤ 0 hoặc giá trị NaN.",
                   "253 video có số mục nhãn khác số frame; 231 video dư đúng một mục. Nhóm này tập trung theo lớp: toàn bộ 114 video Drone khả kiến, 40 video Bird khả kiến và 77 video Bird hồng ngoại. Vì vậy không thể loại bỏ nhóm này mà không mất lớp Drone (ADR-0004).",
                   "58 video có bước nhảy tâm hộp lớn; một phần do camera xoay hoặc zoom, nên giả định camera cố định không đúng cho toàn bộ dữ liệu."])
        c.para(f"Để quyết định cách dùng video dư một mục, nhóm đo độ nhạy: nếu tỷ lệ cặp frame liên tiếp có IoU ≥ 0,5 đạt từ 90% trở lên thì việc lệch một frame hầu như không làm đổi kết quả khớp ở ngưỡng IoU 0,5 của mAP@0.5. Kết quả ở Hình {R('f_offset_sens')}: Drone dư một mục đạt 98,6% (95 video) và Bird dư một mục đạt 95,3% (34 video), nên nhóm này được giữ lại với cách căn frame i ↔ nhãn i (offset 0). Nhóm Bird thiếu nhãn chỉ đạt 87,5% và bị loại.")
        c.image(a.fig_w3 / "fig_w3_offset_sensitivity.png", 14, "Độ nhạy với lệch một khung hình theo nhóm video khả kiến (Kaggle run 03a, offset_sensitivity_summary.json).", "f_offset_sens")
        c.para("Nhóm cũng thăm dò chiều lệch bằng bảng xem có nhóm đối chứng, với luật chấm đặt trước (ADR-0004 mục 6). Ở nhóm đối chứng, người xem chỉ chọn đúng 53% (8/15 lựa chọn rõ ràng), thấp hơn ngưỡng 80%, nên phương pháp xem không đủ tin cậy và chiều lệch được ghi là chưa xác định. Kết quả này chỉ là thăm dò, không phải review mù độc lập, vì khóa đáp án nằm cùng gói kết quả với bảng xem.")
        c.para("Sau khi phân tích baseline A (mục 5.4), nhóm ghi nhận thêm: 111/114 video Drone khả kiến dư một mục có đúng một mục nhãn rỗng (annotation_audit.csv); ở cả 92 video Drone đã xuất, mục rỗng đó rơi vào frame 0 (yolo_manifest.csv.gz), trong khi review v2 thấy drone ngay ở frame 0. Chi tiết này nghiêng về giả thuyết mục đầu tiên là mục thừa (nhãn đúng của frame i là mục i + 1).")
        # --- W4: hai kiểm chứng độc lập
        g, gc, gr = OFF["groups"]["Drone|plus1"], OFF["groups"]["control_equal"], GS["groups"]
        ex = GS["exploratory_center"]
        c.para("Tuần 4 kiểm chứng chiều lệch bằng hai phương pháp độc lập, cùng luật quyết định đặt trước (ADR-0006, PR #43, 22/10/2026): phương pháp được coi là tin cậy khi nhóm đối chứng (video khớp số nhãn, mặc định đúng offset 0) có ≥ 80% video nghiêng đúng chiều và sign test theo video p < 0,01; chỉ khi đó mới xét nhóm dư một mục. Đơn vị kiểm định là video vì các frame trong cùng video không độc lập.")
        c.bullets([
            "Run 06 (dự đoán của baseline A trên val): so IoU giữa hộp dự đoán và nhãn i, nhãn i + 1 (scripts/kaggle/w4_offset_check.py).",
            "Tập chuẩn CVAT: Lê Ngọc An vẽ lại 168 ảnh từ 157 video khi chưa biết đáp án; khóa đáp án tách riêng và chỉ mở sau khi annotation được commit (PR #53, #54; scripts/dataset/score_cvat_gold.py)."])
        c.table("Kiểm chứng chiều lệch nhãn theo luật đặt trước (offset_check_summary.json; gold_score.json).",
                ["Phương pháp", "Đối chứng: video nghiêng về i / tổng, p", "Drone dư 1 mục: video nghiêng về i+1 / tổng, p", "Kết luận theo luật"],
                [["Run 06 (IoU dự đoán)", f"{gc['videos'] - gc['videos_i1_better']}/{gc['videos']}, p = {pv(gc['sign_test_p'])}",
                  f"{g['videos_i1_better']}/{g['videos']}, p = {pv(g['sign_test_p'])}", "UNDETERMINED (đối chứng không đạt)"],
                 ["Tập chuẩn CVAT (IoU hộp vẽ tay)", f"{gr['control_equal']['videos'] - gr['control_equal']['videos_i1_better']}/{gr['control_equal']['videos']}, p = {pv(gr['control_equal']['sign_test_p'])}",
                  f"{gr['Drone|plus1']['videos_i1_better']}/{gr['Drone|plus1']['videos']}, p = {pv(gr['Drone|plus1']['sign_test_p'])}", "UNDETERMINED (đối chứng không đạt)"]],
                [4.0, 4.2, 4.6, 3.4], size=8.5, key="t_offset")
        bl = ex["box_vs_label"]
        c.para(f"Theo luật, cả hai phương pháp đều chưa kết luận được nên dữ liệu huấn luyện tuần 4 giữ nguyên e1-yolo-v1 (offset 0). Tập chuẩn cho thêm một phát hiện về nhãn gốc (Hình {R('f_cvat')}): hộp vẽ tay có tâm gần như trùng nhãn (trung vị lệch {vn(bl['median_center_dist_px'], 1)} px; {vn(100 * bl['frac_center_dist_le_10px'], 1)}% ảnh lệch không quá 10 px) nhưng diện tích chỉ bằng khoảng {vn(bl['median_area_ratio_annot_over_label_i'], 2)} lần hộp nhãn. Như vậy hộp nhãn của bộ dữ liệu rộng hơn vật thể nhiều, và IoU chịu ảnh hưởng của độ rộng hộp nhiều hơn của vị trí.")
        c.image(a.fig_w4 / "fig_w4_cvat_box_vs_label.png", 13.5, "Hộp vẽ lại trên tập chuẩn so với nhãn gốc: lệch tâm và tỷ lệ diện tích (cvat_gold_an_20261028.zip, gold_KEY.zip).", "f_cvat")
        e = ex["groups"]
        c.para(f"Phân tích thăm dò (thêm sau khi xem kết quả, không thay luật): dùng khoảng cách tâm thay cho IoU, {e['Drone|plus1']['videos_closer_to_i1']}/{e['Drone|plus1']['videos']} video Drone dư một mục gần nhãn i + 1 hơn (p = {pv(e['Drone|plus1']['sign_test_p'])}), trong khi đối chứng có {e['control_equal']['videos'] - e['control_equal']['videos_closer_to_i1']}/{e['control_equal']['videos']} video gần nhãn i (p = {pv(e['control_equal']['sign_test_p'])}). Hai phương pháp độc lập cùng nghiêng về offset 1 cho Drone dư một mục, nhưng đối chứng của cả hai đều chưa đủ mạnh, nên việc đổi dữ liệu cần một ADR mới có luật đặt trước (dự kiến tuần 7).")
        c.para(f"Review nhãn lần 2 xem 358 video, mỗi video 8 frame (trải đều và frame có bước nhảy lớn nhất) kèm ảnh phóng to quanh hộp, có hỗ trợ công cụ. Quy tắc: SAI_NHAN khi hộp rỗng trong lúc vật thể nhìn rõ ở chỗ khác hoặc một đoạn dài thiếu nhãn dù vẫn thấy vật thể; KHONG_RO khi không đủ thông tin. Kết quả nêu ở Bảng {R('t_review')}. Ở tuần 4, Lê Ngọc An review độc lập {AG['videos']} video chọn ngẫu nhiên: đồng ý {AG['agree']}/{AG['videos']} ({vn(AG['percent_agree'], 1)}%), Cohen's κ = {vn(AG['cohen_kappa'], 2)} (review_v2_agreement.json); cả {AG['videos'] - AG['agree']} video lệch đều do hai người dùng tiêu chí khác nhau (\"thấy vật thể\" so với \"hộp chứa vật ở mọi frame\"), cần thống nhất trước tuần 7.")
        c.table("Kết quả review nhãn v2 (review_v2_summary.json).", ["Kết luận", "Số video", "Ghi chú"],
                [["OK", 283, "Bao gồm trường hợp lệch một frame ngay tại điểm chuyển cảnh"],
                 ["SAI_NHAN", 60, "Tập trung ở lớp Bird; 10 video \"không có nhãn\" thực tế có vật thể bay → không dùng làm ảnh âm tính"],
                 ["KHONG_RO", 15, "Vật thể quá mờ hoặc khung hình không đủ thông tin"]],
                [3.0, 2.4, 10.8], key="t_review")
        c.heading3("3.2.4 Chia train/val/test")
        c.para("Đơn vị chia là video (tệp video và nhãn luôn cùng một tập), phân tầng theo modality × lớp, tỷ lệ 70/15/15, seed chọn bằng tìm kiếm tất định (cơ sở 20261011, chọn 20261217) để cân bằng thêm theo số frame, số hộp và khoảng cách. Không chia theo frame. Tăng cường dữ liệu chỉ áp dụng trên train; ngưỡng chọn trên val; test khóa tới đánh giá cuối. Giao thức split được cả hai thành viên duyệt (ADR-0003; An 26/10, Quang 27/10/2026) và đóng băng tại tag w04 với SHA-256 7e39940e…; từ sau tag này split không thay đổi.")
        c.table("Split v1 (data/splits/video_split_v1.csv).", ["Tập", "Video", "Frame", "Frame có hộp"],
                [["train", 454, "142.187", "136.013"], ["val", 98, "30.545", "28.943"], ["test", 98, "30.596", "29.596"]], [3, 3, 4, 4], key="t_split")
        c.image(a.fig_w2 / "fig_split_v1_by_class.png", 11, "Số video theo lớp trong từng tập của split v1.", "f_split")
        c.para("Nguy cơ rò rỉ còn lại: 562 cặp video khác tập có khung hình gần giống theo dHash (437 cặp cùng lớp) do dữ liệu thu ở ít vị trí; 123/279 cặp video hồng ngoại – khả kiến cùng lớp và số thứ tự nằm khác tập nhưng chưa có bằng chứng là cùng sự kiện. Vì vậy báo cáo không khẳng định tập test là \"cảnh chưa thấy\".")
        c.heading3("3.2.5 Dữ liệu huấn luyện cho detector (tuần 3–4)")
        c.para(f"Theo ADR-0004, baseline A chỉ dùng ảnh khả kiến (640×512), bốn lớp Airplane = 0, Bird = 1, Drone = 2, Helicopter = 3, lấy 1 frame trên 10 frame, chỉ xuất train và val. Quá trình chọn video và kết quả xuất được thể hiện ở Hình {R('f_funnel')}, Hình {R('f_yolo')} và Bảng {R('t_yolo')}. Mọi cấu hình so sánh ở tuần 4 dùng đúng tập này (cùng fingerprint).")
        c.image(a.fig_w3 / "fig_w3_data_funnel.png", 15, "Từ video khả kiến tới tập huấn luyện e1-yolo-v1 (Kaggle run 03b, inclusion_decisions.csv).", "f_funnel")
        c.image(a.fig_w3 / "fig_w3_yolo_images.png", 15.5, "Số ảnh theo lớp và cỡ hộp bao trong tập e1-yolo-v1 (dataset_stats.csv).", "f_yolo")
        c.table("Tập e1-yolo-v1 (dataset_card.json, fingerprint d0ac7e23…).", ["Tập", "Video", "Ảnh", "Ảnh có hộp", "Ảnh không nhãn", "Hộp nhỏ / vừa / lớn"],
                [["train", 178, "5.667", "5.544", 123, "3.041 / 1.894 / 609"], ["val", 38, "1.202", "1.162", 40, "475 / 574 / 113"]],
                [2.0, 2.0, 2.4, 2.6, 2.6, 4.6], key="t_yolo",
                note="Giới hạn: tập val chỉ còn 3 video Bird (73 ảnh có hộp) nên AP lớp Bird trên val dao động lớn; 77/242 video khả kiến thuộc train và val chưa được xem bằng mắt. Ảnh không nhãn chủ yếu là frame 0 của video dư một mục và đoạn thiếu nhãn, không phải ảnh nền trời trống (mục 5.4).")

    # ======================================================================== 5.1, 5.3, 5.4
    def s51(c):
        c.para(f"Mọi bước xử lý dữ liệu thật và huấn luyện chạy trên Kaggle; mỗi lần chạy ghi phiên bản thư viện, phần cứng, commit mã nguồn và SHA-256 của dữ liệu đầu vào. Bảng {R('t_env')} tóm tắt môi trường các lần huấn luyện tuần 3 và tuần 4.")
        c.table("Môi trường huấn luyện (env.json, stage_status.json của Kaggle run 04 và run 09).", ["Thành phần", "Giá trị"],
                [["Phần cứng", "1 × NVIDIA Tesla T4 15 GB (phiên Kaggle có 2 GPU, Ultralytics dùng GPU 0); cùng loại GPU cho mọi mô hình so sánh"],
                 ["Phần mềm", "Python 3.13; PyTorch 2.11.0+cu128 [9]; Ultralytics 8.4.183 [12]; OpenCV 4.14 [8]"],
                 ["Mã nguồn", "Run 04 (baseline A): commit 9597fce. Run 09 (5 cấu hình): commit 1a71f5b; notebook scripts/kaggle/notebooks/w4_run09_train_compare.ipynb; phiên 1–2 tài khoản Kaggle của Quang, phiên 3 (RT-DETR-l) tài khoản của An"],
                 ["Dữ liệu", "e1-yolo-v1, fingerprint d0ac7e23…, đóng gói một tệp zip, kiểm SHA-256 từng ảnh trước khi huấn luyện"],
                 ["Tái lập", "seed 20261013, deterministic = true; 50 epoch, patience 15; weights best.pt/last.pt lưu Google Drive kèm SHA-256 (weights_manifest.json)"]],
                [3.4, 12.8], key="t_env")

    def s53(c):
        c.heading3("5.3.1 Baseline A (tuần 3)")
        c.para(f"Baseline A là YOLOv8n khởi tạo từ trọng số COCO, ảnh vào 640, tối đa 50 epoch, dừng sớm khi fitness trên val không cải thiện sau 15 epoch (giao thức: docs/w3/training_protocol.md). Toàn bộ số liệu dưới đây đo trên tập validation; tập test vẫn khóa. Vì val vừa dùng để dừng sớm và chọn checkpoint, các số này lạc quan và không được so trực tiếp với chỉ tiêu trên test ở Bảng {R('t_targets')}.")
        c.para(f"Quá trình huấn luyện dừng ở epoch 36, checkpoint tốt nhất ở epoch 21, tổng thời gian khoảng 27 phút (Hình {R('f_lc')}). Loss trên train giảm đều trong khi loss hộp trên val không giảm thêm sau khoảng epoch 12–20 và mAP trên val đạt đỉnh ở epoch 21, cho thấy mô hình bắt đầu khớp quá mức với tập train; cơ chế dừng sớm giữ checkpoint tại đỉnh.")
        c.image(a.fig_w3 / "fig_w3_learning_curves.png", 15.5, "Learning curve của baseline A: box loss trên train và val, mAP trên val theo epoch (train/results.csv, Kaggle run 04).", "f_lc")
        c.para(f"Kết quả theo lớp ở Bảng {R('t_baseline')} và Hình {R('f_perclass')}. AP@0.5 và AP@0.5:0.95 tính trên toàn bộ đường precision–recall với ngưỡng confidence 0,001. Cột P và R là giá trị Ultralytics báo tại một ngưỡng confidence chung cho mọi lớp, chọn để F1 trung bình các lớp lớn nhất; đây không phải ngưỡng vận hành.")
        c.table("Kết quả baseline A trên val (baseline_A_val_metrics.json).", ["Lớp", "P", "R", "AP@0.5", "AP@0.5:0.95"],
                [["Airplane", "0,764", "0,672", "0,677", "0,306"], ["Bird", "0,729", "0,849", "0,865", "0,382"],
                 ["Drone", "0,838", "0,871", "0,809", "0,266"], ["Helicopter", "0,921", "0,867", "0,879", "0,414"],
                 ["Tất cả", "0,813", "0,815", "0,807", "0,342"]], [3.4, 2.6, 2.6, 3.4, 3.4], key="t_baseline")
        c.image(a.fig_w3 / "fig_w3_per_class_ap.png", 13.5, "AP@0.5 và AP@0.5:0.95 theo lớp trên val (baseline_A_val_per_class.csv).", "f_perclass")
        c.para(f"Ngưỡng vận hành được chọn theo giao thức: duyệt confidence 0,05–0,90 bước 0,05, chọn ngưỡng có F1 lớp Drone lớn nhất trên val, đồng hạng thì lấy ngưỡng cao hơn. Ngưỡng chọn được là 0,25 (Bảng {R('t_op')}). Ngưỡng có F1 trung bình 4 lớp lớn nhất là 0,35 (F1 = 0,814), chỉ dùng để tham khảo.")
        c.table("Ngưỡng vận hành chọn trên val (operating_points.csv, Kaggle run 05).", ["Confidence", "Drone P", "Drone R", "Drone F1", "4 lớp P", "4 lớp R", "F1 trung bình"],
                [["0,20", "0,794", "0,884", "0,836", "0,786", "0,843", "0,799"],
                 ["0,25 (chọn)", "0,832", "0,882", "0,856", "0,814", "0,837", "0,808"],
                 ["0,30", "0,834", "0,878", "0,855", "0,826", "0,826", "0,811"],
                 ["0,35", "0,837", "0,870", "0,853", "0,835", "0,818", "0,814"]],
                [2.6, 2.0, 2.0, 2.0, 2.0, 2.0, 2.6], size=8.5, key="t_op")
        # --- W4
        c.heading3("5.3.2 So sánh các cấu hình detector (tuần 4)")
        c.para("Nhóm không mặc định chọn một mô hình rồi chỉ huấn luyện mô hình đó. Năm cấu hình mới được huấn luyện trên cùng tập e1-yolo-v1, cùng seed, cùng ngân sách 50 epoch / patience 15 và cùng phiên bản thư viện; mỗi cấu hình chỉ đổi một yếu tố so với mốc gần nhất để biết khác biệt đến từ đâu (docs/w4/training_protocol_w4.md mục 4). Mỗi mô hình được phân tích bằng cùng script và cùng cách chọn ngưỡng (F1 lớp Drone lớn nhất trên val). Luật chọn mô hình được ghi vào giao thức trước khi có kết quả (commit 2ae4c50, PR #51, 27/10/2026).")
        rows = []
        for m in ORDER:
            r = CMP[m]
            rows.append([m, CHANGE[m], r["imgsz"], vn(r["map50"]), vn(r["map50_95"]), vn(r["ap50_95_Drone"]),
                         f"{vn(r['Drone_F1_op'])} ({vn(r['conf_op'], 2)})", vn(r["inference_ms"], 2), f"{r['epochs_run']} ({r['best_epoch']})",
                         "OK" if r["train_health"] == "OK" else "Không hợp lệ"])
        sds = [float(CMP[m]["val_map50_95_epoch_sd"]) for m in ORDER if CMP[m]["train_health"] == "OK"]
        c.table("Sáu cấu hình detector trên val (results/W04/comparison_w4.csv, tạo bằng scripts/reporting/build_comparison.py).",
                ["Cấu hình", "Đổi so với mốc", "imgsz", "mAP@0.5", "mAP@0.5:0.95", "AP@0.5:0.95 Drone", "F1 Drone (ngưỡng)", "ms/ảnh", "Epoch (best)", "Train"],
                rows, [2.7, 2.6, 1.0, 1.3, 1.5, 1.5, 1.7, 1.1, 1.3, 1.4], size=7.5, key="t_cmp",
                note=f"Số đo trên val (lạc quan). ms/ảnh: thời gian suy luận trong bước val trên T4, chưa phải FPS pipeline. rtdetr_l_640 không hợp lệ: loss thành NaN từ epoch 3 (train/results.csv). Độ lệch chuẩn mAP@0.5:0.95 trên val giữa các epoch (bỏ 5 epoch đầu) là {vn(min(sds), 3)}–{vn(max(sds), 3)} tùy mô hình.")
        c.image(a.fig_w4 / "fig_w4_accuracy_vs_latency.png", 15, "mAP@0.5:0.95 trên val và thời gian suy luận; vạch đứt là giới hạn 25 ms/ảnh của luật chọn (comparison_w4.csv).", "f_acc_lat")
        c.image(a.fig_w4 / "fig_w4_ap_by_class.png", 15.5, "AP@0.5 theo lớp của sáu cấu hình trên val (comparison_w4.csv).", "f_ap_class")
        A, Y = CMP["baseline_A"], CMP["yolo11n_640"]
        c.para(f"Áp dụng luật chọn đặt trước (Bảng {R('t_cmp')}, Hình {R('f_acc_lat')}):")
        c.bullets([
            f"Ràng buộc tốc độ ≤ 25 ms/ảnh loại rtdetr_l_640 ({vn(CMP['rtdetr_l_640']['inference_ms'], 1)} ms); mô hình này cũng không hợp lệ do lỗi huấn luyện.",
            f"mAP@0.5:0.95 cao nhất là yolo11n_640 ({vn(Y['map50_95'], 4)}), tiếp theo là baseline_A ({vn(A['map50_95'], 4)}). Chênh lệch {vn(float(Y['map50_95']) - float(A['map50_95']), 4)} nhỏ hơn 0,01 nên được coi là hòa.",
            f"Khi hòa, luật chọn mô hình nhanh hơn: baseline_A ({vn(A['inference_ms'], 3)} ms) so với yolo11n_640 ({vn(Y['inference_ms'], 3)} ms). Kết quả: giữ baseline A (YOLOv8n @640) làm detector cho tuần 5 (ADR-0007)."])
        c.para(f"Chênh lệch tốc độ giữa hai mô hình chỉ khoảng {vn(float(Y['inference_ms']) - float(A['inference_ms']), 3)} ms, nằm trong sai số của một lần đo; nếu coi tốc độ cũng hòa thì tiêu chí phụ (F1 lớp Drone) sẽ chọn YOLO11n ({vn(Y['Drone_F1_op'])} so với {vn(A['Drone_F1_op'])}). Nhóm không đổi luật sau khi xem số; kết luận được ghi là hai mô hình ngang nhau trong phạm vi một seed và sẽ chạy lại ít nhất ba seed trước khi đóng băng tính năng (tuần 11). Thay detector chỉ là thay tệp weights, không đổi giao diện detector → tracker, nên lựa chọn này không chặn tuần 5.")

    def s54(c):
        c.heading3("5.4.1 Baseline A (tuần 3)")
        c.para("Phân tích lỗi thực hiện tại ngưỡng 0,25 trên val, khớp dự đoán với nhãn khi cùng lớp và IoU ≥ 0,5 (scripts/kaggle/w3_analyze_baseline.py, Kaggle run 05). Bốn nhận xét chính:")
        c.rich([("Bỏ sót chiếm phần lớn lỗi, nhầm lớp ít. ", True), ("Khi bỏ điều kiện cùng lớp, số hộp bị bỏ sót là Airplane 83/289, Drone 58/511, Helicopter 30/285, Bird 2/73; số hộp bị gán sai lớp chỉ từ 1 đến 6 ở mỗi cặp lớp (class_confusion.csv).", False)])
        c.rich([("Recall không giảm đều theo cỡ vật thể. ", True), (f"Hộp nhỏ hơn 32×32 px có recall 0,863, không thấp hơn hộp vừa (0,803) (Hình {R('f_recall_size')}). Recall thấp của Airplane cỡ vừa (0,563) tập trung ở ba video: V_AIRPLANE_027 (0/33), V_AIRPLANE_007 (8/30), V_AIRPLANE_005 (16/33) (recall_by_video.csv), nên đây là lỗi theo cảnh hơn là theo kích thước. Helicopter cỡ nhỏ có recall thấp nhất (0,667, 60 hộp).", False)])
        c.image(a.fig_w3 / "fig_w3_recall_by_size.png", 15, "Recall theo lớp và cỡ hộp tại confidence 0,25 trên val; bỏ các ô có dưới 5 hộp (recall_by_size.csv, Kaggle run 05).", "f_recall_size")
        c.rich([("Định vị hộp còn kém với vật thể nhỏ. ", True), ("Khoảng cách giữa AP@0.5 (0,809) và AP@0.5:0.95 (0,266) lớn nhất ở lớp Drone, nghĩa là mô hình tìm được vật thể nhưng hộp chưa khớp chặt. Hai nguyên nhân có thể là nhãn lệch một frame ở video dư một mục và độ rộng hộp nhãn không đồng đều (mục 3.2.3).", False)])
        c.rich([("Tập val không có ảnh nền trống thật. ", True), ("Cả 40 ảnh val không có nhãn đều có dự đoán ở ngưỡng 0,25 (negatives_fp.json), nhưng đây không phải dự đoán sai trên nền trời: 20 ảnh là frame 0 của video dư một mục (17 Drone, 3 Bird) — nơi review thấy vật thể nhưng mục nhãn rỗng — và 20 ảnh là đoạn thiếu nhãn f110–f300 của V_BIRD_041. Vì vậy chưa đo được tỷ lệ cảnh báo giả trên nền trời; việc này cần video không có vật thể (tuần 7, hard negatives).", False)])
        c.heading3("5.4.2 Kết quả so sánh tuần 4")
        A, B, A9, AU, RT = (CMP[m] for m in ("baseline_A", "detector_B", "baseline_A_960", "baseline_A_aug", "rtdetr_l_640"))
        c.rich([("Tăng imgsz lên 960 không giúp. ", True), (f"baseline_A_960 đạt mAP@0.5:0.95 {vn(A9['map50_95'])}, thấp hơn baseline A ({vn(A['map50_95'])}), trong khi chậm gấp {vn(float(A9['inference_ms']) / float(A['inference_ms']), 1)} lần. Mọi ảnh trong e1-yolo-v1 có kích thước gốc 640×512 (yolo_manifest.csv.gz), nên imgsz 960 chỉ phóng to ảnh chứ không thêm chi tiết. Muốn có thêm chi tiết cho vật thể nhỏ cần nguồn ảnh có độ phân giải cao hơn, không phải tăng imgsz.", False)])
        c.rich([("Model lớn hơn cũng không giúp trên lớp Drone. ", True), (f"detector_B (YOLOv8s @960) đạt {vn(B['map50_95'])}, ngang baseline_A_960 khi chỉ đổi cỡ model; AP@0.5 lớp Helicopter cao nhất ({vn(B['ap50_Helicopter'])}) nhưng lớp Drone thấp nhất ({vn(B['ap50_Drone'])}), và thời gian suy luận {vn(B['inference_ms'], 1)} ms/ảnh.", False)])
        c.rich([("Giảm scale augmentation làm kết quả kém hơn. ", True), (f"baseline_A_aug (scale 0,3) đạt {vn(AU['map50_95'])}, thấp hơn baseline A {vn(float(A['map50_95']) - float(AU['map50_95']), 3)} (vượt ngưỡng hòa); AP@0.5 lớp Bird giảm từ {vn(A['ap50_Bird'])} xuống {vn(AU['ap50_Bird'])} và Airplane từ {vn(A['ap50_Airplane'])} xuống {vn(AU['ap50_Airplane'])}. Thay đổi này không được giữ.", False)])
        c.rich([("RT-DETR-l không hợp lệ. ", True), (f"Loss thành NaN ở epoch 3 (cuối giai đoạn warmup, amp bật); từ đó mAP trên val bằng 0 và checkpoint \"tốt nhất\" là epoch {RT['best_epoch']}, gần như vẫn là trọng số COCO. Số trong Bảng {R('t_cmp')} không phản ánh năng lực của RT-DETR. Mô hình không được huấn luyện lại để chọn vì đã vượt giới hạn tốc độ; nếu cần cho phần so sánh, chạy lại với amp tắt, AdamW và lr0 = 10⁻⁴, ghi vào giao thức.", False)])
        c.rich([("Val nhiễu, chênh lệch nhỏ không đáng tin. ", True), ("mAP@0.5:0.95 trên val dao động giữa các epoch với độ lệch chuẩn 0,02–0,04, và \"epoch tốt nhất\" là giá trị lớn nhất của một đường cong nhiễu. Vì vậy chênh lệch dưới khoảng 0,02 giữa các mô hình chưa nên coi là khác biệt thật; cần nhiều seed hoặc bootstrap theo video.", False)])
        c.rich([("Ưu tiên cải thiện dữ liệu trước khi thử mô hình lớn hơn. ", True), ("Luật 4 của giao thức được kích hoạt: AP@0.5:0.95 lớp Drone của mọi cấu hình chỉ 0,23–0,28 và recall hộp nhỏ không cải thiện rõ so với baseline A. Tuần 7 ưu tiên: quyết định chiều lệch nhãn bằng ADR mới, sửa video nhãn lỗi sau khi thống nhất tiêu chí review, đo độ biến thiên độ rộng hộp nhãn, và bổ sung ảnh nền trống / hard negative.", False)])

    fill(57, mo_dau); fill(63, s11); fill(66, s12); fill(69, s13); fill(72, s14); fill(75, s15)
    fill(81, s21); fill(84, s22)
    fill(96, s32); fill(123, s51); fill(129, s53); fill(132, s54)

    replace_with_field(40, 'TOC \\o "1-3" \\h \\z \\u', "Nhấn F9 trong Word để cập nhật mục lục.")
    replace_with_field(46, 'TOC \\h \\z \\c "Hình"', "Nhấn F9 để cập nhật danh sách hình.")
    replace_with_field(51, 'TOC \\h \\z \\c "Bảng"', "Nhấn F9 để cập nhật danh sách bảng.")

    t = d.tables[2]
    extra = [("ADR", "Architecture Decision Record – bản ghi quyết định kỹ thuật"), ("AP", "Average Precision"),
             ("CVAT", "Computer Vision Annotation Tool – công cụ gán nhãn ảnh"), ("DETR", "DEtection TRansformer"),
             ("FPS", "Frames per second – số khung hình mỗi giây"), ("HOTA", "Higher Order Tracking Accuracy"),
             ("IDF1", "ID F1 score"), ("IoU", "Intersection over Union"), ("IR", "Infrared – hồng ngoại"),
             ("mAP", "mean Average Precision"), ("MOT", "Multi-Object Tracking – theo dõi đa đối tượng"),
             ("MVP", "Minimum Viable Product – sản phẩm khả dụng tối thiểu"), ("NMS", "Non-Maximum Suppression"),
             ("ReID", "Re-identification – tái nhận dạng"), ("ROI", "Region of Interest – vùng giám sát"),
             ("SORT", "Simple Online and Realtime Tracking"), ("UAV", "Unmanned Aerial Vehicle – phương tiện bay không người lái")]
    last = t.rows[-1]; last.cells[0].text, last.cells[1].text = extra[0]
    for k, v in extra[1:]:
        t._tbl.append(copy.deepcopy(last._tr)); row = t.rows[-1]; row.cells[0].text = k; row.cells[1].text = v

    REFS = [
        "[1] Ultralytics, “Multi-object tracking with Ultralytics YOLO,” Ultralytics Docs. [Online]. Available: https://docs.ultralytics.com/modes/track/ (accessed Oct. 21, 2026).",
        "[2] Y. Zhang, P. Sun, Y. Jiang, D. Yu, F. Weng, Z. Yuan, P. Luo, W. Liu, and X. Wang, “ByteTrack: Multi-object tracking by associating every detection box,” in Proc. Eur. Conf. Comput. Vis. (ECCV), 2022. [Online]. Available: https://arxiv.org/abs/2110.06864",
        "[3] N. Aharon, R. Orfaig, and B.-Z. Bobrovsky, “BoT-SORT: Robust associations multi-pedestrian tracking,” arXiv preprint arXiv:2206.14651, 2022.",
        "[4] Y. Cao et al., “VisDrone-DET2021: The vision meets drone object detection challenge results,” in Proc. IEEE/CVF Int. Conf. Comput. Vis. Workshops (ICCVW), 2021.",
        "[5] G. Chen et al., “VisDrone-MOT2021: The vision meets drone multiple object tracking challenge results,” in Proc. IEEE/CVF Int. Conf. Comput. Vis. Workshops (ICCVW), 2021.",
        "[6] Y. Zhao et al., “DETRs beat YOLOs on real-time object detection,” in Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR), 2024. [Online]. Available: https://arxiv.org/abs/2304.08069",
        "[7] D. Du et al., “The unmanned aerial vehicle benchmark: Object detection and tracking,” in Proc. Eur. Conf. Comput. Vis. (ECCV), 2018. [Online]. Available: https://arxiv.org/abs/1804.00518",
        "[8] OpenCV, “OpenCV 4.x documentation.” [Online]. Available: https://docs.opencv.org/4.x/ (accessed Oct. 21, 2026).",
        "[9] PyTorch, “PyTorch documentation.” [Online]. Available: https://pytorch.org/docs/stable/index.html (accessed Oct. 21, 2026).",
        "[10] NVIDIA, “TensorRT documentation.” [Online]. Available: https://docs.nvidia.com/deeplearning/tensorrt/ (accessed Oct. 21, 2026).",
        "[11] F. Svanström, F. Alonso-Fernandez, and C. Englund, “A dataset for multi-sensor drone detection,” Data in Brief, vol. 39, Art. no. 107521, Dec. 2021. Dataset: https://github.com/DroneDetectionThesis/Drone-detection-dataset",
        "[12] G. Jocher, J. Qiu, and A. Chaurasia, “Ultralytics YOLO,” 2023. [Online]. Available: https://github.com/ultralytics/ultralytics (AGPL-3.0).",
    ] + REFS_AN
    ref_ps = [p for p in d.paragraphs if p.text[:4].startswith("[") and p.text[1:2].isdigit()]
    guide = next(p for p in d.paragraphs if p.text.startswith("[Dùng một chuẩn thống nhất"))
    anchor = ref_ps[-1]
    for i, p in enumerate(ref_ps):
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        p.add_run(REFS[i])
    cur = Cursor(anchor)
    for txt in REFS[len(ref_ps):]:
        q = cur.para(txt); q.style = anchor.style
        if anchor._p.pPr is not None:
            q._p.remove(q._p.get_or_add_pPr()); q._p.insert(0, copy.deepcopy(anchor._p.pPr))
    guide._p.getparent().remove(guide._p)
    st = d.settings.element
    uf = OxmlElement("w:updateFields"); uf.set(qn("w:val"), "true"); st.append(uf)
    return d, keys, dict(n)


_, k1, _ = build({})
doc, k2, counts = build(k1)
if k1 != k2:
    raise SystemExit("so hinh/bang khong on dinh giua hai luot")
a.out.parent.mkdir(parents=True, exist_ok=True)
doc.save(a.out)
print("saved", a.out, counts)
