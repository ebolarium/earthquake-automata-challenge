"""Compare a generated ETAS likelihood file with the committed contract."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "reference-comcat25.json"
GENERATED = (
    ROOT
    / "artifacts"
    / "reference-comcat25"
    / "workspace"
    / "Experiments"
    / "ETAS"
    / "output_data_ComCat_25"
    / "ll_scores.json"
)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = json.loads(GENERATED.read_text(encoding="utf-8"))
    expected = manifest["expected_results"]["likelihood"]
    absolute_tolerance = manifest["alignment_tolerances"][
        "replay_likelihood_absolute"
    ]

    for expected_name, actual_name in (("etas", "ETAS"), ("poisson", "Poisson")):
        for component in ("nll", "tll", "sll"):
            expected_value = expected[expected_name][component]
            actual_value = actual[actual_name][component]
            delta = abs(actual_value - expected_value)
            if not math.isclose(
                actual_value,
                expected_value,
                rel_tol=0.0,
                abs_tol=absolute_tolerance,
            ):
                raise ValueError(
                    f"{actual_name}.{component} differs by {delta:.3g}: "
                    f"expected {expected_value}, got {actual_value}"
                )
            print(f"ok  {actual_name}.{component} delta={delta:.3g}")

    print(f"likelihood aligned within absolute tolerance {absolute_tolerance:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
