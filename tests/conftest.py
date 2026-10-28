"""Them scripts/kaggle va scripts/dataset vao sys.path de test import truc tiep."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("scripts/kaggle", "scripts/dataset"):
    sys.path.insert(0, str(ROOT / sub))
