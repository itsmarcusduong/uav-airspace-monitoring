import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/reporting"))
import w7_confusion_analysis as analysis  # noqa: E402


@pytest.mark.parametrize(
    ("overlap", "expected"),
    [
        (0.099, "background"),
        (0.1, "mislocalized"),
        (0.499, "mislocalized"),
        (0.5, "other_high_overlap_unmatched"),
    ],
)
def test_fp_iou_boundaries(monkeypatch, overlap, expected):
    monkeypatch.setattr(analysis, "iou", lambda _a, _b: overlap)
    prediction = (2, 0.8, (0, 0, 1, 1))
    gt = [(0, (0, 0, 1, 1))]
    assert analysis.classify_fp(0, prediction, gt, set(), [prediction]) == expected


def test_duplicate_has_priority_over_gt_overlap(monkeypatch):
    prediction = (2, 0.8, (0, 0, 1, 1))
    matched_prediction = (0, 0.9, (0, 0, 1, 1))
    gt = [(0, (0, 0, 1, 1))]

    def overlap(a, b):
        return 0.5 if b == gt[0][1] else 0.8

    monkeypatch.setattr(analysis, "iou", overlap)
    assert analysis.classify_fp(
        0, prediction, gt, {1}, [prediction, matched_prediction]
    ) == "duplicate"
