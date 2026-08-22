#!/usr/bin/env python3
"""Build the frozen CH-002 fault graph and initial-state particle ensemble."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.fault_graph import (
    build_fault_graph,
    condition_ensemble_on_branch_masks,
    sample_initial_state_ensemble,
)
from etas_challenge.readiness_replay import balanced_particle_branches
from etas_challenge.training_matrix import sha256_file, write_deterministic_npz
from etas_challenge.ucerf3_faults import FaultSection


FAULTS_SHA256 = "890d1a907ace5cd0d28e1e2f227669c4a8066397fe86a6d36ac4e610b7351543"
CORRELATION_LENGTH_KM = 25.0
ALIGNMENT_FLOOR = 0.25
GRAPH_SMOOTHNESS = 4.0
PARTICLES = 256
SEED = 20260822


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--faults",
        type=Path,
        default=Path("data/local/ch002-ucerf3-fault-sections-v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/ch002-fault-graph-initial-state-v1.npz"),
    )
    args = parser.parse_args()

    if sha256_file(args.faults) != FAULTS_SHA256:
        raise ValueError("CH-002 clean fault-section hash changed")
    payload = json.loads(args.faults.read_text(encoding="utf-8"))
    sections = [FaultSection(**item) for item in payload["sections"]]
    graph = build_fault_graph(
        sections,
        correlation_length_km=CORRELATION_LENGTH_KM,
        alignment_floor=ALIGNMENT_FLOOR,
    )
    ensemble = sample_initial_state_ensemble(
        graph.adjacency,
        particles=PARTICLES,
        seed=SEED,
        graph_smoothness=GRAPH_SMOOTHNESS,
    )
    particle_branches = balanced_particle_branches(PARTICLES)
    active_masks = np.asarray(
        [
            [section.slip_rate_mm_per_year[branch] is not None for section in sections]
            for branch in particle_branches
        ],
        dtype=bool,
    )
    ensemble = condition_ensemble_on_branch_masks(ensemble, active_masks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_deterministic_npz(
        args.output,
        {
            "section_ids": graph.section_ids,
            "trace_distance_km": graph.trace_distance_km,
            "axial_alignment": graph.axial_alignment,
            "shared_fault_model": graph.shared_fault_model,
            "adjacency": graph.adjacency,
            "stress_component": ensemble.stress_component.astype(np.float32),
            "effective_strength_component": (
                ensemble.effective_strength_component.astype(np.float32)
            ),
            "criticality_margin": ensemble.criticality_margin.astype(np.float32),
            "particle_loading_branch": particle_branches,
            "particle_active_sections": active_masks,
            "correlation_length_km": np.asarray(CORRELATION_LENGTH_KM),
            "alignment_floor": np.asarray(ALIGNMENT_FLOOR),
            "graph_smoothness": np.asarray(GRAPH_SMOOTHNESS),
            "particles": np.asarray(PARTICLES, dtype=np.int16),
            "seed": np.asarray(SEED, dtype=np.int32),
            "faults_sha256": np.asarray(FAULTS_SHA256),
        },
    )
    edge_count = int(np.count_nonzero(np.triu(graph.adjacency > 1e-6, k=1)))
    print(
        f"built {len(sections)}-section graph and {PARTICLES} particles at "
        f"{args.output} (sha256={sha256_file(args.output)}, "
        f"effective_edges={edge_count})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
