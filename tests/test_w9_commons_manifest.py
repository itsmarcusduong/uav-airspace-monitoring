"""W9-03: manifest Commons tren phan hoi API gia (khong goi mang); sang loc doc lap va chia split theo tac gia."""
import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "dataset"))
import commons_manifest as cm  # noqa: E402

USER_LINK = "<a href='//commons.wikimedia.org/wiki/User:Ai_B' title='User:Ai B'>Ai</a>"


def fake_fetch(params):
    if params.get("list") == "categorymembers":
        if "cmcontinue" not in params:
            return {"query": {"categorymembers": [{"title": "File:Birds a.webm"}, {"title": "File:DJI drone sky.webm"}]}, "continue": {"cmcontinue": "x"}}
        return {"query": {"categorymembers": [{"title": "File:Clouds b.webm"}, {"title": "File:Plane c.webm"}, {"title": "File:Photo.jpg"},
                                              {"title": "File:Sky timelapse.webm"}, {"title": "File:Gulls slow motion.webm"},
                                              {"title": "File:Sky d.webm"}]}}
    info = {"File:Birds a.webm": ("video/webm", 1280, 720, 32.0, "CC BY-SA 4.0", USER_LINK),
            "File:DJI drone sky.webm": ("video/webm", 1920, 1080, 60.0, "CC0", "X"),
            "File:Clouds b.webm": ("video/webm", 1920, 1080, 5.0, "CC0", "X"),
            "File:Plane c.webm": ("video/webm", 1920, 1080, 40.0, "All rights reserved", "X"),
            "File:Photo.jpg": ("image/jpeg", 4000, 3000, None, "CC0", "X"),
            "File:Sky timelapse.webm": ("video/webm", 1920, 1080, 40.0, "CC0", "X"),
            "File:Gulls slow motion.webm": ("video/webm", 1920, 1080, 40.0, "CC0", "X"),
            "File:Sky d.webm": ("video/webm", 1920, 1080, 40.0, "CC0", "Unknown author")}
    pages = []
    for t in params["titles"].split("|"):
        mime, w, h, dur, lic, art = info[t]
        md = {"LicenseShortName": {"value": lic}, "LicenseUrl": {"value": "https://x"}, "Artist": {"value": art}}
        pages.append({"title": t, "imageinfo": [{"descriptionurl": "https://commons.wikimedia.org/wiki/" + t, "url": "https://upload/" + t, "mime": mime,
                                                 "width": w, "height": h, "duration": dur, "size": 1, "sha1": "ab", "user": "Up", "extmetadata": md}]})
    return {"query": {"pages": pages}}


def test_manifest_filters_and_writes_two_separate_screen_files(tmp_path, monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)
    out = tmp_path / "neg_commons_candidates.csv"
    assert cm.main(["--categories", "Test", "--out", str(out)], fetch=fake_fetch) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    # drone, ngan, giay phep dong, anh, time-lapse, slow-motion: bi loai
    assert [r["title"] for r in rows] == ["File:Birds a.webm", "File:Sky d.webm"]
    a, d = rows
    assert a["artist"] == "Ai" and a["author_key"] == "user:ai b" and a["author_status"] == "ok" and a["uploader"] == "Up"
    assert d["author_status"] == "needs_review" and d["author_key"] == ""
    assert "screen_an" not in rows[0] and "screen_quang" not in rows[0]          # ung vien khong chua cot sang loc
    sq, sa = tmp_path / "neg_commons_screen_quang.csv", tmp_path / "neg_commons_screen_an.csv"
    for p in (sq, sa):                                                            # hai ban rieng, chi gom tac gia ro
        assert [r["title"] for r in csv.DictReader(p.open(encoding="utf-8"))] == ["File:Birds a.webm"]


def test_time_lapse_category_is_refused(tmp_path):
    assert "Time-lapse videos of clouds" not in cm.CATEGORIES
    with pytest.raises(SystemExit, match="chinh sua"):
        cm.main(["--categories", "Time-lapse videos of clouds", "--out", str(tmp_path / "c.csv")], fetch=fake_fetch)


@pytest.mark.parametrize("html,key,status", [
    (USER_LINK, "user:ai b", "ok"),
    ("<a href='https://commons.wikimedia.org/w/index.php?title=User:Foo&action=edit'>F</a>", "user:foo", "ok"),
    ("  John   SMITH. ", "name:john smith", "ok"),
    ("Own work", "", "needs_review"),
    ("", "", "needs_review"),
    ("Unknown author", "", "needs_review"),
    ("<a href='/wiki/User:A'>A</a> and <a href='/wiki/User:B'>B</a>", "", "needs_review"),
])
def test_author_key(html, key, status):
    assert cm.author_key(html) == (key, status)


