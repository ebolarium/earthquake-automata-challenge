"""Validate and report a fresh ETAS inversion against the reference."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "reference-comcat25.json"
GENERATED = (
    ROOT
    / "artifacts"
    / "reference-comcat25"
    / "inversion-workspace"
    / "Experiments"
    / "ETAS"
    / "output_data_ComCat_25"
    / "parameters_0.json"
)
GENERATED_LIKELIHOOD = GENERATED.with_name("ll_scores.json")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = json.loads(GENERATED.read_text(encoding="utf-8"))
    expected = manifest["expected_results"]
    tolerances = manifest["alignment_tolerances"]

    if actual["n_target_events"] != expected["n_target_events"]:
        raise ValueError(
            "target-event count mismatch: "
            f"expected {expected['n_target_events']}, "
            f"got {actual['n_target_events']}"
        )
    if actual["n_iterations"] != expected["n_iterations"]:
        raise ValueError(
            "iteration-count mismatch: "
            f"expected {expected['n_iterations']}, got {actual['n_iterations']}"
        )

    print("name,expected,actual,absolute_delta")
    _validate_difference(
        "beta",
        expected["beta"],
        actual["beta"],
        tolerances["fresh_inversion_beta_absolute"],
    )
    for name, expected_value in expected["final_parameters"].items():
        _validate_difference(
            name,
            expected_value,
            actual["final_parameters"][name],
            tolerances["fresh_inversion_parameter_absolute"],
        )

    _validate_difference(
        "n_hat",
        expected["n_hat"],
        actual["n_hat"],
        tolerances["fresh_inversion_n_hat_absolute"],
    )

    actual_likelihood = json.loads(GENERATED_LIKELIHOOD.read_text(encoding="utf-8"))
    for expected_name, actual_name in (("etas", "ETAS"), ("poisson", "Poisson")):
        for component in ("nll", "tll", "sll"):
            _validate_difference(
                f"{actual_name}.{component}",
                expected["likelihood"][expected_name][component],
                actual_likelihood[actual_name][component],
                tolerances["fresh_inversion_likelihood_absolute"],
            )

    print(f"n_iterations,{actual['n_iterations']}")
    print(f"n_target_events,{actual['n_target_events']}")
    print("fresh inversion aligned")
    return 0


def _validate_difference(
    name: str, expected: float, actual: float, tolerance: float
) -> None:
    delta = abs(actual - expected)
    print(f"{name},{expected:.17g},{actual:.17g},{delta:.17g}")
    if delta > tolerance:
        raise ValueError(f"{name} differs by {delta:.3g}; tolerance is {tolerance:g}")


if __name__ == "__main__":
    raise SystemExit(main())
