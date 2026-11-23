"""W9-03: manifest Commons tren phan hoi API gia (khong goi mang)."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "dataset"))
import commons_manifest as cm  # noqa: E402


def fake_fetch(params):
    if params.get("list") == "categorymembers":
        if "cmcontinue" not in params:
            return {"query": {"categorymembers": [{"title": "File:Birds a.webm"}, {"title": "File:DJI drone sky.webm"}]}, "continue": {"cmcontinue": "x"}}
        return {"query": {"categorymembers": [{"title": "File:Clouds b.webm"}, {"title": "File:Plane c.webm"}, {"title": "File:Photo.jpg"}]}}
    md = lambda lic: {"LicenseShortName": {"value": lic}, "LicenseUrl": {"value": "https://x"}, "Artist": {"value": "<a href='u'>Ai</a>"}}  # noqa: E731
    info = {"File:Birds a.webm": ("video/webm", 1280, 720, 32.0, "CC BY-SA 4.0"), "File:DJI drone sky.webm": ("video/webm", 1920, 1080, 60.0, "CC0"),
            "File:Clouds b.webm": ("video/webm", 1920, 1080, 5.0, "CC0"), "File:Plane c.webm": ("video/webm", 1920, 1080, 40.0, "All rights reserved"),
            "File:Photo.jpg": ("image/jpeg", 4000, 3000, None, "CC0")}
    pages = []
    for t in params["titles"].split("|"):
        mime, w, h, dur, lic = info[t]
        pages.append({"title": t, "imageinfo": [{"descriptionurl": "https://commons.wikimedia.org/wiki/" + t, "url": "https://upload/" + t, "mime": mime,
                                                 "width": w, "height": h, "duration": dur, "size": 1, "sha1": "ab", "extmetadata": md(lic)}]})
    return {"query": {"pages": pages}}


def test_manifest_filters_license_duration_drone(tmp_path, monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)
    out = tmp_path / "m.csv"
    assert cm.main(["--categories", "Test", "--out", str(out)], fetch=fake_fetch) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["title"] for r in rows] == ["File:Birds a.webm"]                        # drone, ngan, giay phep dong, anh: bi loai
    assert rows[0]["artist"] == "Ai" and rows[0]["license"] == "CC BY-SA 4.0" and rows[0]["screen_an"] == ""


def test_finalize_keeps_only_double_keep_and_splits_by_artist(tmp_path):
    import pytest
    rows = [{**{f: "" for f in cm.FIELDS}, "title": f"File:{i}.webm", "artist": a, "duration_s": "60", "screen_quang": q, "screen_an": n}
            for i, (a, q, n) in enumerate([("A", "keep", "keep"), ("A", "keep", "keep"), ("B", "keep", "reject"), ("C", "reject", "reject")])]
    cand = tmp_path / "c.csv"
    with cand.open("w", newline="", encoding="utf-8") as fh:
        w = cm.csv.DictWriter(fh, fieldnames=cm.FIELDS); w.writeheader(); w.writerows(rows)
    st = cm.finalize(cand, tmp_path / "v1.csv")
    out = list(cm.csv.DictReader((tmp_path / "v1.csv").open(encoding="utf-8")))
    assert st["kept"] == 2 and st["agreement"] == 0.75 and {r["split"] for r in out} == {cm.split_of("A")}
    rows[3]["screen_an"] = ""
    with cand.open("w", newline="", encoding="utf-8") as fh:
        w = cm.csv.DictWriter(fh, fieldnames=cm.FIELDS); w.writeheader(); w.writerows(rows)
    with pytest.raises(SystemExit, match="chua sang loc"):
        cm.finalize(cand, tmp_path / "v1.csv")
