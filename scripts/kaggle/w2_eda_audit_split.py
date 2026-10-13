#!/usr/bin/env python3
"""E1 W2 Kaggle job: inventory + annotation audit + EDA + video-level split v1 + review sheets.

Chay tren Kaggle (CPU la du). Xem docs/w2/W2_PLAN.md de biet cach chay va tai ket qua.

    python w2_eda_audit_split.py --data-root /kaggle/input/e1-svanstrom-raw \
        --inventory /kaggle/input/e1-w2-tools/svanstrom_files.csv \
        --out /kaggle/working/w2_outputs --commit <git-sha-or-UNKNOWN>

Moi stage doc lap: stage loi se duoc ghi vao stage_status.json va cac stage con lai van chay.
Khong dung random khong co seed. Chi doc du lieu, khong sua du lieu goc.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import math
import platform
import random
import re
import shutil
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path

LOG = logging.getLogger("w2")
NAME = re.compile(r"^(IR|V)_(AIRPLANE|BIRD|DRONE|HELICOPTER)_(\d+)$")
CLASS_ID = {"AIRPLANE": 0, "BIRD": 1, "DRONE": 2, "HELICOPTER": 3}
CLASS_ORDER = ["AIRPLANE", "BIRD", "DRONE", "HELICOPTER"]
# categorical slots 1-4 of the reference palette (light surface)
CLASS_COLOR = {"AIRPLANE": "#2a78d6", "BIRD": "#eb6834", "DRONE": "#1baf7a", "HELICOPTER": "#eda100"}
SMALL_AREA = 32 * 32      # theo thuyet minh: bbox nho = dien tich < 32x32 px tren anh goc
MEDIUM_AREA = 96 * 96
TARGET = {"train": 0.70, "val": 0.15, "test": 0.15}


# ----------------------------------------------------------------------------- helpers
def resolve_root(root: Path) -> Path:
    """Tim thu muc chua Data/Video_IR va Data/Video_V (chap nhan nhieu cap long nhau)."""
    if (root / "Data" / "Video_IR").is_dir():
        return root
    for cand in sorted(root.rglob("Video_IR")):
        if cand.is_dir() and cand.parent.name == "Data" and (cand.parent / "Video_V").is_dir():
            return cand.parent.parent
    raise SystemExit(f"Khong tim thay Data/Video_IR va Data/Video_V duoi {root}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fields:
        path.write_text("", encoding="utf-8")
        return
    fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def dhash(gray) -> int:
    import cv2
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def quantiles(values: list[float], qs=(0.05, 0.25, 0.5, 0.75, 0.95)) -> dict:
    if not values:
        return {f"q{int(q*100):02d}": "" for q in qs}
    s = sorted(values)
    return {f"q{int(q*100):02d}": round(s[min(len(s) - 1, int(q * (len(s) - 1)))], 2) for q in qs}


def clean_box(box):
    """Tra ve (x,y,w,h) float hoac None neu vang/khong hop le ve kieu."""
    if box is None:
        return None
    try:
        x, y, w, h = (float(v) for v in list(box)[:4])
    except Exception:
        return "MALFORMED"
    if any(math.isnan(v) or math.isinf(v) for v in (x, y, w, h)):
        return "MALFORMED"
    return (x, y, w, h)


# ----------------------------------------------------------------------------- stages
def stage_env(out: Path, commit: str) -> None:
    info = {
        "python": sys.version, "platform": platform.platform(), "commit": commit,
        "cpu_count": __import__("os").cpu_count(),
    }
    for mod in ("cv2", "numpy", "pandas", "scipy", "matplotlib", "openpyxl", "mcos_decoder"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "present")
        except Exception as exc:  # noqa: BLE001
            info[mod] = f"MISSING ({exc.__class__.__name__})"
    try:
        info["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=20).stdout.strip() or "none"
    except Exception:
        info["nvidia_smi"] = "none/unavailable"
    (out / "env.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")


def stage_checksums(root: Path, inventory: Path | None, out: Path) -> dict:
    if not inventory or not inventory.is_file():
        (out / "checksum_verification.csv").write_text("status\nSKIPPED_NO_INVENTORY\n", encoding="utf-8")
        return {"checked": 0, "mismatch": 0, "missing": 0, "skipped": True}
    rows, mism, miss = [], 0, 0
    with inventory.open(encoding="utf-8-sig") as fh:
        recs = list(csv.DictReader(fh))
    for rec in recs:
        p = root / rec["relative_path"]
        if not p.is_file():
            status, got = "MISSING", ""
            miss += 1
        else:
            got = sha256(p)
            status = "OK" if got.lower() == rec["sha256"].lower() else "MISMATCH"
            mism += status == "MISMATCH"
        rows.append({"relative_path": rec["relative_path"], "expected": rec["sha256"], "actual": got, "status": status})
    write_csv(out / "checksum_verification.csv", rows)
    return {"checked": len(rows), "mismatch": mism, "missing": miss, "skipped": False}


def read_workbook(root: Path, out: Path) -> dict:
    """Doc Video_dataset_description.xlsx; tra ve {(IR|V, CLASS, number): {...}}. Loi -> {} va ghi chu."""
    path = root / "Data" / "Video_dataset_description.xlsx"
    meta: dict = {}
    try:
        import pandas as pd
        raw = pd.read_excel(path, header=None)
        header_row = next(i for i in range(min(15, len(raw))) if raw.iloc[i].astype(str).str.upper().str.contains("SENSOR").any())
        df = raw.iloc[header_row + 1:].copy()
        df.columns = [" ".join(str(c).split()).upper() for c in raw.iloc[header_row]]
        (out / "workbook_columns.json").write_text(json.dumps(
            {"columns": list(df.columns), "rows": len(df), "head": df.head(5).astype(str).values.tolist()},
            indent=2, ensure_ascii=False), encoding="utf-8")
        for _, r in df.iterrows():
            sensor = str(r.get("SENSOR", "")).strip().upper()
            cls = str(r.get("CLASS", "")).strip().upper()
            num = str(r.get("NUMBER", "")).strip().split(".")[0]
            if not sensor or not cls or not num.isdigit():
                continue
            mod = "IR" if sensor.startswith("I") else "V"
            meta[(mod, cls, int(num))] = {
                "distance_bin": str(r.get("DISTANCE BIN", "")).strip(),
                "inter_bin_number": str(r.get("INTER BIN NUMBER", "")).strip(),
                "drone_type_or_source": str(r.get("DRONE TYPE / INTERNET SOURCE", "")).strip(),
            }
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Khong doc duoc workbook: %s", exc)
        (out / "workbook_columns.json").write_text(json.dumps({"error": str(exc)}), encoding="utf-8")
    return meta


def stage_inventory_and_labels(root: Path, out: Path, meta: dict):
    """Giai ma toan bo video + nhan. Tra ve (inventory_rows, labels_by_video, hashes)."""
    import cv2
    from mcos_decoder import load_groundtruth  # type: ignore

    inv, labels, hashes = [], {}, {}
    anno_path = out / "annotations_per_frame.csv.gz"
    with gzip.open(anno_path, "wt", newline="", encoding="utf-8") as gz:
        aw = csv.writer(gz)
        aw.writerow(["video_id", "frame_index", "has_bbox", "x", "y", "w", "h"])
        videos = sorted(root.glob("Data/Video_*/*.mp4"))
        for n, video in enumerate(videos, 1):
            m = NAME.match(video.stem)
            if not m:
                continue
            mod, cls, num = m.group(1), m.group(2), int(m.group(3))
            label_path = video.with_name(video.stem + "_LABELS.mat")
            cap = cv2.VideoCapture(str(video))
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            prop_n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            decoded, h_first, h_mid = 0, None, None
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if decoded == 0 or decoded == prop_n // 2:
                    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if decoded == 0:
                        h_first = dhash(g)
                    if decoded == prop_n // 2:
                        h_mid = dhash(g)
                decoded += 1
            cap.release()
            boxes, label_err = [], ""
            try:
                boxes = [clean_box(b) for b in load_groundtruth(label_path)]
            except Exception as exc:  # noqa: BLE001
                label_err = f"{exc.__class__.__name__}: {exc}"
            labels[video.stem] = boxes
            hashes[video.stem] = (h_first, h_mid if h_mid is not None else h_first)
            for i, b in enumerate(boxes):
                if isinstance(b, tuple):
                    aw.writerow([video.stem, i, 1, *(round(v, 3) for v in b)])
                else:
                    aw.writerow([video.stem, i, 0, "", "", "", ""])
            md = meta.get((mod, cls, num), {})
            inv.append({
                "video_id": video.stem, "modality": mod, "class_name": cls.title(), "class_id": CLASS_ID[cls],
                "number": num, "mp4_bytes": video.stat().st_size, "fps": round(fps, 3),
                "width": width, "height": height, "frames_prop": prop_n, "frames_decoded": decoded,
                "duration_sec": round(decoded / fps, 3) if fps else "", "label_entries": len(boxes),
                "label_error": label_error_text(label_err), "label_file_exists": label_path.is_file(),
                "distance_bin": md.get("distance_bin", ""), "inter_bin_number": md.get("inter_bin_number", ""),
                "drone_type_or_source": md.get("drone_type_or_source", ""),
                "dhash_first": f"{h_first:016x}" if h_first is not None else "",
                "dhash_mid": f"{hashes[video.stem][1]:016x}" if h_first is not None else "",
            })
            if n % 50 == 0:
                LOG.info("inventory %d/%d", n, len(videos))
    write_csv(out / "video_inventory.csv", inv)
    return inv, labels, hashes


def label_error_text(s: str) -> str:
    return s.replace("\n", " ")[:200]


def stage_audit(inv: list[dict], labels: dict, out: Path) -> list[dict]:
    rows = []
    for rec in inv:
        boxes = labels.get(rec["video_id"], [])
        W, H = rec["width"], rec["height"]
        pos = [(i, b) for i, b in enumerate(boxes) if isinstance(b, tuple)]
        malformed = sum(1 for b in boxes if b == "MALFORMED")
        nonpos = sum(1 for _, b in pos if b[2] <= 0 or b[3] <= 0)
        oob = sum(1 for _, b in pos if b[0] < -1 or b[1] < -1 or b[0] + b[2] > W + 1 or b[1] + b[3] > H + 1)
        edge = sum(1 for _, b in pos if b[0] <= 1 or b[1] <= 1 or b[0] + b[2] >= W - 1 or b[1] + b[3] >= H - 1)
        dup = sum(1 for (i, a), (j, b) in zip(pos, pos[1:]) if j == i + 1 and a == b)
        jumps = [math.hypot((a[0] + a[2] / 2) - (b[0] + b[2] / 2), (a[1] + a[3] / 2) - (b[1] + b[3] / 2))
                 for (i, a), (j, b) in zip(pos, pos[1:]) if j == i + 1]
        gaps = sum(1 for k in range(1, len(boxes)) if isinstance(boxes[k], tuple) != isinstance(boxes[k - 1], tuple))
        areas = [b[2] * b[3] for _, b in pos if b[2] > 0 and b[3] > 0]
        issues = []
        if rec["label_error"]:
            issues.append("label_unreadable")
        if len(boxes) != rec["frames_decoded"]:
            issues.append("label_len_mismatch")
        if not pos:
            issues.append("no_positive_bbox")
        if nonpos:
            issues.append("nonpositive_wh")
        if oob:
            issues.append("bbox_out_of_image")
        if malformed:
            issues.append("malformed_box")
        if pos and dup / len(pos) > 0.5:
            issues.append("many_duplicate_consecutive")
        if jumps and max(jumps) > 0.25 * W:
            issues.append("large_center_jump")
        if rec["frames_prop"] and abs(rec["frames_prop"] - rec["frames_decoded"]) > 2:
            issues.append("frame_count_prop_mismatch")
        rows.append({
            "video_id": rec["video_id"], "modality": rec["modality"], "class_name": rec["class_name"],
            "frames_decoded": rec["frames_decoded"], "label_entries": len(boxes), "frames_with_bbox": len(pos),
            "frames_absent": len(boxes) - len(pos), "gap_transitions": gaps, "nonpositive_wh": nonpos,
            "out_of_image": oob, "touching_edge": edge, "malformed": malformed,
            "duplicate_consecutive": dup, "max_center_jump_px": round(max(jumps), 1) if jumps else "",
            "area_median": round(sorted(areas)[len(areas) // 2], 1) if areas else "",
            "small_ratio": round(sum(a < SMALL_AREA for a in areas) / len(areas), 3) if areas else "",
            "issues": ";".join(issues), "needs_manual_review": bool(issues),
        })
    write_csv(out / "annotation_audit.csv", rows)
    cnt = Counter(i for r in rows for i in r["issues"].split(";") if i)
    summary = {"videos": len(rows), "videos_with_issues": sum(r["needs_manual_review"] for r in rows),
               "issue_counts": dict(cnt),
               "all_absent_videos": [r["video_id"] for r in rows if "no_positive_bbox" in r["issues"]]}
    (out / "annotation_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return rows


def stage_stats(inv: list[dict], labels: dict, out: Path) -> list[dict]:
    groups = defaultdict(list)
    for rec in inv:
        groups[(rec["modality"], rec["class_name"])].append(rec)
    rows = []
    for (mod, cls), recs in sorted(groups.items()):
        areas, ws, hs = [], [], []
        present = 0
        for rec in recs:
            for b in labels[rec["video_id"]]:
                if isinstance(b, tuple) and b[2] > 0 and b[3] > 0:
                    present += 1
                    areas.append(b[2] * b[3]); ws.append(b[2]); hs.append(b[3])
        q = quantiles(areas)
        rows.append({
            "modality": mod, "class_name": cls, "videos": len(recs),
            "frames": sum(r["frames_decoded"] for r in recs), "frames_with_bbox": present,
            "small_lt32sq": sum(a < SMALL_AREA for a in areas), "medium_32_96": sum(SMALL_AREA <= a < MEDIUM_AREA for a in areas),
            "large_ge96sq": sum(a >= MEDIUM_AREA for a in areas),
            "small_ratio": round(sum(a < SMALL_AREA for a in areas) / len(areas), 3) if areas else "",
            "area_q05": q["q05"], "area_q25": q["q25"], "area_median": q["q50"], "area_q75": q["q75"], "area_q95": q["q95"],
            "w_median": quantiles(ws)["q50"], "h_median": quantiles(hs)["q50"],
        })
    write_csv(out / "class_stats.csv", rows)
    return rows


def split_once(units: dict, strata: dict, seed: int):
    """units: unit_id -> dict(frames,boxes). strata: stratum -> [unit_id]. Tra ve assignment unit->split."""
    rng = random.Random(seed)
    assign = {}
    for key in sorted(strata, key=str):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        n = len(ids)
        n_test = max(1, round(TARGET["test"] * n)) if n >= 4 else 0
        n_val = max(1, round(TARGET["val"] * n)) if n >= 4 else 0
        for i, u in enumerate(ids):
            assign[u] = "test" if i < n_test else "val" if i < n_test + n_val else "train"
    return assign


def split_score(assign: dict, units: dict, class_of: dict) -> float:
    score = 0.0
    for cls in CLASS_ORDER:
        for field in ("frames", "boxes"):
            tot = sum(units[u][field] for u in units if class_of[u] == cls) or 1
            for sp in ("val", "test"):
                share = sum(units[u][field] for u in units if class_of[u] == cls and assign[u] == sp) / tot
                score += abs(share - TARGET[sp])
    return score


def stage_split(inv, labels, hashes, out: Path, seed: int, n_seeds: int, group_by: str):
    boxes_n = {r["video_id"]: sum(isinstance(b, tuple) for b in labels[r["video_id"]]) for r in inv}
    by_id = {r["video_id"]: r for r in inv}
    units, class_of, members, strata = {}, {}, defaultdict(list), defaultdict(list)
    for r in inv:
        gid = r["video_id"] if group_by == "video" else f"{r['class_name'].upper()}_{r['number']:03d}"
        members[gid].append(r["video_id"])
    for gid, vids in members.items():
        first = by_id[vids[0]]
        units[gid] = {"frames": sum(by_id[v]["frames_decoded"] for v in vids), "boxes": sum(boxes_n[v] for v in vids)}
        class_of[gid] = first["class_name"].upper()
        key = (first["modality"], first["class_name"]) if group_by == "video" else (first["class_name"],)
        strata[key].append(gid)
    best, best_seed, best_score = None, None, 1e9
    for k in range(n_seeds):
        s = seed + k
        a = split_once(units, strata, s)
        sc = split_score(a, units, class_of)
        if sc < best_score:
            best, best_seed, best_score = a, s, sc
    rows = []
    for gid, vids in sorted(members.items()):
        for v in sorted(vids):
            r = by_id[v]
            rows.append({"video_id": v, "group_id": gid, "modality": r["modality"], "class_name": r["class_name"],
                         "split": best[gid], "frames": r["frames_decoded"], "frames_with_bbox": boxes_n[v],
                         "all_absent": boxes_n[v] == 0})
    write_csv(out / "split_v1.csv", rows)
    summ = defaultdict(lambda: {"videos": 0, "frames": 0, "bbox_frames": 0})
    for r in rows:
        for key in ((r["split"], r["modality"], r["class_name"]), (r["split"], "ALL", "ALL")):
            s = summ[key]; s["videos"] += 1; s["frames"] += r["frames"]; s["bbox_frames"] += r["frames_with_bbox"]
    write_csv(out / "split_summary.csv", [{"split": k[0], "modality": k[1], "class_name": k[2], **v} for k, v in sorted(summ.items())])

    # ---- leakage diagnostics
    split_of = {r["video_id"]: r["split"] for r in rows}
    near = []
    ids = sorted(hashes)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if split_of[a] == split_of[b] or by_id[a]["modality"] != by_id[b]["modality"]:
                continue
            ha, hb = hashes[a], hashes[b]
            if None in (ha[0], hb[0]):
                continue
            d = min(hamming(ha[0], hb[0]), hamming(ha[1], hb[1]), hamming(ha[0], hb[1]), hamming(ha[1], hb[0]))
            if d <= 4:
                near.append({"video_a": a, "split_a": split_of[a], "video_b": b, "split_b": split_of[b], "min_hamming": d})
    write_csv(out / "leakage_near_duplicate_pairs.csv", near, ["video_a", "split_a", "video_b", "split_b", "min_hamming"])
    pair_rows = []
    for cls in CLASS_ORDER:
        nums = {int(r["number"]) for r in inv if r["class_name"].upper() == cls}
        for num in sorted(nums):
            ir, vv = f"IR_{cls}_{num:03d}", f"V_{cls}_{num:03d}"
            if ir in split_of and vv in split_of:
                pair_rows.append({"class_name": cls.title(), "number": num, "ir_split": split_of[ir], "v_split": split_of[vv],
                                  "same_split": split_of[ir] == split_of[vv]})
    write_csv(out / "leakage_ir_v_same_number.csv", pair_rows, ["class_name", "number", "ir_split", "v_split", "same_split"])
    report = {
        "group_by": group_by, "base_seed": seed, "n_seeds_searched": n_seeds, "chosen_seed": best_seed,
        "balance_score_lower_is_better": round(best_score, 4), "target_ratio": TARGET,
        "near_duplicate_cross_split_pairs": len(near),
        "ir_v_same_number_pairs": len(pair_rows),
        "ir_v_same_number_pairs_in_different_splits": sum(not p["same_split"] for p in pair_rows),
        "note": ("IR_x va V_x cung class+number CHUA duoc xac minh la cung su kien quay; "
                 "xem leakage_ir_v_same_number.csv va workbook de quyet dinh (NEEDS_REVIEW)."),
    }
    (out / "split_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return rows


def stage_review_sheets(root: Path, split_rows, labels, out: Path, seed: int) -> None:
    """Contact sheet de An/Quang kiem tra cheo bang mat: toan bo test + 10% train + video bi flag."""
    import cv2
    import numpy as np
    audit = {r["video_id"]: r for r in csv.DictReader((out / "annotation_audit.csv").open(encoding="utf-8"))}
    rng = random.Random(seed)
    train = sorted(r["video_id"] for r in split_rows if r["split"] == "train")
    pick_train = set(rng.sample(train, max(1, math.ceil(0.10 * len(train))))) if train else set()
    chosen = []
    for r in sorted(split_rows, key=lambda r: r["video_id"]):
        v = r["video_id"]
        flagged = audit.get(v, {}).get("needs_manual_review") in (True, "True")
        reason = "test" if r["split"] == "test" else "train10pct" if v in pick_train else "flagged" if flagged else ""
        if flagged and reason != "flagged":
            reason += "+flagged"
        if reason:
            chosen.append((v, r["split"], reason))
    cell_w, cell_h, per_sheet = 320, 256, 4
    sheets_dir = out / "review_sheets"
    sheets_dir.mkdir(exist_ok=True)
    assignment = []
    for s0 in range(0, len(chosen), per_sheet):
        batch = chosen[s0:s0 + per_sheet]
        canvas = np.full((per_sheet * (cell_h + 22), 3 * cell_w, 3), 252, np.uint8)
        sheet_name = f"sheet_{s0 // per_sheet + 1:03d}.jpg"
        for row_i, (vid, sp, reason) in enumerate(batch):
            boxes = labels[vid]
            pos = [i for i, b in enumerate(boxes) if isinstance(b, tuple)]
            picks = [pos[int(q * (len(pos) - 1))] for q in (0.25, 0.5, 0.75)] if pos else []
            video = next(root.glob(f"Data/Video_*/{vid}.mp4"))
            cap = cv2.VideoCapture(str(video))
            y0 = row_i * (cell_h + 22)
            cv2.putText(canvas, f"{vid} | {sp} | {reason}", (4, y0 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1, cv2.LINE_AA)
            for col, fi in enumerate(picks):
                cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
                ok, frame = cap.read()
                if not ok:
                    continue
                x, y, w, h = boxes[fi]
                cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 1)
                sx = cell_w / frame.shape[1]
                small = cv2.resize(frame, (cell_w, cell_h))
                cv2.putText(small, f"f{fi}", (4, cell_h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
                canvas[y0 + 22:y0 + 22 + cell_h, col * cell_w:(col + 1) * cell_w] = small
            cap.release()
            assignment.append({"sheet": sheet_name, "video_id": vid, "split": sp, "reason": reason,
                               "reviewer": "An" if (s0 // per_sheet) % 2 == 0 else "Quang",
                               "verdict": "", "notes": ""})
        cv2.imwrite(str(sheets_dir / sheet_name), canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])
    write_csv(out / "review_assignment.csv", assignment,
              ["sheet", "video_id", "split", "reason", "reviewer", "verdict", "notes"])


def stage_plots(inv, labels, split_rows, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.edgecolor": "#c3c2b7",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.color": "#ececea", "grid.linewidth": 0.6, "font.size": 10, "text.color": "#0b0b0b"})
    classes = [c.title() for c in CLASS_ORDER]
    # 1) videos per modality x class
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for k, cls in enumerate(classes):
        vals = [sum(1 for r in inv if r["modality"] == m and r["class_name"] == cls) for m in ("IR", "V")]
        bars = ax.bar([x + (k - 1.5) * 0.2 for x in (0, 1)], vals, 0.18, color=CLASS_COLOR[cls.upper()], label=cls)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 2, str(v), ha="center", fontsize=8, color="#52514e")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["IR (hong ngoai)", "V (kha kien)"])
    ax.set_ylabel("So video"); ax.set_title("So video theo cam bien va lop"); ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout(); fig.savefig(out / "fig_videos_by_modality_class.png", dpi=150); plt.close(fig)
    # 2) bbox area distribution by class (log), per modality panel
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, mod in zip(axes, ("IR", "V")):
        for cls in classes:
            areas = [b[2] * b[3] for r in inv if r["modality"] == mod and r["class_name"] == cls
                     for b in labels[r["video_id"]] if isinstance(b, tuple) and b[2] > 0 and b[3] > 0]
            if areas:
                ax.hist(areas, bins=[2 ** (i / 2) for i in range(0, 40)], histtype="step", linewidth=1.6,
                        color=CLASS_COLOR[cls.upper()], label=cls)
        ax.axvline(SMALL_AREA, color="#52514e", linestyle=":", linewidth=1)
        ax.set_xscale("log"); ax.set_title(mod); ax.set_xlabel("Dien tich bbox (px^2, log)")
    axes[0].set_ylabel("So frame"); axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("Phan bo kich thuoc bbox (duong cham: 32x32)", fontsize=10)
    fig.tight_layout(); fig.savefig(out / "fig_bbox_area_by_class.png", dpi=150); plt.close(fig)
    # 3) split videos by class
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for k, cls in enumerate(classes):
        vals = [sum(1 for r in split_rows if r["split"] == sp and r["class_name"] == cls) for sp in ("train", "val", "test")]
        ax.bar([x + (k - 1.5) * 0.2 for x in range(3)], vals, 0.18, color=CLASS_COLOR[cls.upper()], label=cls)
    ax.set_xticks(range(3)); ax.set_xticklabels(["train", "val", "test"]); ax.set_ylabel("So video")
    ax.set_title("Split v1: so video theo lop"); ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout(); fig.savefig(out / "fig_split_videos_by_class.png", dpi=150); plt.close(fig)


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("w2_outputs"))
    ap.add_argument("--inventory", type=Path, help="svanstrom_files.csv tu W1 de doi chieu sha256")
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--n-seeds", type=int, default=200, help="so seed thu de can bang split")
    ap.add_argument("--group-by", choices=["video", "pair"], default="video",
                    help="video: moi video la 1 nhom; pair: gom IR/V cung class+number")
    ap.add_argument("--skip-sheets", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    root = resolve_root(args.data_root)
    status: dict = {}

    def run(name, fn, *a, **kw):
        try:
            LOG.info("== stage %s", name)
            res = fn(*a, **kw)
            status[name] = "OK"
            return res
        except BaseException as exc:  # noqa: BLE001
            status[name] = f"FAILED: {exc.__class__.__name__}: {exc}"
            LOG.error("stage %s failed\n%s", name, traceback.format_exc())
            return None

    run("env", stage_env, out, args.commit)
    chk = run("checksums", stage_checksums, root, args.inventory, out)
    meta = run("workbook", read_workbook, root, out) or {}
    res = run("inventory_labels", stage_inventory_and_labels, root, out, meta)
    if res:
        inv, labels, hashes = res
        run("audit", stage_audit, inv, labels, out)
        run("stats", stage_stats, inv, labels, out)
        split_rows = run("split", stage_split, inv, labels, hashes, out, args.seed, args.n_seeds, args.group_by)
        if split_rows:
            run("plots", stage_plots, inv, labels, split_rows, out)
            if not args.skip_sheets:
                run("review_sheets", stage_review_sheets, root, split_rows, labels, out, args.seed)
        totals = {"videos": len(inv), "frames_decoded": sum(r["frames_decoded"] for r in inv),
                  "by_modality": dict(Counter(r["modality"] for r in inv)),
                  "by_class": dict(Counter(r["class_name"] for r in inv)),
                  "resolutions": dict(Counter(f"{r['modality']}:{r['width']}x{r['height']}" for r in inv))}
    else:
        totals = {}
    (out / "stage_status.json").write_text(json.dumps(
        {"stages": status, "checksums": chk, "totals": totals, "args": {k: str(v) for k, v in vars(args).items()}},
        indent=2, ensure_ascii=False), encoding="utf-8")
    zip_base = out.parent / (out.name + "_bundle")
    shutil.make_archive(str(zip_base), "zip", out)
    LOG.info("Done. Bundle: %s.zip | stages: %s", zip_base, status)
    return 0 if all(v == "OK" for v in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
