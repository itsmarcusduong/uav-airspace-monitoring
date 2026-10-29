#!/usr/bin/env python3
"""So sanh nhieu seed va ap luat chon dat truoc (docs/w4/training_protocol_w4.md muc 6; issue #59, ADR-0007).

Moi --item la mot cap "<thu muc train>=<thu muc analysis>" (bang chung Kaggle cua w3_train_baseline.py va
w3_analyze_baseline.py). Ho mo hinh = ten experiment bo hau to _s<seed>. Tu choi neu fingerprint du lieu khac nhau.

    python scripts/reporting/build_seed_comparison.py \
        --item results/W03/kaggle_run_04/train_evidence=results/W03/kaggle_run_05/analysis \
        --item results/W04/kaggle_run_09/phien_1/train_yolo11n_640=results/W04/kaggle_run_09/phien_1/analysis_yolo11n_640 \
        --item results/W05/kaggle_run_13/train_baseline_A_s20261029=results/W05/kaggle_run_13/analysis_baseline_A_s20261029 ... \
        --a baseline_A --b yolo11n_640 --out results/W05
Dau ra: seed_comparison.csv (moi run), seed_summary.csv (moi ho), seed_decision.json, seed_comparison.md
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_comparison import one  # noqa: E402

TIE_MAP, TIE_SPEED_REL, TIE_F1 = 0.01, 0.10, 0.01


def family(name: str) -> str:
    return re.sub(r"_s\d+$", "", name)


def stats(xs: list[float]) -> dict:
    return {"n": len(xs), "mean": round(st.mean(xs), 5), "sd": round(st.stdev(xs), 5) if len(xs) > 1 else None,
            "min": round(min(xs), 5), "max": round(max(xs), 5)}


def decide(sa: dict, sb: dict, a: str, b: str, speed_limit: float = 25.0) -> dict:
    """Luat muc 6. sa/sb: {'map': stats, 'ms': stats, 'f1': stats}. Mac dinh giu a (mo hinh dang dung)."""
    steps = []
    ok = {m: s["ms"]["mean"] <= speed_limit for m, s in ((a, sa), (b, sb))}
    if not all(ok.values()):
        keep = [m for m, v in ok.items() if v]
        return {"choice": keep[0] if keep else a, "reason": f"rang buoc toc do: {ok}", "steps": steps}
    d = sb["map"]["mean"] - sa["map"]["mean"]
    steps.append(f"delta mAP50-95 ({b} - {a}) = {d:+.4f}")
    if abs(d) >= TIE_MAP:
        return {"choice": b if d > 0 else a, "reason": f"|delta mAP| >= {TIE_MAP}", "steps": steps}
    fa, fb = sa["ms"]["mean"], sb["ms"]["mean"]
    rel = (max(fa, fb) - min(fa, fb)) / max(fa, fb)
    steps.append(f"hoa mAP; chenh toc do tuong doi = {rel:.3f}")
    if rel >= TIE_SPEED_REL:
        return {"choice": a if fa < fb else b, "reason": f"hoa mAP, nhanh hon >= {TIE_SPEED_REL:.0%}", "steps": steps}
    df = sb["f1"]["mean"] - sa["f1"]["mean"]
    steps.append(f"hoa toc do; delta F1 Drone = {df:+.4f}")
    if abs(df) >= TIE_F1:
        return {"choice": b if df > 0 else a, "reason": f"hoa mAP va toc do, |delta F1 Drone| >= {TIE_F1}", "steps": steps}
    return {"choice": a, "reason": "hoa ca ba tieu chi -> giu mo hinh dang dung", "steps": steps}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--item", action="append", required=True, help="<train_dir>=<analysis_dir>")
    ap.add_argument("--a", default="baseline_A", help="mo hinh dang dung (giu khi hoa)")
    ap.add_argument("--b", default="yolo11n_640")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=Path("."))
    a = ap.parse_args()
    rows = []
    for it in a.item:
        t, _, an = it.partition("=")
        if not an:
            raise SystemExit(f"--item can dang train=analysis: {it}")
        r = one(Path(t), Path(an), a.root)
        r["family"] = family(r["model"])
        import yaml
        r["seed"] = int(yaml.safe_load(sorted(Path(t).glob("*.yaml"))[0].read_text(encoding="utf-8"))["train"]["seed"])
        rows.append(r)
    if len({r["fingerprint"] for r in rows}) > 1:
        raise SystemExit(f"fingerprint khac nhau: { {r['model']: r['fingerprint'] for r in rows} }")
    dup = {(r["family"], r["seed"]) for r in rows}
    if len(dup) != len(rows):
        raise SystemExit("trung (ho, seed)")
    valid = [r for r in rows if r["train_health"] == "OK"]
    summ = {}
    for fam in (a.a, a.b):
        rs = [r for r in valid if r["family"] == fam]
        if not rs:
            raise SystemExit(f"khong co run hop le cho {fam}")
        summ[fam] = {"seeds": sorted(r["seed"] for r in rs), "map": stats([float(r["map50_95"]) for r in rs]),
                     "map50": stats([float(r["map50"]) for r in rs]), "ms": stats([float(r["inference_ms"]) for r in rs]),
                     "f1": stats([float(r["Drone_F1_op"]) for r in rs]), "invalid": [r["model"] for r in rows if r["family"] == fam and r not in valid]}
    dec = decide(summ[a.a], summ[a.b], a.a, a.b)
    a.out.mkdir(parents=True, exist_ok=True)
    keys = ["family", "seed", "model", "map50", "map50_95", "ap50_95_Drone", "Drone_F1_op", "conf_op", "inference_ms", "epochs_run",
            "best_epoch", "train_health", "val_map50_95_epoch_sd", "gpu", "ultralytics", "fingerprint", "run_commit", "source"]
    with (a.out / "seed_comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["family"], r["seed"])))
    with (a.out / "seed_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["family", "seeds", "metric", "n", "mean", "sd", "min", "max"])
        for fam, s in summ.items():
            for m in ("map", "map50", "ms", "f1"):
                w.writerow([fam, " ".join(map(str, s["seeds"])), {"map": "map50_95", "map50": "map50", "ms": "inference_ms", "f1": "Drone_F1_op"}[m],
                            *[s[m][k] for k in ("n", "mean", "sd", "min", "max")]])
    out = {"rule": "docs/w4/training_protocol_w4.md muc 6", "a": a.a, "b": a.b, "summary": summ, "decision": dec,
           "thresholds": {"map": TIE_MAP, "speed_rel": TIE_SPEED_REL, "f1": TIE_F1}}
    (a.out / "seed_decision.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["| Mô hình | Seed | mAP@0.5:0.95 (TB ± SD) | min–max | ms/ảnh (TB) | F1 Drone (TB) |", "|---|---|---|---|---|---|"]
    for fam, s in summ.items():
        md.append(f"| {fam} | {', '.join(map(str, s['seeds']))} | {s['map']['mean']:.4f} ± {f"{s['map']['sd']:.4f}" if s['map']['sd'] is not None else "—"} | "
                  f"{s['map']['min']:.4f}–{s['map']['max']:.4f} | {s['ms']['mean']:.2f} | {s['f1']['mean']:.3f} |")
    md += ["", f"**Quyết định theo luật:** {dec['choice']} — {dec['reason']}. " + "; ".join(dec["steps"])]
    (a.out / "seed_comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
