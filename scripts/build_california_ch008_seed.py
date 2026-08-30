#!/usr/bin/env python3
"""Build the locked California CH-008 terminal state at the retrospective boundary."""

from __future__ import annotations

import json
from pathlib import Path
import platform
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_ch004_validation import EPOCH, build_evaluator  # noqa: E402
from etas_challenge.prospective_replay import replay_california_ch008_state  # noqa: E402
from etas_challenge.training_matrix import sha256_file, write_deterministic_npz  # noqa: E402


CONFIG = ROOT / "configs/challenge/ch008-retrospective-v1.json"
PARENT_MODEL = ROOT / "models/ch004-marked-renewal-v1.json"
CH008_MODEL = ROOT / "models/ch008-boundary-sensitivity-v1.json"
REPLAY_MODULE = ROOT / "src/etas_challenge/prospective_replay.py"
OUTPUT = ROOT / "data/production/california-ch008-seed-20260819-v1.npz"
MANIFEST = ROOT / "data/manifests/california-ch008-seed-20260819-v1.json"


def ordered_parameters(model: dict, names: list[str]) -> np.ndarray:
    return np.asarray([model["parameters"][name] for name in names], dtype=float)


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    parent_model = json.loads(PARENT_MODEL.read_text(encoding="utf-8"))
    ch008_model = json.loads(CH008_MODEL.read_text(encoding="utf-8"))
    for path_key, hash_key in (
        ("event_history", "event_history_sha256"),
        ("fault_graph", "fault_graph_sha256"),
        ("fault_grid", "fault_grid_sha256"),
        ("fault_sections", "fault_sections_sha256"),
        ("grid", "grid_sha256"),
        ("simulation_config", "simulation_config_sha256"),
    ):
        if sha256_file(ROOT / config[path_key]) != config[hash_key]:
            raise ValueError(f"locked California seed input changed: {path_key}")
    if sha256_file(PARENT_MODEL) != config["parent_model_sha256"]:
        raise ValueError("locked CH-004 model changed")
    if sha256_file(CH008_MODEL) != config["model_sha256"]:
        raise ValueError("locked CH-008 model changed")
    with np.load(ROOT / config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}
    evaluator = build_evaluator(config, history)
    parent_names = json.loads(
        (ROOT / config["parent_fit_config"]).read_text(encoding="utf-8")
    )["parameter_order"]
    ch008_names = config["parameter_order"]
    state = replay_california_ch008_state(
        evaluator,
        ordered_parameters(parent_model, parent_names),
        ordered_parameters(ch008_model, ch008_names),
    )
    as_of_day = int(history["all_issue_days"][-1]) + 1
    as_of = np.datetime_as_string(EPOCH + np.timedelta64(as_of_day, "D"), unit="s") + "Z"
    if as_of != "2026-08-19T00:00:00Z":
        raise ValueError("California retrospective boundary changed")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_deterministic_npz(
        OUTPUT,
        {
            "age": state.age.astype(np.float64),
            "exposure": state.exposure.astype(np.float64),
            "roots": state.roots.astype(np.float64),
            "as_of": np.asarray(as_of),
            "event_history_sha256": np.asarray(config["event_history_sha256"]),
            "parent_model_sha256": np.asarray(config["parent_model_sha256"]),
            "ch008_model_sha256": np.asarray(config["model_sha256"]),
        },
    )
    manifest = {
        "schema_version": 1,
        "state_id": "california-ch008-seed-20260819-v1",
        "status": "locked_retrospective_terminal_state",
        "region_id": "california-relm",
        "as_of": as_of,
        "history_boundary": "forecast_before_same_day_observations",
        "tool": {
            "name": "scripts/build_california_ch008_seed.py",
            "script_sha256": sha256_file(Path(__file__)),
            "replay_module_sha256": sha256_file(REPLAY_MODULE),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "inputs": {
            "config": str(CONFIG.relative_to(ROOT)),
            "config_sha256": sha256_file(CONFIG),
            "event_history_sha256": config["event_history_sha256"],
            "fault_graph_sha256": config["fault_graph_sha256"],
            "fault_grid_sha256": config["fault_grid_sha256"],
            "fault_sections_sha256": config["fault_sections_sha256"],
            "parent_model_sha256": config["parent_model_sha256"],
            "ch008_model_sha256": config["model_sha256"],
        },
        "output": {
            "path": str(OUTPUT.relative_to(ROOT)),
            "sha256": sha256_file(OUTPUT),
            "bytes": OUTPUT.stat().st_size,
            "arrays": {
                "age": list(state.age.shape),
                "exposure": list(state.exposure.shape),
                "roots": list(state.roots.shape),
            },
        },
        "claim_boundary": (
            "Exact terminal latent state of the locked California CH-008 retrospective "
            "replay; no prospective observation or score is read."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "as_of": as_of, **manifest["output"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
