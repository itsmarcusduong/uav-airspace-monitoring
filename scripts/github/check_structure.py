#!/usr/bin/env python3
"""Kiem tra cau truc GitHub + Evidence theo mau bat buoc cua GVHD (tu W4; ADR-0010).

Mau GVHD cho moi tuan N:
  Milestone TuanN
  ├── Issue #xx – <Sinh vien A> – <ket qua A>      (moi issue mot sinh vien, mot ket qua)
  ├── Issue #yy – <Sinh vien B> – <ket qua B>
  ├── PR #.. -> reviewer la thanh vien khac
  └── Tag/commit cuoi tuan: wNN
  Evidence/WNN/ gom README.md, metrics.csv, test-results.*, figures/, manifest.json

Tag: BAT BUOC o W4, W8, W11, W14 (De cuong muc 10: "tag milestone toi thieu o cac tuan W4, W8, W11, W14").
Cac tuan khac: "tag/commit cuoi tuan" -> script in commit cuoi tuan tren main (theo han milestone) de ghi vao bao cao;
neu tuan do co tag thi kiem tag nam tren main. Ap dung tu W6 (ADR-0010); khong ra soat lai cac tuan da qua.

Script chi DOC (GitHub REST API cong khai + thu muc Evidence trong repo) va in bang PASS/WARN/FAIL theo tuan.
Chay truoc khi gan tag cuoi tuan va truoc khi nop bao cao:

    python scripts/github/check_structure.py --weeks 6 --current 6 [--out docs/status/W06_github_structure.md]

Muc FAIL = sai mau GVHD (phai sua). WARN = nen sua nhung khong sai mau (vd. PR chua co review cua nguoi con lai).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "itsmarcusduong/uav-airspace-monitoring"
MEMBERS = {"Dương Minh Quang": "itsmarcusduong", "Lê Ngọc An": "NgocAnMaster"}
EVIDENCE_REQUIRED = ["README.md", "metrics.csv", "manifest.json"]
TITLE_RE = re.compile(r"^W(\d+)-(\d+) – (?P<name>[^–]+?) – (?P<result>.+)$")
TAG_WEEKS = {4, 8, 11, 14}
LOG = logging.getLogger("check_structure")


# ----------------------------------------------------------------------------- kiem tra thuan (khong I/O)
def check_issue(issue: dict, week: int) -> list[tuple[str, str]]:
    """Tra ve danh sach (muc, loi). Issue phai: ten `WN-xx – Ho ten – ket qua`, dung MOT sinh vien, assignee khop ten."""
    out = []
    m = TITLE_RE.match(issue["title"])
    if not m:
        return [("FAIL", "tieu de khong theo mau `WN-xx – <Ho ten> – <ket qua>`")]
    name = m.group("name").strip()
    if name not in MEMBERS:
        out.append(("FAIL", f"ten sinh vien '{name}' khong phai mot thanh vien (moi issue mot sinh vien)"))
    assignees = [a["login"] for a in issue.get("assignees", [])]
    if len(assignees) != 1:
        out.append(("FAIL", f"can dung 1 assignee, dang co {assignees}"))
    elif name in MEMBERS and assignees[0] != MEMBERS[name]:
        out.append(("FAIL", f"assignee {assignees[0]} khong khop ten trong tieu de ({MEMBERS[name]})"))
    return out


def check_pr(pr: dict, requested: set[str], reviewers: set[str]) -> list[tuple[str, str]]:
    """PR phai co reviewer la thanh vien khac (yeu cau review); WARN neu nguoi do chua review."""
    author = pr["user"]["login"]
    others = {v for v in MEMBERS.values() if v != author}
    if not (requested | reviewers) & others:
        return [("FAIL", f"chua gui review request cho thanh vien khac {sorted(others)}")]
    if not reviewers & others:
        return [("WARN", "thanh vien khac chua review (review sau merge van ghi lai duoc)")]
    return []


def check_evidence(d: Path) -> list[tuple[str, str]]:
    if not d.is_dir():
        return [("FAIL", f"thieu thu muc Evidence/{d.name}")]
    out = [("FAIL", f"thieu {d.name}/{f}") for f in EVIDENCE_REQUIRED if not (d / f).is_file()]
    if not list(d.glob("test-results.*")):
        out.append(("FAIL", f"thieu {d.name}/test-results.*"))
    fig = d / "figures"
    if not fig.is_dir():
        out.append(("FAIL", f"thieu {d.name}/figures/"))
    elif not [p for p in fig.iterdir() if p.name != ".gitkeep"]:
        out.append(("WARN", f"{d.name}/figures/ rong"))
    man = d / "manifest.json"
    if man.is_file():
        files = json.loads(man.read_text(encoding="utf-8")).get("files", [])
        bad = [f["path"] for f in files if not (d / f["path"]).is_file()
               or hashlib.sha256((d / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
        if bad:
            out.append(("FAIL", f"manifest.json khong khop SHA-256: {bad[:3]}"))
    tr = d / "test-results.json"
    if tr.is_file():
        s = json.loads(tr.read_text(encoding="utf-8")).get("summary", {})
        if s.get("failed"):
            out.append(("WARN", f"test-results.json co {s['failed']} kiem tra FAIL"))
    return out


# ----------------------------------------------------------------------------- I/O
def api(path: str) -> list | dict:
    """GET GitHub API, tu dong lay het cac trang."""
    out, url = [], f"https://api.github.com/repos/{REPO}/{path}"
    tok = os.environ.get("GITHUB_READ_TOKEN", "")
    while url:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {tok}"} if tok else {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            link = r.headers.get("Link", "")
        if isinstance(data, dict):
            return data
        out += data
        url = next((p.split(";")[0].strip("<> ") for p in link.split(",") if 'rel="next"' in p), None)
    return out


def tag_on_main(tag: str) -> str | None:
    try:
        sha = subprocess.run(["git", "-C", str(ROOT), "rev-list", "-n1", tag], capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", sha, "origin/main"], check=True, capture_output=True)
        return sha
    except subprocess.CalledProcessError:
        return None


def week_end_commit(due_on: str | None) -> str | None:
    """Commit cuoi cung tren origin/main truoc han milestone (due_on cua GitHub la 00:00 UTC ngay het han)."""
    if not due_on:
        return None
    day = due_on[:10]
    r = subprocess.run(["git", "-C", str(ROOT), "log", "--first-parent", "origin/main", f"--before={day}T23:59:59+07:00", "-1",
                        "--format=%h %cd", "--date=format:%d/%m %H:%M"], capture_output=True, text=True)
    return r.stdout.strip() or None


def parse_weeks(s: str) -> list[int]:
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weeks", default="6", help="vd 6 hoac 6-8 (ap dung tu W6, khong ra soat lai tuan cu)")
    ap.add_argument("--current", type=int, default=0, help="tuan dang lam: chua bat buoc tag va Evidence cua tuan nay")
    ap.add_argument("--out", type=Path, help="ghi bang ket qua ra file markdown")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "--tags", "origin"], capture_output=True)
    milestones = {m["title"]: m for m in api("milestones?state=all&per_page=100")}
    issues = api("issues?state=all&per_page=100")
    tags = {t["name"] for t in api("tags?per_page=100")}
    rows = []

    def add(week, item, level, msg):
        rows.append({"week": week, "item": item, "level": level, "msg": msg})

    for w in parse_weeks(a.weeks):
        ms = milestones.get(f"Tuan{w}")
        if not ms:
            add(w, f"Milestone Tuan{w}", "FAIL", "khong ton tai"); continue
        mine = [i for i in issues if (i.get("milestone") or {}).get("number") == ms["number"]]
        iss = [i for i in mine if "pull_request" not in i]
        prs = [i for i in mine if "pull_request" in i]
        if not iss:
            add(w, f"Milestone Tuan{w}", "FAIL", "khong co issue")
        owners = set()
        for i in iss:
            m = TITLE_RE.match(i["title"])
            if m:
                owners.add(m.group("name").strip())
            for lv, msg in check_issue(i, w):
                add(w, f"Issue #{i['number']}", lv, msg)
        if iss and owners != set(MEMBERS):
            add(w, f"Milestone Tuan{w}", "WARN", f"chua co issue cua {sorted(set(MEMBERS) - owners)}")
        for p in prs:
            pr = api(f"pulls/{p['number']}")
            if not pr.get("merged_at") and pr.get("state") == "closed":
                continue
            ev = api(f"issues/{p['number']}/events?per_page=100")
            req = {e["requested_reviewer"]["login"] for e in ev if e.get("event") == "review_requested" and e.get("requested_reviewer")}
            rev = {r["user"]["login"] for r in api(f"pulls/{p['number']}/reviews?per_page=100")}
            for lv, msg in check_pr(pr, req, rev):
                add(w, f"PR #{p['number']}", lv, msg)
        tag = f"w{w:02d}"
        if w != a.current:
            if tag in tags and not tag_on_main(tag):
                add(w, f"Tag {tag}", "FAIL", "tag khong nam tren main")
            elif tag not in tags and w in TAG_WEEKS:
                add(w, f"Tag {tag}", "FAIL", "tuan bat buoc co tag (De cuong muc 10: W4, W8, W11, W14)")
            elif tag not in tags:
                add(w, "Commit cuoi tuan", "INFO", f"{week_end_commit(ms.get('due_on')) or 'khong tim thay'} (tuan nay khong bat buoc tag)")
            for lv, msg in check_evidence(ROOT / "Evidence" / f"W{w:02d}"):
                add(w, f"Evidence/W{w:02d}", lv, msg)
        elif w in TAG_WEEKS:
            add(w, f"Tag {tag}", "INFO", "tuan nay BAT BUOC gan tag khi chot tuan")
        if not any(r["week"] == w and r["level"] in ("FAIL", "WARN") for r in rows):
            add(w, "Tuan", "PASS", f"{len(iss)} issue, {len(prs)} PR" + ("" if w != a.current else " (dang lam, chua kiem tag/Evidence)"))
    n_fail = sum(r["level"] == "FAIL" for r in rows)
    md = ["| Tuần | Mục | Mức | Chi tiết |", "|---|---|---|---|"] + [f"| W{r['week']:02d} | {r['item']} | {r['level']} | {r['msg']} |" for r in rows]
    md += ["", f"FAIL: {n_fail}, WARN: {sum(r['level'] == 'WARN' for r in rows)}. Tạo bằng `scripts/github/check_structure.py --weeks {a.weeks}`."]
    text = "\n".join(md) + "\n"
    print(text)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(text, encoding="utf-8")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
