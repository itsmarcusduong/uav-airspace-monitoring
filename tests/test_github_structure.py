"""Kiem tra luat cau truc GitHub/Evidence theo mau GVHD (scripts/github/check_structure.py), du lieu gia."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "github"))
import check_structure as cs  # noqa: E402


def iss(title, *who):
    return {"title": title, "assignees": [{"login": w} for w in who]}


def test_issue_title_one_student_one_assignee():
    assert cs.check_issue(iss("W6-01 – Dương Minh Quang – Run 14", "itsmarcusduong"), 6) == []
    assert cs.check_issue(iss("W6-02 – Dương Minh Quang, Lê Ngọc An – chung", "itsmarcusduong", "NgocAnMaster"), 6)[0][0] == "FAIL"
    assert cs.check_issue(iss("W6-03 – Lê Ngọc An – x", "itsmarcusduong"), 6)[0][1].startswith("assignee")
    assert cs.check_issue(iss("Run 14 tracking", "itsmarcusduong"), 6)[0][0] == "FAIL"


def test_pr_reviewer_must_be_other_member():
    pr = {"user": {"login": "itsmarcusduong"}}
    assert cs.check_pr(pr, {"NgocAnMaster"}, {"NgocAnMaster"}) == []
    assert cs.check_pr(pr, {"NgocAnMaster"}, set())[0][0] == "WARN"
    assert cs.check_pr(pr, set(), {"itsmarcusduong"})[0][0] == "FAIL"


def test_evidence_folder(tmp_path):
    d = tmp_path / "W09"
    assert cs.check_evidence(d)[0][0] == "FAIL"
    (d / "figures").mkdir(parents=True)
    for f in ("README.md", "metrics.csv", "test-results.json"):
        (d / f).write_text("{}" if f.endswith(".json") else "x")
    (d / "figures" / "a.png").write_bytes(b"p")
    import hashlib
    files = [{"path": p.relative_to(d).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in d.rglob("*") if p.is_file()]
    (d / "manifest.json").write_text(json.dumps({"files": files}))
    assert cs.check_evidence(d) == []
    (d / "metrics.csv").write_text("changed")
    assert any("SHA-256" in m for _, m in cs.check_evidence(d))


def test_evidence_manifest_must_cover_files(tmp_path):
    """Review #86: bo metrics.csv (hoac mot hinh) khoi manifest thi phai FAIL, du SHA cac file con lai dung."""
    import hashlib
    d = tmp_path / "W09"
    (d / "figures").mkdir(parents=True)
    for f in ("README.md", "metrics.csv", "test-results.json"):
        (d / f).write_text("{}" if f.endswith(".json") else "x")
    (d / "figures" / "a.png").write_bytes(b"p")
    keep = [p for p in d.rglob("*") if p.is_file() and p.name not in ("metrics.csv",)]
    files = [{"path": p.relative_to(d).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in keep]
    (d / "manifest.json").write_text(json.dumps({"files": files}))
    msgs = [m for lv, m in cs.check_evidence(d) if lv == "FAIL"]
    assert any("metrics.csv" in m and "khong liet ke" in m for m in msgs)
    (d / "manifest.json").write_text(json.dumps({"files": []}))
    assert any("khong liet ke" in m for _, m in cs.check_evidence(d))


def test_tag_weeks_follow_de_cuong():
    assert cs.TAG_WEEKS == {4, 8, 11, 14}
