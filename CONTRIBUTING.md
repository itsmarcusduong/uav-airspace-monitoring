# Contribution workflow

## Roles and review

Lê Ngọc An owns analysis/design and the designated technical module. Dương Minh Quang owns the complementary technical module, integration and testing. Both members contribute to experiments and the report, and each reviews the other member’s pull requests.

## Before work

Create/select one Issue in the current weekly milestone. Assign one primary owner, list acceptance criteria, expected evidence and a reviewer. Use labels `week:Wn`, `area:data`, `area:model`, `area:tracking`, `area:system`, `area:report`, and `type:decision` as applicable.

## Pull request gate

The PR description must contain: linked Issue, scope, test/validation command, evidence path/link, limitations, and reviewer approval. Merge only after the other member reviews it. Configure GitHub branch protection for `main`: require a pull request, one approving review, resolved conversations and passing checks when checks exist.

## Milestones, tags and evidence (GVHD template, ADR-0010)

- Milestones are named `Tuan1` … `Tuan14`. Every issue has exactly one student and one result: `WN-xx – <Họ tên> – <kết quả>`, with that student as the only assignee.
- Every PR requests review from the other member.
- Every week ends with a tag `wNN` on the last commit of the week on `main`, plus a release `WN — v0.N` with the two PDFs. Releases also mark W4, W8, W11 and W14.
- `Evidence/WNN/` contains `README.md`, `metrics.csv`, `test-results.*`, `figures/`, `manifest.json` (built by `scripts/reporting/build_evidence.py`).
- Before tagging, run `python scripts/github/check_structure.py --weeks 1-N --current N`; it must report no FAIL.
- A weekly report cites the merged PR or the tag, never an unreviewed local change.
