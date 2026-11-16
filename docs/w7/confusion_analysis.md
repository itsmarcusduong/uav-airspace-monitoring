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
