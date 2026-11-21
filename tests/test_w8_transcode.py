"""W8-02 (#115): job Kaggle ma hoa lai video val sang H.264 cho dashboard (scripts/kaggle/w8_transcode_media.py)."""
import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
def test_transcode_media_keeps_frames_fps_size(tmp_path, monkeypatch):
    """Job Kaggle W8: ma hoa H.264 tren video tong hop, giu so frame/fps/kich thuoc; tu choi split test."""
    import shutil as sh
    if not (sh.which("ffmpeg") and sh.which("ffprobe")):
        pytest.skip("khong co ffmpeg")
    import cv2
    import numpy as np
    sys.path.insert(0, str(ROOT / "scripts" / "kaggle"))
    import w3_export_yolo
    import w8_transcode_media as tm
    vdir = tmp_path / "raw/Data/Video_V"; vdir.mkdir(parents=True)
    vw = cv2.VideoWriter(str(vdir / "V_DRONE_001.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (64, 48))
    for i in range(31):
        vw.write(np.full((48, 64, 3), (i * 7) % 255, np.uint8))
    vw.release()
    man = tmp_path / "m.csv.gz"
    with gzip.open(man, "wt", encoding="utf-8", newline="") as fh:
        fh.write("image,split,video_id\nimages/val/a.jpg,val,V_DRONE_001\nimages/train/b.jpg,train,V_BIRD_009\n")
    monkeypatch.setattr(w3_export_yolo, "find_video_dir", lambda root: tmp_path / "raw/Data")
    out = tmp_path / "w8_media"
    monkeypatch.setattr(sys, "argv", ["x", "--data-root", str(tmp_path), "--manifest", str(man), "--out", str(out)])
    assert tm.main() == 0
    m = json.loads((out / "media_manifest.json").read_text())
    f = m["files"][0]
    assert m["videos"] == 1 and f["out"]["codec"] == "h264" and f["out"]["frames"] == 31 and f["same_frames_fps_size"]
    assert (tmp_path / "w8_media.zip").is_file()
    monkeypatch.setattr(sys, "argv", ["x", "--data-root", str(tmp_path), "--manifest", str(man), "--split", "test"])
    with pytest.raises(SystemExit):
        tm.main()


def test_ffmpeg_cmd_old_version_uses_vsync():
    sys.path.insert(0, str(ROOT / "scripts" / "kaggle"))
    import w8_transcode_media as tm
    assert "-vsync" in tm.ffmpeg_cmd(Path("a"), Path("b"), 23, 4) and "-fps_mode" in tm.ffmpeg_cmd(Path("a"), Path("b"), 23, 6)