def _cand_row(i, key, uploader, dur=60):
    return {**{f: "" for f in cm.CAND_FIELDS}, "title": f"File:{i}.webm", "page": f"p{i}", "author_key": key,
            "author_status": "ok" if key else "needs_review", "uploader": uploader, "duration_s": str(dur)}


def test_alias_via_shared_uploader_stays_in_one_split():
    rows = [_cand_row(0, "name:j smith", "JS"), _cand_row(1, "user:jsmith", "JS"), _cand_row(2, "user:other", "O")]
    g = cm.author_groups(rows)
    assert g["File:0.webm"] == g["File:1.webm"] != g["File:2.webm"]
    sp = cm.assign_splits(rows)
    assert sp["File:0.webm"][1] == sp["File:1.webm"][1]


def test_split_targets_quarter_of_duration_and_is_deterministic():
    rows = [_cand_row(i, f"user:a{i}", f"u{i}") for i in range(40)]
    sp = cm.assign_splits(rows)
    train = sum(1 for _, s in sp.values() if s == "neg_train")
    assert 10 <= train <= 11 and sp == cm.assign_splits(list(reversed(rows)))


def _write(path, fields, rows):
    cm.write_csv(path, fields, rows)
    return path


def _setup(tmp_path, decisions_q, decisions_a, keys):
    rows = [_cand_row(i, k, f"u{k}") for i, k in enumerate(keys)] + [_cand_row(99, "", "x")]
    cand = _write(tmp_path / "neg_commons_candidates.csv", cm.CAND_FIELDS, rows)
    scr = lambda dec: [{"title": f"File:{i}.webm", "page": f"p{i}", "screen": d, "screen_note": "" if d == "keep" else "co nguoi"}  # noqa: E731
                       for i, d in enumerate(dec)]
    return cand, _write(tmp_path / "q.csv", cm.SCREEN_FIELDS, scr(decisions_q)), _write(tmp_path / "a.csv", cm.SCREEN_FIELDS, scr(decisions_a))


def test_finalize_double_keep_two_splits_and_stats(tmp_path):
    keys = [f"user:a{i}" for i in range(12)]
    dq = ["keep"] * 11 + ["reject"]
    da = ["keep"] * 10 + ["reject", "reject"]
    cand, q, a = _setup(tmp_path, dq, da, keys)
    st = cm.finalize(cand, q, a, tmp_path / "v1.csv")
    out = list(csv.DictReader((tmp_path / "v1.csv").open(encoding="utf-8")))
    assert st["kept"] == 10 and st["needs_review_author"] == 1 and st["screened"] == 12
    assert st["agreement"] == round(11 / 12, 4) and st["cohen_kappa"] is not None
    assert {r["split"] for r in out} == {"neg_train", "neg_eval"} and st["clips"]["neg_train"] + st["clips"]["neg_eval"] == 10
    assert set(st["inputs_sha256"]) == {"neg_commons_candidates.csv", "q.csv", "a.csv"}
    assert (tmp_path / "v1.json").exists()


def test_finalize_refuses_incomplete_mismatched_or_one_split(tmp_path):
    keys = ["user:a0", "user:a1"]
    cand, q, a = _setup(tmp_path, ["keep", "keep"], ["keep", ""], keys)
    with pytest.raises(SystemExit, match="An: 1 clip chua sang loc"):
        cm.finalize(cand, q, a, tmp_path / "v1.csv")
    cand, q, a = _setup(tmp_path, ["keep", "reject"], ["keep", "keep"], keys)
    _write(q, cm.SCREEN_FIELDS, [{"title": "File:0.webm", "page": "p0", "screen": "keep", "screen_note": ""},
                                 {"title": "File:1.webm", "page": "p1", "screen": "reject", "screen_note": ""}])
    with pytest.raises(SystemExit, match="thieu ly do"):
        cm.finalize(cand, q, a, tmp_path / "v1.csv")
    cand, q, a = _setup(tmp_path, ["keep"], ["keep"], ["user:a0"])
    cand2 = _write(cand, cm.CAND_FIELDS, [_cand_row(0, "user:a0", "u"), _cand_row(1, "user:a1", "u")])
    with pytest.raises(SystemExit, match="khong khop"):
        cm.finalize(cand2, q, a, tmp_path / "v1.csv")
    cand, q, a = _setup(tmp_path, ["keep", "keep"], ["keep", "keep"], ["user:a0", "user:a1"])
    _write(cand, cm.CAND_FIELDS, [_cand_row(0, "user:a0", "same"), _cand_row(1, "user:a1", "same")])  # mot nhom -> mot split
    with pytest.raises(SystemExit, match="ca hai split"):
        cm.finalize(cand, q, a, tmp_path / "v1.csv")


