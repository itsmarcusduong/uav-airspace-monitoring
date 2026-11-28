"""W9: chay ca ham main cua job Kaggle (benchmark e1pipe, FBD-SV neg_eval) voi detector gia va video tong hop."""
import csv
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in ("scripts/pipeline", "scripts/alert", "scripts/kaggle"):
    sys.path.insert(0, str(ROOT / sub))
import e1pipe  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="can ffmpeg")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mkvideo(p: Path, w, h, fps, n):
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate={fps}", "-frames:v", str(n),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)], check=True)


class FakeDet:
    """Detector gia: mot hop Drone di ngang qua giua khung (frame dem theo so lan goi)."""
    def __init__(self, weights, conf=0.1, iou=0.5, imgsz=640, device="0", quantize=None):
        self.f = 0; self.kw = dict(weights=weights, device=device, quantize=quantize)

    def __call__(self, frame):
        h, w = frame.shape[:2]; x = 10 + 5 * (self.f % 120); self.f += 1
        return np.array([[x, h / 2 - 10, x + 20, h / 2 + 10, 0.8, 2]], dtype=np.float32)


@pytest.fixture()
def tools(tmp_path):
    t = tmp_path / "tools"
    subprocess.run([sys.executable, str(ROOT / "scripts/kaggle/make_tools_bundle.py"), "--out", str(t)], check=False, capture_output=True)
    assert (t / "scripts/pipeline/e1pipe.py").is_file() and (t / "TOOLS_MANIFEST.json").is_file()
    return t


def test_bench_main_cpu_with_fake_detector(tmp_path, tools, monkeypatch):
    import w9_e1pipe_bench as wb
    data = tmp_path / "raw"; vids = ["V_DRONE_901", "V_BIRD_902"]
    for v in vids:
        mkvideo(data / "Data/Video_V" / f"{v}.mp4", 640, 512, 30, 45)
    r17 = tools / "results/W08/kaggle_run_17"
    with (r17 / "w8_run17/meta.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["video_id", "class_name", "frames", "fps", "width", "height"])
        w.writerows([[vids[0], "Drone", 45, 30.0, 640, 512], [vids[1], "Bird", 45, 30.0, 640, 512]])
    (r17 / "media_manifest.json").write_text(json.dumps({"files": [{"video_id": v, "src_sha256": sha(data / "Data/Video_V" / f"{v}.mp4")} for v in vids]}))
    wt = tmp_path / "best.pt"; wt.write_bytes(b"fake")
    monkeypatch.setattr(e1pipe, "UltralyticsDetector", FakeDet)
    out = tmp_path / "out"
    argv = ["x", "--data-root", str(data), "--tools", str(tools), "--weights", str(wt), "--weights-sha", sha(wt), "--config", "CPU",
            "--rep", "1", "--save-outputs", "--out", str(out), "--commit", "test"]
    monkeypatch.setattr(sys, "argv", argv)
    assert wb.main() == 0
    ev = out / "w9_CPU_rep1"
    st = json.loads((ev / "stage_status.json").read_text())
    assert all(v["status"] == "OK" for v in st.values()) and {"inputs", "env", "run", "detect", "dump", "summary"} <= set(st)
    s = json.loads((ev / "summary.json").read_text())
    assert s["frames"] == 90 and s["latency_ms"]["frames_measured"] == 60 and s["latency_ms"]["total"]["p95"] > 0
    with gzip.open(ev / "latency.csv.gz", "rt") as fh:
        assert sum(1 for _ in fh) == 91
    for v in vids:
        assert (ev / "tracks/tracker_bytetrack_e1" / f"{v}.csv").is_file() and (ev / "dets" / f"{v}.csv").is_file()
    assert (out / "w9_CPU_rep1_evidence.zip").is_file()
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit, match="da ton tai"):
        wb.main()
    (data / "Data/Video_V" / f"{vids[0]}.mp4").write_bytes(b"hong")         # video bi doi -> dung
    monkeypatch.setattr(sys, "argv", argv + ["--overwrite"])
    with pytest.raises(SystemExit, match="SHA-256 khac"):
        wb.main()


