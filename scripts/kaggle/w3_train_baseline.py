#!/usr/bin/env python3
"""E1 W3 Kaggle job 04: train baseline A (Ultralytics YOLO) tren du lieu e1-yolo-v1 va danh gia tren val.

Chay tren Kaggle GPU. Huong dan: docs/w3/W3_PLAN.md muc D.

    python w3_train_baseline.py --data-dir /kaggle/input/e1-yolo-v1/e1-yolo-v1 \
        --config baseline_A.yaml --out /kaggle/working --commit <sha>

Stage: env -> data -> train -> val -> metrics -> artefacts -> weights -> bundle (ghi stage_status.json).
Khong dung split test. Weights khong nam trong zip bang chung; tai rieng best.pt/last.pt len Drive + SHA-256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import platform
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

LOG = logging.getLogger("w3_train")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def as_float(x):
    try:
        return round(float(x), 5)
    except Exception:
        return None


def stage_env(ev: Path, commit: str, cfg_path: Path) -> dict:
    info = {"python": sys.version, "platform": platform.platform(), "commit": commit,
            "config_file": cfg_path.name, "config_sha256": sha256(cfg_path)}
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
    except Exception as exc:  # noqa: BLE001
        info["torch"] = f"MISSING ({exc})"
    try:
        import ultralytics
        info["ultralytics"] = ultralytics.__version__
    except Exception as exc:  # noqa: BLE001
        info["ultralytics"] = f"MISSING ({exc})"
    try:
        info["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=20).stdout.strip() or "none"
    except Exception:
        info["nvidia_smi"] = "none/unavailable"
    (ev / "env.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    return info


def stage_data(data_dir: Path, ev: Path, cfg: dict) -> dict:
    import yaml
    if (data_dir / "images" / "test").exists():
        raise RuntimeError("Du lieu co images/test: test phai bi khoa, dung lai")
    for sp in ("train", "val"):
        if not any((data_dir / "images" / sp).glob("*.jpg")):
            raise RuntimeError(f"Khong co anh trong images/{sp}")
    card = json.loads((data_dir / "dataset_card.json").read_text(encoding="utf-8"))
    if cfg.get("dataset_version") and card.get("dataset_version") != cfg["dataset_version"]:
        raise RuntimeError(f"dataset_version lech: config={cfg['dataset_version']} card={card.get('dataset_version')}")
    d = yaml.safe_load((data_dir / "data.yaml").read_text(encoding="utf-8"))
    d["path"] = str(data_dir.resolve())
    runtime = ev.parent / "data_runtime.yaml"
    runtime.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    shutil.copy2(data_dir / "dataset_card.json", ev / "dataset_card.json")
    return {"data_yaml": str(runtime), "dataset_version": card.get("dataset_version"),
            "fingerprint": card.get("content_fingerprint_sha256"), "images": card.get("images"),
            "train_images": len(list((data_dir / "images" / "train").glob("*.jpg"))),
            "val_images": len(list((data_dir / "images" / "val").glob("*.jpg")))}


def stage_train(cfg: dict, data_yaml: str, runs: Path) -> dict:
    from ultralytics import YOLO
    model = YOLO(cfg["model"])
    model.train(data=data_yaml, project=str(runs), name=cfg["experiment"], exist_ok=True, **cfg.get("train", {}))
    wdir = runs / cfg["experiment"] / "weights"
    if not (wdir / "best.pt").is_file():
        raise RuntimeError(f"khong thay best.pt trong {wdir}")
    return {"train_dir": str(runs / cfg["experiment"])}


def stage_val(cfg: dict, data_yaml: str, runs: Path):
    from ultralytics import YOLO
    best = runs / cfg["experiment"] / "weights" / "best.pt"
    vcfg = dict(cfg.get("val", {}))
    vcfg["split"] = "val"                       # khong cho phep doi sang test o W3
    return YOLO(str(best)).val(data=data_yaml, project=str(runs), name=cfg["experiment"] + "_val", exist_ok=True, **vcfg)


def stage_metrics(m, ev: Path, cfg: dict) -> dict:
    box = m.box
    names = m.names if isinstance(m.names, dict) else dict(enumerate(m.names))
    rows = []
    idx = list(getattr(box, "ap_class_index", []))
    for k, c in enumerate(idx):
        rows.append({"class_id": int(c), "class_name": names.get(int(c), str(c)),
                     "precision": as_float(box.p[k]), "recall": as_float(box.r[k]),
                     "ap50": as_float(box.ap50[k]), "ap50_95": as_float(box.ap[k])})
    with (ev / "baseline_A_val_per_class.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["class_id", "class_name", "precision", "recall", "ap50", "ap50_95"])
        w.writeheader(); w.writerows(rows)
    overall = {"experiment": cfg["experiment"], "split": "val", "precision_mean": as_float(box.mp),
               "recall_mean": as_float(box.mr), "map50": as_float(box.map50), "map50_95": as_float(box.map),
               "speed_ms_per_image": {k: as_float(v) for k, v in (getattr(m, "speed", {}) or {}).items()},
               "note": "Danh gia tren VAL; val cung dung de dung som/chon best.pt nen so lieu lac quan. Test bi khoa."}
    (ev / "baseline_A_val_metrics.json").write_text(json.dumps({"overall": overall, "per_class": rows}, indent=2,
                                                                ensure_ascii=False), encoding="utf-8")
    return {"map50": overall["map50"], "map50_95": overall["map50_95"]}


def stage_artefacts(runs: Path, ev: Path, cfg: dict) -> dict:
    copied = []
    for sub, pats in ((cfg["experiment"], ("results.csv", "results.png", "args.yaml", "*curve*.png", "confusion_matrix*.png",
                                           "labels*.jpg", "labels*.png")),
                      (cfg["experiment"] + "_val", ("*curve*.png", "confusion_matrix*.png", "predictions.json"))):
        src = runs / sub
        dst = ev / ("train" if sub == cfg["experiment"] else "val")
        dst.mkdir(parents=True, exist_ok=True)
        for pat in pats:
            for p in sorted(src.glob(pat)):
                shutil.copy2(p, dst / p.name); copied.append(f"{dst.name}/{p.name}")
    if not any(c.endswith("results.csv") for c in copied):
        raise RuntimeError("khong co results.csv (learning curves)")
    return {"files": len(copied)}


def stage_weights(runs: Path, ev: Path, cfg: dict) -> dict:
    out = {}
    for name in ("best.pt", "last.pt"):
        p = runs / cfg["experiment"] / "weights" / name
        if p.is_file():
            out[name] = {"sha256": sha256(p), "bytes": p.stat().st_size, "kaggle_path": str(p), "drive_link": ""}
    (ev / "weights_manifest.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return {k: v["sha256"][:12] for k, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, required=True, help="thu muc chua data.yaml, images/, labels/, dataset_card.json")
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working"))
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--model-override", default="", help="chi de kiem thu (vd yolov8n.yaml); khong dung cho run chinh thuc")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import yaml
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if args.model_override:
        cfg["model"] = args.model_override
    ev = args.out / "w3_train_evidence"; runs = (args.out / "runs").resolve()  # tuyet doi: Ultralytics 8.4 them "detect/" neu duong dan tuong doi
    if ev.exists():
        shutil.rmtree(ev)
    ev.mkdir(parents=True)
    shutil.copy2(args.config, ev / args.config.name)
    status: dict = {}

    def run(name, fn):
        try:
            res = fn()
            status[name] = {"status": "OK", **(res if isinstance(res, dict) else {})}
            return res
        except Exception as exc:  # noqa: BLE001
            LOG.error("stage %s FAILED: %s", name, exc)
            status[name] = {"status": "FAILED", "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
            return None
        finally:
            (ev / "stage_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    run("env", lambda: stage_env(ev, args.commit, args.config))
    data = run("data", lambda: stage_data(args.data_dir, ev, cfg))
    if data and run("train", lambda: stage_train(cfg, data["data_yaml"], runs)):
        m = None
        def _val():
            nonlocal m
            m = stage_val(cfg, data["data_yaml"], runs)
            return {}
        if run("val", _val) is not None:
            run("metrics", lambda: stage_metrics(m, ev, cfg))
        run("artefacts", lambda: stage_artefacts(runs, ev, cfg))
        run("weights", lambda: stage_weights(runs, ev, cfg))

    def bundle():
        z = args.out / "w3_train_evidence.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(ev.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(ev.parent))
        return {"zip": z.name, "sha256": sha256(z)}
    run("bundle", bundle)
    print(json.dumps({k: v.get("status") for k, v in status.items()}, indent=2))
    return 0 if all(v.get("status") == "OK" for v in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
