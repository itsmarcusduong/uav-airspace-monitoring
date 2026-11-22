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


# ----------------------------------------------------------------------------- W05
def w05(w: Week):
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "reporting"))
    import build_seed_comparison as bsc  # noqa: E402
    import build_track_comparison as btc  # noqa: E402
    a_sha = rjson("results/W03/kaggle_run_04/train_evidence/weights_manifest.json")["best.pt"]["sha256"]
    fp = rjson("results/W03/kaggle_run_03b/export_evidence/dataset_card.json")["content_fingerprint_sha256"]
    # --- tracking: run 12 (default), run 12b (e1)
    for run, sub in (("kaggle_run_12", "default"), ("kaggle_run_12b", "e1")):
        base = f"results/W05/{run}/w5_track"
        st, inp, env = rjson(f"{base}/stage_status.json"), rjson(f"{base}/inputs.json"), rjson(f"{base}/env.json")
        w.check(f"{run}_all_stages_ok", all(v.get("status") == "OK" for v in st.values()), ", ".join(st), f"{base}/stage_status.json")
        w.check(f"{run}_val_only_test_unused", inp["split"] == "val" and inp["test_used"] is False, f"{inp['videos']} video val", f"{base}/inputs.json")
        w.check(f"{run}_weights_eq_baseline_A_run04", inp["weights_sha256"] == a_sha, a_sha[:16], f"{base}/inputs.json")
        diffs = {t: v["diff_vs_ultralytics_default"] for t, v in inp["trackers"].items()}
        exp = (lambda d: d == {}) if sub == "default" else (lambda d: set(d) == {"track_buffer"} and d["track_buffer"]["e1"] == 45)
        w.check(f"{run}_tracker_cfg_as_protocol", all(exp(d) for d in diffs.values()), json.dumps(diffs, ensure_ascii=False), f"{base}/inputs.json")
        n_tracks = sum(1 for _ in (ROOT / base / "tracks").rglob("*.csv"))
        w.check(f"{run}_track_log_per_video_and_tracker", n_tracks == inp["videos"] * len(inp["trackers"]), f"{n_tracks} file", f"{base}/tracks")
        w.m("track_videos", inp["videos"], "video", "val", source=f"{base}/inputs.json", producer="scripts/kaggle/w5_track_videos.py", run_commit=env["commit"][:7])
        w.m("track_gt_frames", inp["gt_frames"], "frame", "val", source=f"{base}/inputs.json", run_commit=env["commit"][:7])
    tc = rcsv("results/W05/track_comparison.csv")
    for r in tc:
        for k in ("idsw_per_1000_gt_frames", "id_switches", "track_recall_pooled", "median_dominant_id_coverage", "videos_single_id", "fragments", "false_tracks"):
            w.m(f"{k}@iou{r['iou_thr']}", r[k], "", f"val/{r['class']}", r["tracker"], "results/W05/track_comparison.csv", "scripts/reporting/build_track_comparison.py")
    td = rjson("results/W05/track_decision.json"); d = td["decision"]
    for t, v in td["fps_median"].items():
        w.m("fps_median_decode_detect_track", v, "FPS", "val", t, "results/W05/track_decision.json", "scripts/reporting/build_track_comparison.py")
    re_d = btc.decide(d["a"], d["b"], d["idsw_per_1000"][d["a"]], d["idsw_per_1000"][d["b"]])
    w.check("adr0008_rule_reproduced", re_d["choice"] == d["choice"] and re_d["tie"] == d["tie"], f"{d['choice']} ({d['reason']})", "results/W05/track_decision.json")
    w.check("adr0008_decision_pair_is_e1", (d["a"], d["b"]) == ("tracker_bytetrack_e1", "tracker_botsort_e1") and d["reference_only"] is False,
            f"{d['a']} vs {d['b']}", "results/W05/track_decision.json")
    w.m("tracker_decision", d["choice"], "", "val", source="results/W05/track_decision.json", producer="scripts/reporting/build_track_comparison.py")
    gp = rjson("results/W05/track_gaps.json")
    for pr in gp["pairs"]:
        w.m("track_logs_identical_run12_vs_12b", f"{pr['identical']}/{pr['files']}", "video", "val", pr["b"]["dir"].split("/")[-1],
            "results/W05/track_gaps.json", "scripts/reporting/track_gap_stats.py")
    for f, c in (("results/W05/fig_w5_tracking_by_class.png", "ID switch / 1000 frame GT theo lớp, ByteTrack-e1 và BoT-SORT-e1 (val, IoU 0,5)"),
                 ("results/W05/fig_w5_seeds.png", "mAP@0.5:0.95 và F1 Drone theo seed, baseline A và YOLO11n (val)")):
        w.fig(f, c)
    demo = rjson("results/W05/kaggle_run_12/w5_track/demo/demo_index.json")
    for x in demo:
        w.external.append({"name": f"demo/{x['file']}", "link": x.get("drive_link", ""), "sha256": x["sha256"], "bytes": x.get("bytes", 0)})
    w.check("run12_demo_videos_have_drive_link", all(x.get("drive_link") for x in demo), ", ".join(x["video_id"] for x in demo),
            "results/W05/kaggle_run_12/w5_track/demo/demo_index.json")
    # --- seeds: run 13
    R13 = ROOT / "results/W05/kaggle_run_13"
    rr = json.loads((R13 / "w5_seed_runs.json").read_text(encoding="utf-8"))
    w.check("run13_return_codes_zero", all(v["train_rc"] == 0 and v["analysis_rc"] == 0 for v in rr["runs"].values()), ", ".join(rr["runs"]),
            "results/W05/kaggle_run_13/w5_seed_runs.json")
    w.check("run13_fingerprint_eq_run03b", rr["fingerprint"] == fp, fp[:16], "results/W05/kaggle_run_13/w5_seed_runs.json")
    for exp in rr["runs"]:
        t, an = R13 / f"train_{exp}", R13 / f"analysis_{exp}"
        st = json.loads((t / "stage_status.json").read_text(encoding="utf-8")); sa = json.loads((an / "stage_status.json").read_text(encoding="utf-8"))
        ok = all(v.get("status") == "OK" for v in list(st.values()) + list(sa.values()) if isinstance(v, dict) and "status" in v)
        w.check(f"run13_{exp}_stages_ok", ok, f"{len(st)}+{len(sa)} stage", str((t / "stage_status.json").relative_to(ROOT)))
        wm = json.loads((t / "weights_manifest.json").read_text(encoding="utf-8"))
        for name, v in wm.items():
            if name.endswith(".pt"):
                w.external.append({"name": f"{exp}/{name}", "link": v.get("drive_link", ""), "sha256": v["sha256"], "bytes": v["bytes"]})
        w.check(f"run13_{exp}_weights_sha_and_link", all(v.get("sha256") and v.get("drive_link") for k, v in wm.items() if k.endswith(".pt")),
                ", ".join(wm), str((t / "weights_manifest.json").relative_to(ROOT)))
    sc = rcsv("results/W05/seed_comparison.csv")
    for r in sc:
        for k in ("map50", "map50_95", "ap50_95_Drone", "Drone_F1_op", "inference_ms", "best_epoch"):
            w.m(k, r[k], "", "val", f"{r['family']}@seed{r['seed']}", "results/W05/seed_comparison.csv", "scripts/reporting/build_seed_comparison.py", r["run_commit"])
    w.check("seed_comparison_same_fingerprint_gpu_ultralytics", len({(r["fingerprint"], r["gpu"], r["ultralytics"]) for r in sc}) == 1,
            f"{sc[0]['fingerprint']} / {sc[0]['gpu']} / {sc[0]['ultralytics']}", "results/W05/seed_comparison.csv")
    w.check("seed_comparison_3_seeds_each", all(sum(r["family"] == f for r in sc) == 3 for f in ("baseline_A", "yolo11n_640")), "3 + 3",
            "results/W05/seed_comparison.csv")
    sd = rjson("results/W05/seed_decision.json")
    for fam, v in sd["summary"].items():
        for k in ("map", "f1", "ms"):
            w.m(f"seed_{k}_mean", v[k]["mean"], "", "val", fam, "results/W05/seed_decision.json", "scripts/reporting/build_seed_comparison.py")
            w.m(f"seed_{k}_sd", v[k]["sd"], "", "val", fam, "results/W05/seed_decision.json", "scripts/reporting/build_seed_comparison.py")
    re_s = bsc.decide(sd["summary"][sd["a"]], sd["summary"][sd["b"]], sd["a"], sd["b"])
    w.check("protocol_s6_rule_reproduced", re_s["choice"] == sd["decision"]["choice"], f"{sd['decision']['choice']} ({re_s['reason']})",
            "results/W05/seed_decision.json")
    w.m("detector_decision_3_seeds", sd["decision"]["choice"], "", "val", source="results/W05/seed_decision.json", producer="scripts/reporting/build_seed_comparison.py")


