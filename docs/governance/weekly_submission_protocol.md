# Weekly submission protocol

## Required LMS artefacts from W2

Each week one representative submits two Drive links:

1. A 1-2 page weekly work report in DOCX/PDF.
2. A separately versioned updated-project document in DOCX/PDF, preserving the lecturer's template formatting.

The report includes: week/milestone, Issue and PR/release links, commit SHA, work allocation, Planned-Done-Evidence-Problems-Next week table, demo/video link when available, and result CSV/JSON/model-card/dataset evidence when available. Missing evidence is stated as unavailable; it is not fabricated.

## Required repository record

For each week create `docs/status/W<week>_planned_done_evidence.md`, `reports/W<week>/`, and `docs/project_versions/W<week>/`. Keep the DOCX source and final PDF in the latter two directories; record Drive links in the weekly status file after submission. Each scope change adds an ADR under `docs/decisions/`.

## Version naming

- `E1_W02_bao_cao_cong_viec.docx` and `.pdf`
- `E1_DoAn_v0.2_W02.docx` and `.pdf`
- `results/W02/<experiment>.csv` or `.json` when a measurement exists

Do not overwrite W1 or any previously submitted document.
