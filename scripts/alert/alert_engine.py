#!/usr/bin/env python3
"""Geofence + canh bao theo quy dao (W6, issue #76, ADR-0009). Ham thuan, khong I/O, kiem thu bang du lieu tong hop.

Hai luat duoc so sanh:
  R0 detector-only: frame nao co detection Drone (conf >= conf_min) nam trong ROI thi "dang canh bao"; cac doan lien tiep,
     cach nhau <= merge_gap, la mot canh bao.
  R1 theo track (Thuyet minh muc 10.2): ung vien -> xac nhan (>= confirm_k frame bang chung trong confirm_n frame) ->
     canh bao khi track xac nhan, lop da so la Drone, o trong ROI lien tuc >= dwell -> ket thuc khi het bang chung trong
     ROI qua end_timeout. Track moi chong hop (IoU >= dup_iou) voi track dang/vua canh bao trong relink_s duoc gan vao
     CUNG su kien (track trung, doi ID). Canh bao sinh tu frame co detection that, khong tu vi tri du doan cua tracker.
Quy dao: moi canh bao ghi "vao_vung" neu track da duoc thay ngoai ROI truoc khi vao, nguoc lai "xuat_hien_trong_vung".
Canh bao som (tham do): ngoai suy tam hop theo van toc trung binh predict_window dong gan nhat, predict_horizon giay.

Toa do: track/detection theo pixel (x, y, w, h goc tren-trai); polygon chuan hoa [0, 1].
"""
from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass, field


# ----------------------------------------------------------------------------- hinh hoc
def point_in_polygon(px: float, py: float, poly: list) -> bool:
    """Ray casting; diem nam dung tren canh duoc tinh la trong."""
    n, inside = len(poly), False
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if _on_segment(px, py, x1, y1, x2, y2):
            return True
        if (y1 > py) != (y2 > py):
            xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < xi:
                inside = not inside
    return inside


def _on_segment(px, py, x1, y1, x2, y2, eps=1e-9) -> bool:
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > eps:
        return False
    return min(x1, x2) - eps <= px <= max(x1, x2) + eps and min(y1, y2) - eps <= py <= max(y1, y2) + eps


def _seg_intersect(a, b, c, d) -> bool:
    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    return any(o == 0 and _on_segment(p[0], p[1], s[0], s[1], e[0], e[1])
               for o, p, s, e in ((o1, c, a, b), (o2, d, a, b), (o3, a, c, d), (o4, b, c, d)))


def box_in_roi(box, poly, width: float, height: float, mode: str = "center") -> bool:
    """box = (x, y, w, h) pixel. mode center: tam hop trong polygon; box: hop giao polygon (ke ca chua nhau)."""
    x, y, w, h = (float(v) for v in box)
    if mode == "center":
        return point_in_polygon((x + w / 2) / width, (y + h / 2) / height, poly)
    if mode != "box":
        raise ValueError(f"mode khong hop le: {mode}")
    corners = [(x / width, y / height), ((x + w) / width, y / height), ((x + w) / width, (y + h) / height), (x / width, (y + h) / height)]
    if any(point_in_polygon(cx, cy, poly) for cx, cy in corners):
        return True
    if any(corners[0][0] <= px <= corners[1][0] and corners[0][1] <= py <= corners[2][1] for px, py in poly):
        return True
    edges = list(zip(corners, corners[1:] + corners[:1]))
    pedges = list(zip(poly, poly[1:] + poly[:1]))
    return any(_seg_intersect(a, b, c, d) for a, b in edges for c, d in pedges)


def iou(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def frames(seconds: float, fps: float) -> int:
    """So frame toi thieu tuong ung mot khoang thoi gian (lam tron len, >= 1)."""
    return max(1, math.ceil(seconds * fps - 1e-9))


def _box(r) -> tuple:
    return (float(r["x"]), float(r["y"]), float(r["w"]), float(r["h"]))


def runs(flags: list[bool]) -> list[tuple[int, int]]:
    """Cac doan True lien tiep -> [(dau, cuoi)] (bao gom hai dau)."""
    out, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1)); start = None
    return out


