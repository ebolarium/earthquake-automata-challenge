"""Report raw differences between generated and expected ETAS parameters."""

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


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = json.loads(GENERATED.read_text(encoding="utf-8"))
    expected = manifest["expected_results"]

    if actual["n_target_events"] != expected["n_target_events"]:
        raise ValueError(
            "target-event count mismatch: "
            f"expected {expected['n_target_events']}, "
            f"got {actual['n_target_events']}"
        )

    print("name,expected,actual,absolute_delta")
    _print_difference("beta", expected["beta"], actual["beta"])
    for name, expected_value in expected["final_parameters"].items():
        _print_difference(name, expected_value, actual["final_parameters"][name])

    print(f"n_iterations,{actual['n_iterations']}")
    print(f"n_target_events,{actual['n_target_events']}")
    return 0


def _print_difference(name: str, expected: float, actual: float) -> None:
    print(f"{name},{expected:.17g},{actual:.17g},{abs(actual - expected):.17g}")


if __name__ == "__main__":
    raise SystemExit(main())
