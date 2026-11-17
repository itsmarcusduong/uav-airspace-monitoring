# W7 confusion analysis — classification rules

## False-positive classification (locked before counting)

Apply these rules only after matching detections to ground truth (GT) independently
within each image/frame. Sort detections by descending confidence and greedily
match each detection to the highest-IoU still-unmatched GT at IoU ≥ 0.5; a match
must also have the same class. A detection matched this way is a true positive,
not a false positive. A detection that is not matched is a false positive (FP).

For each unmatched detection, calculate IoU against every GT box and every other
detection in the same image/frame. Assign exactly one category in this order:

1. **Duplicate box:** IoU ≥ 0.5 with a *different detection already matched as a
   true positive*. Class does not affect this overlap check.
2. **Mislocalized:** not a duplicate, and maximum IoU with any GT is ≥ 0.1 and
   < 0.5. The lower boundary is inclusive; the 0.5 boundary is excluded.
3. **True background:** not a duplicate, and IoU with every GT is < 0.1 (or the
   image/frame has no GT). The 0.1 boundary is excluded.
4. **Other high-overlap unmatched:** not a duplicate, but maximum IoU with a GT
   is ≥ 0.5. This residual category covers, for example, an unmatched
   wrong-class detection or a one-to-one matching conflict. It must not be
   relabeled as mislocalized or background.

The duplicate rule has priority if an FP satisfies more than one condition.
These thresholds, priority, and residual category are fixed before reviewing
any counts by category; observed results must not be used to revise them.

## Measured results

The rules above were committed first (`2563b8f`). Counts below were read and
calculated only afterward. The source is V0 `none` at confidence 0.25, with the
40 manually identified unlabeled images excluded: 1,162 scored images and 40
ignored images. The reproducible calculation is:

```text
python scripts/reporting/w7_confusion_analysis.py
```

The script recomputes detections from run 13 and GT from run 14, applies the
recorded 40-image ignore list, and stops with an error unless its per-class
counts and confusion matrix match `summary.json`.

### Detection confusion

`per_class` uses greedy, descending-confidence matching to the highest-IoU
unmatched GT of the same class at IoU ≥ 0.5. The confusion matrix uses a separate
greedy pass, in the same confidence order and at the same IoU threshold, but
without requiring matching classes. Thus `nen` means no GT was assigned in the
class-agnostic pass; it does not mean the image area was visually confirmed as
empty. `bo_sot` is an unmatched GT.

| GT \ prediction | Airplane | Bird | Drone | Helicopter | Missed (`bo_sot`) |
|---|---:|---:|---:|---:|---:|
| Airplane | 193 | 0 | 8 | 12 | 76 |
| Bird | 2 | 56 | 0 | 9 | 6 |
| Drone | 0 | 0 | 427 | 0 | 88 |
| Helicopter | 0 | 0 | 1 | 235 | 49 |
| No GT assigned (`nen`) | 66 | 10 | 74 | 29 | — |

Bird precision/recall at conf 0.25 is **0.5481 / 0.7808** in run 13's
`operating_points.csv` with the 40 images retained, and **0.8636 / 0.7808**
in V0 after excluding them (`TP=57`, `FP=9`, `GT=73`). The unchanged recall is
consistent with these images having no GT labels. The precision increase is a
label-accounting effect, not a model improvement.

### Box size and video

Run 13 `recall_by_size.csv` groups GT by box area: small `<32² px`, medium
`32²–<96² px`, and large `≥96² px`. Overall recall was **0.8147 (387/475)**
small, **0.7491 (430/574)** medium, and **0.8850 (100/113)** large. Medium
boxes had the lowest recall and the most misses (144); small and large boxes
had 88 and 13 misses. Notable class/size results include Helicopter-small
33/60 (0.5500) and Airplane-medium 102/174 (0.5862).

On the retained V0 slice, the largest per-video detection FP counts were
`V_AIRPLANE_005` (29; 7/33 GT matched), `V_AIRPLANE_007` (24; 6/30), and
`V_HELICOPTER_012` (18; 15/32). In run 13 `recall_by_video.csv`,
`V_BIRD_041` has the largest unfiltered per-video FP count (47); after the
40-image exclusion it has 4. The per-video FP column groups all unmatched
predicted classes by the video being evaluated; it is not a per-class Bird FP
count.

The V0 tracking file reports 211 ID switches across 38 videos. `V_DRONE_025`
contributes the largest single-video count, 60 (followed by `V_DRONE_077` 27
and `V_AIRPLANE_009` 25); 60/211 is a large single-video share, not a majority
of all switches.

### Hard-negative catalogue

