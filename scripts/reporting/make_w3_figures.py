#!/usr/bin/env python3
"""Hinh W3 cho version do an v0.3 (chi doc file ket qua trong results/W03).
    python scripts/reporting/make_w3_figures.py --results results/W03 --out reports/w3/figures
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
CLASS_COLOR = {"Airplane": "#2a78d6", "Bird": "#eb6834", "Drone": "#1baf7a", "Helicopter": "#eda100"}
SIZE_COLOR = {"small": "#1c5cab", "medium": "#5598e7", "large": "#9ec5f4", "negatives": "#b4b2a9"}
SIZE_LABEL = {"small": "nhỏ (<32²)", "medium": "vừa (32²–96²)", "large": "lớn (≥96²)", "negatives": "ảnh âm tính"}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})


def funnel(res: Path, out: Path):
    dec = list(csv.DictReader((res / "kaggle_run_03b/export_evidence/inclusion_decisions.csv").open(encoding="utf-8")))
    card = json.loads((res / "kaggle_run_03b/export_evidence/dataset_card.json").read_text(encoding="utf-8"))
    excl = Counter("Review v2: SAI_NHAN" if d["reason"].startswith("review") else "Lệch số nhãn (thiếu/dư >1)"
                   for d in dec if d["include"] == "False")
    kept = sum(d["include"] == "True" for d in dec)
    steps = [("Video khả kiến có nhãn", 285), ("Thuộc train + val (test khóa: 43)", len(dec)), ("Giữ lại để xuất YOLO", kept)]
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    y = list(range(len(steps)))[::-1]
    ax.barh(y, [s[1] for s in steps], color="#2a78d6", height=0.55)
    for yi, (lab, v) in zip(y, steps):
        ax.text(v + 4, yi, f"{v}", va="center", color=INK)
        ax.text(-4, yi, lab, va="center", ha="right", color=INK)
    ax.set_yticks([]); ax.set_xlim(0, 330); ax.set_xlabel("số video")
    ax.text(kept + 40, y[-1], "Loại: " + "; ".join(f"{k} {v}" for k, v in excl.items()), va="center", color=INK2, fontsize=8)
    ax.set_title(f"Từ video gốc tới tập e1-yolo-v1 ({card['images']:,} ảnh; stride {card['stride']})".replace(",", "."),
                 loc="left", color=INK, fontsize=10)
    ax.grid(axis="x", color=GRID, lw=.6); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(out / "fig_w3_data_funnel.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def yolo_stats(res: Path, out: Path):
    rows = list(csv.DictReader((res / "kaggle_run_03b/export_evidence/dataset_stats.csv").open(encoding="utf-8")))
    classes = ["Airplane", "Bird", "Drone", "Helicopter"]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), sharey=False)
    for ax, sp in zip(axes, ["train", "val"]):
        base = [0] * 4
        for k in ["small", "medium", "large", "negatives"]:
            vals = [int(next(r for r in rows if r["split"] == sp and r["class_name"] == c)[k]) for c in classes]
            ax.bar(classes, vals, bottom=base, color=SIZE_COLOR[k], width=0.6, edgecolor="white", linewidth=1,
                   label=SIZE_LABEL[k])
            base = [b + v for b, v in zip(base, vals)]
        for i, b in enumerate(base):
            ax.text(i, b, f"{b:,}".replace(",", "."), ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_title(sp, loc="left", color=INK); ax.set_ylabel("số ảnh"); ax.grid(axis="y", color=GRID, lw=.6); ax.set_axisbelow(True)
        ax.set_ylim(0, max(base) * 1.15)
    axes[1].legend(fontsize=7, frameon=False, loc="upper right")
    fig.tight_layout(); fig.savefig(out / "fig_w3_yolo_images.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def sensitivity(res: Path, out: Path):
    s = json.loads((res / "kaggle_run_03a/export_evidence/offset_sensitivity_summary.json").read_text(encoding="utf-8"))
    g = s["groups"]
    name = {"equal": "khớp số nhãn", "plus1": "dư 1 mục", "minus": "thiếu nhãn"}
    items = sorted(g.items(), key=lambda kv: kv[1]["frac_iou_ge_min"])
    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    for i, (k, v) in enumerate(items):
        _, cls, kind = k.split("|")
        ax.plot([0.8, v["frac_iou_ge_min"]], [i, i], color=GRID, lw=1, zorder=1)
        ax.scatter(v["frac_iou_ge_min"], i, s=55, color=CLASS_COLOR[cls], zorder=3, edgecolor="white", linewidth=1.5)
        ax.text(v["frac_iou_ge_min"] + 0.004, i, f"{v['frac_iou_ge_min']:.1%}".replace(".", ","), va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([f"{k.split('|')[1]} – {name[k.split('|')[2]]} ({v['videos']} video)" for k, v in items])
    ax.axvline(s["iou_frac_required"], color=INK2, ls="--", lw=1)
    ax.text(s["iou_frac_required"], len(items) - 0.4, " ngưỡng 90%", color=INK2, fontsize=8, va="top")
    ax.set_xlim(0.8, 1.02); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}")); ax.set_xlabel("tỷ lệ cặp frame liên tiếp có IoU ≥ 0,5")
    ax.grid(axis="x", color=GRID, lw=.6); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(out / "fig_w3_offset_sensitivity.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def learning(res: Path, out: Path):
    rows = [{k.strip(): v for k, v in r.items()} for r in
            csv.DictReader((res / "kaggle_run_04/train_evidence/train/results.csv").open(encoding="utf-8"))]
    ep = [int(float(r["epoch"])) for r in rows]
    fit = [0.1 * float(r["metrics/mAP50(B)"]) + 0.9 * float(r["metrics/mAP50-95(B)"]) for r in rows]
    best = ep[max(range(len(fit)), key=lambda i: fit[i])]
    fig, ax = plt.subplots(1, 2, figsize=(7.6, 2.8))
    ax[0].plot(ep, [float(r["train/box_loss"]) for r in rows], color="#2a78d6", lw=2, label="train")
    ax[0].plot(ep, [float(r["val/box_loss"]) for r in rows], color="#eb6834", lw=2, label="val")
    ax[0].set_title("box loss", loc="left", color=INK); ax[0].set_xlabel("epoch")
    ax[1].plot(ep, [float(r["metrics/mAP50(B)"]) for r in rows], color="#2a78d6", lw=2, label="mAP@0.5")
    ax[1].plot(ep, [float(r["metrics/mAP50-95(B)"]) for r in rows], color="#1baf7a", lw=2, label="mAP@0.5:0.95")
    ax[1].set_title("mAP trên val", loc="left", color=INK); ax[1].set_xlabel("epoch"); ax[1].set_ylim(0, 1)
    for a in ax:
        a.axvline(best, color=INK2, ls="--", lw=1); a.grid(color=GRID, lw=.6); a.set_axisbelow(True)
        a.legend(fontsize=7, frameon=False)
    ax[1].text(best + 0.5, 0.95, f"best.pt (epoch {best})", fontsize=7.5, color=INK2, va="top")
    fig.tight_layout(); fig.savefig(out / "fig_w3_learning_curves.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def per_class(res: Path, out: Path):
    rows = list(csv.DictReader((res / "kaggle_run_04/train_evidence/baseline_A_val_per_class.csv").open(encoding="utf-8")))
    names = [r["class_name"] for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    w = 0.36
    x = range(len(rows))
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], [float(r["ap50"]) for r in rows], w, color="#2a78d6", label="AP@0.5")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], [float(r["ap50_95"]) for r in rows], w, color="#9ec5f4", label="AP@0.5:0.95")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015, f"{b.get_height():.2f}".replace(".", ","),
                    ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(list(x)); ax.set_xticklabels(names); ax.set_ylim(0, 1.15); ax.set_yticks([0, .2, .4, .6, .8, 1]); ax.set_ylabel("AP (val)")
    ax.grid(axis="y", color=GRID, lw=.6); ax.set_axisbelow(True); ax.legend(fontsize=7.5, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(); fig.savefig(out / "fig_w3_per_class_ap.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def recall_size(res: Path, out: Path):
    rows = list(csv.DictReader((res / "kaggle_run_05/analysis/recall_by_size.csv").open(encoding="utf-8")))
    sizes = ["small", "medium", "large"]; lab = {"small": "nhỏ (<32²)", "medium": "vừa (32²–96²)", "large": "lớn (≥96²)"}
    classes = ["Airplane", "Bird", "Drone", "Helicopter"]
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    w = 0.19
    for k, c in enumerate(classes):
        for j, sz in enumerate(sizes):
            r = next((r for r in rows if r["class"] == c and r["size"] == sz), None)
            if not r or int(r["gt"]) < 5:
                continue
            xpos = j + (k - 1.5) * (w + 0.01)
            ax.bar(xpos, float(r["recall"]), w, color=CLASS_COLOR[c], label=c if j == 0 or not any(
                rr["class"] == c and rr["size"] in sizes[:j] and int(rr["gt"]) >= 5 for rr in rows) else None)
            ax.text(xpos, float(r["recall"]) + 0.02, f"n={r['gt']}", ha="center", fontsize=6.5, color=INK2, rotation=90)
    ax.set_xticks(range(3)); ax.set_xticklabels([lab[s] for s in sizes]); ax.set_ylim(0, 1.25)
    ax.set_yticks([0, .25, .5, .75, 1]); ax.set_ylabel("recall @ conf 0,25")
    ax.grid(axis="y", color=GRID, lw=.6); ax.set_axisbelow(True); ax.legend(fontsize=7.5, frameon=False, ncol=4, loc="upper left")
    fig.tight_layout(); fig.savefig(out / "fig_w3_recall_by_size.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--results", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    funnel(a.results, a.out); yolo_stats(a.results, a.out); sensitivity(a.results, a.out)
    learning(a.results, a.out); per_class(a.results, a.out); recall_size(a.results, a.out); print("ok", a.out)


if __name__ == "__main__":
    main()
