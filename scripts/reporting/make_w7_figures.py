#!/usr/bin/env python3
"""Hinh cho bao cao W7 va version v0.7 (doc file ket qua, khong nhap tay so lieu).

    python scripts/reporting/make_w7_figures.py --out results/W07

- fig_w7_postproc.png: ID switch / 1000 frame GT theo lop cho V0/V1/V2 (ADR-0012),
  results/W07/postproc/V*/summary.json.
- fig_w7_idsw_by_video.png: ID switch theo video, V0 va V2 (bien the duoc chon), chi video co ID switch o V0,
  results/W07/postproc/V*/per_video_tracking.csv.
- fig_w7_confusion.png: ma tran nham V0 muc anh, conf 0,25, ghep tham lam theo conf, bo 40 anh loi nhan
  (V0_none/summary.json -> detection.confusion; PR #108 doi chieu khop).
- fig_w7_pipeline.png: so do pipeline muc 3.3 (nhan lay tu Mermaid trong docs/w7/chuong3_3.3_3.4_nhap_An.md, ve 2 hang).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("make_w7_figures")
PP = ROOT / "results/W07/postproc"
VARS = [("V0_none", "V0: hiện tại (NMS cùng lớp 0,7)", "#eb6834"),
        ("V1_agnostic_nms", "V1: NMS không phân lớp 0,5", "#9a9a92"),
        ("V2_nms_iou", "V2: NMS cùng lớp 0,5 (chọn)", "#2a78d6")]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3dd"
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)


def summ(d: str) -> dict:
    return json.loads((PP / d / "summary.json").read_text(encoding="utf-8"))


def postproc_figure(out: Path, plt) -> None:
    cats = ["all"] + CLASSES
    S = {d: summ(d)["tracking"] for d, _, _ in VARS}
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    w = 0.26
    for j, (d, lab, c) in enumerate(VARS):
        for i, k in enumerate(cats):
            v = float(S[d][k]["idsw_per_1000_gt_frames"])
            xi = i + (j - 1) * (w + 0.02)
            ax.bar(xi, v, width=w, color=c, label=lab if i == 0 else None)
            ax.text(xi, v, f"{v:.1f}".replace(".", ","), ha="center", va="bottom", fontsize=6.8, color=INK)
    nv = {k: S["V0_none"][k]["videos"] for k in cats}
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels([("Tất cả" if k == "all" else k) + f" ({nv[k]})" for k in cats], fontsize=8, color=INK)
    ax.set_ylim(0, max(float(S[d][k]["idsw_per_1000_gt_frames"]) for d, _, _ in VARS for k in cats) * 1.25)
    ax.set_ylabel("ID switch / 1000 frame GT", fontsize=8, color=MUTED)
    ax.set_title("Hậu xử lý detection rồi ByteTrack-e1 offline (val, số video trong ngoặc; GT dẫn xuất)", loc="left", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right"); style(ax)
    fig.tight_layout(); fig.savefig(out, dpi=200, facecolor="white"); plt.close(fig)


def per_video(d: str) -> dict:
    with (PP / d / "per_video_tracking.csv").open(encoding="utf-8") as fh:
        return {r["video_id"]: r for r in csv.DictReader(fh)}


def idsw_by_video_figure(out: Path, plt) -> None:
    v0, v2 = per_video("V0_none"), per_video("V2_nms_iou")
    vids = sorted((k for k in v0 if int(v0[k]["id_switches"]) > 0), key=lambda k: -int(v0[k]["id_switches"]))
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    y = list(range(len(vids)))[::-1]
    for yi, k in zip(y, vids):
        a, b = int(v0[k]["id_switches"]), int(v2[k]["id_switches"])
        ax.plot([b, a], [yi, yi], color=GRID, lw=2, zorder=1)
        ax.scatter([a], [yi], s=18, color=VARS[0][2], zorder=2, label="V0" if yi == y[0] else None)
        ax.scatter([b], [yi], s=18, color=VARS[2][2], zorder=3, label="V2 (chọn)" if yi == y[0] else None)
    ax.set_yticks(y); ax.set_yticklabels([k.replace("V_", "") for k in vids], fontsize=6.5, color=INK)
    ax.set_xlabel("số ID switch trong video", fontsize=8, color=MUTED)
    ax.set_title(f"ID switch theo video ({len(vids)} video có ID switch ở V0; không video nào tăng ở V2)", loc="left", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=7); ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(out, dpi=200, facecolor="white"); plt.close(fig)


def confusion_figure(out: Path, plt) -> None:
    det = summ("V0_none")["detection"]; m = det["confusion"]
    rows, cols = CLASSES + ["nen"], CLASSES + ["bo_sot"]
    rl = CLASSES + ["Nền (không GT)"]; cl = CLASSES + ["Bỏ sót"]
    M = [[m.get(f"{r}->{c}", 0) if not (r == "nen" and c == "bo_sot") else None for c in cols] for r in rows]
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    mx = max(v for row in M for v in row if v is not None)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ["#f4f8fd", "#2a78d6", "#0b3f80"])
    img = [[(v if v is not None else 0) for v in row] for row in M]
    ax.imshow(img, cmap=cmap, vmin=0, vmax=mx, aspect="auto")
    for i, row in enumerate(M):
        for j, v in enumerate(row):
            if v is None:
                ax.text(j, i, "—", ha="center", va="center", fontsize=8, color=MUTED)
            else:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=8, color="white" if v > mx * 0.45 else INK)
    ax.set_xticks(range(len(cl))); ax.set_xticklabels(cl, fontsize=7.5, color=INK)
    ax.set_yticks(range(len(rl))); ax.set_yticklabels(rl, fontsize=7.5, color=INK)
    ax.set_xlabel("dự đoán", fontsize=8, color=MUTED); ax.set_ylabel("nhãn (GT)", fontsize=8, color=MUTED)
    ax.set_title(f"Ma trận nhầm V0, conf 0,25, {det['images']} ảnh val (bỏ {det['ignored_images']} ảnh lỗi nhãn)", loc="left", fontsize=8.5, color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout(); fig.savefig(out, dpi=200, facecolor="white"); plt.close(fig)


def pipeline_figure(out: Path, plt) -> None:
    """Ve lai so do Mermaid cua An thanh 2 hang x 4 o (ban LR mot hang qua rong cho trang A4); nhan lay tu ban nhap."""
    md = (ROOT / "docs/w7/chuong3_3.3_3.4_nhap_An.md").read_text(encoding="utf-8")
    src = re.search(r"```mermaid\n(.+?)```", md, re.S)
    if not src:
        raise ValueError("khong thay so do Mermaid trong ban nhap 3.3")
    nodes = list(dict(re.findall(r'([A-Z])\["(.+?)"\]', src.group(1))).items())
    order = [n for n, _ in nodes]
    edges = re.findall(r'([A-Z])(?:\["[^"]*"\])?\s*-->\s*([A-Z])', src.group(1))
    if [a for a, _ in edges] != order[:-1] or [b for _, b in edges] != order[1:] or len(order) != 8:
        raise ValueError("so do 3.3 khong con la chuoi 8 buoc tuyen tinh; cap nhat ham ve")
    labels = [t.replace("<br/>", "\n") for _, t in nodes]
    fig, ax = plt.subplots(figsize=(6.8, 2.6)); ax.set_xlim(0, 4); ax.set_ylim(0, 2); ax.axis("off")
    pos = [(i + 0.5, 1.5) for i in range(4)] + [(3.5 - i, 0.5) for i in range(4)]
    bw, bh = 0.86, 0.66
    from matplotlib.patches import FancyBboxPatch
    for i, ((x, y), t) in enumerate(zip(pos, labels)):
        hi = "ADR-0012" in t
        ax.add_patch(FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh, boxstyle="round,pad=0.01,rounding_size=0.04",
                                    fc="#eaf2fc" if hi else "#f5f5f2", ec="#2a78d6" if hi else MUTED, lw=0.9))
        ax.text(x, y, t, ha="center", va="center", fontsize=6.6, color=INK, wrap=True)
        ax.text(x - bw / 2 + 0.03, y + bh / 2 - 0.05, str(i + 1), ha="left", va="top", fontsize=6, color=MUTED)
    for (x1, y1), (x2, y2) in zip(pos[:-1], pos[1:]):
        if y1 == y2:
            s = 1 if x2 > x1 else -1
            ax.annotate("", (x2 - s * bw / 2, y2), (x1 + s * bw / 2, y1), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.9))
        else:
            ax.annotate("", (x2, y2 + bh / 2), (x1, y1 - bh / 2), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.9))
    fig.tight_layout(pad=0.2); fig.savefig(out, dpi=220, facecolor="white"); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/W07")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a.out.mkdir(parents=True, exist_ok=True)
    postproc_figure(a.out / "fig_w7_postproc.png", plt)
    idsw_by_video_figure(a.out / "fig_w7_idsw_by_video.png", plt)
    confusion_figure(a.out / "fig_w7_confusion.png", plt)
    pipeline_figure(a.out / "fig_w7_pipeline.png", plt)
    LOG.info("ghi %s", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