def test_author_key_ignores_title_attribute_of_red_link():
    """Commons: lien ket tai khoan chua co trang co title 'User:X (page does not exist)' -> van la MOT tai khoan."""
    h = ('<a href="//commons.wikimedia.org/w/index.php?title=User:Meerah_Dhiman&action=edit&redlink=1" class="new" '
         'title="User:Meerah Dhiman (page does not exist)">Meerah Dhiman</a>')
    assert cm.author_key(h) == ("user:meerah dhiman", "ok")


def fake_fetch_v2(params):
    if params.get("list") == "categorymembers" and params.get("cmtype") == "subcat":
        subs = {"Category:Videos of birds": ["Category:Videos of geese", "Category:Aerial videos of birds", "Category:Time-lapse videos of birds"],
                "Category:Videos of geese": ["Category:Videos of geese in zoo"]}
        return {"query": {"categorymembers": [{"title": s} for s in subs.get(params["cmtitle"], [])]}}
    if params.get("list") == "categorymembers":
        files = {"Category:Videos of birds": ["File:Birds a.webm", "File:Sky d.webm"], "Category:Videos of geese": ["File:Geese e.webm"]}
        return {"query": {"categorymembers": [{"title": f} for f in files.get(params["cmtitle"], [])]}}
    pages = []
    for t in params["titles"].split("|"):
        md = {"LicenseShortName": {"value": "CC0"}, "LicenseUrl": {"value": "https://x"}, "Artist": {"value": USER_LINK}}
        pages.append({"title": t, "imageinfo": [{"descriptionurl": "https://c/" + t, "url": "https://u/" + t, "mime": "video/webm", "width": 1280,
                                                 "height": 720, "duration": 30.0, "size": 1, "sha1": "ab", "user": "Up", "extmetadata": md}]})
    return {"query": {"pages": pages}}


def test_expand_categories_depth_one_filters_aerial_and_edited():
    cats = cm.expand_categories(["Videos of birds"], 1, fake_fetch_v2)
    assert cats == ["Videos of birds", "Videos of geese"]                 # khong xuong cap 2, bo aerial va time-lapse


def test_v2_excludes_v1_titles_and_caps_deterministically(tmp_path, monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)
    v1 = tmp_path / "neg_commons_candidates.csv"
    cm.write_csv(v1, cm.CAND_FIELDS, [{"title": "File:Birds a.webm"}])
    out = tmp_path / "neg_commons_v2_candidates.csv"
    assert cm.main(["--v2", "--categories", "Videos of birds", "--exclude", str(v1), "--out", str(out)], fetch=fake_fetch_v2) == 0
    assert [r["title"] for r in csv.DictReader(out.open(encoding="utf-8"))] == ["File:Geese e.webm", "File:Sky d.webm"]
    assert (tmp_path / "neg_commons_v2_screen_quang.csv").exists() and (tmp_path / "neg_commons_v2_screen_an.csv").exists()
    out2 = tmp_path / "c2.csv"
    cm.main(["--v2", "--categories", "Videos of birds", "--exclude", str(v1), "--max-minutes", "0.4", "--out", str(out2)], fetch=fake_fetch_v2)
    one = [r["title"] for r in csv.DictReader(out2.open(encoding="utf-8"))]
    assert len(one) == 1 and one == [r["title"] for r in cm.cap_minutes([{"title": "File:Geese e.webm", "duration_s": 30}, {"title": "File:Sky d.webm", "duration_s": 30}], 0.4)]


def test_v2_requires_exclude(tmp_path):
    with pytest.raises(SystemExit):
        cm.main(["--v2", "--out", str(tmp_path / "x.csv")], fetch=fake_fetch_v2)


def test_get_retries_on_429_with_retry_after(monkeypatch):
    import io
    import urllib.error
    calls, slept = [], []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def opener(req, timeout):
        calls.append(req.full_url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {"Retry-After": "7"} if len(calls) == 1 else {}, None)
        return Resp(b'{"ok": 1}')

    assert cm.get({"action": "query"}, opener=opener, sleep=slept.append, clock=lambda: 0.0) == {"ok": 1}
    assert len(calls) == 3 and 7.0 in slept and 10.0 in slept           # Retry-After, roi 5*2^1
    assert "maxlag=5" in calls[0]


def test_get_raises_other_http_errors():
    import urllib.error

    def opener(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        cm.get({"action": "query"}, opener=opener, sleep=lambda s: None, clock=lambda: 0.0)
