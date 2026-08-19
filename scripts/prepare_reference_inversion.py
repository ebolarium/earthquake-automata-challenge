"""Prepare a parameter-free workspace for the upstream ETAS inversion."""

from __future__ import annotations

import shutil
from pathlib import Path

from verify_reference_artifacts import main as verify_reference_artifacts


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "reference" / "upstream" / "EarthquakeNPP"
WORKSPACE = ROOT / "artifacts" / "reference-comcat25" / "inversion-workspace"
OUTPUT = (
    WORKSPACE
    / "Experiments"
    / "ETAS"
    / "output_data_ComCat_25"
    / "parameters_0.json"
)

COPIES = (
    "Datasets/ComCat/ComCat_catalog.csv",
    "Datasets/ComCat/california_shape.npy",
    "Experiments/ETAS/config/ComCat_25.json",
    "Experiments/ETAS/invert_etas.py",
)


def main() -> int:
    verify_reference_artifacts()
    if OUTPUT.exists():
        print(f"completed inversion output already exists: {OUTPUT}")
        return 0

    for relative_name in COPIES:
        source = UPSTREAM / relative_name
        destination = WORKSPACE / relative_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"copied {relative_name}")

    print(f"parameter-free inversion workspace ready: {WORKSPACE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
