#!/usr/bin/env python3
"""Run CH009-003 with the pre-score inactive-row evaluator correction."""

from __future__ import annotations

import json
from pathlib import Path

import fit_ch009_phase_coherent_debt as protocol

from etas_challenge.phase_coherent_debt_ablation_fit_v2 import (
    PhaseCoherentDebtAblationFitEvaluatorV2,
)
from etas_challenge.training_matrix import sha256_file


protocol.PhaseCoherentDebtAblationFitEvaluator = (
    PhaseCoherentDebtAblationFitEvaluatorV2
)


def main() -> int:
    result = protocol.main()
    args = protocol.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    manifest_path = Path(config["fit_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tool"].update(
        {
            "name": "scripts/fit_ch009_phase_coherent_debt_v2.py",
            "script_sha256": sha256_file(Path(__file__)),
            "base_script_sha256": config["base_fit_script_sha256"],
        }
    )
    protocol.atomic_json(manifest_path, manifest)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