def w06(w: Week):
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "alert"))
    import evaluate_alerts as ea  # noqa: E402
    yolo = rjson("results/W05/kaggle_run_13/train_yolo11n_640_s20261030/weights_manifest.json")["best.pt"]["sha256"]
    lf = lambda rel: hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    # --- run 14: YOLO11n + ByteTrack-e1, detection tho, GT, ghep theo frame
    B = "results/W06/kaggle_run_14/w6_run14"
    st, inp, env = rjson(f"{B}/stage_status.json"), rjson(f"{B}/inputs.json"), rjson(f"{B}/env.json")
    rc = env["commit"][:7]
    w.check("run14_all_stages_ok", all(v.get("status") == "OK" for v in st.values()), ", ".join(st), f"{B}/stage_status.json")
    w.check("run14_val_only_test_unused", inp["split"] == "val" and inp["test_used"] is False, f"{inp['videos']} video val", f"{B}/inputs.json")
    w.check("run14_weights_eq_yolo11n_s20261030", inp["weights_sha256"] == yolo, yolo[:16], f"{B}/inputs.json")
    diffs = {t: v["diff_vs_ultralytics_default"] for t, v in inp["trackers"].items()}
    w.check("run14_tracker_is_bytetrack_e1", list(diffs) == ["tracker_bytetrack_e1"] and set(diffs["tracker_bytetrack_e1"]) == {"track_buffer"},
            json.dumps(diffs, ensure_ascii=False), f"{B}/inputs.json")
    n = {d: sum(1 for _ in (ROOT / B / d).rglob("*.csv")) for d in ("dets", "gt", "tracks", "matches")}
    w.check("run14_one_file_per_video", all(v == inp["videos"] for v in n.values()), json.dumps(n), B)
    ts = rjson(f"{B}/track_summary.json")["summary"]["tracker_bytetrack_e1@0.5"]
    for k in ("all", "Drone"):
        for f in ("idsw_per_1000_gt_frames", "id_switches", "track_recall_pooled", "videos_single_id", "false_tracks"):
            w.m(f"{f}@iou0.5", ts[k][f], "", f"val/{k}", "yolo11n_s20261030+bytetrack_e1", f"{B}/track_summary.json", "scripts/kaggle/w5_track_videos.py", rc)
    w.m("track_gt_frames", inp["gt_frames"], "frame", "val", source=f"{B}/inputs.json", run_commit=rc)
    # --- doi detector: baseline A (run 12b) vs YOLO11n (run 14), cung ByteTrack-e1
    sw = rcsv("results/W06/detector_swap_tracking/summary.csv")
    yall = next(r for r in sw if r["detector"] == "yolo11n_s20261030" and r["class"] == "all")
    w.check("detector_swap_matches_run14", abs(float(yall["idsw_per_1000_gt_frames"]) - ts["all"]["idsw_per_1000_gt_frames"]) < 1e-3,
            f"{yall['idsw_per_1000_gt_frames']} vs {ts['all']['idsw_per_1000_gt_frames']}", "results/W06/detector_swap_tracking/summary.csv")
    for r in sw:
        w.m("idsw_per_1000_gt_frames@iou0.5", r["idsw_per_1000_gt_frames"], "", f"val/{r['class']}", r["detector"],
            "results/W06/detector_swap_tracking/summary.csv", "scripts/reporting/compare_detector_tracking.py")
    dup = rjson("results/W06/duplicate_boxes.json")
    for lab, v in dup["tracks"].items():
        for k in ("same_class_id_pairs", "cross_class_id_pairs", "same_class_pair_frames", "cross_class_pair_frames"):
            w.m(f"overlapping_tracks_{k}", v.get(k, 0), "pair", "val", lab, "results/W06/duplicate_boxes.json", "scripts/reporting/duplicate_box_stats.py")
    # --- canh bao (ADR-0009): R0 vs R1
    A = "results/W06/alert_eval/alert_summary.json"
    al = rjson(A)
    w.check("alert_configs_eq_adr0009", al["roi_config"]["sha256"] == lf("configs/roi_w6.yaml") and al["alert_config"]["sha256"] == lf("configs/alert_e1.yaml"),
            f"roi {al['roi_config']['sha256'][:12]} / alert {al['alert_config']['sha256'][:12]}", A)
    w.check("alert_eval_val_only_yolo11n", al["test_used"] is False and al["weights_sha256"] == yolo and al["evidence"] == B, f"{al['videos']} video", A)
    re_d = ea.decide(al["summary"], "center_hex", "center")
    w.check("adr0009_rule_reproduced", re_d["verdict"] == al["decision"]["verdict"] == "PASS", re_d["reason"], A)
    for rule in ("R0", "R1"):
        g = al["summary"][f"center_hex|center|{rule}"]
        for k in ("events", "detected", "event_recall", "alerts", "event_precision_1to1", "false_alerts_nondrone", "false_alerts_drone_videos",
                  "duplicates", "false_alerts_per_hour_nondrone", "false_alerts_per_hour_nondrone_upper95", "latency_median_s", "hours_nondrone"):
            w.m(f"alert_{k}", g[k], "", "val", f"{rule}@center_hex/center", A, "scripts/alert/evaluate_alerts.py")
    for adr in ("ADR-0009-roi-alert-protocol.md", "ADR-0011-external-data-plan.md"):
        txt = (ROOT / "docs/decisions" / adr).read_text(encoding="utf-8")
        w.check(f"{adr.split('-')[0]}-{adr.split('-')[1]}_accepted", "**Accepted**" in txt.split("\n## ")[0], "", f"docs/decisions/{adr}")
    # --- run 15: video demo canh bao
    D = "results/W06/kaggle_run_15/w6_alert_demo"
    s15 = rjson(f"{D}/stage_status.json")
    w.check("run15_all_stages_ok", all(v.get("status") == "OK" for v in s15.values()), ", ".join(s15), f"{D}/stage_status.json")
    w.check("run15_weights_eq_yolo11n_s20261030", s15["inputs"]["weights_sha256"] == yolo, yolo[:16], f"{D}/stage_status.json")
    log = {(r["video_id"], r["rule"], r["start_f"], r["end_f"]) for r in rcsv("results/W06/alert_eval/alert_log.csv")
           if r["roi"] == "center_hex" and r["point"] == "center"}
    dem = {(r["video_id"], r["rule"], r["start_f"], r["end_f"]) for r in rcsv(f"{D}/demo_alerts.csv")}
    w.check("run15_demo_alerts_eq_alert_log", dem == log, f"{len(dem)} canh bao", f"{D}/demo_alerts.csv")
    for idx in (f"{B}/demo/demo_index.json", f"{D}/demo_index.json"):
        demo = rjson(idx)
        for x in demo:
            w.external.append({"name": f"demo/W06/{x['file']}", "link": x.get("drive_link", ""), "sha256": x["sha256"], "bytes": x.get("bytes", 0)})
        w.check(f"{idx.split('/')[2]}_demo_videos_have_drive_link", all(x.get("drive_link") for x in demo), ", ".join(x["video_id"] for x in demo), idx)
    # --- du lieu: do phu Svanstrom, 40 anh val am tinh
    cov = rjson("results/W06/dataset_coverage.json")["visible"]
    w.m("non_drone_minutes_all_splits", cov["non_drone_minutes_all_splits"], "min", "train+val+test", source="results/W06/dataset_coverage.json",
        producer="scripts/reporting/dataset_coverage_stats.py")
    w.m("target_negative_minutes", cov["target_negative_minutes"], "min", source="results/W06/dataset_coverage.json")
    V = "results/W06/val_negative_frames"
    vs = rjson(f"{V}/val_negative_summary.json")
    w.check("val_negatives_match_run13_count", vs["check_run13"]["match"] is True, f"{vs['negative_frames']} anh, {vs['with_det']} co du doan", f"{V}/val_negative_summary.json")
    mr = rcsv(f"{V}/manual_review_classification.csv")
    keys = {(r["video_id"], r["frame"]) for r in rcsv(f"{V}/val_negative_frames.csv")}
    w.check("manual_review_covers_40_negatives", {(r["video_id"], r["frame"]) for r in mr} == keys and len(mr) == 40, f"{len(mr)} dong", f"{V}/manual_review_classification.csv")
    c = Counter(r["conclusion"] for r in mr)
    for k, v in sorted(c.items()):
        w.m(f"val_negative_manual_{k}", v, "image", "val", source=f"{V}/manual_review_classification.csv")
    w.external.append({"name": "kaggle_run_16/w6_negframes.zip (gui An, khong len Drive)", "link": "",
                       "sha256": "67ec70c18fafe29002bb2e524629d4d6c391fe4f61071c86f46910f8e5185195", "bytes": 0})
    for f, cap in (("results/W06/fig_w6_alerts.png", "R0 và R1, ROI center_hex, điểm tâm: cảnh báo sai, lặp, bỏ sót (val, run 14)"),
                   ("results/W06/fig_w6_detector_swap.png", "ID switch / 1000 frame GT theo lớp khi đổi detector, cùng ByteTrack-e1 (val)")):
        w.fig(f, cap)


