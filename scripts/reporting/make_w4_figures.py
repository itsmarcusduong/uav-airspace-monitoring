#!/usr/bin/env python3
"""Hinh cho bao cao W4 va version v0.4 (khong nhap tay so lieu).

    python scripts/reporting/make_w4_figures.py --out reports/w4/figures

- fig_w4_accuracy_vs_latency.png, fig_w4_ap_by_class.png: chep tu results/W04 (tao boi build_comparison.py).
- fig_w4_tracking_by_detection.png: so do Mermaid trong docs/w4/chuong2_nhap_An.md (An viet), render bang mmdc.
- eq_w4_iou.png, eq_w4_prf1.png: cong thuc hien thi ($$...$$) trong cung file, render bang matplotlib mathtext.
- fig_w4_cvat_box_vs_label.png: hop An ve so voi nhan goc (tap chuan CVAT): lech tam va ty le dien tich.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
log = logging.getLogger("make_w4_figures")


def mermaid(md: Path, out: Path) -> None:
    m = re.search(r"```mermaid\n(.*?)```", md.read_text(encoding="utf-8"), re.S)
    if not m:
        raise SystemExit(f"{md}: khong thay khoi mermaid")
    src = out.with_suffix(".mmd")
    # chi doi huong bo cuc LR -> TB de hinh vua khổ A4 (noi dung so do giu nguyen)
    src.write_text(m.group(1).replace("flowchart LR", "flowchart TB", 1), encoding="utf-8")
    cfg = out.parent / "_mmd_config.json"
    cfg.write_text(json.dumps({"theme": "neutral", "themeVariables": {"fontFamily": "DejaVu Sans", "fontSize": "15px"}}), encoding="utf-8")
    r = subprocess.run(["mmdc", "-i", str(src), "-o", str(out), "-c", str(cfg), "-s", "3", "-b", "white", "-w", "900"],
                       capture_output=True, text=True)
    src.unlink(missing_ok=True); cfg.unlink(missing_ok=True)
    if r.returncode != 0 or not out.is_file():
        raise SystemExit(f"mmdc that bai: {r.stderr[-500:]}")


def equations(md: Path) -> list[str]:
    eqs = re.findall(r"\$\$\s*(.*?)\s*\$\$", md.read_text(encoding="utf-8"), re.S)
    # mathtext khong ho tro \operatorname va xuong dong
    return [" ".join(e.replace(r"\operatorname", r"\mathrm").split()) for e in eqs]


def render_eq(tex: str, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=15)
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.04, transparent=False, facecolor="white")
    plt.close(fig)


def cvat_figure(ann_zip: Path, key_zip: Path, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with zipfile.ZipFile(key_zip) as z:
        key = list(csv.DictReader(z.read("gold_key.csv").decode("utf-8").splitlines()))
    ann = {}
    with zipfile.ZipFile(ann_zip) as z:
        for n in z.namelist():
            if n.endswith(".txt") and Path(n).stem.startswith("gold_"):
                ann[Path(n).stem] = [tuple(map(float, ln.split()[1:])) for ln in z.read(n).decode("utf-8").splitlines() if ln.strip()]
    pts = {}
    for k in key:
        b = ann.get(k["gold_id"], [])
        if len(b) != 1:
            continue
        W, H = float(k["width"]), float(k["height"])
        cx, cy, w, h = b[0]
        li = json.loads(k["label_i"])
        d = math.dist((cx * W, cy * H), (li[0] + li[2] / 2, li[1] + li[3] / 2))
        ratio = (w * W * h * H) / (li[2] * li[3])
        pts.setdefault(k["class_name"], []).append((d, ratio))
    pal = {"Drone": "#2a78d6", "Bird": "#eb6834", "Airplane": "#1baf7a", "Helicopter": "#7a5cd6"}
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for c, v in pts.items():
        ax.scatter([p[0] for p in v], [p[1] for p in v], s=16, color=pal.get(c, "#888"), label=f"{c} ({len(v)})", alpha=0.85)
    ax.axhline(1, color="#9a9893", lw=0.8, ls="--")
    ax.text(15, 1.1, "hộp An = hộp nhãn", fontsize=7, color="#6b6a66")
    ax.set_yscale("log"); ax.set_xlabel("lệch tâm hộp An so với nhãn i (px)"); ax.set_ylabel("diện tích hộp An / hộp nhãn")
    ax.legend(fontsize=7, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    ax.grid(color="#d9d8d4", lw=.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "reports/w4/figures")
    ap.add_argument("--chapter2", type=Path, default=ROOT / "docs/w4/chuong2_nhap_An.md")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    a.out.mkdir(parents=True, exist_ok=True)
    for f in ("fig_w4_accuracy_vs_latency.png", "fig_w4_ap_by_class.png"):
        src = ROOT / "results/W04" / f
        if not src.is_file():
            raise SystemExit(f"thieu {src}: chay build_comparison.py truoc")
        shutil.copy2(src, a.out / f)
    mermaid(a.chapter2, a.out / "fig_w4_tracking_by_detection.png")
    eqs = equations(a.chapter2)
    if len(eqs) != 2:
        raise SystemExit(f"can 2 cong thuc hien thi trong {a.chapter2}, thay {len(eqs)}")
    for name, tex in zip(("eq_w4_iou.png", "eq_w4_prf1.png"), eqs):
        render_eq(tex, a.out / name)
    G = ROOT / "results/W04/cvat_gold"
    cvat_figure(G / "cvat_gold_an_20261028.zip", G / "gold_KEY.zip", a.out / "fig_w4_cvat_box_vs_label.png")
    log.info("xong: %s", sorted(p.name for p in a.out.iterdir()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
