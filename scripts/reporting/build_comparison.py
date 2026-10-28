#!/usr/bin/env python3
"""Bang so sanh cac mo hinh tren VAL (issue #39/#48) tu bang chung Kaggle — khong nhap tay so lieu.

Doc moi cap thu muc train_<exp>/ + analysis_<exp>/ duoi --runs (vd results/W04/kaggle_run_09) va bang chung baseline A
cua W3 (--baseline-train, --baseline-analysis). Tu choi so sanh neu fingerprint du lieu hoac split khac nhau.

    python scripts/reporting/build_comparison.py --runs results/W04/kaggle_run_09 \
        --baseline-train results/W03/kaggle_run_04/train_evidence --baseline-analysis results/W03/kaggle_run_05/analysis \
        --out results/W04
Dau ra: comparison_w4.csv, comparison_w4.md, fig_w4_accuracy_vs_latency.png, fig_w4_ap_by_class.png
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ORDER = ["baseline_A", "baseline_A_aug", "baseline_A_960", "yolo11n_640", "detector_B", "rtdetr_l_640"]


def rel(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def g(pc: dict, cls: str, k: str):
    """AP theo lop; lop khong co trong val -> rong (khong bia so 0)."""
    return pc.get(cls, {}).get(k, "")


def f3(v):
    return f"{v:.3f}" if isinstance(v, (int, float)) else "—"


def health(res: list) -> tuple:
    """Suc khoe qua trinh train tu results.csv: epoch dau tien co loss NaN (neu co) va do lech chuan mAP@0.5:0.95 tren val
    giua cac epoch (bo 5 epoch dau) — thuoc do nhieu cua val, dung khi dien giai chenh lech nho giua cac mo hinh."""
    first_nan = next((int(float(r["epoch"])) for r in res
                      if any("loss" in k and str(v).strip().lower() == "nan" for k, v in r.items())), None)
    key = next((k for k in res[0] if k.strip() == "metrics/mAP50-95(B)"), None) if res else None
    vals = [float(r[key]) for r in res[5:] if key and str(r[key]).strip().lower() != "nan"]
    sd = (sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5 if len(vals) > 2 else ""
    return first_nan, (round(sd, 4) if sd != "" else "")


def one(train: Path, analysis: Path, root: Path) -> dict:
    st = json.loads((train / "stage_status.json").read_text(encoding="utf-8"))
    env = json.loads((train / "env.json").read_text(encoding="utf-8"))
    mf = sorted(train.glob("*_val_metrics.json"))[0]
    met = json.loads(mf.read_text(encoding="utf-8"))
    cfg_file = sorted(p for p in train.glob("*.yaml"))[0]
    import yaml
    cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    sa = json.loads((analysis / "analysis_summary.json").read_text(encoding="utf-8"))
    op = sa["stages"]["operating_points"]
    rbs = {r["size"]: r["recall"] for r in csv.DictReader((analysis / "recall_by_size.csv").open(encoding="utf-8")) if r["class"] == "ALL"}
    pc = {r["class_name"]: r for r in met["per_class"]}
    res = list(csv.DictReader((train / "train" / "results.csv").open(encoding="utf-8")))
    o = met["overall"]
    bad = [k for k, v in st.items() if v.get("status") != "OK"] + [k for k, v in sa["status"].items() if v != "OK"]
    if bad:
        raise SystemExit(f"{train}: stage loi {bad}")
    first_nan, sd = health(res)
    return {"model": cfg["experiment"], "weights": cfg["model"], "imgsz": cfg["train"]["imgsz"], "batch": cfg["train"]["batch"],
            "split": "val", "map50": o["map50"], "map50_95": o["map50_95"],
            "ap50_Drone": g(pc, "Drone", "ap50"), "ap50_95_Drone": g(pc, "Drone", "ap50_95"),
            "ap50_Airplane": g(pc, "Airplane", "ap50"), "ap50_Bird": g(pc, "Bird", "ap50"), "ap50_Helicopter": g(pc, "Helicopter", "ap50"),
            "conf_op": op["conf_selected_on_val"], "Drone_P_op": op["Drone_P"], "Drone_R_op": op["Drone_R"], "Drone_F1_op": op["Drone_F1"],
            "all_P_op": op["all_P"], "all_R_op": op["all_R"],
            "recall_small_op": rbs.get("small", ""), "recall_medium_op": rbs.get("medium", ""), "recall_large_op": rbs.get("large", ""),
            "inference_ms": o["speed_ms_per_image"].get("inference"), "epochs_run": len(res),
            "best_epoch": sa["stages"]["curves"]["best_epoch_by_map50_95"],
            "train_minutes": round(float(res[-1]["time"]) / 60, 1) if "time" in res[-1] else "",
            "train_health": "OK" if first_nan is None else f"INVALID: loss NaN tu epoch {first_nan}",
            "val_map50_95_epoch_sd": sd,
            "gpu": env.get("gpu"), "ultralytics": env.get("ultralytics"), "fingerprint": st["data"]["fingerprint"][:16],
            "run_commit": env.get("commit", "")[:7], "source": rel(mf, root)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--baseline-train", type=Path)
    ap.add_argument("--baseline-analysis", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=Path("."))
    a = ap.parse_args()
    rows = []
    if a.baseline_train:
        rows.append(one(a.baseline_train, a.baseline_analysis, a.root))
    for runs in a.runs:
        for t in sorted(runs.rglob("train_*")):
            if t.is_dir() and (t.parent / t.name.replace("train_", "analysis_", 1)).is_dir():
                rows.append(one(t, t.parent / t.name.replace("train_", "analysis_", 1), a.root))
    seen = {}
    for r in rows:                      # cung experiment xuat hien 2 lan -> giu ban moi nhat (sau trong danh sach)
        seen[r["model"]] = r
    rows = sorted(seen.values(), key=lambda r: ORDER.index(r["model"]) if r["model"] in ORDER else 99)
    fps = {r["fingerprint"] for r in rows}
    if len(fps) > 1:
        raise SystemExit(f"Fingerprint du lieu khac nhau, khong so sanh: { {r['model']: r['fingerprint'] for r in rows} }")
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "comparison_w4.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    hdr = "| Mô hình | imgsz | mAP@0.5 | mAP@0.5:0.95 | AP@0.5 Drone | F1 Drone @ngưỡng | ngưỡng | recall nhỏ | ms/ảnh | epoch (best) | train |\n|---|---|---|---|---|---|---|---|---|---|---|\n"
    body = "".join(f"| {r['model']} ({r['weights']}) | {r['imgsz']} | {f3(r['map50'])} | {f3(r['map50_95'])} | {f3(r['ap50_Drone'])} | "
                   f"{f3(r['Drone_F1_op'])} | {r['conf_op']} | {r['recall_small_op']} | {r['inference_ms']:.2f} | {r['epochs_run']} ({r['best_epoch']}) | {r['train_health']} |\n" for r in rows)
    note = (f"\nTất cả trên **val** (lạc quan: val dùng để dừng sớm, chọn checkpoint và ngưỡng); cùng dữ liệu (fingerprint `{rows[0]['fingerprint']}…`), "
            f"cùng seed và ngân sách 50 epoch/patience 15; GPU {rows[0]['gpu']}. Thời gian suy luận đo trong bước val (batch), không phải FPS pipeline.\n")
    (a.out / "comparison_w4.md").write_text(hdr + body + note, encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pal = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#7a5cd6", "#d64b78"]
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    ys = [r["map50_95"] for r in rows]
    gap = 0.06 * (max(ys) - min(ys) or 0.01)          # khoang cach toi thieu giua hai nhan gan nhau (don vi truc y)
    placed = []                                          # (x, y_nhan) da dat, de tranh chong nhan
    for i, r in sorted(enumerate(rows), key=lambda t: -t[1]["map50_95"]):
        x, y = r["inference_ms"], r["map50_95"]
        valid = r["train_health"] == "OK"
        ax.scatter(x, y, s=70, color=pal[i % len(pal)] if valid else "white", edgecolor="white" if valid else pal[i % len(pal)],
                   linewidth=1.5, zorder=3)
        ly = y
        while any(abs(px - x) < 3 and abs(py - ly) < gap for px, py in placed):
            ly -= gap
        placed.append((x, ly))
        ax.annotate(f"{r['model']} @{r['imgsz']}" + ("" if valid else " (train lỗi NaN)"), (x, y), xytext=(x + 0.8, ly), textcoords="data", fontsize=7, va="center",
                    arrowprops=dict(arrowstyle="-", color="#9a9893", lw=0.6) if ly != y else None)
    ax.axvline(25, color="#9a9893", lw=0.8, ls="--")
    ax.text(25.4, max(ys), "giới hạn 25 ms\n(luật chọn)", fontsize=7, color="#6b6a66", va="top")
    ax.set_xlabel("thời gian suy luận (ms/ảnh, bước val, T4)"); ax.set_ylabel("mAP@0.5:0.95 (val)")
    ax.grid(color="#d9d8d4", lw=.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(a.out / "fig_w4_accuracy_vs_latency.png", dpi=200); plt.close(fig)
    cls = ["Airplane", "Bird", "Drone", "Helicopter"]
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    wd = 0.8 / len(rows)
    for i, r in enumerate(rows):
        ax.bar([k + (i - (len(rows) - 1) / 2) * wd for k in range(4)], [float(r[f"ap50_{c}"]) if r[f"ap50_{c}"] != "" else 0 for c in cls], wd * 0.95,
               color=pal[i % len(pal)], label=r["model"])
    ax.set_xticks(range(4)); ax.set_xticklabels(cls); ax.set_ylim(0, 1.15); ax.set_ylabel("AP@0.5 (val)")
    ax.legend(fontsize=7, frameon=False, ncol=3, loc="upper center"); ax.grid(axis="y", color="#d9d8d4", lw=.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(a.out / "fig_w4_ap_by_class.png", dpi=200); plt.close(fig)
    print((a.out / "comparison_w4.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
