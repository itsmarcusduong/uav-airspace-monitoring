"""W9 (#130): uoc luong bo nho list latency cua bo do tren du lieu gia, khong can Kaggle."""
import csv
import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))
import w9_rss_growth_check as rg  # noqa: E402


def _run(tmp_path, n, frames=None):
    d = tmp_path / "run"; d.mkdir()
    with gzip.open(d / "latency.csv.gz", "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["source_id", "frame", "decode", "detect", "track", "alert", "persist", "total"])
        for i in range(n):
            w.writerow([f"V_{i % 3}#{i // 30}", i % 30, 0.4, 9.6, 0.5, 0.03, 0.05, 10.7])
    mem = [{"minute": 0.2, "rss_mb": 100.0, "gpu_alloc_mb": 42.0}, {"minute": 10.2, "rss_mb": 110.0, "gpu_alloc_mb": 42.0}]
    (d / "summary.json").write_text(json.dumps({"frames": n if frames is None else frames, "memory_samples": mem}), encoding="utf-8")
    return d


def test_estimate_grows_with_rows_and_reports_share(tmp_path):
    d = _run(tmp_path, 3000)
    out = tmp_path / "o.json"
    assert rg.main(["--run", str(d), "--out", str(out)]) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["frames"] == 3000 and r["rss_growth_mb"] == 10.0 and r["rss_slope_mb_per_min"] == 1.0
    assert 0 < r["latency_list_mb_estimate"] < 5 and r["share_explained"] == round(r["latency_list_mb_estimate"] / 10.0, 2)
    small = rg.list_bytes([["V", "1", "0.1", "0.1", "0.1", "0.1", "0.1", "0.1"]] * 100)
    big = rg.list_bytes([["V", "1", "0.1", "0.1", "0.1", "0.1", "0.1", "0.1"]] * 1000)
    assert big > 5 * small


def test_refuses_row_count_mismatch(tmp_path):
    d = _run(tmp_path, 10, frames=11)
    with pytest.raises(SystemExit, match="10 dong"):
        rg.main(["--run", str(d), "--out", str(tmp_path / "o.json")])
