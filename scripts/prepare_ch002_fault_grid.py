#!/usr/bin/env python3
"""Build the parameter-neutral nearest-fault representation on the RELM grid."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.fault_grid import nearest_fault_sections
from etas_challenge.training_matrix import (
    GridDefinition,
    sha256_file,
    write_deterministic_npz,
)
from etas_challenge.ucerf3_faults import FaultSection


FAULTS_SHA256 = "890d1a907ace5cd0d28e1e2f227669c4a8066397fe86a6d36ac4e610b7351543"
GRID_SHA256 = "91ddb0f09244c2173cd5fe9fab4405a6582175ee933ba271d63639c8872cdce9"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--faults",
        type=Path,
        default=Path("data/local/ch002-ucerf3-fault-sections-v1.json"),
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=Path("data/grids/california-relm-v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/ch002-ucerf3-relm-nearest-v1.npz"),
    )
    parser.add_argument("--neighbors", type=int, default=4)
    args = parser.parse_args()

    if sha256_file(args.faults) != FAULTS_SHA256:
        raise ValueError("CH-002 clean fault-section hash changed")
    if sha256_file(args.grid) != GRID_SHA256:
        raise ValueError("California RELM grid hash changed")
    payload = json.loads(args.faults.read_text(encoding="utf-8"))
    sections = [FaultSection(**item) for item in payload["sections"]]
    grid = GridDefinition.load(args.grid)
    nearest_ids, distances = nearest_fault_sections(
        grid, sections, neighbors=args.neighbors
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_deterministic_npz(
        args.output,
        {
            "cell_origin_units": grid.origin_units.astype(np.int16),
            "nearest_section_ids": nearest_ids,
            "nearest_trace_distances_km": distances,
            "neighbors_per_cell": np.asarray(args.neighbors, dtype=np.int16),
            "faults_sha256": np.asarray(FAULTS_SHA256),
            "grid_sha256": np.asarray(GRID_SHA256),
        },
    )
    print(
        f"mapped {grid.num_cells} cells to {args.neighbors} nearest sections "
        f"at {args.output} (sha256={sha256_file(args.output)}, "
        f"nearest_max_km={float(np.max(distances[:, 0])):.3f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
