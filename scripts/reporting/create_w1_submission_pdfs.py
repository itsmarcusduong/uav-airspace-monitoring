"""Generate the two W1 PDF submission artifacts from verified W1 evidence."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "w1"
FONT = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


def register_fonts():
    pdfmetrics.registerFont(TTFont("ArialVN", str(FONT)))
    pdfmetrics.registerFont(TTFont("ArialVNBold", str(FONT_BOLD)))


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="ArialVNBold", fontSize=17,
                                leading=21, alignment=TA_CENTER, spaceAfter=10),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName="ArialVN", fontSize=10,
                                   leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceAfter=14),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="ArialVNBold", fontSize=13,
                              leading=16, textColor=colors.HexColor("#17365D"), spaceBefore=10, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="ArialVNBold", fontSize=11,
                              leading=14, textColor=colors.HexColor("#17365D"), spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="ArialVN", fontSize=9.5,
                                leading=13, spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="ArialVN", fontSize=8,
                                 leading=10),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName="ArialVN", fontSize=8.2,
                                leading=10),
        "cellhead": ParagraphStyle("cellhead", parent=base["BodyText"], fontName="ArialVNBold", fontSize=8.2,
                                    leading=10, textColor=colors.white),
    }


def p(text, style):
    return Paragraph(text, style)


def make_table(rows, widths, s):
    converted = []
    for row_i, row in enumerate(rows):
        converted.append([p(str(item), s["cellhead"] if row_i == 0 else s["cell"]) for item in row])
    table = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2F3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFD")]),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("ArialVN", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(2 * cm, 1.2 * cm, "Đồ án E1 - UAV trong vùng trời sân bay")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Trang {doc.page}")
    canvas.restoreState()


def build(path, story):
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm, title=path.stem, author="Nhóm E1")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def weekly_report(s):
    story = [p("BÁO CÁO KẾT QUẢ CÔNG VIỆC TUẦN W1", s["title"]),
             p("Nhóm E1 - Phát hiện, phân loại và theo dõi UAV trong vùng trời sân bay bằng học sâu<br/>Thời gian: 27/09/2026 - 03/10/2026", s["subtitle"])]
    story += [p("1. Kết luận tuần", s["h1"]),
              p("W1 đã chốt bài toán, lớp đối tượng, nguồn dữ liệu chính, quy tắc annotation ban đầu và rủi ro chia dữ liệu. Svanstrom được chọn là nguồn chính cho giai đoạn dữ liệu vì có góc nhìn quan sát UAV từ mặt đất và các lớp gây nhầm lẫn phù hợp. Chưa huấn luyện hay tích hợp tracker trong W1.", s["body"]),
              p("2. Đối chiếu mốc W1", s["h1"]),
              make_table([
                  ["Mốc E1", "Kết quả và minh chứng"],
                  ["Classes, metric, nguồn dataset", "Lớp: Drone, Bird, Airplane, Helicopter. Metrics đã chốt: detection (precision, recall, F1, mAP), tracking (khi có ID hợp lệ), alert và FPS/độ trễ. Xem docs/w1/mvp_specification.md và research_synthesis.md."],
                  ["Quy tắc annotation", "Đã kiểm tra bbox có kích thước dương, nằm trong frame, ánh xạ lớp; index mẫu giữ video_id, frame_index, bbox và label file. Track ID chưa có trong nhãn Svanstrom."],
                  ["Train/val/test", "Đã khóa nguyên tắc chia theo video/chuỗi, không chia frame ngẫu nhiên. Chưa phát hành split cuối vì đây là mốc W2."],
              ], [4.3*cm, 12.7*cm], s),
              p("3. Dữ liệu và kiểm chứng", s["h1"]),
              make_table([
                  ["Hạng mục", "Kết quả W1 đã kiểm chứng"],
                  ["Svanstrom archive", "650 cặp video/nhãn; 365 IR và 285 visible; 203.328 frame đọc được."],
                  ["Nhãn", "Drone 271; Bird 130; Airplane 133; Helicopter 116 theo video có nhãn dương. Có 12 chuỗi không có bbox dương, được loại khỏi mẫu W1 và giữ làm trường hợp absence/negative cho W2."],
                  ["100 mẫu", "100 JPEG từ 100 video khác nhau, lấy theo seed 20261003. Phân bố: Drone 50, Bird 20, Airplane 15, Helicopter 15; 51 IR và 49 visible."],
                  ["Truy vết", "Mỗi mẫu ghi source video, frame index, bbox, class và label file trong data/samples/index_100_frames.csv. Validation script đã chạy thành công."],
              ], [4.3*cm, 12.7*cm], s),
              p("4. Tài liệu và tái lập", s["h1"]),
              p("Các đầu ra có trong workspace: docs/w1/research_sources.md, dataset_survey.md, dataset_decision.md, annotation_notes.md, data_split_risk.md, validation_report.md; data/manifests/dataset_manifest_v1.csv và license_matrix.csv; scripts/dataset/ để kiểm kê, trích mẫu và kiểm tra manifest.", s["body"]),
              p("5. Rủi ro và việc chưa khẳng định", s["h1"]),
              p("Anti-UAV và VisDrone chưa tải xong, và không phải blocker của W1 vì Svanstrom là nguồn chính. Media license của hai nguồn này phải được xác minh trước khi dùng. Svanstrom không cung cấp persistent track ID trong phần nhãn đã giải mã; vì vậy chưa được phép báo cáo HOTA/IDF1. Không có kết quả train, mAP, FPS hay alert metric trong W1.", s["body"]),
              p("6. Việc W2", s["h1"]),
              p("Khóa split theo video/source group; kiểm kê dữ liệu rộng hơn và audit nhãn; xác định phần cứng và protocol; sau đó mới chuẩn hóa nhãn và train baseline ở W3.", s["body"])]
    build(OUT / "E1_W1_bao_cao_ket_qua_tuan.pdf", story)


def project_version(s):
    story = [p("PHIÊN BẢN ĐỒ ÁN CẬP NHẬT W1", s["title"]),
             p("Nghiên cứu và phát triển hệ thống phát hiện và nhận diện UAV/Drone tại khu vực sân bay<br/>Nhóm E1 - Phiên bản 0.1 - 03/10/2026", s["subtitle"])]
    story += [p("1. Mục tiêu và ranh giới", s["h1"]),
              p("Xây dựng nguyên mẫu xử lý video camera mặt đất hoặc tệp video: phát hiện UAV, phân biệt với chim và máy bay có người lái, duy trì track ID, và cảnh báo khi UAV vào polygon vùng giám sát mô phỏng. Hệ thống hỗ trợ quan sát có người xác minh; không quyết định điều hành bay, không can thiệp UAV và không tuyên bố triển khai tại sân bay thực.", s["body"]),
              p("2. MVP đã chốt", s["h1"]),
              make_table([
                  ["Mô-đun", "Quyết định W1"],
                  ["Dữ liệu", "Svanstrom là nguồn chính; video nhìn từ mặt đất. Lớp Drone, Bird, Airplane, Helicopter. Anti-UAV là nguồn bổ sung tiềm năng; VisDrone chỉ tham khảo phương pháp."],
                  ["Phát hiện", "YOLO làm baseline dự kiến; RT-DETR là cấu hình đối chứng khi tài nguyên và license phù hợp. Chưa chọn model cuối."],
                  ["Theo dõi", "ByteTrack là điểm bắt đầu dự kiến; BoT-SORT chỉ đối chiếu khi cần. Không tích hợp ở W1."],
                  ["Cảnh báo", "Ứng viên Drone -> xác nhận 3 detection trong 5 frame -> ROI liên tục >= 0,3 giây -> lưu evidence và chờ người dùng xác minh."],
              ], [4.3*cm, 12.7*cm], s),
              p("3. Dữ liệu và protocol", s["h1"]),
              p("Archive Svanstrom đã được kiểm kê: 650 cặp video/nhãn, 203.328 frame đọc được và 100 mẫu có truy vết. Split sẽ phân theo video/chuỗi hoặc source group, dự kiến 70/15/15, không tách frame liền kề sang các tập khác. Chỉ augmentation train; chọn ngưỡng trên validation; khóa test trước đánh giá cuối.", s["body"]),
              p("4. Đo lường", s["h1"]),
              make_table([
                  ["Nhóm", "Cách báo cáo"],
                  ["Detection", "Precision, recall, F1, mAP@0.5 và mAP@0.5:0.95 theo lớp; thêm phân tầng kích thước bbox."],
                  ["Tracking", "HOTA, IDF1, ID switches chỉ sau khi track ID ground truth được xác thực/bổ sung."],
                  ["Cảnh báo", "Event precision/recall, cảnh báo sai mỗi giờ video không UAV và trade-off với recall."],
                  ["Hiệu năng", "FPS toàn pipeline và p95 latency, kèm phần cứng, model, input size và cấu hình."],
              ], [4.3*cm, 12.7*cm], s),
              p("5. Kế hoạch tiếp theo", s["h1"]),
              p("W2: chốt split, thống kê lớp và chất lượng nhãn. W3: chuẩn hóa nhãn, train baseline và lưu config/weights/PR curve. W5-W7: tracking, ROI và cảnh báo. Các mốc này phù hợp bảng theo dõi E1 của giảng viên hướng dẫn.", s["body"]),
              p("6. Tài liệu truy vết", s["h1"]),
              p("Phiên bản này được đối chiếu với Thuyet_minh_de_tai_UAV_Drone_san_bay.docx, bảng TheoDoi_TienDo_11_Nhom_DonGian_2026updated.xlsm và bộ tài liệu W1 trong docs/w1/. Chi tiết nguồn, license, checksum và kiểm tra mẫu nằm trong manifest, resource inventory và validation report của workspace.", s["body"])]
    build(OUT / "E1_W1_phien_ban_do_an_cap_nhat.pdf", story)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    register_fonts()
    s = styles()
    weekly_report(s)
    project_version(s)
    print(OUT)
