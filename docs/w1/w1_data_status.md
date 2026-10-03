# W1 data status

## Planned

Survey datasets, establish licenses/manifest, inspect resources, create 100 traceable frames, run a sanity validation, and prepare handoff evidence.

## Done

- Read proposal and E1 template.
- Inventoried local detector/tracker papers and code.
- Verified official sources for Svanstrom, Anti-UAV, VisDrone, ByteTrack, BoT-SORT, RT-DETR and Ultralytics tracking.
- Created research map, survey, decision, manifests, license matrix, split-risk and reproducible scripts.
- Verified manual Svanstrom archive: 650 video/label pairs and 203,328 readable frames.
- Created 100 JPEG samples from 100 distinct videos; validation passed.

## Evidence

- `docs/w1/research_sources.md`
- `data/manifests/dataset_manifest_v1.csv`
- `data/manifests/license_matrix.csv`
- `resources/metadata/svanstrom_files.csv` (1,303 file records; SHA-256 in resource inventory)
- `data/samples/index_100_frames.csv` (100 traced samples; SHA-256 in validation report)
- Local PDFs/README/LICENSE files listed in `resource_inventory.csv`.
- `docs/w1/mvp_specification.md` (phạm vi MVP, quy tắc cảnh báo, metrics và ranh giới).
- `reports/w1/E1_W1_bao_cao_ket_qua_tuan.pdf` (PDF Link 1 để nộp tuần).
- `reports/w1/E1_W1_phien_ban_do_an_cap_nhat.pdf` (PDF Link 2, phiên bản đồ án W1).

## Problems

- Anti-UAV and VisDrone remain not downloaded. This does not block the primary W1 gate because they are secondary/reference sources, but their media licenses must be verified before use.
- Twelve Svanstrom sequences have no positive bbox across their decoded labels; they were excluded from W1 sampling and require treatment as absence/negative cases in W2.

## Next week

1. Freeze a deterministic video/source-group train/validation/test manifest in W2.
2. Run broader EDA and a full annotation audit; preserve all-absent sequences as documented negative/absence cases.
3. Verify Anti-UAV and VisDrone media licenses before any optional download or use.
