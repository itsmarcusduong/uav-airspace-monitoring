#!/usr/bin/env python3
"""Inspect a video dataset without modifying source media."""
from __future__ import annotations
import argparse, csv, hashlib, logging
from pathlib import Path

LOG = logging.getLogger(__name__)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.root.is_dir():
        raise SystemExit(f"Dataset root does not exist: {args.root}")
    rows = []
    for path in sorted(args.root.rglob("*")):
        if path.is_file():
            suffix = path.suffix.lower()
            if suffix in {".mp4", ".avi", ".mov", ".mat", ".xlsx"}:
                rows.append({"relative_path": path.relative_to(args.root).as_posix(), "suffix": suffix, "bytes": path.stat().st_size, "sha256": sha256(path)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "suffix", "bytes", "sha256"])
        writer.writeheader(); writer.writerows(rows)
    LOG.info("Wrote %s inspected-file records to %s", len(rows), args.output)
    return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
