#!/usr/bin/env python3
"""Tao thu muc Evidence/WXX theo cau truc GVHD yeu cau (tu W4):

    Evidence/WXX/README.md, metrics.csv, test-results.json (+ test-results.xml neu co pytest), figures/, manifest.json

Moi so lieu doc tu file ket qua da co trong repo (results/, data/, docs/); khong nhap tay so lieu.
Moi kiem tra trong test-results.json duoc CHAY LAI luc tao (doc file, so khop gia tri), khong chep tu bao cao.

    python scripts/reporting/build_evidence.py --weeks W01 W02 W03 W04 [--pytest-xml <junit.xml>]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "https://github.com/itsmarcusduong/uav-airspace-monitoring"
FIELDS = ["week", "metric", "value", "unit", "split", "model", "source", "producer", "run_commit"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rjson(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def rcsv(rel: str) -> list[dict]:
    p = ROOT / rel
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def git_head() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


class Week:
    def __init__(self, week: str):
        self.week = week
        self.dir = ROOT / "Evidence" / week
        self.metrics: list[dict] = []
        self.checks: list[dict] = []
        self.figures: list[tuple[Path, str]] = []
        self.sources: set[str] = set()
        self.external: list[dict] = []

    def m(self, metric, value, unit="", split="", model="", source="", producer="", run_commit=""):
        self.metrics.append({"week": self.week, "metric": metric, "value": value, "unit": unit, "split": split, "model": model,
                             "source": source, "producer": producer, "run_commit": run_commit})
        if source:
            self.sources.add(source)

    def check(self, name, ok, detail="", source=""):
        self.checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail, "source": source})
        if source:
            self.sources.add(source)

    def fig(self, rel: str, caption: str):
        if (ROOT / rel).is_file():
            self.figures.append((ROOT / rel, caption)); self.sources.add(rel)


# ----------------------------------------------------------------------------- W01
def w01(w: Week):
    man = rcsv("data/manifests/dataset_manifest_v1.csv")
    lic = rcsv("data/manifests/license_matrix.csv")
    idx = rcsv("data/samples/index_100_frames.csv")
    w.m("datasets_surveyed", len(man), "dataset", source="data/manifests/dataset_manifest_v1.csv", producer="scripts/dataset/build_manifest.py")
    w.m("license_rows_usable", sum(r["status"] == "usable" for r in lic), "row", source="data/manifests/license_matrix.csv")
    w.m("license_rows_needs_review_or_fallback", sum(r["status"] != "usable" for r in lic), "row", source="data/manifests/license_matrix.csv")
    w.m("sample_frames", len(idx), "frame", source="data/samples/index_100_frames.csv", producer="scripts/dataset/extract_samples.py")
    vid_col = next(c for c in idx[0] if c in ("video_id", "source_id"))
    w.m("sample_source_videos", len({r[vid_col] for r in idx}), "video", source="data/samples/index_100_frames.csv")
    sid = [r["sample_id"] for r in idx]
    w.check("manifest_has_required_columns", {"dataset_id", "dataset_name", "source_url", "license"} <= set(man[0]),
            f"{len(man[0])} cot", "data/manifests/dataset_manifest_v1.csv")
    w.check("manifest_unique_dataset_ids", len({r["dataset_id"] for r in man}) == len(man), f"{len(man)} dong", "data/manifests/dataset_manifest_v1.csv")
    w.check("samples_exactly_100", len(idx) == 100, f"{len(idx)} dong", "data/samples/index_100_frames.csv")
    w.check("samples_unique_ids", len(set(sid)) == len(sid), "", "data/samples/index_100_frames.csv")
    w.check("license_every_row_has_status", all(r["status"] in ("usable", "needs_review", "fallback") for r in lic),
            str(Counter(r["status"] for r in lic)), "data/manifests/license_matrix.csv")
    w.check("w1_validation_report_passed", "Validation passed" in (ROOT / "docs/w1/validation_report.md").read_text(encoding="utf-8"),
            "validate_manifest.py ngay 2026-10-04 (anh mau khong luu trong Git)", "docs/w1/validation_report.md")
    cls_col = next((c for c in idx[0] if c in ("class_names", "class_name")), None)
    if cls_col:
        _bar(w, Counter(r[cls_col] for r in idx), "fig_w01_sample_classes.png", "Số frame mẫu theo lớp (index_100_frames.csv)", "số frame")


# ----------------------------------------------------------------------------- W02
def w02(w: Week):
    st = rjson("results/W02/kaggle_run_01/stage_status.json")
    au = rjson("results/W02/kaggle_run_01/annotation_audit_summary.json")
    sp = rjson("data/splits/video_split_v1_manifest.json")
    src_s, src_a, src_p = "results/W02/kaggle_run_01/stage_status.json", "results/W02/kaggle_run_01/annotation_audit_summary.json", "data/splits/video_split_v1_manifest.json"
    t = st["totals"]
    w.m("videos", t["videos"], "video", source=src_s, producer="scripts/kaggle/w2_eda_audit_split.py")
    w.m("frames_decoded", t["frames_decoded"], "frame", source=src_s, producer="scripts/kaggle/w2_eda_audit_split.py")
    for k, v in t["by_modality"].items():
        w.m(f"videos_{k}", v, "video", source=src_s)
    for k, v in t["by_class"].items():
        w.m(f"videos_{k}", v, "video", source=src_s)
    w.m("checksum_files_checked", st["checksums"]["checked"], "file", source=src_s)
    w.m("checksum_mismatch", st["checksums"]["mismatch"], "file", source=src_s)
    for k, v in au["issue_counts"].items():
        w.m(f"audit_{k}", v, "video", source=src_a)
    for k, v in sp["counts"].items():
        w.m("split_videos", v, "video", split=k, source=src_p, producer="scripts/dataset/make_video_split.py")
    ls = sp["leakage_screen"]
    w.m("near_duplicate_pairs_across_splits", ls["near_duplicate_pairs_across_splits"], "pair", source=src_p)
    w.check("kaggle_run01_all_stages_ok", all(v == "OK" for v in st["stages"].values()), str(st["stages"]), src_s)
    w.check("checksum_no_mismatch_no_missing", st["checksums"]["mismatch"] == 0 and st["checksums"]["missing"] == 0,
            f"{st['checksums']['checked']} file", src_s)
    rows = rcsv("data/splits/video_split_v1.csv")
    vids = [r["video_id"] for r in rows]
    w.check("split_each_video_once", len(vids) == len(set(vids)) == 650, f"{len(vids)} dong", "data/splits/video_split_v1.csv")
    cnt = Counter(r["split"] for r in rows)
    w.check("split_counts_match_manifest", dict(cnt) == sp["counts"], str(dict(cnt)), "data/splits/video_split_v1.csv")
    raw = (ROOT / "data/splits/video_split_v1.csv").read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    crlf = hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest()
    w.check("split_sha256_matches_manifest", sp["output_sha256"]["video_split_v1.csv"] in (hashlib.sha256(raw).hexdigest(), crlf),
            f"SHA-256 manifest tinh tren ban CRLF (Windows/Kaggle) = {crlf[:16]}; Git luu ban LF {hashlib.sha256(lf).hexdigest()[:16]}", src_p)
    for f, c in (("reports/w2/figures/fig_overview.png", "Sơ đồ tổng quan bài toán"),
                 ("reports/w2/figures/fig_split_v1_by_class.png", "Số video theo lớp trong từng tập split v1")):
        w.fig(f, c)


# ----------------------------------------------------------------------------- W03
def w03(w: Week):
    rv = rjson("results/W03/review/review_v2_summary.json")
    src_rv = "results/W03/review/review_v2_summary.json"
    for k in ("OK", "SAI_NHAN", "KHONG_RO"):
        v = _find_count(rv, k)
        if v is not None:
            w.m(f"review_v2_{k}", v, "video", source=src_rv)
    sens = rjson("results/W03/kaggle_run_03a/export_evidence/offset_sensitivity_summary.json")
    for g, v in sens["groups"].items():
        w.m("offset_sensitivity_frac_iou_ge_0.5", round(v["frac_iou_ge_min"], 4), "ratio", split=g,
            source="results/W03/kaggle_run_03a/export_evidence/offset_sensitivity_summary.json", producer="scripts/kaggle/w3_export_yolo.py")
    card = rjson("results/W03/kaggle_run_03b/export_evidence/dataset_card.json")
    src_c = "results/W03/kaggle_run_03b/export_evidence/dataset_card.json"
    w.m("yolo_images", card["images"], "image", source=src_c, producer="scripts/kaggle/w3_export_yolo.py", run_commit=card["commit"][:7])
    for r in rcsv("results/W03/kaggle_run_03b/export_evidence/dataset_stats.csv"):
        w.m(f"yolo_images_{r['class_name']}", r["images"], "image", split=r["split"], source="results/W03/kaggle_run_03b/export_evidence/dataset_stats.csv")
    E4 = "results/W03/kaggle_run_04/train_evidence"
    env = rjson(f"{E4}/env.json"); met = rjson(f"{E4}/baseline_A_val_metrics.json")
    rc = env["commit"][:7]
    o = met["overall"]
    for k, unit in (("map50", "AP"), ("map50_95", "AP"), ("precision_mean", "ratio"), ("recall_mean", "ratio")):
        w.m(k, o[k], unit, split="val", model="baseline_A_yolov8n_640", source=f"{E4}/baseline_A_val_metrics.json",
            producer="scripts/kaggle/w3_train_baseline.py", run_commit=rc)
    for r in met["per_class"]:
        for k in ("ap50", "ap50_95"):
            w.m(f"{k}_{r['class_name']}", r[k], "AP", split="val", model="baseline_A_yolov8n_640", source=f"{E4}/baseline_A_val_metrics.json", run_commit=rc)
    w.m("inference_ms_per_image", o["speed_ms_per_image"]["inference"], "ms", split="val", model="baseline_A_yolov8n_640",
        source=f"{E4}/baseline_A_val_metrics.json", run_commit=rc)
    res = rcsv(f"{E4}/train/results.csv")
    w.m("epochs_run", len(res), "epoch", model="baseline_A_yolov8n_640", source=f"{E4}/train/results.csv", run_commit=rc)
    E5 = "results/W03/kaggle_run_05/analysis"
    s5 = rjson(f"{E5}/analysis_summary.json"); op = s5["stages"]["operating_points"]
    rc5 = s5["stages"]["inputs"]["commit"][:7]
    for k in ("conf_selected_on_val", "Drone_P", "Drone_R", "Drone_F1", "all_P", "all_R", "macro_F1"):
        w.m(f"op_{k}", op[k], "", split="val", model="baseline_A_yolov8n_640", source=f"{E5}/analysis_summary.json",
            producer="scripts/kaggle/w3_analyze_baseline.py", run_commit=rc5)
    for r in rcsv(f"{E5}/recall_by_size.csv"):
        if r["class"] == "ALL":
            w.m(f"recall_{r['size']}_at_op", r["recall"], "ratio", split="val", model="baseline_A_yolov8n_640", source=f"{E5}/recall_by_size.csv", run_commit=rc5)
    wm = rjson(f"{E4}/weights_manifest.json")
    for name, v in wm.items():
        if name.endswith(".pt"):
            w.external.append({"name": f"baseline_A/{name}", "link": v.get("drive_link", ""), "sha256": v["sha256"], "bytes": v["bytes"]})
    # kiem tra
    for run, path in (("03a_export", "results/W03/kaggle_run_03a/export_evidence/stage_status.json"),
                      ("03a_review", "results/W03/kaggle_run_03a/review_v2/stage_status.json"),
                      ("03b", "results/W03/kaggle_run_03b/export_evidence/stage_status.json"),
                      ("03b_v2", "results/W03/kaggle_run_03b_v2/export_evidence/stage_status.json"),
                      ("04", f"{E4}/stage_status.json"), ("05", f"{E5}/stage_status.json")):
        st = rjson(path)
        stages = st.get("stages", st)
        stages = {k: (v.get("status") if isinstance(v, dict) else v) for k, v in stages.items()
                  if isinstance(v, str) or (isinstance(v, dict) and "status" in v)}
        bad = {k: v for k, v in stages.items() if v not in ("OK", "SKIPPED")}
        w.check(f"kaggle_run_{run}_stages_ok", not bad, "loi: " + str(bad) if bad else f"{len(stages)} stage", path)
    c2 = rjson("results/W03/kaggle_run_03b_v2/export_evidence/dataset_card.json")
    s4 = rjson(f"{E4}/stage_status.json")
    w.check("fingerprint_03b_eq_03b_v2_eq_run04", card["content_fingerprint_sha256"] == c2["content_fingerprint_sha256"] == s4["data"]["fingerprint"],
            card["content_fingerprint_sha256"][:16], f"{E4}/stage_status.json")
    w.check("no_test_images_in_training_data", "test" not in card["splits_exported"], str(card["splits_exported"]), src_c)
    w.check("weights_have_sha256_and_drive_link", all(v.get("sha256") and v.get("drive_link") for v in wm.values() if isinstance(v, dict) and "sha256" in v),
            ", ".join(wm), f"{E4}/weights_manifest.json")
    w.check("run05_val_images_match_predictions", s5["stages"]["inputs"]["val_images"] == s5["stages"]["inputs"]["pred_images"],
            str(s5["stages"]["inputs"]["val_images"]), f"{E5}/analysis_summary.json")
    for f, c in (("reports/w3/figures/fig_w3_data_funnel.png", "Từ video khả kiến tới e1-yolo-v1"),
                 ("reports/w3/figures/fig_w3_offset_sensitivity.png", "Độ nhạy với lệch 1 frame"),
                 ("reports/w3/figures/fig_w3_learning_curves.png", "Learning curve baseline A"),
                 ("reports/w3/figures/fig_w3_per_class_ap.png", "AP theo lớp baseline A (val)"),
                 ("reports/w3/figures/fig_w3_recall_by_size.png", "Recall theo cỡ hộp (val, conf 0,25)")):
        w.fig(f, c)


# ----------------------------------------------------------------------------- W04
def w04(w: Week):
    cmp_path = ROOT / "results/W04/comparison_w4.csv"
    if cmp_path.is_file():
        rows = rcsv("results/W04/comparison_w4.csv")
        for r in rows:
            for k, v in r.items():
                if k not in ("model", "split", "source", "run_commit", "weights", "gpu", "ultralytics", "fingerprint") and v != "":
                    w.m(k, v, split=r.get("split", "val"), model=r["model"], source="results/W04/comparison_w4.csv",
                        producer="scripts/reporting/build_comparison.py", run_commit=r.get("run_commit", ""))
        w.check("comparison_same_fingerprint", len({r["fingerprint"] for r in rows}) == 1, rows[0]["fingerprint"], "results/W04/comparison_w4.csv")
        w.check("comparison_same_ultralytics_and_gpu", len({(r["ultralytics"], r["gpu"]) for r in rows}) == 1,
                f"{rows[0]['ultralytics']} / {rows[0]['gpu']}", "results/W04/comparison_w4.csv")
        w.check("comparison_val_only", all(r["split"] == "val" for r in rows), "test khoa", "results/W04/comparison_w4.csv")
        for f, c in (("results/W04/fig_w4_accuracy_vs_latency.png", "mAP@0.5:0.95 và thời gian suy luận (val, T4)"),
                     ("results/W04/fig_w4_ap_by_class.png", "AP@0.5 theo lớp, 6 mô hình (val)")):
            w.fig(f, c)
    R9 = ROOT / "results/W04/kaggle_run_09"
    for runs in sorted(R9.glob("phien_*/w4_compare_runs.json")):
        rr = json.loads(runs.read_text(encoding="utf-8")); rel9 = str(runs.relative_to(ROOT))
        w.check(f"run09_{runs.parent.name}_return_codes_zero", all(v["train_rc"] == 0 and v["analysis_rc"] == 0 for v in rr["runs"].values()),
                ", ".join(rr["runs"]), rel9)
        for exp in rr["runs"]:
            t, an = runs.parent / f"train_{exp}", runs.parent / f"analysis_{exp}"
            st = json.loads((t / "stage_status.json").read_text(encoding="utf-8"))
            sa = json.loads((an / "stage_status.json").read_text(encoding="utf-8"))
            ok = all(v.get("status") == "OK" for v in st.values() if isinstance(v, dict) and "status" in v) and \
                all(v.get("status") == "OK" for v in sa.values() if isinstance(v, dict) and "status" in v)
            w.check(f"run09_{exp}_stages_ok", ok, f"{len(st)}+{len(sa)} stage", str((t / 'stage_status.json').relative_to(ROOT)))
            card = json.loads((t / "dataset_card.json").read_text(encoding="utf-8"))
            w.check(f"run09_{exp}_fingerprint_eq_run03b", card["content_fingerprint_sha256"] == rr["fingerprint"] ==
                    rjson("results/W03/kaggle_run_03b/export_evidence/dataset_card.json")["content_fingerprint_sha256"],
                    card["content_fingerprint_sha256"][:16], str((t / "dataset_card.json").relative_to(ROOT)))
            wm = json.loads((t / "weights_manifest.json").read_text(encoding="utf-8"))
            for name, v in wm.items():
                if name.endswith(".pt"):
                    w.external.append({"name": f"{exp}/{name}", "link": v.get("drive_link", ""), "sha256": v["sha256"], "bytes": v["bytes"]})
            w.check(f"run09_{exp}_weights_sha_and_link", all(v.get("sha256") and v.get("drive_link") for k, v in wm.items() if k.endswith(".pt")),
                    ", ".join(wm), str((t / "weights_manifest.json").relative_to(ROOT)))
    G = "results/W04/cvat_gold"
    if (ROOT / G / "scoring/gold_score.json").is_file():
        gs = rjson(f"{G}/scoring/gold_score.json"); s11 = rjson("results/W04/kaggle_run_11/stage_status.json")
        src = f"{G}/scoring/gold_score.json"
        w.m("cvat_frames", gs["frames"], "image", source=src, producer="scripts/dataset/score_cvat_gold.py")
        w.m("cvat_frames_no_box", gs["status_counts"]["no_box"], "image", source=src)
        w.m("cvat_median_best_iou", gs["label_quality"]["median_best_iou"], "IoU", source=src)
        for g, v in gs["groups"].items():
            w.m("cvat_iou_videos_i1_better", v["videos_i1_better"], "video", split=g, source=src)
            w.m("cvat_iou_videos", v["videos"], "video", split=g, source=src)
            w.m("cvat_iou_sign_test_p", v["sign_test_p"], "p", split=g, source=src)
        w.m("cvat_control_ok", gs["control_ok"], "bool", source=src)
        for g, v in gs["verdict"].items():
            w.m("cvat_verdict", v, "", split=g, source=src)
        ex = gs.get("exploratory_center", {})
        for k, v in ex.get("box_vs_label", {}).items():
            w.m(f"cvat_explore_{k}", v, "", source=src)
        for g, v in ex.get("groups", {}).items():
            w.m("cvat_explore_videos_closer_to_i1", f"{v['videos_closer_to_i1']}/{v['videos']}", "video", split=g, source=src)
            w.m("cvat_explore_sign_test_p", v["sign_test_p"], "p", split=g, source=src)
        w.check("cvat_key_sha_eq_run11", sha256(ROOT / G / "gold_KEY.zip") == s11["package"]["key_sha256"], s11["package"]["key_sha256"][:16],
                "results/W04/kaggle_run_11/stage_status.json")
        w.check("cvat_all_gold_images_scored", gs["frames"] == s11["select"]["frames"], f"{gs['frames']} anh", src)
        w.check("cvat_run11_no_test_split", s11["inputs"]["test_used"] is False, "test_used=False", "results/W04/kaggle_run_11/stage_status.json")
    if (ROOT / "results/W04/review_v2_agreement.json").is_file():
        ag = rjson("results/W04/review_v2_agreement.json"); src = "results/W04/review_v2_agreement.json"
        for k in ("videos", "agree", "percent_agree", "cohen_kappa"):
            w.m(f"review_v2_an_vs_quang_{k}", ag[k], "", source=src, producer="scripts/dataset/review_agreement.py")
    off = ROOT / "results/W04/kaggle_run_06/w4_offset_check/offset_check_summary.json"
    if off.is_file():
        s = json.loads(off.read_text(encoding="utf-8"))
        rel = str(off.relative_to(ROOT))
        for g, v in s["groups"].items():
            w.m("offset_videos_i1_better", v["videos_i1_better"], "video", split=g, source=rel, producer="scripts/kaggle/w4_offset_check.py")
            w.m("offset_videos", v["videos"], "video", split=g, source=rel)
            w.m("offset_sign_test_p", v["sign_test_p"], "p", split=g, source=rel)
        w.m("offset_control_ok", s["control_ok"], "bool", source=rel)
        for g, v in s["verdict"].items():
            w.m("offset_verdict", v, "", split=g, source=rel)
        st = json.loads((off.parent / "stage_status.json").read_text(encoding="utf-8"))
        w.check("run06_all_stages_ok", all(v.get("status") == "OK" for v in st.values()), str(list(st)), rel.replace("offset_check_summary", "stage_status"))
        pg = ROOT / "results/W03/kaggle_run_04/train_evidence/val/predictions.json.gz"
        w.check("run06_uses_run04_predictions", hashlib.sha256(gzip.open(pg).read()).hexdigest() == st["inputs"]["predictions_sha256"],
                st["inputs"]["predictions_sha256"][:16], "results/W03/kaggle_run_04/train_evidence/val/predictions.json.gz")
        cm = rcsv("results/W03/kaggle_run_03b/export_evidence/yolo_manifest.csv.gz")
        m1 = ROOT / "results/W03/kaggle_run_03b/export_evidence/yolo_manifest.csv.gz"
        m2 = ROOT / "results/W03/kaggle_run_03b_v2/export_evidence/yolo_manifest.csv.gz"
        w.check("run06_uses_run03b_v2_manifest", sha256(m2) == st["inputs"]["manifest_sha256"], st["inputs"]["manifest_sha256"][:16], str(m2.relative_to(ROOT)))
        w.check("manifest_03b_v2_content_eq_03b", gzip.open(m1).read() == gzip.open(m2).read(), "noi dung giai nen trung tung byte (chi khac header gzip)", str(m1.relative_to(ROOT)))
        w.check("run06_covers_all_val_images", st["inputs"]["images"] == sum(r["split"] == "val" for r in cm) and st["inputs"]["images_without_pred"] == 0,
                f"{st['inputs']['images']} anh", rel)


def _find_count(obj, key):
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], int):
            return obj[key]
        for v in obj.values():
            r = _find_count(v, key)
            if r is not None:
                return r
    return None


def _bar(w: Week, counter: Counter, name: str, title: str, ylabel: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = w.dir / "figures"; out.mkdir(parents=True, exist_ok=True)
    keys = sorted(counter)
    fig, ax = plt.subplots(figsize=(6, 2.8))
    ax.bar(keys, [counter[k] for k in keys], color="#2a78d6", width=0.6)
    for i, k in enumerate(keys):
        ax.text(i, counter[k], str(counter[k]), ha="center", va="bottom", fontsize=8)
    ax.set_title(title, loc="left", fontsize=9); ax.set_ylabel(ylabel)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(out / name, dpi=160); plt.close(fig)
    w.figures.append((out / name, title))


def junit_to_checks(w: Week, xml: Path):
    root = ET.parse(xml).getroot()
    for tc in root.iter("testcase"):
        failed = tc.find("failure") is not None or tc.find("error") is not None
        w.check(f"pytest::{tc.get('classname')}::{tc.get('name')}", not failed, f"{float(tc.get('time', 0)):.3f}s", "tests/")


INFO = {
    "W01": ("Tuan1", "Phạm vi, lớp, metric, dataset, quy tắc nhãn, split",
            "Khảo sát dataset và license, manifest v1, 100 frame mẫu có truy nguồn, kiểm tra sơ bộ nhãn."),
    "W02": ("Tuan2", "Chuẩn hóa dataset, thống kê lớp và chất lượng nhãn",
            "Kiểm tra SHA-256 1.303 tệp, EDA 650 video, audit nhãn, split v1 theo video, sàng lọc rò rỉ."),
    "W03": ("Tuan3", "Train baseline (config, weights, mAP/PR)",
            "Review nhãn v2, xuất e1-yolo-v1, train YOLOv8n@640 (baseline A), phân tích val, model card."),
    "W04": ("Tuan4", "Tuning + augmentation, so sánh baseline",
            "Kiểm chứng chiều lệch nhãn (run 06 và tập chuẩn CVAT, ADR-0006), train và so sánh 6 mô hình trên cùng dữ liệu (run 09), áp luật chọn đặt trước (ADR-0007)."),
}
LINKS = {
    "W01": "Báo cáo: reports/w1/. Tài liệu: docs/w1/.",
    "W02": "PR #13, #14. Báo cáo: reports/w2/. Tài liệu: docs/w2/, ADR-0002, ADR-0003.",
    "W03": "Issue #10, #11, #16–#21; PR #22, #23, #25, #26, #28, #31–#35. Báo cáo: reports/w3/. ADR-0004, ADR-0005. Model card: docs/w3/model_card_baseline_A.md.",
    "W04": "Issue #24, #36–#42, #48, #49; PR #43–#47, #50–#55. Báo cáo: reports/w4/ (báo cáo công việc, v0.4). Trạng thái: docs/status/W04_planned_done_evidence.md. Kế hoạch: docs/w4/W4_PLAN.md. ADR-0006, ADR-0007. Giao thức: docs/w4/training_protocol_w4.md.",
}


def write(w: Week, head: str):
    (w.dir / "figures").mkdir(parents=True, exist_ok=True)
    if not w.figures:
        (w.dir / "figures" / ".gitkeep").write_text("", encoding="utf-8")
    for src, _ in w.figures:
        if src.parent != w.dir / "figures":
            shutil.copy2(src, w.dir / "figures" / src.name)
    with (w.dir / "metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS); wr.writeheader(); wr.writerows(w.metrics)
    n_pass = sum(c["status"] == "PASS" for c in w.checks)
    tr = {"week": w.week, "generated_by": "scripts/reporting/build_evidence.py", "repo_commit": head,
          "summary": {"total": len(w.checks), "passed": n_pass, "failed": len(w.checks) - n_pass}, "checks": w.checks}
    (w.dir / "test-results.json").write_text(json.dumps(tr, indent=2, ensure_ascii=False), encoding="utf-8")
    ms, title, scope = INFO[w.week]
    fig_lines = "\n".join(f"| `figures/{p.name}` | {c} |" for p, c in w.figures) or "| — | (chưa có) |"
    ext = "\n".join(f"| {e['name']} | {e['link'] or '—'} | `{e['sha256'][:16]}…` |" for e in w.external) or "| — | — | — |"
    readme = f"""# Evidence {w.week} — {title}

