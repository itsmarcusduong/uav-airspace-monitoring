# Dataset scripts

All scripts use relative paths and Python 3.

```powershell
python scripts/dataset/inspect_dataset.py --root <dataset_root> --output resources/metadata/svanstrom_files.csv
python scripts/dataset/build_manifest.py --root .
python scripts/dataset/extract_samples.py --root <dataset_root_or_archive_parent> --output data/samples --seed 20261003
python scripts/dataset/validate_manifest.py --manifest data/manifests/dataset_manifest_v1.csv --samples data/samples/index_100_frames.csv --dataset-root <decoded_dataset_root>
```

`extract_samples.py` requires OpenCV, SciPy, `mcos-decoder`, and at least 100 readable labelled videos. It writes to a staging directory and only replaces the output once exactly 100 frame images and a traceable index have been generated. For Svanstrom, it decodes MCOS `.mat` labels and records real bbox/class metadata.
