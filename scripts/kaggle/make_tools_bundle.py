#!/usr/bin/env python3
"""Dung thu muc dataset tools cho Kaggle tu repo, giu cau truc thu muc, kem TOOLS_MANIFEST.json (commit + SHA-256 tung tep).

Tu W9 thay cho viec them/thay tung tep bang tay vao e1-w3-tools. Dung cho ca chay tay (nen thu muc roi tai len) va
GitHub Actions (kaggle datasets version -p <out>) - ADR-0016.

    python scripts/kaggle/make_tools_bundle.py --out build/e1-w9-tools [--zip]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ["scripts/pipeline/*.py", "scripts/alert/*.py", "scripts/kaggle/*.py", "scripts/tracking/offline_track.py",
           "configs/tracker_bytetrack_e1.yaml", "configs/roi_w6.yaml", "configs/alert_e1.yaml",
           "results/W08/kaggle_run_17/media_manifest.json", "results/W08/kaggle_run_17/w8_run17/meta.csv",
           "data/manifests/fbd_sv_2024_zip_contents_sha256.csv"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--zip", action="store_true", help="them <out>.zip de tai len giao dien web Kaggle")
    a = ap.parse_args()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "UNKNOWN"
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *{p.split("/")[0] for p in INCLUDE}], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    if a.out.exists():
        shutil.rmtree(a.out)
    files = sorted({f for pat in INCLUDE for f in ROOT.glob(pat) if f.is_file() and "__pycache__" not in f.parts})
    if not files:
        raise SystemExit("khong co tep nao")
    for f in files:
        dst = a.out / f.relative_to(ROOT); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
    man = {"commit": commit, "dirty_worktree": dirty, "files": [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha256(f)} for f in files]}
    (a.out / "TOOLS_MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    if a.zip:
        z = a.out.with_suffix(".zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(a.out.rglob("*")):
                zf.write(p, p.relative_to(a.out))
        print("zip", z)
    print(f"{len(files)} tep, commit {commit[:12]}{' (CO THAY DOI CHUA COMMIT)' if dirty else ''}")
    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main())
