"""Copy locked upstream inputs into an ignored, disposable run workspace."""

from __future__ import annotations

import shutil
from pathlib import Path

from verify_reference_artifacts import main as verify_reference_artifacts


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "reference" / "upstream" / "EarthquakeNPP"
WORKSPACE = ROOT / "artifacts" / "reference-comcat25" / "workspace"

COPIES = {
    "Datasets/ComCat/ComCat_catalog.csv": "Datasets/ComCat/ComCat_catalog.csv",
    "Datasets/ComCat/california_shape.npy": "Datasets/ComCat/california_shape.npy",
    "Experiments/ETAS/config/ComCat_25.json": (
        "Experiments/ETAS/config/ComCat_25.json"
    ),
    "Experiments/ETAS/predict_etas.py": "Experiments/ETAS/predict_etas.py",
    "Experiments/ETAS/invert_etas.py": "Experiments/ETAS/invert_etas.py",
    "Experiments/ETAS/output_data_ComCat_25/parameters_0.json": (
        "Experiments/ETAS/output_data_ComCat_25/parameters_0.json"
    ),
}


def main() -> int:
    verify_reference_artifacts()
    for source_name, destination_name in COPIES.items():
        source = UPSTREAM / source_name
        destination = WORKSPACE / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"copied {source_name}")
    print(f"reference workspace ready: {WORKSPACE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