def test_bench_c2_exports_from_writable_copy(tmp_path, monkeypatch):
    """Run 18: Ultralytics ghi best.onnx canh weights trong /kaggle/input (chi doc) -> C2 that bai. Phai xuat tu ban sao."""
    import ultralytics
    import w9_e1pipe_bench as wb
    ro = tmp_path / "ro"; ro.mkdir(); wt = ro / "best.pt"; wt.write_bytes(b"fake")
    seen = {}

    class FakeYOLO:
        def __init__(self, path):
            seen["src"] = Path(path)

        def export(self, **kw):
            assert seen["src"].parent != ro and kw["format"] == "engine" and kw["half"] and kw["imgsz"] == 640
            e = seen["src"].with_suffix(".engine"); e.write_bytes(b"engine"); return str(e)
    monkeypatch.setattr(ultralytics, "YOLO", FakeYOLO)
    eng = wb.export_engine(wt, sha(wt), tmp_path / "cache" / "best.engine")
    assert eng.read_bytes() == b"engine" and sha(tmp_path / "cache/best.pt") == sha(wt) and seen["src"] == tmp_path / "cache/best.pt"
    with pytest.raises(RuntimeError, match="SHA-256"):
        wb.export_engine(wt, "0" * 64, tmp_path / "cache2" / "best.engine")


def test_neg_main_normalizes_and_counts(tmp_path, tools, monkeypatch):
    import w9_neg_fbdsv as wn
    fbd = tmp_path / "fbd" / "FBD-SV-2024" / "FBD-SV-2024" / "videos" / "train"
    mkvideo(fbd / "bird_1.mp4", 1280, 720, 25, 50)
    mkvideo(fbd / "bird_2.mp4", 1280, 720, 25, 25)
    rows = [{"path": f"FBD-SV-2024/videos/train/bird_{i}.mp4", "bytes": 0, "sha256": sha(fbd / f"bird_{i}.mp4")} for i in (1, 2)]
    rows += [{"path": f"FBD-SV-2024/videos/val/zz_{i:03d}.mp4", "bytes": 0, "sha256": "0" * 64} for i in range(481)]
    with (tools / "data/manifests/fbd_sv_2024_zip_contents_sha256.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"]); w.writeheader(); w.writerows(rows)
    wt = tmp_path / "best.pt"; wt.write_bytes(b"fake")
    monkeypatch.setattr(e1pipe, "UltralyticsDetector", FakeDet)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["x", "--fbd-root", str(tmp_path / "fbd"), "--tools", str(tools), "--weights", str(wt), "--weights-sha", sha(wt),
                                      "--device", "cpu", "--max-clips", "2", "--work", str(tmp_path / "work"), "--out", str(out), "--commit", "test"])
    assert wn.main() == 0
    ev = out / "w9_neg_fbdsv"
    s = json.loads((ev / "neg_summary.json").read_text())
    pc = list(csv.DictReader((ev / "per_clip.csv").open()))
    assert s["clips"] == 2 and [r["src_fps"] for r in pc] == ["25.0", "25.0"]
    assert [int(r["frames"]) for r in pc] == [60, 30]                      # 25 -> 30 fps: 2 s -> 60 frame, 1 s -> 30 frame
    assert s["R0"]["false_alerts"] >= 1 and s["frac_frames_drone_det"] > 0.5  # detector gia luon thay Drone -> canh bao sai
    assert not (tmp_path / "work").exists()                                # video chuan hoa khong de lai
    assert not list(ev.rglob("*.mp4")) and not list(ev.rglob("*.jpg"))


