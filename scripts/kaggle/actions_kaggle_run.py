#!/usr/bin/env python3
"""Chay mot job Kaggle tu GitHub Actions (ADR-0016; docs/w9/W9_PLAN.md muc E). Chi duoc goi tu workflow bam tay.

Cac buoc:
  1. dung dataset tools tu repo dung commit (make_tools_bundle.py) -> mot tep e1-w9-tools.zip -> kaggle datasets version;
  2. chep notebook, dien COMMIT / RUNNER / CONFIG bang thay the co kiem (khong sua tay) -> kernel-metadata.json
     (dataset_sources, kernel_sources, GPU) -> kaggle kernels push;
  3. cho trang thai complete/error (toi da --timeout-min);
  4. kaggle kernels output -> SHA-256 tung tep -> ACTIONS_OUTPUT_MANIFEST.json (workflow tai len lam artifact).
Ket qua KHONG tu commit vao repo. Du lieu (Svanstrom, FBD-SV) khong di qua runner: notebook doc dataset Kaggle co san.

    python scripts/kaggle/actions_kaggle_run.py --job run18_bench --commit <sha> --out out
Can bien moi truong KAGGLE_USERNAME, KAGGLE_KEY (GitHub Secrets do Quang them).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER = "minhquangdng"
TOOLS_DATASET = f"{USER}/e1-w9-tools"
JOBS = {
    "run18_bench": {"notebook": "w9_run18_bench.ipynb", "datasets": [TOOLS_DATASET, f"{USER}/e1-svanstrom-raw"], "gpu": True},
    "run19_neg_fbdsv": {"notebook": "w9_run19_neg_fbdsv.ipynb", "datasets": [TOOLS_DATASET, f"{USER}/e1-fbd-sv-2024"], "gpu": True},
    "run20_stability": {"notebook": "w9_run20_stability.ipynb", "datasets": [TOOLS_DATASET, f"{USER}/e1-svanstrom-raw"], "gpu": True},
}
KERNEL_SOURCES = [f"{USER}/e1-w5-run13"]                 # best.pt yolo11n_640_s20261030


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def fill_notebook(nb: dict, values: dict[str, str]) -> dict:
    """Thay dong `NAME = ...` dau tien cua moi bien trong o code dau tien co bien do. Moi bien phai xuat hien dung mot lan."""
    for name, val in values.items():
        hits = 0
        for c in nb["cells"]:
            if c["cell_type"] != "code":
                continue
            src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
            new, k = re.subn(rf'^{name} = "[^"\n]*"', f'{name} = "{val}"', src, count=1, flags=re.M)
            if k:
                c["source"] = new; hits += k
        if hits != 1:
            raise SystemExit(f"notebook: bien {name} xuat hien {hits} lan (can dung 1)")
    return nb


def kernel_metadata(job: str, slug: str) -> dict:
    j = JOBS[job]
    return {"id": slug, "title": slug.split("/", 1)[1], "code_file": j["notebook"], "language": "python", "kernel_type": "notebook",
            "is_private": True, "enable_gpu": j["gpu"], "enable_internet": True, "dataset_sources": j["datasets"],
            "kernel_sources": KERNEL_SOURCES, "competition_sources": [], "machine_shape": "NvidiaTeslaT4" if j["gpu"] else "None"}


def sh(*cmd: str, check: bool = True) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    print("$", " ".join(cmd), "\n", r.stdout[-2000:], r.stderr[-2000:], flush=True)
    if check and r.returncode != 0:
        raise SystemExit(f"loi: {' '.join(cmd)}")
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job", choices=["check", *JOBS], required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--config", default="", help="run20_stability: C0/C1/C2")
    ap.add_argument("--tag", default="", help="nhan run (ADR-0016 muc 2), vd. b2: tao notebook Kaggle rieng e1-w9-<job>-<tag>, khong ghi de notebook dang chay")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--timeout-min", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true", help="chi dung thu muc, khong goi Kaggle (kiem thu)")
    a = ap.parse_args()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if head != a.commit:
        raise SystemExit(f"checkout {head[:12]} khac --commit {a.commit[:12]}")
    if a.job == "check":                                  # chi kiem ket noi va quyen doc cac dataset private
        a.out.mkdir(parents=True, exist_ok=True)
        res = {d: sh("kaggle", "datasets", "status", d, check=False).strip()[-80:]
               for d in (TOOLS_DATASET, f"{USER}/e1-svanstrom-raw", f"{USER}/e1-fbd-sv-2024")}
        for d, s in res.items():
            print(f"{d}: {s}")
        (a.out / "ACTIONS_OUTPUT_MANIFEST.json").write_text(json.dumps({"job": "check", "commit": a.commit, "datasets": res}, indent=2) + "\n")
        return 0 if all("ready" in s.lower() for s in res.values()) else 1
    if a.job == "run20_stability" and a.config not in ("C0", "C1", "C2"):
        raise SystemExit("run20_stability can --config C0/C1/C2")
    build = a.out / "_build"
    shutil.rmtree(build, ignore_errors=True)
    tools = build / "tools_src"
    if subprocess.run([sys.executable, str(ROOT / "scripts/kaggle/make_tools_bundle.py"), "--out", str(tools), "--zip"]).returncode != 0:
        raise SystemExit("make_tools_bundle that bai (worktree khong sach?)")
    ds = build / "tools_dataset"; ds.mkdir(parents=True)
    shutil.move(str(tools.with_suffix(".zip")), ds / "e1-w9-tools.zip")
    (ds / "dataset-metadata.json").write_text(json.dumps({"id": TOOLS_DATASET, "title": "e1-w9-tools", "licenses": [{"name": "other"}]}))
    kd = build / "kernel"; kd.mkdir()
    nb = json.loads((ROOT / "scripts/kaggle/notebooks" / JOBS[a.job]["notebook"]).read_text(encoding="utf-8"))
    vals = {"COMMIT": a.commit, "RUNNER": "github-actions"}
    if a.job == "run20_stability":
        vals["CONFIG"] = a.config
    (kd / JOBS[a.job]["notebook"]).write_text(json.dumps(fill_notebook(nb, vals), ensure_ascii=False, indent=1), encoding="utf-8")
    if a.tag and not re.fullmatch(r"[a-z0-9]{1,12}", a.tag):
        raise SystemExit("--tag chi gom a-z, 0-9, toi da 12 ky tu")
    slug = f"{USER}/e1-w9-{a.job.replace('_', '-')}" + (f"-{a.tag}" if a.tag else "")
    (kd / "kernel-metadata.json").write_text(json.dumps(kernel_metadata(a.job, slug), indent=2))
    if a.dry_run:
        print("dry-run:", build)
        return 0
    kdir = Path.home() / ".kaggle"
    if not (os.environ.get("KAGGLE_API_TOKEN") or (kdir / "access_token").is_file() or (kdir / "kaggle.json").is_file()):
        raise SystemExit("chua co khoa Kaggle (buoc actions_kaggle_auth.py)")
    sh("kaggle", "datasets", "version", "-p", str(ds), "-m", f"commit {a.commit} (GitHub Actions run {os.environ.get('GITHUB_RUN_ID', '')})")
    for _ in range(60):                                   # cho dataset xu ly xong
        if "ready" in sh("kaggle", "datasets", "status", TOOLS_DATASET, check=False).lower():
            break
        time.sleep(30)
    else:
        raise SystemExit("dataset tools chua san sang sau 30 phut")
    sh("kaggle", "kernels", "push", "-p", str(kd))
    t0 = time.time(); state = ""
    while time.time() - t0 < a.timeout_min * 60:
        time.sleep(60)
        state = sh("kaggle", "kernels", "status", slug, check=False).lower()
        if "complete" in state or "error" in state or "cancel" in state:
            break
    res = a.out / "kernel_output"; res.mkdir(parents=True, exist_ok=True)
    sh("kaggle", "kernels", "output", slug, "-p", str(res), check=False)
    files = sorted(p for p in res.rglob("*") if p.is_file())
    man = {"job": a.job, "commit": a.commit, "tag": a.tag, "kernel": slug, "final_status": state.strip()[-200:], "actions_run_id": os.environ.get("GITHUB_RUN_ID", ""),
           "kaggle_cli": sh("kaggle", "--version", check=False).strip(),
           "files": [{"path": p.relative_to(res).as_posix(), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files]}
    (a.out / "ACTIONS_OUTPUT_MANIFEST.json").write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.rmtree(build, ignore_errors=True)
    return 0 if "complete" in state else 1


if __name__ == "__main__":
    sys.exit(main())
