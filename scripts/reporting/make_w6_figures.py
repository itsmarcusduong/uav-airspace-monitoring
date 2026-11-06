#!/usr/bin/env python3
"""Hinh cho bao cao W6 va version v0.6 (doc file ket qua, khong nhap tay so lieu).

    python scripts/reporting/make_w6_figures.py --out results/W06

- fig_w6_alerts.png: R0 (chi detector) va R1 (theo track), ROI center_hex, diem tam, val run 14:
  canh bao sai tren video khong Drone, canh bao sai tren video Drone, canh bao lap, su kien GT bo sot
  (results/W06/alert_eval/alert_summary.json).
- fig_w6_detector_swap.png: ID switch / 1000 frame GT theo lop, ByteTrack-e1, baseline A vs YOLO11n
  (results/W06/detector_swap_tracking/summary.csv).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("make_w6_figures")
C1, C2, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1f1f1e", "#6b6a64", "#e4e3dd"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)


def bars(ax, cats, series, w=0.36, fmt="{:g}"):
    for j, (lab, c, vals) in enumerate(series):
        for i, v in enumerate(vals):
            xi = i + (j - 0.5) * (w + 0.03)
            ax.bar(xi, v, width=w, color=c, label=lab if i == 0 else None)
            ax.text(xi, v, fmt.format(v), ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.set_xticks(range(len(cats))); ax.set_xticklabels(cats, fontsize=8, color=INK)
    ax.set_ylim(0, max(v for _, _, vals in series for v in vals) * 1.3)


def alerts_figure(out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = json.loads((ROOT / "results/W06/alert_eval/alert_summary.json").read_text(encoding="utf-8"))["summary"]
    r0, r1 = s["center_hex|center|R0"], s["center_hex|center|R1"]
    cats = ["Sai, video không Drone", "Sai, video Drone", "Cảnh báo lặp", "Sự kiện bỏ sót"]
    val = lambda r: [r["false_alerts_nondrone"], r["false_alerts_drone_videos"], r["duplicates"], r["events"] - r["detected"]]
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    bars(ax, cats, [("R0 chỉ detector", C2, val(r0)), ("R1 theo track", C1, val(r1))])
    ax.set_ylabel("số cảnh báo / sự kiện", fontsize=8, color=MUTED)
    mins = f"{r0['hours_nondrone'] * 60:.1f}".replace(".", ",")
    ax.set_title(f"Cảnh báo ROI center_hex, điểm tâm (val, {r0['events']} sự kiện GT, {mins} phút video không Drone)",
                 loc="left", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper right"); style(ax)
    fig.tight_layout(); fig.savefig(out, dpi=200, facecolor="white"); plt.close(fig)


def swap_figure(out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with (ROOT / "results/W06/detector_swap_tracking/summary.csv").open(encoding="utf-8") as fh:
        r = list(csv.DictReader(fh))
    cls = ["all", "Airplane", "Bird", "Drone", "Helicopter"]
    get = lambda d, k: next(x for x in r if x["detector"] == d and x["class"] == k)
    nv = {k: get("baseline_A", k)["videos"] for k in cls}
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    bars(ax, [("Tất cả" if k == "all" else k) + f" ({nv[k]})" for k in cls],
         [("baseline A (YOLOv8n)", C2, [round(float(get("baseline_A", k)["idsw_per_1000_gt_frames"]), 1) for k in cls]),
          ("YOLO11n s20261030", C1, [round(float(get("yolo11n_s20261030", k)["idsw_per_1000_gt_frames"]), 1) for k in cls])], fmt="{:.1f}")
    ax.set_ylabel("ID switch / 1000 frame GT", fontsize=8, color=MUTED)
    ax.set_title("Đổi detector, cùng ByteTrack-e1 (val, số video trong ngoặc; GT dẫn xuất ADR-0008)", loc="left", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2); style(ax)
    fig.tight_layout(); fig.savefig(out, dpi=200, facecolor="white"); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/W06")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    a.out.mkdir(parents=True, exist_ok=True)
    alerts_figure(a.out / "fig_w6_alerts.png")
    swap_figure(a.out / "fig_w6_detector_swap.png")
    LOG.info("ghi %s", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