Milestone **{ms}** · Tạo bởi `scripts/reporting/build_evidence.py` tại commit `{head[:7]}` · {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

**Phạm vi:** {scope}

**Liên kết:** {LINKS[w.week]} Repo: {REPO}

## Nội dung thư mục
| File | Mô tả |
|---|---|
| `metrics.csv` | {len(w.metrics)} chỉ số; mỗi dòng có `source` (file gốc trong repo), `producer` (script), `run_commit` |
| `test-results.json` | {len(w.checks)} kiểm tra chạy lại lúc tạo Evidence: **{n_pass} PASS / {len(w.checks) - n_pass} FAIL** |
| `figures/` | Hình dùng trong báo cáo tuần |
| `manifest.json` | SHA-256 của mọi tệp trong thư mục này và của tệp nguồn |

## Hình
| File | Nội dung |
|---|---|
{fig_lines}

## Artefact lớn (ngoài Git)
| Tên | Link | SHA-256 |
|---|---|---|
{ext}

## Tái tạo
```
python scripts/reporting/build_evidence.py --weeks {w.week}
```
Số liệu trên validation là lạc quan (val dùng để chọn checkpoint/ngưỡng); test khóa tới đánh giá cuối (ADR-0005).
"""
    (w.dir / "README.md").write_text(readme, encoding="utf-8")
    files = sorted(p for p in w.dir.rglob("*") if p.is_file() and p.name != "manifest.json")
    man = {"week": w.week, "milestone": ms, "repo_commit": head, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "files": [{"path": str(p.relative_to(w.dir)).replace("\\", "/"), "sha256": sha256(p), "bytes": p.stat().st_size} for p in files],
           "sources": [{"path": s, "sha256": sha256(ROOT / s)} for s in sorted(w.sources) if (ROOT / s).is_file()],
           "external_artifacts": w.external}
    (w.dir / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{w.week}: {len(w.metrics)} metrics, {n_pass}/{len(w.checks)} PASS, {len(w.figures)} figures")
    return len(w.checks) - n_pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weeks", nargs="+", default=["W01", "W02", "W03", "W04"])
    ap.add_argument("--pytest-xml", type=Path, help="JUnit XML cua pytest (copy thanh test-results.xml cua tuan cuoi)")
    a = ap.parse_args()
    head = git_head()
    fails = 0
    for wk in a.weeks:
        w = Week(wk)
        if w.dir.exists():
            shutil.rmtree(w.dir)
        w.dir.mkdir(parents=True)
        {"W01": w01, "W02": w02, "W03": w03, "W04": w04}[wk](w)
        if a.pytest_xml and wk == a.weeks[-1]:
            shutil.copy2(a.pytest_xml, w.dir / "test-results.xml")
            junit_to_checks(w, a.pytest_xml)
        fails += write(w, head)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
