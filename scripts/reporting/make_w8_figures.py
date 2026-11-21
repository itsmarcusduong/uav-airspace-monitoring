#!/usr/bin/env python3
"""Hinh cho bao cao W8 va version v0.8 (doc file ket qua, khong nhap tay so lieu).

    python scripts/reporting/make_w8_figures.py --out results/W08

- fig_w8_arch.png, fig_w8_deploy.png, fig_w8_erd.png, fig_w8_sequence.png: 4 so do Mermaid muc 4.1-4.2
  (ban nhap cua An + sua khi tich hop, scripts/reporting/w8_chapter4.py), render bang mmdc.
- fig_w8_v2_verify.png: run 14 so voi run 17 theo 5 dieu kien luat B (results/W08/v2_verify/v2_verify.json).
- fig_w8_dup.png: ty le hop trung theo 4 dieu kien cua chan doan (results/W08/kaggle_run_17/w8_dupdiag/dup_diagnostic.json).
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import w8_chapter4 as c4  # noqa: E402

LOG = logging.getLogger("make_w8_figures")
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3dd"
C14, C17 = "#eb6834", "#2a78d6"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)


def mermaid(src_text: str, out: Path, width: int = 900) -> None:
    src = out.with_suffix(".mmd"); src.write_text(src_text, encoding="utf-8")
    cfg = out.parent / "_mmd_config.json"
    cfg.write_text(json.dumps({"theme": "neutral", "themeVariables": {"fontFamily": "DejaVu Sans", "fontSize": "15px"}}), encoding="utf-8")
    r = subprocess.run(["mmdc", "-i", str(src), "-o", str(out), "-c", str(cfg), "-s", "3", "-b", "white", "-w", str(width)],
                       capture_output=True, text=True)
    src.unlink(missing_ok=True); cfg.unlink(missing_ok=True)
    if r.returncode != 0 or not out.is_file():
        raise SystemExit(f"mmdc that bai: {r.stderr[-500:]}")


def v2_figure(out: Path, plt) -> None:
    v = json.loads((ROOT / "results/W08/v2_verify/v2_verify.json").read_text(encoding="utf-8"))["rule_b"]["conditions"]
    panels = [("1_drone_image_recall_drop_le_0.02", "Recall Drone mức ảnh", "≤ 0,02 giảm", 1.0),
              ("5_pooled_track_recall_drop_le_0.02", "Track recall gộp", "≤ 0,02 giảm", 1.0),
              ("4_idsw_reduction_ge_20pct", "ID switch / 1000 frame GT", "giảm ≥ 20%", None)]
    fig, axs = plt.subplots(1, 3, figsize=(9.0, 2.8))
    for ax, (k, title, rule, ymax) in zip(axs, panels):
        a, b = float(v[k]["run14"]), float(v[k]["run17"])
        bars = ax.bar(["run 14\nNMS 0,7", "run 17\nNMS 0,5 (V2)"], [a, b], color=[C14, C17], width=0.55)
        for r, val in zip(bars, (a, b)):
            ax.text(r.get_x() + r.get_width() / 2, val, f"{val:.3f}".replace(".", ","), ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_title(f"{title}\n(luật: {rule})", fontsize=9, color=INK)
        if ymax:
            ax.set_ylim(0, ymax)
        style(ax)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def dup_figure(out: Path, plt) -> None:
    d = json.loads((ROOT / "results/W08/kaggle_run_17/w8_dupdiag/dup_diagnostic.json").read_text(encoding="utf-8"))["conditions"]
    order = [("jpg_fp32", "JPG\nfp32"), ("frame_fp32", "frame mp4\nfp32"), ("jpg_fp16", "JPG\nfp16"), ("frame_fp16", "frame mp4\nfp16")]
    vals = [100 * d[k]["dup_rate"] for k, _ in order]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    bars = ax.bar([lbl for _, lbl in order], vals, color=["#2a78d6", "#2a78d6", "#7fa9e0", "#7fa9e0"], width=0.55)
    for r, val, (k, _) in zip(bars, vals, order):
        ax.text(r.get_x() + r.get_width() / 2, val, f"{val:.1f}%\n({d[k]['dup_same_class_iou_0.5_0.7']}/{d[k]['boxes']})".replace(".", ","),
                ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.axhline(0.6, color=C14, lw=1.2, ls="--", label="model.val (W7): 0,6%")
    ax.axhline(8, color=MUTED, lw=0.8, ls=":", label="ngưỡng 8% (luật C.3)")
    ax.legend(loc="upper center", ncol=2, fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, 1.12))
    ax.set_ylabel("Hộp trùng cùng lớp (%)", fontsize=8, color=MUTED); ax.set_ylim(0, 15)
    style(ax); fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/W08")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "DejaVu Sans"
    a.out.mkdir(parents=True, exist_ok=True)
    blocks = c4.mermaid_blocks(c4.fixed_text())
    names = ["fig_w8_arch.png", "fig_w8_deploy.png", "fig_w8_erd.png", "fig_w8_sequence.png"]
    if len(blocks) != len(names):
        raise SystemExit(f"ban nhap co {len(blocks)} so do Mermaid, ky vong {len(names)}")
    for b, n in zip(blocks, names):
        mermaid(b.replace("flowchart LR", "flowchart TB", 1), a.out / n, width=1100 if "erDiagram" in b else 900)
    v2_figure(a.out / "fig_w8_v2_verify.png", plt)
    dup_figure(a.out / "fig_w8_dup.png", plt)
    LOG.info("da ghi %d hinh vao %s", len(names) + 2, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