def test_neg_main_stops_on_ffmpeg_timeout_and_logs_progress(tmp_path, tools, monkeypatch, capsys):
    """Run 19 lan dau im lang 3,3 gio: ffmpeg/ffprobe phai co timeout, stage_status ghi FAIL kem clip; job in tien do."""
    import subprocess
    import w9_neg_fbdsv as wn
    fbd = tmp_path / "fbd" / "FBD-SV-2024" / "videos" / "train"
    mkvideo(fbd / "bird_1.mp4", 1280, 720, 25, 25)
    rows = [{"path": "FBD-SV-2024/videos/train/bird_1.mp4", "bytes": 0, "sha256": sha(fbd / "bird_1.mp4")}]
    rows += [{"path": f"FBD-SV-2024/videos/val/zz_{i:03d}.mp4", "bytes": 0, "sha256": "0" * 64} for i in range(482)]
    with (tools / "data/manifests/fbd_sv_2024_zip_contents_sha256.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"]); w.writeheader(); w.writerows(rows)
    wt = tmp_path / "best.pt"; wt.write_bytes(b"fake")
    real = subprocess.run

    def hang(cmd, *a, **k):
        if cmd[0] == "ffmpeg":
            assert k.get("timeout") == wn.CMD_TIMEOUT_S
            raise subprocess.TimeoutExpired(cmd, k["timeout"])
        return real(cmd, *a, **k)
    monkeypatch.setattr(wn.subprocess, "run", hang)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["x", "--fbd-root", str(tmp_path / "fbd"), "--tools", str(tools), "--weights", str(wt), "--weights-sha", sha(wt),
                                      "--device", "cpu", "--max-clips", "1", "--work", str(tmp_path / "work"), "--out", str(out), "--commit", "test"])
    with pytest.raises(SystemExit, match="ffmpeg qua"):
        wn.main()
    st = json.loads((out / "w9_neg_fbdsv" / "stage_status.json").read_text())
    assert st["normalize"]["status"] == "FAIL" and st["normalize"]["clip"] == "train/bird_1"
    assert "[normalize] bat dau 1 clip" in capsys.readouterr().out


def test_run19_notebook_relays_log_and_smoke_runs_first():
    nb = json.loads((ROOT / "scripts/kaggle/notebooks/w9_run19_neg_fbdsv.ipynb").read_text(encoding="utf-8"))
    code = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    i_smoke = next(i for i, s in enumerate(code) if '"--max-clips", "10"' in s)
    i_full = next(i for i, s in enumerate(code) if 'run_logged(BASE + ["--out", "/kaggle/working"])' in s)
    assert i_smoke < i_full and "subprocess.Popen" in code[i_smoke] and "assert rc_smoke == 0" in code[i_smoke]
    assert "/tmp/e1_smoke" in code[i_smoke]                                 # ket qua chay thu khong vao Output


def test_w9_notebooks_parse_and_read_real_keys():
    """Moi o code cua notebook W9 phai dung cu phap; cac khoa notebook doc phai co trong dau ra that cua job (xem test o tren)."""
    import ast
    import re
    keys = set()
    for n in ("w9_run18_bench.ipynb", "w9_run19_neg_fbdsv.ipynb", "w9_run20_stability.ipynb"):
        nb = json.loads((ROOT / "scripts/kaggle/notebooks" / n).read_text(encoding="utf-8"))
        for c in nb["cells"]:
            if c["cell_type"] == "code":
                src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
                ast.parse("\n".join(l for l in src.splitlines() if not l.lstrip().startswith("!")))
                keys |= set(re.findall(r'(?:s|sb|tm|st)\.get\("([a-z_0-9]+)"', src)) | set(re.findall(r'(?:\bs|tm)\["([a-z_0-9]+)"\]', src))
    known = {"frames", "fps_excl_warmup", "latency_ms", "stability", "memory_samples", "minutes", "rss_ratio",   # summary.json
             "clips", "R1", "R0", "frac_frames_drone_det", "adr0011_trigger",                                    # neg_summary.json
             "commit", "dirty_worktree", "files"}                                                                 # TOOLS_MANIFEST.json
    assert keys <= known, keys - known


def test_actions_runner_fills_notebook_and_metadata(tmp_path):
    import actions_kaggle_run as ak
    nb = json.loads((ROOT / "scripts/kaggle/notebooks/w9_run20_stability.ipynb").read_text(encoding="utf-8"))
    out = ak.fill_notebook(nb, {"COMMIT": "a" * 40, "RUNNER": "github-actions", "CONFIG": "C1"})
    src = "".join("".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in out["cells"] if c["cell_type"] == "code")
    assert 'COMMIT = "' + "a" * 40 + '"' in src and 'RUNNER = "github-actions"' in src and 'CONFIG = "C1"' in src
    with pytest.raises(SystemExit, match="xuat hien 0 lan"):
        ak.fill_notebook(nb, {"KHONG_CO": "x"})
    m = ak.kernel_metadata("run19_neg_fbdsv", "minhquangdng/e1-w9-run19-neg-fbdsv")
    assert m["is_private"] and m["enable_gpu"] and "minhquangdng/e1-fbd-sv-2024" in m["dataset_sources"] and m["kernel_sources"] == ["minhquangdng/e1-w5-run13"]