def merge(intervals: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    """Gop cac doan cach nhau <= gap frame (so frame trong o giua)."""
    out = []
    for s, e in sorted(intervals):
        if out and s - out[-1][1] - 1 <= gap:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


# ----------------------------------------------------------------------------- GT su kien
def gt_events(gt_rows: list[dict], n_frames: int, fps: float, poly, width, height, cfg: dict) -> list[tuple[int, int]]:
    """Su kien GT: tam hop nhan trong ROI lien tuc >= gt_dwell_s; cac su kien cach nhau <= merge_gap_s duoc gop."""
    inside = [False] * n_frames
    for r in gt_rows:
        f = int(r["frame"])
        if 0 <= f < n_frames and box_in_roi(_box(r), poly, width, height, "center"):
            inside[f] = True
    keep = [(s, e) for s, e in runs(inside) if e - s + 1 >= frames(cfg["gt_dwell_s"], fps)]
    return merge(keep, frames(cfg["merge_gap_s"], fps))


# ----------------------------------------------------------------------------- R0
def r0_alerts(dets: list[dict], n_frames: int, fps: float, poly, width, height, cfg: dict) -> list[dict]:
    active = [False] * n_frames
    for d in dets:
        f = int(d["frame"])
        if (0 <= f < n_frames and int(d["cls"]) == cfg["drone_class"] and float(d["conf"]) >= cfg["conf_min"]
                and box_in_roi(_box(d), poly, width, height, cfg.get("point", "center"))):
            active[f] = True
    return [{"rule": "R0", "start": s, "end": e, "tracks": [], "kind": "detector"}
            for s, e in merge(runs(active), frames(cfg["merge_gap_s"], fps))]


# ----------------------------------------------------------------------------- R1
@dataclass
class _Track:
    tid: int
    evidence: deque = field(default_factory=deque)          # cac frame co bang chung Drone (trong confirm_n gan nhat)
    votes: Counter = field(default_factory=Counter)
    confirmed: bool = False
    seen_outside: bool = False
    streak_start: int | None = None                         # dau chuoi frame lien tiep co bang chung trong ROI
    last_in: int | None = None
    last_box: tuple | None = None
    last_frame: int | None = None
    centers: deque = field(default_factory=deque)
    prewarned: bool = False


def r1_alerts(tracks: list[dict], n_frames: int, fps: float, poly, width, height, cfg: dict) -> tuple[list[dict], list[dict]]:
    """Tra ve (canh bao, canh bao som). Xu ly nhan qua (causal) theo frame."""
    by_f: dict[int, list[dict]] = {}
    for t in tracks:
        by_f.setdefault(int(t["frame"]), []).append(t)
    K, N = cfg["confirm_k"], cfg["confirm_n"]
    dwell, timeout = frames(cfg["dwell_s"], fps), frames(cfg["end_timeout_s"], fps)
    relink, gap = frames(cfg["relink_s"], fps), frames(cfg["merge_gap_s"], fps)
    horizon, window = frames(cfg["predict_horizon_s"], fps), int(cfg["predict_window"])
    mode = cfg.get("point", "center")
    st: dict[int, _Track] = {}
    alerts: list[dict] = []                  # {start, end, tracks:set, last_box, last_in, kind}
    prewarn: list[dict] = []
    owner: dict[int, dict] = {}              # track -> canh bao dang mo/da mo
    for f in range(n_frames):
        for r in by_f.get(f, []):
            tid = int(r["id"]); s = st.setdefault(tid, _Track(tid))
            b = _box(r); cls = int(r["cls"]); s.votes[cls] += 1
            ev = cls == cfg["drone_class"] and float(r["conf"]) >= cfg["conf_min"]
            if ev:
                s.evidence.append(f)
            while s.evidence and s.evidence[0] <= f - N:
                s.evidence.popleft()
            if len(s.evidence) >= K:
                s.confirmed = True
            inside = box_in_roi(b, poly, width, height, mode)
            if not inside:
                s.seen_outside = True
            if ev and inside:
                if s.streak_start is None or s.last_in is None or s.last_in < f - 1:
                    s.streak_start = f
                s.last_in = f
            elif s.last_in is not None and s.last_in < f:
                s.streak_start = None
            s.last_box, s.last_frame = b, f
            cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
            s.centers.append((f, cx, cy))
            while len(s.centers) > window:
                s.centers.popleft()
            drone_votes = s.votes[cfg["drone_class"]]
            drone_major = drone_votes > max(
                (votes for cls, votes in s.votes.items() if cls != cfg["drone_class"]),
                default=0,
            )
            # canh bao som (tham do): track xac nhan, lop Drone, dang ngoai ROI, ngoai suy vao ROI trong horizon
            if s.confirmed and drone_major and not inside and not s.prewarned and len(s.centers) >= 2:
                (f0, x0, y0), (f1, x1, y1) = s.centers[0], s.centers[-1]
                if f1 > f0:
                    vx, vy = (x1 - x0) / (f1 - f0), (y1 - y0) / (f1 - f0)
                    if point_in_polygon((cx + vx * horizon) / width, (cy + vy * horizon) / height, poly):
                        s.prewarned = True
                        prewarn.append({"track": tid, "frame": f})
            # mo canh bao hoac gan vao canh bao da co
            if tid in owner:
                a = owner[tid]
                if ev and inside and a["end"] is None:
                    a["last_in"] = f; a["last_box"] = b
                continue
            if s.confirmed and drone_major and ev and inside and s.streak_start is not None and f - s.streak_start + 1 >= dwell:
                link = None
                for a in alerts:
                    recent = a["end"] is None or f - a["end"] <= max(relink, gap)
                    if recent and a["last_box"] is not None and iou(a["last_box"], b) >= cfg["dup_iou"]:
                        link = a; break
                if link is None:
                    for a in alerts:                 # chong lap: canh bao vua dong trong merge_gap (khong chong hop) -> mo lai
                        if a["end"] is not None and f - a["end"] - 1 <= gap and set(a["tracks"]) & {tid}:
                            link = a; break
                if link is not None:
                    link["tracks"].add(tid); link["end"] = None; link["last_in"] = f; link["last_box"] = b
                    owner[tid] = link
                else:
                    a = {"rule": "R1", "start": f, "end": None, "tracks": {tid}, "last_in": f, "last_box": b,
                         "kind": "vao_vung" if s.seen_outside else "xuat_hien_trong_vung"}
                    alerts.append(a); owner[tid] = a
        # dong canh bao het bang chung trong ROI qua timeout
        for a in alerts:
            if a["end"] is None and f - a["last_in"] > timeout:
                a["end"] = a["last_in"]
                for t in list(a["tracks"]):
                    if owner.get(t) is a:
                        del owner[t]
    for a in alerts:
        if a["end"] is None:
            a["end"] = a["last_in"]
    out = [{"rule": "R1", "start": a["start"], "end": a["end"], "tracks": sorted(a["tracks"]), "kind": a["kind"]} for a in alerts]
    return out, prewarn


# ----------------------------------------------------------------------------- danh gia su kien
def match_events(alerts: list[dict], events: list[tuple[int, int]], tol: int) -> dict:
    """Canh bao khop su kien neu giao [s - tol, e + tol]. Moi su kien: canh bao khop dau tien = TP, cac canh bao khop them = lap.
    Canh bao khong khop su kien nao = canh bao sai. `first_alerts` = so canh bao la canh bao dau tien cua it nhat mot su kien
    (dung cho event precision mot-mot: canh bao lap khong duoc tinh dung; review #83)."""
    hit = [[i for i, a in enumerate(alerts) if a["start"] <= e + tol and a["end"] >= s - tol] for s, e in events]
    matched = {i for h in hit for i in h}
    first = [min(h, key=lambda i: alerts[i]["start"]) for h in hit if h]
    latency = [alerts[i]["start"] - s for (s, _), i in zip([ev for ev, h in zip(events, hit) if h], first)]
    return {"events": len(events), "detected": sum(1 for h in hit if h), "alerts": len(alerts), "matched_alerts": len(matched),
            "first_alerts": len(set(first)),
            "false_alerts": len(alerts) - len(matched), "duplicates": sum(max(0, len(h) - 1) for h in hit),
            "latency_frames": latency, "false_alert_ids": [i for i in range(len(alerts)) if i not in matched]}