Counts below are detections at conf ≥ 0.25, after the 40-image exclusion,
unless explicitly marked otherwise. Video totals are from the reproducible
script; class-confusion counts are also present in the V0 matrix.

| Type | Count and video examples | Measured evidence and proposed handling |
|---|---|---|
| Airplane predicted as Drone | 8: `V_AIRPLANE_037` (6), `V_AIRPLANE_007` (1), `V_AIRPLANE_052` (1) | Matrix class-confusion cells. Add correctly labeled, video-separated aircraft examples in future data work; do not alter labels or train in W7. |
| Helicopter predicted as Drone | 1: `V_HELICOPTER_039` (1) | Matrix class-confusion cell. Same data treatment as aircraft; do not change warning thresholds. |
| Bird predicted as Drone | 0 in the retained V0 confusion matrix; no video example in this scored slice | Do not infer this error from appearance or the 40 ignored images. If more evidence is needed, collect licensed bird examples in W8 and label/review them under ADR-0013. |
| Duplicate Drone box in the `nen→Drone` pool | 11: `V_AIRPLANE_037` (8), `V_AIRPLANE_052` (1), `V_DRONE_032` (1), `V_DRONE_077` (1) | Classified by the precommitted overlap-with-correct-TP rule. Evaluate only the already registered W7 post-processing variants; no threshold change is made here. |
| Mislocalized Drone box in the `nen→Drone` pool | 63: `V_DRONE_049` (11), `V_DRONE_095` (10), `V_DRONE_011` (7), with the rest in the script output | Maximum IoU to GT is `[0.1, 0.5)`. Future data/model work should improve localization; no label edits or retraining in W7. |
| Geometric background Drone box in the `nen→Drone` pool | 0; no video example in the retained 74-box pool | By the fixed rule, none of these boxes had IoU < 0.1 with every GT. Separately, W6's manual review documents one Drone FP on empty sky at `V_DRONE_080` frame 0, among the 40 excluded images; it is not part of the 74-box count. Use licensed public negatives in W8, not new W7 collection. |
| Other high-overlap unmatched Drone box | 0 in the `nen→Drone` pool | Kept as an explicit residual in the rules so unmatched IoU ≥ 0.5 cases are not silently called background or mislocalized. |

The 74 `nen→Drone` detections therefore partition into **11 duplicates + 63
mislocalized + 0 geometric background + 0 residual**. This is separate from
the 9 class-confusion detections above (8 Airplane and 1 Helicopter); together
they account for V0's 83 Drone FPs.

W6 provides relevant but differently denominated context: `duplicate_boxes.json`
counts 2,000 same-class and 50 cross-class overlapping track-pair frames at
IoU 0.3 (54 same-class and 4 cross-class ID pairs). `alert_error_review.md`
visually verifies the recurring Drone-on-Airplane/Helicopter pattern and reports
104/120 frames with a cross-class overlap among the sampled R0 alert windows.
These W6 track/frame counts are not added to the W7 per-detection counts.

## Interpretation and limitations

- The dominant measurable source of V0 `nen→Drone` errors on the retained slice
  is localization overlap in the 0.1–0.5 band (63/74), followed by duplicate
  detections (11/74); this is a geometric grouping, not a new visual label.
- The largest retained detection-FP count is in `V_AIRPLANE_005`, while
  `V_DRONE_025` has the most tracker ID switches. These are different metrics
  and must not be combined into one error total.
- The 40 ignored images were removed because they contain unlabeled real
  objects; they are not valid negative examples. W6's one documented empty-sky
  FP is outside the scored V0 pool.
- Box-size recall comes from run 13; V0 per-video detection and confusion counts
  come from the separate W7 calculation. Their matching/aggregation scopes
  differ as described above. W6 duplicate and alert figures use still other
  units.
- This is validation-only evidence from 38 videos; the non-Drone video exposure
  is only 3.7 minutes. It cannot establish an operational false-alert rate or
  generalization to new footage.
- No video was collected in W7. Per ADR-0013, licensed public video collection
  is deferred to W8. No labels were edited, no model was retrained, no test set
  was evaluated, and no alert threshold was changed.

## Sources

- `results/W07/postproc/V0_none/summary.json`,
  `results/W07/postproc/V0_none/per_video_tracking.csv`
- `results/W05/kaggle_run_13/analysis_yolo11n_640_s20261030/operating_points.csv`,
  `recall_by_size.csv`, `recall_by_video.csv`,
  `train_yolo11n_640_s20261030/val/predictions.json.gz`
- `results/W06/duplicate_boxes.json`,
  `results/W06/val_negative_frames/manual_review_classification.csv`,
  `docs/w6/alert_error_review.md`
- `results/W06/kaggle_run_14/w6_run14/{meta.csv,gt/}`
