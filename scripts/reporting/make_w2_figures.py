#!/usr/bin/env python3
"""Ve 2 hinh cho bao cao W2: so do tong quan bai toan va phan bo split v1 (tu video_split_v1.csv)."""
import argparse, csv
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ap = argparse.ArgumentParser()
ap.add_argument("--split", type=Path, default=Path("data/splits/video_split_v1.csv"))
ap.add_argument("--out", type=Path, default=Path("reports/w2/figures"))
a = ap.parse_args()
a.out.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(10, 3.2)); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 30)
boxes = [("Camera mặt đất\n(video V / IR)", 1), ("Phát hiện\nYOLOv8n / đối chứng", 21), ("Theo dõi\nByteTrack / BoT-SORT", 41),
         ("Vùng giám sát\n(polygon ROI)", 61), ("Cảnh báo + log\n(người xác minh)", 81)]
for t, x in boxes:
    ax.add_patch(FancyBboxPatch((x, 9), 17, 12, boxstyle="round,pad=0.4", fc="#e8f0fe", ec="#1a4fa0"))
    ax.text(x + 8.5, 15, t, ha="center", va="center", fontsize=9)
for x in (18.6, 38.6, 58.6, 78.6):
    ax.annotate("", xy=(x + 2.4, 15), xytext=(x, 15), arrowprops=dict(arrowstyle="->", color="#333"))
ax.text(50, 3, "Lớp: Drone / Bird / Airplane / Helicopter  •  Đánh giá: mAP, P/R, FPS, độ trễ, cảnh báo giả (W3–W11)", ha="center", fontsize=9)
ax.text(50, 27, "Chu trình xử lý đề xuất (W2: dữ liệu + nhãn + split; các khối còn lại thực hiện ở W3–W8)", ha="center", fontsize=10, weight="bold")
fig.savefig(a.out / "fig_overview.png", dpi=170, bbox_inches="tight"); plt.close(fig)

rows = list(csv.DictReader(a.split.open(encoding="utf-8")))
classes = ["Airplane", "Bird", "Drone", "Helicopter"]
fig, ax = plt.subplots(figsize=(7, 3.4))
bottom = [0] * 4
for sp, col in (("train", "#4c78a8"), ("val", "#f58518"), ("test", "#54a24b")):
    vals = [sum(1 for r in rows if r["split"] == sp and r["class_name"] == c) for c in classes]
    ax.bar(classes, vals, bottom=bottom, label=sp, color=col)
    bottom = [b + v for b, v in zip(bottom, vals)]
ax.set_ylabel("Số video"); ax.legend(); ax.set_title("Split v1 theo video (454/98/98)", fontsize=10)
fig.savefig(a.out / "fig_split_v1_by_class.png", dpi=170, bbox_inches="tight")
print(Counter(r["split"] for r in rows))
