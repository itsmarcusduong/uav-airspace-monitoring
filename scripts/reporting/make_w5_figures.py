#!/usr/bin/env python3
"""Hinh cho bao cao W5 va version v0.5 (doc file ket qua, khong nhap tay so lieu).

    python scripts/reporting/make_w5_figures.py --out results/W05

- fig_w5_seeds.png: mAP@0.5:0.95 va F1 Drone theo seed, baseline A va YOLO11n (results/W05/seed_comparison.csv).
- fig_w5_tracking_by_class.png: ID switch / 1000 frame GT theo lop, ByteTrack-e1 va BoT-SORT-e1, IoU 0,5
  (results/W05/track_comparison.csv).
"""
from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("make_w5_figures")
C1, C2, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1f1f1e", "#6b6a64", "#e4e3dd"


def rows(rel: str) -> list[dict]:
    with (ROOT / rel).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)


def seeds_figure(out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = rows("results/W05/seed_comparison.csv")
    fams = ["baseline_A", "yolo11n_640"]; names = {"baseline_A": "baseline A (YOLOv8n)", "yolo11n_640": "YOLO11n"}
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7))
    for ax, col, title in ((axes[0], "map50_95", "mAP@0.5:0.95 (val)"), (axes[1], "Drone_F1_op", "F1 lớp Drone tại ngưỡng vận hành (val)")):
        for i, (fam, c) in enumerate(zip(fams, (C1, C2))):
            ys = [float(x[col]) for x in r if x["family"] == fam]
            ax.scatter([i] * len(ys), ys, s=46, color=c, edgecolor="white", linewidth=2, zorder=3)
            m = sum(ys) / len(ys)
            ax.hlines(m, i - 0.22, i + 0.22, color=c, lw=2, zorder=2)
            ax.text(i + 0.26, m, f"TB {m:.3f}", va="center", fontsize=8, color=INK)
        ax.set_xticks([0, 1]); ax.set_xticklabels([names[f] for f in fams], fontsize=8, color=INK)
        ax.set_xlim(-0.5, 1.8); ax.set_title(title, loc="left", fontsize=9, color=INK)
        style(ax)
    fig.text(0.01, 0.01, "Mỗi chấm là một seed (20261013, 20261029, 20261030); gạch ngang là trung bình.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(out, dpi=200, facecolor="white"); plt.close(fig)


def tracking_figure(out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = [x for x in rows("results/W05/track_comparison.csv") if x["iou_thr"] == "0.5"]
    cls = ["Airplane", "Bird", "Drone", "Helicopter"]
    trk = [("tracker_bytetrack_e1", "ByteTrack-e1", C1), ("tracker_botsort_e1", "BoT-SORT-e1", C2)]
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    w = 0.36
    for j, (t, lab, c) in enumerate(trk):
        for i, k in enumerate(cls):
            x = next(z for z in r if z["tracker"] == t and z["class"] == k)
            v = float(x["idsw_per_1000_gt_frames"])
            xi = i + (j - 0.5) * (w + 0.03)
            ax.bar(xi, v, width=w, color=c, label=lab if i == 0 else None)
            ax.text(xi, v, f"{v:.1f}", ha="center", va="bottom", fontsize=7.5, color=INK)
    nv = {k: next(z for z in r if z["tracker"] == trk[0][0] and z["class"] == k)["videos"] for k in cls}
    ax.set_xticks(range(len(cls))); ax.set_xticklabels([f"{k} ({nv[k]} video)" for k in cls], fontsize=8, color=INK)
    ax.set_ylabel("ID switch / 1000 frame GT", fontsize=8, color=MUTED)
    ax.set_title("ID switch theo lớp, IoU 0,5, detector baseline A (val, 38 video)", loc="left", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper right"); style(ax)
    fig.tight_layout(); fig.savefig(out, dpi=200, facecolor="white"); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/W05")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    a.out.mkdir(parents=True, exist_ok=True)
    seeds_figure(a.out / "fig_w5_seeds.png")
    tracking_figure(a.out / "fig_w5_tracking_by_class.png")
    LOG.info("ghi %s", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
