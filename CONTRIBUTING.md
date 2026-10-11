# Contribution workflow

## Roles and review

Lê Ngọc An owns analysis/design and the designated technical module. Dương Minh Quang owns the complementary technical module, integration and testing. Both members contribute to experiments and the report, and each reviews the other member’s pull requests.

## Before work

Create/select one Issue in the current weekly milestone. Assign one primary owner, list acceptance criteria, expected evidence and a reviewer. Use labels `week:Wn`, `area:data`, `area:model`, `area:tracking`, `area:system`, `area:report`, and `type:decision` as applicable.

## Pull request gate

The PR description must contain: linked Issue, scope, test/validation command, evidence path/link, limitations, and reviewer approval. Merge only after the other member reviews it. Configure GitHub branch protection for `main`: require a pull request, one approving review, resolved conversations and passing checks when checks exist.

## Milestones and releases

Create milestones W1-W14. Tag releases at W4, W8, W11 and W14 after review. A weekly report cites either the merged PR or the release/tag, never an unreviewed local change.