def w07(w: Week):
    """W7: cong tai tao offline, thi nghiem hau xu ly V0/V1/V2 (ADR-0012), phan tich nham lan (An #108), nguon video cong khai (ADR-0013)."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "experiments"))
    import w7_postproc as wp  # noqa: E402
    P = "results/W07/postproc"
    rp = rjson(f"{P}/repro_check.json")
    w.check("repro_track_logs_ge_37_of_38_videos", rp["track_logs"]["videos_identical"] >= 37 and rp["track_logs"]["videos"] == 38,
            f"{rp['track_logs']['videos_identical']}/{rp['track_logs']['videos']} video, {rp['track_logs']['row_match_rate']}", f"{P}/repro_check.json")
    w.check("repro_alerts_identical_run14", rp["alerts_identical"] is True, "R0/R1 center_hex/center", f"{P}/repro_check.json")
    w.check("repro_image_pr_identical_run13", rp["detection_identical"] is True, "P/R theo lop @0,25", f"{P}/repro_check.json")
    w.check("adr0012_accepted_before_variants", wp.adr_accepted(), "PR #105", "docs/decisions/ADR-0012-w7-postprocessing-experiments.md")
    ps = rjson(f"{P}/postproc_summary.json")
    S = {t: rjson(f"{P}/{d}/summary.json") for t, d in (("none", "V0_none"), ("agnostic_nms", "V1_agnostic_nms"), ("nms_iou", "V2_nms_iou"))}
    redo = wp.decide(S["none"], {k: S[k] for k in ("agnostic_nms", "nms_iou")})
    w.check("adr0012_decision_reproduced", redo["choice"] == ps["decision"]["choice"] == "nms_iou", redo["reason"], f"{P}/postproc_summary.json")
    for v, s in S.items():
        tag = f"{s['tag']}_{v}"
        w.m("detections_kept", s["dets_kept"], "box", "val", tag, f"{P}/postproc_summary.json", "scripts/experiments/w7_postproc.py")
        for f in ("idsw_per_1000_gt_frames", "id_switches", "track_recall_pooled", "videos_single_id", "false_tracks", "fragments"):
            w.m(f"{f}@iou0.5", s["tracking"]["all"][f], "", "val/all", tag, f"{P}/{s['tag']}_{v}/summary.json", "scripts/experiments/w7_postproc.py")
        for rule in ("R0", "R1"):
            g = s["alerts"][f"center_hex|center|{rule}"]
            for k in ("detected", "events", "false_alerts_nondrone", "duplicates", "event_precision_1to1"):
                w.m(f"alert_{k}", g[k], "", "val", f"{tag}/{rule}", f"{P}/{s['tag']}_{v}/summary.json", "scripts/experiments/w7_postproc.py")
        d = s["detection"]["per_class"]["Drone"]
        w.m("drone_recall@conf0.25", d["R"], "", "val (bo 40 anh loi nhan)", tag, f"{P}/{s['tag']}_{v}/summary.json", "scripts/experiments/w7_postproc.py")
        w.m("drone_precision@conf0.25", d["P"], "", "val (bo 40 anh loi nhan)", tag, f"{P}/{s['tag']}_{v}/summary.json", "scripts/experiments/w7_postproc.py")
    ex = rjson(f"{P}/exploratory.json")
    e2 = ex["variants"]["V2_nms_iou"]
    w.check("v2_no_video_with_more_idsw", e2["idsw_by_video"]["worse"] == 0, json.dumps(e2["idsw_by_video"]), f"{P}/exploratory.json")
    w.m("exploratory_v2_idsw_reduction_without_top1_video", e2["idsw_without_top1"]["reduction"], "", "val", "V2", f"{P}/exploratory.json", "scripts/experiments/w7_postproc_explore.py")
    w.m("exploratory_v2_removed_conf_ge_0.25", e2["removed_detections"]["removed_conf_ge_0.25"], "box", "val", "V2", f"{P}/exploratory.json", "scripts/experiments/w7_postproc_explore.py")
    du = ex["duplicates_on_same_val_frames"]
    for k in ("video_predict", "image_val"):
        w.m(f"exploratory_same_class_dup_rate_{k}", du[k]["dup_rate"], "", f"val {du['frames']} frame", source=f"{P}/exploratory.json", producer="scripts/experiments/w7_postproc_explore.py")
    ca = rjson("results/W07/confusion_analysis.json")
    w.check("confusion_analysis_matches_v0", ca["matches_saved_summary"] is True and ca["confusion"] == S["none"]["detection"]["confusion"],
            f"{ca['images']} anh, bo {ca['ignored_images']}", "results/W07/confusion_analysis.json")
    for k, v in ca["nen_to_drone_categories"].items():
        w.m(f"nen_to_drone_{k}", v["count"], "box", "val", "V0", "results/W07/confusion_analysis.json", "scripts/reporting/w7_confusion_analysis.py")
    for k, v in ca["non_drone_gt_predicted_as_drone"].items():
        w.m(f"{k}_predicted_as_drone", v["count"], "box", "val", "V0", "results/W07/confusion_analysis.json", "scripts/reporting/w7_confusion_analysis.py")
    txt = (ROOT / "docs/decisions/ADR-0013-public-negative-sources.md").read_text(encoding="utf-8").split("\n## ")[0]
    w.check("adr0013_status_recorded", "**Proposed**" in txt or "**Accepted**" in txt,
            "Accepted" if "**Accepted**" in txt else "Proposed (cho An duyet)", "docs/decisions/ADR-0013-public-negative-sources.md")
    lm = {r["dataset_id"]: r for r in rcsv("data/manifests/license_matrix.csv")}
    w.check("license_matrix_has_adr0013_sources", all(k in lm for k in ("DS-WIKIMEDIA-COMMONS", "DS-PIXABAY-VIDEO", "DS-PEXELS-VIDEO", "DS-UAVDB")),
            ", ".join(f"{k}:{lm[k]['status']}" for k in ("DS-WIKIMEDIA-COMMONS", "DS-PIXABAY-VIDEO", "DS-PEXELS-VIDEO", "DS-UAVDB") if k in lm), "data/manifests/license_matrix.csv")
    for f, cap in (("results/W07/fig_w7_postproc.png", "ID switch / 1000 frame GT theo lớp của V0/V1/V2 (val, offline)"),
                   ("results/W07/fig_w7_idsw_by_video.png", "ID switch theo video, V0 và V2"),
                   ("results/W07/fig_w7_confusion.png", "Ma trận nhầm V0, conf 0,25, val bỏ 40 ảnh lỗi nhãn"),
                   ("results/W07/fig_w7_pipeline.png", "Pipeline mục 3.3 (bản nháp của An)")):
        w.fig(f, cap)


def w08(w: Week):
    """W8: run 17 (V2 trong detector, luat W8_PLAN muc B), chan doan hop trung (muc C), pipeline phat lai (ADR-0015), kich ban E2E."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "experiments"))
    import w8_v2_verify as vv  # noqa: E402
    V = "results/W08/v2_verify/v2_verify.json"
    K = "results/W08/kaggle_run_17"
    st = rjson(f"{K}/w8_run17/stage_status.json"); sd = rjson(f"{K}/w8_dupdiag/stage_status.json")
    w.check("run17_all_stages_ok", all(v.get("status") == "OK" for v in st.values()) and all(v.get("status") == "OK" for v in sd.values()),
            ", ".join(st) + " | " + ", ".join(sd), f"{K}/w8_run17/stage_status.json")
    inp = rjson(f"{K}/w8_run17/inputs.json")
    w.check("run17_val_only_same_weights_nms05", inp["split"] == "val" and inp["test_used"] is False and inp["detector"]["nms_iou"] == 0.5
            and inp["weights_sha256"].startswith("a3de1e01"), f"nms {inp['detector']['nms_iou']}, weights {inp['weights_sha256'][:8]}", f"{K}/w8_run17/inputs.json")
    mm = rjson(f"{K}/media_manifest.json")
    w.check("media_transcode_same_frames_fps_size", mm["videos"] == 38 and not mm["mismatch"], f"{mm['videos']} video, lech {len(mm['mismatch'])}", f"{K}/media_manifest.json")
    v = rjson(V)
    def pv(run):
        rows = csv.DictReader((ROOT / f"results/W08/v2_verify/per_video_tracking_{run}.csv").open(encoding="utf-8"))
        return [{"video_id": r["video_id"], "track_recall": float(r["track_recall"]) if r["track_recall"] not in ("", "None") else None} for r in rows]
    redo_b = vv.rule_b(v["runs"]["run14"] | {"per_video": pv("run14")}, v["runs"]["run17"] | {"per_video": pv("run17")})
    w.check("rule_b_reproduced_apply_v2", redo_b["apply_v2"] is True and v["rule_b"]["apply_v2"] is True,
            "; ".join(f"{k}: {c['run14']} -> {c['run17']}" for k, c in v["rule_b"]["conditions"].items()), V)
    redo_c = vv.rule_c(rjson(f"{K}/w8_dupdiag/dup_diagnostic.json"))
    w.check("rule_c_reproduced_case3", redo_c["gate_pass"] and redo_c["c3_all_ge_8pct"] and redo_c == v["rule_c"], redo_c["interpretation"][:80], V)
    ck = v["checks"]
    w.check("run17_offline_eval_matches_kaggle", all(a == b for a, b in ck["consistency_with_kaggle_summary"].values()),
            json.dumps(ck["consistency_with_kaggle_summary"]), V)
    w.check("fp16_effective_in_diagnostic", ck["fp16_effective"]["images_with_different_dets_fp32_vs_fp16"]["jpg"] > 0,
            json.dumps(ck["fp16_effective"]["images_with_different_dets_fp32_vs_fp16"]), V)
    for run in ("run14", "run17"):
        r = v["runs"][run]; t = r["tracking"]["all"]; a1 = r["alerts"]["center_hex|center|R1"]; a0 = r["alerts"]["center_hex|center|R0"]
        for f in ("idsw_per_1000_gt_frames", "id_switches", "track_recall_pooled", "fragments", "false_tracks"):
            w.m(f"{f}@iou0.5", t[f], "", "val/all", run, V, "scripts/experiments/w8_v2_verify.py")
        for k in ("detected", "events", "alerts", "false_alerts_nondrone"):
            w.m(f"alert_R1_{k}", a1[k], "", "val", run, V, "scripts/experiments/w8_v2_verify.py")
        w.m("alert_R0_false_alerts_nondrone", a0["false_alerts_nondrone"], "", "val", run, V, "scripts/experiments/w8_v2_verify.py")
        d = r["image_level"]["per_class"]["Drone"]
        w.m("drone_recall@conf0.25_video_dets", d["R"], "", "val (bo 40 anh loi nhan)", run, V, "scripts/experiments/w8_v2_verify.py")
        w.m("drone_precision@conf0.25_video_dets", d["P"], "", "val (bo 40 anh loi nhan)", run, V, "scripts/experiments/w8_v2_verify.py")
        w.m("detections", r["detections"], "box", "val", run, V, "scripts/experiments/w8_v2_verify.py")
        w.m("median_fps_reference", r["median_fps"], "fps", "val", run, V, "scripts/experiments/w8_v2_verify.py")
    for k, c in v["rule_c"]["dup_rate"].items():
        w.m(f"dup_rate_same_class_{k}", c, "", "val 1202 anh", "yolo11n s20261030", f"{K}/w8_dupdiag/dup_diagnostic.json", "scripts/kaggle/w8_dup_diagnostic.py",
            inp.get("commit", ""))
    w.m("run17_vs_offline_v2_match_rate", ck["run17_vs_offline_v2_on_run14"]["match_rate"], "", "val", "run17", V, "scripts/experiments/w8_v2_verify.py")
    E = "results/W08/e2e/e2e_fixture_results.json"
    e = rjson(E)
    w.check("e2e_fixture_cases_all_pass", not e["summary"]["fail"] and len(e["summary"]["pass"]) == 8, ", ".join(e["summary"]["pass"]), E)
    man = list(csv.DictReader((ROOT / "results/W08/e2e/e2e_manual_An.csv").open(encoding="utf-8")))
    w.check("e2e_manual_no_fail", all(r["status"] in ("PASS", "CHUA_KIEM_DUOC") for r in man) and len(man) == 13,
            f"PASS {sum(r['status'] == 'PASS' for r in man)}, chua kiem duoc {sum(r['status'] == 'CHUA_KIEM_DUOC' for r in man)}", "results/W08/e2e/e2e_manual_An.csv")
    covered = {r["case"] for r in man if r["status"] == "PASS"} | set(e["summary"]["pass"])
    w.m("e2e_cases_pass", len(covered), "case", "13 ca (#118)", "", "results/W08/e2e/", "scripts/pipeline/e2e_fixtures.py + An")
    w.m("e2e_cases_not_testable_in_replay", 13 - len(covered), "case", "13 ca (#118)", "", "results/W08/e2e/", "scripts/pipeline/e2e_fixtures.py + An")
    for adr in ("ADR-0014-fbd-sv-evaluation-only", "ADR-0015-e2e-architecture-mvp"):
        txt = (ROOT / f"docs/decisions/{adr}.md").read_text(encoding="utf-8").split("\n## ")[0]
        w.check(f"{adr[:8].lower()}_status_recorded", "**Accepted**" in txt or "**Proposed**" in txt,
                "Accepted" if "**Accepted**" in txt else "Proposed", f"docs/decisions/{adr}.md")
    w.check("openapi_contract_lists_endpoints", {"/health", "/runs", "/sources", "/events", "/events/{event_id}/review", "/media/{run_id}/{source_id}", "/config_audit"}
            <= set(rjson("docs/w8/openapi_w8.json")["paths"]), "", "docs/w8/openapi_w8.json")
    lm = {r["dataset_id"]: r for r in rcsv("data/manifests/license_matrix.csv")}
    w.check("license_evidence_fbd_sv_saved", (ROOT / "data/manifests/license_evidence/fbd_sv_2024_figshare_27377595.json").is_file(),
            next((f"{k}:{r['status']}" for k, r in lm.items() if "FBD" in k), "khong co dong FBD"), "data/manifests/license_evidence/")
    for f, cap in (("results/W08/fig_w8_v2_verify.png", "Luật áp dụng V2: run 14 so với run 17 (val)"),
                   ("results/W08/fig_w8_dup.png", "Tỷ lệ hộp trùng theo đầu vào và độ chính xác số"),
                   ("results/W08/fig_w8_arch.png", "Kiến trúc tổng thể (mục 4.1, bản nháp của An)"),
                   ("results/W08/fig_w8_erd.png", "ERD kho sự kiện (mục 4.2)")):
        w.fig(f, cap)
    w.external.append({"name": "bundle w8_demo/bundle.json (run14 + run17, 38 video H.264; Drive w8, khong vao Git)", "link": "",
                       "sha256": "491974f8ba43380c22e0e43f38b8b40464455751187fc9da3078b61268da1bc3", "bytes": 0})
    for x in rjson(f"{K}/w8_run17/demo/demo_index.json"):
        w.external.append({"name": f"demo/W08/{x['file']}", "link": x.get("drive_link", ""), "sha256": x["sha256"], "bytes": x.get("bytes", 0)})


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
    "W05": ("Tuan5", "Tích hợp tracker, video test ID ổn định",
            "Pipeline video → detector → tracker trên 38 video val (run 12, 12b), độ đo liên kết trên GT dẫn xuất (ADR-0008), chọn tracker theo luật đặt trước; 3 seed cho baseline A và YOLO11n (run 13), chọn lại detector (ADR-0007 cập nhật)."),
    "W06": ("Tuan6", "Geofence + cảnh báo theo trajectory",
            "Run 14: YOLO11n s20261030 + ByteTrack-e1 trên 38 video val, lưu detection thô, GT, ghép theo frame; mô-đun ROI/cảnh báo R0 (chỉ detector) và R1 (theo track) theo giao thức đặt trước ADR-0009; video demo cảnh báo (run 15); phân tích lỗi cảnh báo, hộp trùng, 40 ảnh val âm tính (run 16); kế hoạch dữ liệu W7–W12 (ADR-0011)."),
    "W07": ("Tuan7", "Hard negatives + confusion analysis",
            "Cổng tái tạo tracker offline trên detection của run 14; thí nghiệm hậu xử lý detection V0/V1/V2 theo luật đặt trước ADR-0012 (chọn V2, NMS cùng lớp IoU 0,5); phân tích nhầm lẫn và hard negative trên val (An, #98); nguồn video âm tính công khai có giấy phép thay video tự quay (ADR-0013, thu thập W8); Chương III bản 1."),
    "W08": ("Tuan8", "Pipeline E2E + dashboard/log",
            "Kaggle run 17: V2 (NMS cùng lớp IoU 0,5) trong detector, áp luật đặt trước W8_PLAN mục B → áp dụng V2; chẩn đoán hộp trùng video so với ảnh val (mục C, trường hợp 3). Pipeline phát lại: kho sự kiện SQLite chỉ thêm, API FastAPI + WebSocket, dashboard, nhật ký review và cấu hình (ADR-0015). 13 kịch bản E2E của An: 9 đạt, 0 trượt, 4 không kiểm được ở chế độ phát lại. Tập âm tính e1-neg-v1 chưa xong (chuyển W9)."),
    "W04": ("Tuan4", "Tuning + augmentation, so sánh baseline",
            "Kiểm chứng chiều lệch nhãn (run 06 và tập chuẩn CVAT, ADR-0006), train và so sánh 6 mô hình trên cùng dữ liệu (run 09), áp luật chọn đặt trước (ADR-0007)."),
}
LINKS = {
    "W01": "Báo cáo: reports/w1/. Tài liệu: docs/w1/.",
    "W02": "PR #13, #14. Báo cáo: reports/w2/. Tài liệu: docs/w2/, ADR-0002, ADR-0003.",
    "W03": "Issue #10, #11, #16–#21; PR #22, #23, #25, #26, #28, #31–#35. Báo cáo: reports/w3/. ADR-0004, ADR-0005. Model card: docs/w3/model_card_baseline_A.md.",
    "W05": "Issue #57–#62; PR #63–#70. Báo cáo: reports/w5/ (báo cáo công việc, v0.5). Trạng thái: docs/status/W05_planned_done_evidence.md. Kế hoạch: docs/w5/W5_PLAN.md. ADR-0007 (cập nhật), ADR-0008. Giao thức: docs/w5/tracking_protocol_w5.md, docs/w4/training_protocol_w4.md mục 6.",
    "W06": "Issue #74–#79, #88; PR #80–#83, #86, #87, #89–#95. Báo cáo: reports/w6/ (báo cáo công việc, v0.6). Trạng thái: docs/status/W06_planned_done_evidence.md. Kế hoạch: docs/w6/W6_PLAN.md. ADR-0009, ADR-0010, ADR-0011. Phân tích: docs/w6/alert_error_review.md, docs/w6/val_negative_frames.md, docs/w7/data_expansion_proposal.md.",
    "W08": "Issue #113, #115–#119; PR #114, #120–#127 và PR chốt tuần. Báo cáo: reports/w8/ (báo cáo công việc, v0.8). Trạng thái: docs/status/W08_planned_done_evidence.md. Kế hoạch: docs/w8/W8_PLAN.md. ADR-0014, ADR-0015. Kết quả: docs/w8/v2_verify_results.md, results/W08/e2e/README.md.",
    "W07": "Issue #97–#101; PR #102–#109 và PR chốt tuần. Báo cáo: reports/w7/ (báo cáo công việc, v0.7). Trạng thái: docs/status/W07_planned_done_evidence.md. Kế hoạch: docs/w7/W7_PLAN.md. ADR-0012, ADR-0013. Phân tích: docs/w7/postproc_results.md, docs/w7/confusion_analysis.md.",
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
    ap.add_argument("--weeks", nargs="+", default=["W01", "W02", "W03", "W04", "W05"])
    ap.add_argument("--pytest-xml", type=Path, help="JUnit XML cua pytest (copy thanh test-results.xml cua tuan cuoi)")
    a = ap.parse_args()
    head = git_head()
    fails = 0
    for wk in a.weeks:
        w = Week(wk)
        if w.dir.exists():
            shutil.rmtree(w.dir)
        w.dir.mkdir(parents=True)
        {"W01": w01, "W02": w02, "W03": w03, "W04": w04, "W05": w05, "W06": w06, "W07": w07, "W08": w08}[wk](w)
        if a.pytest_xml and wk == a.weeks[-1]:
            shutil.copy2(a.pytest_xml, w.dir / "test-results.xml")
            junit_to_checks(w, a.pytest_xml)
        fails += write(w, head)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
