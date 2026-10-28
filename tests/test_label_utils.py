"""Kiem tra ham xu ly nhan dung chung (w3_export_yolo, w3_review_sheets, w3_analyze_baseline)."""
import math
from pathlib import Path

import pytest

import w3_analyze_baseline as an
import w3_export_yolo as ex
import w3_review_sheets as rs


@pytest.mark.parametrize("mod", [ex, rs])
def test_to_box_valid_and_absent(mod):
    assert mod.to_box(None) is None
    assert mod.to_box([1, 2, 3, 4]) == (1.0, 2.0, 3.0, 4.0)


@pytest.mark.parametrize("bad", [[1, 2, float("nan"), 4], ["a", 1, 2, 3]])
@pytest.mark.parametrize("mod", [ex, rs])
def test_to_box_malformed_is_not_absent(mod, bad):
    assert mod.to_box(bad) == "MALFORMED"


def test_review_sheet_rejects_nonpositive_size():
    assert rs.to_box([1, 2, 0, 4]) == rs.MALFORMED


def test_label_kind():
    assert ex.label_kind(300, 300) == "equal"
    assert ex.label_kind(301, 300) == "plus1"
    assert ex.label_kind(290, 300) != "plus1"


def test_iou_basic():
    assert ex.iou((0, 0, 10, 10), (0, 0, 10, 10)) == pytest.approx(1.0)
    assert ex.iou((0, 0, 10, 10), (5, 0, 10, 10)) == pytest.approx(50 / 150)
    assert ex.iou((0, 0, 10, 10), (20, 20, 5, 5)) == 0.0


def test_parse_label_line_valid():
    assert an.parse_label_line("2 0.5 0.5 0.1 0.2", Path("x.txt"), 1, 4) == (2, 0.5, 0.5, 0.1, 0.2)


@pytest.mark.parametrize("line", ["2 0.5 0.5 0.1", "7 0.5 0.5 0.1 0.1", "2 1.5 0.5 0.1 0.1",
                                  "2 0.5 0.5 0 0.1", "2.0 0.5 0.5 0.1 0.1", "x 0.5 0.5 0.1 0.1",
                                  "2 nan 0.5 0.1 0.1"])
def test_parse_label_line_rejects(line):
    with pytest.raises(an.LabelError) as e:
        an.parse_label_line(line, Path("x.txt"), 3, 4)
    assert "x.txt:3" in str(e.value)


def test_load_preds_detects_one_based(tmp_path):
    p = tmp_path / "p.json"
    p.write_text('[{"image_id":"a","category_id":1,"bbox":[0,0,1,1],"score":0.9},'
                 '{"image_id":"a","category_id":4,"bbox":[0,0,1,1],"score":0.5}]')
    preds, off = an.load_preds(p, 4)
    assert off == 1 and [q[0] for q in preds["a"]] == [0, 3]


def test_review_agreement_kappa():
    import review_agreement as ra
    rows = [{"video_id": f"v{i}", "verdict": a, "review_quang_v2": b}
            for i, (a, b) in enumerate([("OK", "OK")] * 6 + [("SAI_NHAN", "SAI_NHAN")] * 2 + [("OK", "SAI_NHAN")] * 2 + [("", "OK")])]
    r = ra.agreement(rows, "verdict", "review_quang_v2")
    assert r["videos"] == 10 and r["agree"] == 8
    # po = 0.8; pe = (8*6 + 2*4)/100 = 0.56; kappa = 0.24/0.44
    assert r["cohen_kappa"] == round(0.24 / 0.44, 4)
    assert [d["video_id"] for d in r["disagreements"]] == ["v8", "v9"]


def test_comparison_health_detects_nan_and_noise():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "reporting"))
    import build_comparison as bc
    ok = [{"epoch": str(e), "train/box_loss": "1.0", "metrics/mAP50-95(B)": str(0.30 + (0.02 if e % 2 else 0))} for e in range(1, 13)]
    first, sd = bc.health(ok)
    assert first is None and 0.009 < sd < 0.012
    bad = [dict(r) for r in ok]; bad[2]["train/box_loss"] = "nan"
    assert bc.health(bad)[0] == 3
