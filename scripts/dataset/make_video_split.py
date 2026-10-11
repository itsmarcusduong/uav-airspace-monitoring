#!/usr/bin/env python3
"""Split v1 cho Svanstrom: chia theo VIDEO (khong theo file/frame), phan tang modality x class,
can bang them theo distance bin (CLOSE/MEDIUM/DISTANT) bang tim seed tat dinh.

Chi doc metadata nho (ket qua Kaggle + workbook), khong giai ma video:
    python scripts/dataset/make_video_split.py \
        --inventory results/W02/kaggle_run_01/w2_outputs_bundle/video_inventory.csv \
        --audit results/W02/kaggle_run_01/w2_outputs_bundle/annotation_audit.csv \
        --workbook resources/datasets/svanstrom-drone-detection-dataset/Drone-detection-dataset-master/Data/Video_dataset_description.xlsx \
        --out data/splits --seed 20261011 --n-seeds 3000
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import random
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("split")
TARGET = {"train": 0.70, "val": 0.15, "test": 0.15}
CLASSES = ["Airplane", "Bird", "Drone", "Helicopter"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_distance_bins(xlsx: Path) -> dict[str, str]:
    import openpyxl
    ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = [" ".join(str(c).split()).upper() for c in rows[0]]
    idx = {name: header.index(name) for name in ("SENSOR", "CLASS", "NUMBER", "DISTANCE BIN")}
    out = {}
    for r in rows[1:]:
        if r[idx["NUMBER"]] is None:
            continue
        mod = "IR" if str(r[idx["SENSOR"]]).upper().startswith("I") else "V"
        vid = f"{mod}_{str(r[idx['CLASS']]).upper()}_{int(r[idx['NUMBER']]):03d}"
        out[vid] = str(r[idx["DISTANCE BIN"]]).strip().upper()
    return out


def allocate(strata: dict, rng: random.Random) -> dict[str, str]:
    assign = {}
    for key in sorted(strata):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        n = len(ids)
        n_test = max(1, round(TARGET["test"] * n)) if n >= 4 else 0
        n_val = max(1, round(TARGET["val"] * n)) if n >= 4 else 0
        for i, v in enumerate(ids):
            assign[v] = "test" if i < n_test else "val" if i < n_test + n_val else "train"
    return assign


def score(assign: dict, vids: dict) -> float:
    """Tong lech so voi 15%/15% cho: frames & bbox-frames theo class; videos & frames theo distance bin va modality."""
    total = 0.0
    def dev(select, field):
        tot = sum(vids[v][field] for v in vids if select(vids[v])) or 1
        s = 0.0
        for sp in ("val", "test"):
            share = sum(vids[v][field] for v in vids if select(vids[v]) and assign[v] == sp) / tot
            s += abs(share - TARGET[sp])
        return s
    for c in CLASSES:
        total += dev(lambda r, c=c: r["class_name"] == c, "frames") + dev(lambda r, c=c: r["class_name"] == c, "boxes")
    for d in ("CLOSE", "MEDIUM", "DISTANT"):
        total += dev(lambda r, d=d: r["distance_bin"] == d, "one") + dev(lambda r, d=d: r["distance_bin"] == d, "frames")
    for m in ("IR", "V"):
        total += dev(lambda r, m=m: r["modality"] == m, "frames")
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--workbook", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("data/splits"))
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--n-seeds", type=int, default=3000)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    inv = {r["video_id"]: r for r in read_csv(args.inventory)}
    aud = {r["video_id"]: r for r in read_csv(args.audit)}
    bins = read_distance_bins(args.workbook)
    if len(inv) != 650 or set(inv) != set(aud) or set(inv) - set(bins):
        raise SystemExit(f"Du lieu khong khop: inv={len(inv)} audit={len(aud)} thieu_bin={len(set(inv) - set(bins))}")
    vids = {}
    for v, r in inv.items():
        vids[v] = {"video_id": v, "modality": r["modality"], "class_name": r["class_name"],
                   "distance_bin": bins[v], "frames": int(r["frames_decoded"]),
                   "boxes": int(aud[v]["frames_with_bbox"]), "one": 1,
                   "all_absent": int(aud[v]["frames_with_bbox"]) == 0,
                   "issues": aud[v]["issues"]}
    strata = defaultdict(list)
    for v, r in vids.items():
        strata[(r["modality"], r["class_name"])].append(v)
    best, best_seed, best_score = None, None, 1e9
    for k in range(args.n_seeds):
        s = args.seed + k
        a = allocate(strata, random.Random(s))
        sc = score(a, vids)
        if sc < best_score:
            best, best_seed, best_score = a, s, sc
    rows = [{**{k: r[k] for k in ("video_id", "modality", "class_name", "distance_bin", "frames", "all_absent", "issues")},
             "frames_with_bbox": r["boxes"], "group_id": r["video_id"], "split": best[v]}
            for v, r in sorted(vids.items())]
    args.out.mkdir(parents=True, exist_ok=True)
    fields = ["video_id", "group_id", "modality", "class_name", "distance_bin", "split", "frames", "frames_with_bbox", "all_absent", "issues"]
    with (args.out / "video_split_v1.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)

    summ = []
    for sp in ("train", "val", "test"):
        sel = [r for r in rows if r["split"] == sp]
        for dim, key in (("ALL", lambda r: "ALL"), ("modality", lambda r: r["modality"]),
                         ("class", lambda r: r["class_name"]), ("distance_bin", lambda r: r["distance_bin"])):
            for k in sorted({key(r) for r in sel}):
                g = [r for r in sel if key(r) == k]
                summ.append({"split": sp, "dimension": dim, "value": k, "videos": len(g),
                             "frames": sum(r["frames"] for r in g), "frames_with_bbox": sum(r["frames_with_bbox"] for r in g),
                             "all_absent_videos": sum(r["all_absent"] for r in g)})
    with (args.out / "video_split_v1_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)

    # ---- chan doan ro ri (sang loc, KHONG phai bang chung day du)
    split_of = {r["video_id"]: r["split"] for r in rows}
    hashes = {v: [int(inv[v][k], 16) for k in ("dhash_first", "dhash_mid") if inv[v].get(k)] for v in inv}
    ids = sorted(inv)
    near = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if split_of[a] == split_of[b] or inv[a]["modality"] != inv[b]["modality"] or not hashes[a] or not hashes[b]:
                continue
            d = min(bin(x ^ y).count("1") for x in hashes[a] for y in hashes[b])
            if d <= 4:
                near.append({"video_a": a, "split_a": split_of[a], "video_b": b, "split_b": split_of[b], "min_hamming": d,
                             "same_class": a.split("_")[1] == b.split("_")[1]})
    with (args.out / "video_split_v1_leakage_near_duplicates.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["video_a", "split_a", "video_b", "split_b", "min_hamming", "same_class"])
        w.writeheader(); w.writerows(near)
    pairs = [(v, "IR_" + v[2:]) for v in inv if v.startswith("V_") and ("IR_" + v[2:]) in inv]
    pair_cross = sum(split_of[a] != split_of[b] for a, b in pairs)

    # ---- kiem tra tinh toan ven
    counts = Counter(r["split"] for r in rows)
    assert sum(counts.values()) == 650 and len({r["video_id"] for r in rows}) == 650
    manifest = {
        "split_version": "v1", "unit": "video (mp4 + _LABELS.mat di cung nhau)", "videos": 650,
        "counts": dict(counts), "target_ratio": TARGET, "strata": "modality x class",
        "balanced_on": ["class frames/bbox-frames", "distance_bin videos/frames", "modality frames"],
        "leakage_screen": {"method": "dHash khung dau/giua, Hamming<=4, cung modality, khac split",
                           "near_duplicate_pairs_across_splits": len(near),
                           "of_which_same_class": sum(r["same_class"] for r in near),
                           "ir_v_same_class_number_pairs": len(pairs), "ir_v_pairs_in_different_splits": pair_cross},
        "base_seed": args.seed, "n_seeds_searched": args.n_seeds, "chosen_seed": best_seed,
        "balance_score_lower_is_better": round(best_score, 4),
        "inputs_sha256": {p.name: sha256(p) for p in (args.inventory, args.audit, args.workbook)},
        "output_sha256": {"video_split_v1.csv": sha256(args.out / "video_split_v1.csv")},
        "status": "PROPOSED - dong bang (freeze) sau khi An va Quang ky duyet va tag commit",
        "known_limits": ["Khong kiem soat duoc trung canh/dia diem giua cac split (khong co metadata phien quay).",
                         "IR_x va V_x cung class+number khong duoc coi la cung su kien; xem docs/w2/split_protocol.md.",
                         "12 video khong co bbox duoc giu lam am tinh (all_absent=True)."],
    }
    (args.out / "video_split_v1_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG.info("counts=%s seed=%s score=%.4f", dict(counts), best_seed, best_score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
