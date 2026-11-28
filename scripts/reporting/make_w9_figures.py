#!/usr/bin/env python3
"""Hinh cho bao cao W9 va version v0.9 (doc file ket qua, khong nhap tay so lieu).

    python scripts/reporting/make_w9_figures.py --out results/W09

- fig_w9_bench.png: FPS va p95 total theo cau hinh (trung vi 3 lan, thanh loi min-max), nguong NFR1
  (results/W09/benchmark/benchmark.csv, benchmark_summary.json).
- fig_w9_stage.png: p50 tung buoc cua pipeline theo cau hinh (benchmark_summary.json, stage_p50_median_ms).
- fig_w9_stability.png: RSS va bo nho GPU moi 60 giay khi chay on dinh 60 phut (summary.json cua run 20).
- fig_w9_neg.png: canh bao sai/gio R0 va R1 tren FBD-SV-2024, kem can tren Poisson 95% (neg_summary.json cua run 19b3).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("make_w9_figures")
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3dd"
COL = {"C0": "#2a78d6", "C1": "#7fa9e0", "C2": "#1b9e77", "CPU": "#9a9890"}
STAGE_COL = {"decode": "#9a9890", "detect": "#2a78d6", "track": "#eb6834", "alert": "#1b9e77", "persist": "#c9a227"}
NAME = {"C0": "C0\nPyTorch fp32", "C1": "C1\nPyTorch fp16", "C2": "C2\nTensorRT fp16", "CPU": "CPU\nfp32 (5 video)"}
BENCH = ROOT / "results/W09/benchmark"
STAB = ROOT / "results/W09/kaggle_run_20/w9_C0_rep1_stab/summary.json"
NEG = ROOT / "results/W09/kaggle_run_19/w9_neg_fbdsv/neg_summary.json"


def vn(x: float, n: int = 1) -> str:
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def style(ax, grid_axis: str = "y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    (ax.yaxis if grid_axis == "y" else ax.xaxis).grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)


def bench_figure(out: Path, plt) -> None:
    s = json.loads((BENCH / "benchmark_summary.json").read_text(encoding="utf-8"))
    cfgs = [c for c in ("C0", "C1", "C2", "CPU") if c in s["timing"]]
    tm = s["timing"]
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 3.0))
    for ax, (key, lo, hi, title, thr, thr_lbl) in zip(axs, [
            ("fps_median", "fps_min", "fps_max", "FPS toàn pipeline (trung vị, min–max)", 15, "NFR1: ≥ 15 FPS"),
            ("p95_total_median", "p95_total_min", "p95_total_max", "Độ trễ p95 total (ms, trung vị, min–max)", None, None)]):
        vals = [tm[c][key] for c in cfgs]
        err = [[tm[c][key] - tm[c][lo] for c in cfgs], [tm[c][hi] - tm[c][key] for c in cfgs]]
        bars = ax.bar([NAME[c] for c in cfgs], vals, yerr=err, capsize=3, color=[COL[c] for c in cfgs], width=0.55, ecolor=INK)
        top = max(tm[c][hi] for c in cfgs)
        for r, c in zip(bars, cfgs):
            ax.text(r.get_x() + r.get_width() / 2, tm[c][hi] + top * 0.02, vn(tm[c][key], 1), ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_ylim(0, top * 1.15)
        if thr:
            ax.axhline(thr, color="#b3261e", lw=1.0, ls="--"); ax.text(0.30, thr + top * 0.01, thr_lbl, fontsize=7, color="#b3261e", ha="left", va="bottom")
        ax.set_title(title, fontsize=9, color=INK, loc="left"); style(ax)
    fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


def stage_figure(out: Path, plt) -> None:
    s = json.loads((BENCH / "benchmark_summary.json").read_text(encoding="utf-8"))["timing"]
    cfgs = [c for c in ("C0", "C1", "C2", "CPU") if c in s]
    stages = ["decode", "detect", "track", "alert", "persist"]
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 2.4), gridspec_kw={"width_ratios": [3, 1.2]})
    gpu = [c for c in cfgs if c != "CPU"]
    for ax, group in ((axs[0], gpu), (axs[1], [c for c in cfgs if c == "CPU"])):
        left = [0.0] * len(group)
        for st in stages:
            v = [s[c]["stage_p50_median_ms"][st] for c in group]
            ax.barh([NAME[c].replace("\n", " ") for c in group], v, left=left, color=STAGE_COL[st], label=st, height=0.55)
            left = [a + b for a, b in zip(left, v)]
        for i, c in enumerate(group):
            ax.text(left[i], i, f"  {vn(s[c]['stage_p50_median_ms']['total'], 1)} ms", va="center", fontsize=8, color=INK)
        ax.set_xlim(0, max(left) * 1.3 if left else 1); ax.invert_yaxis(); style(ax, "x")
    axs[0].set_title("p50 từng bước (ms), GPU T4", fontsize=9, color=INK, loc="left")
    axs[1].set_title("CPU", fontsize=9, color=INK, loc="left")
    axs[0].legend(ncol=5, fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(0.0, -0.18))
    fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


def stability_figure(out: Path, plt) -> None:
    s = json.loads(STAB.read_text(encoding="utf-8"))
    m = s["memory_samples"]; sb = s["stability"]
    fig, ax = plt.subplots(figsize=(9.0, 2.6))
    x = [r["minute"] for r in m]
    ax.plot(x, [r["rss_mb"] for r in m], color="#2a78d6", lw=1.6, label="RSS (MB)")
    ax.axhline(sb["rss_min10"] * 1.10, color="#b3261e", lw=1.0, ls="--")
    ax.text(x[0], sb["rss_min10"] * 1.10, " ngưỡng 1,10 × RSS phút 10", fontsize=7, color="#b3261e", va="bottom")
    ax2 = ax.twinx(); ax2.plot(x, [r.get("gpu_alloc_mb", 0) for r in m], color="#eb6834", lw=1.2, ls="-", label="GPU cấp phát (MB)")
    ax2.set_ylim(0, max(r.get("gpu_alloc_mb", 0) for r in m) * 4 or 1); ax2.tick_params(colors=MUTED, labelsize=8)
    for sp in ("top",):
        ax2.spines[sp].set_visible(False)
    ax.set_xlabel("phút", fontsize=8, color=MUTED); ax.set_ylabel("RSS (MB)", fontsize=8, color=MUTED); ax2.set_ylabel("GPU (MB)", fontsize=8, color=MUTED)
    ax.set_title(f"Chạy ổn định 60 phút, C0: RSS phút 60 / phút 10 = {vn(sb['rss_ratio'], 3)}", fontsize=9, color=INK, loc="left")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="lower right")
    style(ax); fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


def neg_figure(out: Path, plt) -> None:
    s = json.loads(NEG.read_text(encoding="utf-8"))
    rules = ["R0", "R1"]
    vals = [s[r]["per_hour"] for r in rules]; up = [s[r]["per_hour_upper95"] for r in rules]
    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    bars = ax.bar(["R0 (chỉ detector)", "R1 (theo track)"], vals, yerr=[[0, 0], [u - v for u, v in zip(up, vals)]], capsize=3,
                  color=["#eb6834", "#2a78d6"], width=0.5, ecolor=INK)
    for r, u, v, k in zip(bars, up, vals, rules):
        ax.text(r.get_x() + r.get_width() / 2, u + max(up) * 0.03, f"{vn(v, 1)}/giờ ({s[k]['false_alerts']} cảnh báo)", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_ylim(0, max(up) * 1.3)
    ax.set_title(f"Cảnh báo sai trên FBD-SV-2024 ({s['clips']} clip, {vn(s['minutes'], 2)} phút), thanh lỗi: cận trên Poisson 95%",
                 fontsize=8.5, color=INK, loc="left")
    style(ax); fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/W09")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "DejaVu Sans"
    a.out.mkdir(parents=True, exist_ok=True)
    for name, fn, need in (("fig_w9_bench.png", bench_figure, BENCH / "benchmark_summary.json"),
                           ("fig_w9_stage.png", stage_figure, BENCH / "benchmark_summary.json"),
                           ("fig_w9_stability.png", stability_figure, STAB),
                           ("fig_w9_neg.png", neg_figure, NEG)):
        if not need.is_file():
            raise SystemExit(f"thieu {need.relative_to(ROOT)}")
        fn(a.out / name, plt); LOG.info("%s", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
