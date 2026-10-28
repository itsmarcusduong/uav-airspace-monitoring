#!/usr/bin/env python3
"""Do do lien ket (association) cho tracker tren GT dan xuat "1 track/video" (issue #57, ADR-0008).

Bo du lieu Svanstrom KHONG co track ID. Moi video co toi da 1 hop nhan/frame cho 1 vat the muc tieu, nen GT dan
xuat gan cung mot ID cho moi frame co hop nhan. Cac do do duoi day chi do muc on dinh ID cua *vat the duoc gan nhan*;
chung KHONG phai MOTA/IDF1/HOTA chuan (khong co nhan cho cac vat the khac trong khung hinh).

Ham thuan (khong I/O) de kiem thu bang du lieu tong hop.
"""
from __future__ import annotations

from collections import Counter

Box = tuple  # (x, y, w, h) pixel, goc tren-trai


def iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def match_frames(gt: list, tracks: list[dict], iou_thr: float) -> list[dict]:
    """gt[i] = hop (x,y,w,h) hoac None cho frame i. tracks: dict frame, id, cls, conf, x, y, w, h.

    Moi frame co GT: chon hop track co IoU lon nhat voi GT (khong xet lop); khop neu IoU >= iou_thr.
    Tra ve danh sach theo frame: {frame, has_gt, matched, id, cls, iou, n_tracks}.
    """
    by_f: dict[int, list[dict]] = {}
    for t in tracks:
        by_f.setdefault(int(t["frame"]), []).append(t)
    out = []
    for f, g in enumerate(gt):
        cand = by_f.get(f, [])
        rec = {"frame": f, "has_gt": g is not None, "matched": False, "id": None, "cls": None, "iou": 0.0, "n_tracks": len(cand)}
        if g is not None and cand:
            best = max(cand, key=lambda t: iou(g, (t["x"], t["y"], t["w"], t["h"])))
            u = iou(g, (best["x"], best["y"], best["w"], best["h"]))
            rec["iou"] = round(u, 4)
            if u >= iou_thr:
                rec.update(matched=True, id=int(best["id"]), cls=int(best["cls"]))
        out.append(rec)
    return out


def video_metrics(gt: list, tracks: list[dict], gt_cls: int, iou_thr: float = 0.5, min_false_len: int = 5) -> dict:
    """Do do cho mot video. ID switch: so lan ID khop thay doi giua hai frame khop lien tiep (bo qua khoang mat).
    Fragment: so lan GT tu "khong khop" chuyen sang "khop" sau lan khop dau tien.
    Track gia: ID khong bao gio khop GT va xuat hien >= min_false_len frame (co the la vat that khong duoc gan nhan)."""
    m = match_frames(gt, tracks, iou_thr)
    gt_frames = [r for r in m if r["has_gt"]]
    matched = [r for r in gt_frames if r["matched"]]
    ids = [r["id"] for r in matched]
    idsw = sum(1 for a, b in zip(ids, ids[1:]) if a != b)
    frag, seen, prev = 0, False, False
    for r in gt_frames:
        if r["matched"] and seen and not prev:
            frag += 1
        seen |= r["matched"]; prev = r["matched"]
    cnt = Counter(ids)
    dom_id, dom_n = (cnt.most_common(1)[0] if cnt else (None, 0))
    track_len = Counter(int(t["id"]) for t in tracks)
    matched_ids = set(ids)
    false_ids = [i for i, n in track_len.items() if i not in matched_ids and n >= min_false_len]
    n_gt = len(gt_frames)
    return {
        "gt_frames": n_gt,
        "matched_frames": len(matched),
        "track_recall": round(len(matched) / n_gt, 4) if n_gt else None,
        "n_ids_on_target": len(matched_ids),
        "id_switches": idsw,
        "idsw_per_100_gt_frames": round(100 * idsw / n_gt, 3) if n_gt else None,
        "fragments": frag,
        "dominant_id": dom_id,
        "dominant_id_coverage": round(dom_n / n_gt, 4) if n_gt else None,
        "class_consistency": round(sum(r["cls"] == gt_cls for r in matched) / len(matched), 4) if matched else None,
        "n_track_ids": len(track_len),
        "false_tracks": len(false_ids),
        "false_track_frames": sum(track_len[i] for i in false_ids),
        "frames_no_gt_with_tracks": sum(1 for r in m if not r["has_gt"] and r["n_tracks"] > 0),
        "mean_iou_matched": round(sum(r["iou"] for r in matched) / len(matched), 4) if matched else None,
    }


def summarize(rows: list[dict]) -> dict:
    """Tong hop nhieu video: cong don so dem, trung vi cac ty le. Don vi phan tich la video."""
    def med(xs):
        xs = sorted(x for x in xs if x is not None)
        if not xs:
            return None
        k = len(xs) // 2
        return xs[k] if len(xs) % 2 else round((xs[k - 1] + xs[k]) / 2, 4)
    gt = sum(r["gt_frames"] for r in rows)
    sw = sum(r["id_switches"] for r in rows)
    return {
        "videos": len(rows),
        "gt_frames": gt,
        "matched_frames": sum(r["matched_frames"] for r in rows),
        "track_recall_pooled": round(sum(r["matched_frames"] for r in rows) / gt, 4) if gt else None,
        "id_switches": sw,
        "idsw_per_1000_gt_frames": round(1000 * sw / gt, 3) if gt else None,
        "fragments": sum(r["fragments"] for r in rows),
        "videos_single_id": sum(1 for r in rows if r["n_ids_on_target"] == 1),
        "videos_no_match": sum(1 for r in rows if r["n_ids_on_target"] == 0),
        "median_dominant_id_coverage": med([r["dominant_id_coverage"] for r in rows]),
        "median_track_recall": med([r["track_recall"] for r in rows]),
        "median_class_consistency": med([r["class_consistency"] for r in rows]),
        "false_tracks": sum(r["false_tracks"] for r in rows),
    }
