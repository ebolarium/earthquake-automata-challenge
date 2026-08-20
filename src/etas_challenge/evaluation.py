"""Contracts for committed pyCSEP evaluation manifests."""

from __future__ import annotations

import re


PYCSEP_EVALUATION_SCHEMA_VERSION = 1


def validate_pycsep_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != PYCSEP_EVALUATION_SCHEMA_VERSION:
        raise ValueError("unsupported pyCSEP manifest schema_version")
    if manifest.get("status") != "completed":
        raise ValueError("pyCSEP manifest must have completed status")
    for section in ("tool", "inputs", "protocol", "outputs", "results"):
        if not isinstance(manifest.get(section), dict):
            raise ValueError(f"pyCSEP manifest missing {section}")
    if manifest["protocol"].get("n_simulations", 0) <= 0:
        raise ValueError("pyCSEP evaluation must contain simulations")
    for key, value in manifest["outputs"].items():
        if key.endswith("_sha256") and not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"invalid SHA-256 at outputs.{key}")
    for model in ("etas", "poisson"):
        tests = manifest["results"].get(model)
        if not isinstance(tests, dict):
            raise ValueError(f"pyCSEP manifest missing {model} results")
        if set(tests) != {"number", "spatial", "pseudolikelihood", "magnitude"}:
            raise ValueError(f"pyCSEP manifest has incomplete {model} tests")
