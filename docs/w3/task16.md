For #16, use `main`’s `data/splits/video_split_v1.csv` as the starting point: the W2 README says it is the official split and specifically says not to use the alternative split from `code-lna` (or any subbranches).

## 1. Verify and approve the split

The proposed official split has 650 videos: train 454, validation 98, test 98. Its summary lists Visible counts of **199 / 43 / 43**. Confirm these counts and that each `video_id` occurs in exactly one split before exporting anything.

On a local checkout, calculate the exact split-file hash with PowerShell:

```powershell
Get-FileHash .\data\splits\video_split_v1.csv -Algorithm SHA256
```

The current manifest records this hash:

```text
7e39940eb948880951a05edf199887ec6b42ae557c85088d63a561a49604e5e2
```

Compare it to the file you intend to use. If it differs, stop and determine why rather than silently accepting a changed split. Record the reviewed hash and approval in the ADR/PR. The current split protocol says the split is still proposed pending both members’ approval.

## 2. Draft ADR-0004 before exporting

These are the decisions #16 needs recorded. Values marked **proposed** still need team approval; don’t treat them as already agreed.

```markdown
# ADR-0004: W3 Visible YOLO export

- Status: Proposed
- Split: `data/splits/video_split_v1.csv`
- Split SHA-256: <reviewed hash>
- Scope: Visible (`modality == V`) only
- Classes / IDs: Airplane=0, Bird=1, Drone=2, Helicopter=3
- Sampling: <approved stride and start frame>
- Label mismatch policy: <approved exclusion or verified correction rule>
- Empty labels: retain only videos with verified frame/label alignment;
  write an empty YOLO label file for sampled frames with no box.
- Test: export separately from train/val; do not use for training,
  checkpoint selection, or W3 metrics.
- Reviewers: <names and approval date>
```

One reasonable **proposal** is every fifth frame starting at index 0, with the four class IDs above. The class order matters: the existing W2 script uses Airplane/Bird/Drone/Helicopter, but `code-lna`’s YAML uses a different order. Whichever order is approved must be identical in every label file, YAML, config, and report.

## 3. Apply an explicit annotation policy

The W2 audit reports 253 videos with a mismatch between decoded frames and label entries: 231 with one extra label, 6 with fewer labels by 1–3, 13 with substantially shorter labels, and 3 with longer labels. The alignment diagnostic was inconclusive.

**Safest initial policy:** exclude all videos where `len(labels) != frames_decoded`, list each exclusion and reason, and export only aligned videos. Do not guess an offset or treat unlabeled tail frames as negative examples. The 12 videos with no positive box may be retained as negative examples only when frame/label alignment is verified; write an empty `.txt` label file for each sampled frame.

If the team later chooses to correct a mismatch, document the per-video correction and have it independently checked before including it. Don’t fold an unverified correction into the exporter.

## 4. Export images and YOLO labels on Kaggle

Use the approved split and W2 audit outputs as Kaggle inputs, together with the raw Svanström dataset and `mcos-decoder`/OpenCV. Put the following core logic in a Kaggle script such as `scripts/kaggle/w3_export_yolo.py`; this is an example to implement, not code I’ve added to the repository:

```python
from pathlib import Path
import csv
import cv2
from mcos_decoder import load_groundtruth

CLASS_ID = {"AIRPLANE": 0, "BIRD": 1, "DRONE": 2, "HELICOPTER": 3}
STRIDE = 5  # replace with the value approved in ADR-0004

with open(split_csv, newline="", encoding="utf-8-sig") as f:
    split_rows = list(csv.DictReader(f))
with open(inventory_csv, newline="", encoding="utf-8-sig") as f:
    inventory = {r["video_id"]: r for r in csv.DictReader(f)}

for row in split_rows:
    if row["modality"] != "V":
        continue

    video_id, split = row["video_id"], row["split"]
    audit = inventory[video_id]
    video = data_root / "Data" / "Video_V" / f"{video_id}.mp4"
    label_mat = data_root / "Data" / "Video_V" / f"{video_id}_LABELS.mat"
    boxes = load_groundtruth(label_mat)

    # Quarantine mismatched videos; record video_id and reason in an exclusions file.
    if len(boxes) != int(audit["frames_decoded"]):
        exclusions.append({
            "video_id": video_id,
            "split": split,
            "reason": f"labels={len(boxes)} decoded={audit['frames_decoded']}",
        })
        continue

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video}")

    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_index % STRIDE == 0:
            height, width = frame.shape[:2]
            box = boxes[frame_index]
            lines = []

            if box is not None:
                x, y, w, h = map(float, box[:4])
                if w <= 0 or h <= 0 or x < 0 or y < 0:
                    raise ValueError(f"Invalid bbox: {video_id} frame {frame_index}: {box}")
                if x + w > width or y + h > height:
                    raise ValueError(f"Out-of-image bbox: {video_id} frame {frame_index}: {box}")

                class_name = row["class_name"].upper()
                class_id = CLASS_ID[class_name]
                cx, cy = (x + w / 2) / width, (y + h / 2) / height
                lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w/width:.6f} {h/height:.6f}")

            # Write the frame under <split>/images/ and matching .txt under <split>/labels/.
            # Create the .txt even when `lines` is empty (verified negative frame).
            write_yolo_image_and_label(split, video_id, frame_index, frame, lines)

        frame_index += 1

    cap.release()
    if frame_index != int(audit["frames_decoded"]):
        raise RuntimeError(
            f"Decoded count changed for {video_id}: {frame_index} != {audit['frames_decoded']}"
        )
```

`write_yolo_image_and_label` should create deterministic filenames, such as `V_DRONE_001_000000.jpg` and `.txt`, under separate `train`, `val`, and `test` directories. Include all three split counts in the evidence, but store `test` separately and keep it out of the training YAML. A training YAML should list only `train` and `val`, with the approved class names/order.

The example assumes all positive boxes are represented as a four-value `(x, y, w, h)` sequence, as in the existing W2 script. Before running the full export, test that assumption against a few decoded labels and the expected image dimensions; fail loudly on malformed or out-of-bounds boxes.

## 5. Verify and package the evidence

Before marking #16 complete, check:

- No video ID appears in more than one split; only Visible videos were exported.
- Exported videos, exclusions, frames, images, and boxes have counts by split and class. Explain any count difference from 199/43/43 Visible videos.
- Every exported image has exactly one corresponding label file, including empty files for verified negatives.
- YOLO labels have five fields per positive box, a class ID from 0–3, and normalized coordinates/dimensions in the valid range.
- Spot-check images and boxes across all four classes and all exported splits.
- The manifest records the split hash, ADR choices, stride, excluded videos/reasons, counts, and SHA-256 hashes for output artifacts.
- `stage_status.json` marks every required stage `OK`; any unexpected decode, label, or write error fails the run rather than being silently skipped.

Keep large exported image data on Kaggle/Drive if needed; commit the script, ADR, and compact evidence. The clean handoff is: **split approval → ADR review → small export pilot and spot-check → full export → evidence review**.