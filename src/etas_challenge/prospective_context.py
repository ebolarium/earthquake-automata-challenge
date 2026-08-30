"""Hash-locked geometry and rate context for prospective CH-008 runtime."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from etas_challenge.emergence_fit import strongest_neighbor_transition
from etas_challenge.fault_grid import nearest_fault_sections_for_points
from etas_challenge.grid_forecast import analytical_background_rates
from etas_challenge.readiness_fit import SparseGeometry, sparse_geometry
from etas_challenge.readiness_replay import branch_loading_vector
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.training_matrix import GridDefinition, sha256_file
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


@dataclass(frozen=True, slots=True)
class CaliforniaRuntimeContext:
    grid: GridDefinition
    sections: tuple[FaultSection, ...]
    section_ids: np.ndarray
    active_sections: np.ndarray
    transitions: tuple
    grid_geometries: tuple[SparseGeometry, ...]
    state_background_grid: np.ndarray
    baseline_background_grid: np.ndarray
    expected_section_background: np.ndarray
    beta: float
    magnitude_reference: float
    maximum_log_tilt: float
    bandwidth_km: float
    cutoff_km: float
    fault_prior_odds: float
    event_neighbors: int

    def event_geometries(
        self, latitudes: np.ndarray, longitudes: np.ndarray
    ) -> tuple[SparseGeometry, ...]:
        nearest_ids, nearest_distances = nearest_fault_sections_for_points(
            latitudes,
            longitudes,
            list(self.sections),
            neighbors=self.event_neighbors,
        )
        return tuple(
            sparse_geometry(
                nearest_ids,
                nearest_distances,
                self.section_ids,
                active,
                bandwidth_km=self.bandwidth_km,
                cutoff_km=self.cutoff_km,
                fault_prior_odds=self.fault_prior_odds,
            )
            for active in self.active_sections
        )


def load_california_runtime_context(root: Path) -> CaliforniaRuntimeContext:
    """Load the exact retrospective state geometry plus prospective ETAS baseline."""

    config_path = root / "configs/challenge/ch008-retrospective-v1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paths = {
        "fault_graph": root / "data/production/ch002-fault-graph-initial-state-v1.npz",
        "fault_grid": root / "data/production/ch002-ucerf3-relm-nearest-v1.npz",
        "fault_sections": root / "data/production/ch002-ucerf3-fault-sections-v1.json",
        "grid": root / config["grid"],
        "simulation_config": root / config["simulation_config"],
    }
    for name, path in paths.items():
        expected = config[f"{name}_sha256"]
        if sha256_file(path) != expected:
            raise ValueError(f"California runtime input changed: {name}")

    with np.load(paths["fault_graph"], allow_pickle=False) as source:
        section_ids = source["section_ids"].copy()
        adjacency = source["adjacency"].astype(float)
    with np.load(paths["fault_grid"], allow_pickle=False) as source:
        cell_origins = source["cell_origin_units"].copy()
        grid_ids = source["nearest_section_ids"].copy()
        grid_distances = source["nearest_trace_distances_km"].copy()
        event_neighbors = int(source["neighbors_per_cell"])
    payload = json.loads(paths["fault_sections"].read_text(encoding="utf-8"))
    sections = tuple(
        sorted(
            (FaultSection(**item) for item in payload["sections"]),
            key=lambda section: section.section_id,
        )
    )
    grid = GridDefinition.load(paths["grid"])
    if not np.array_equal(cell_origins, grid.origin_units):
        raise ValueError("California fault and forecast grids disagree")
    simulation = json.loads(paths["simulation_config"].read_text(encoding="utf-8"))
    etas_model_path = root / "models/etas/california-comcat25-v1.json"
    etas_model = json.loads(etas_model_path.read_text(encoding="utf-8"))
    fixed = config["fixed_contract"]
    if grid_ids.shape[1] != fixed["grid_neighbors"]:
        raise ValueError("California fault-grid neighbor count changed")

    state_background = analytical_background_rates(
        grid,
        10.0 ** simulation["parameters"]["log10_mu"],
        simulation["earth_radius_km"],
    )
    baseline_background = analytical_background_rates(
        grid,
        10.0 ** etas_model["parameters"]["log10_mu"],
        simulation["earth_radius_km"],
    )
    active_rows = []
    transitions = []
    geometries = []
    expected = []
    for branch in SLIP_RATE_BRANCHES:
        _, active = branch_loading_vector(list(sections), branch)
        active_rows.append(active)
        transitions.append(
            strongest_neighbor_transition(adjacency, active, fixed["graph_neighbors"])
        )
        geometry = sparse_geometry(
            grid_ids,
            grid_distances,
            section_ids,
            active,
            bandwidth_km=fixed["grid_bandwidth_km"],
            cutoff_km=fixed["grid_cutoff_km"],
            fault_prior_odds=fixed["fault_prior_odds"],
        )
        geometries.append(geometry)
        section_mass, _ = aggregate_sparse_section_mass(
            state_background, geometry, len(section_ids)
        )
        expected.append(section_mass)
    return CaliforniaRuntimeContext(
        grid=grid,
        sections=sections,
        section_ids=section_ids,
        active_sections=np.asarray(active_rows),
        transitions=tuple(transitions),
        grid_geometries=tuple(geometries),
        state_background_grid=state_background,
        baseline_background_grid=baseline_background,
        expected_section_background=np.asarray(expected),
        beta=float(simulation["beta"]),
        magnitude_reference=float(simulation["m_ref"]),
        maximum_log_tilt=float(fixed["maximum_log_tilt"]),
        bandwidth_km=float(fixed["grid_bandwidth_km"]),
        cutoff_km=float(fixed["grid_cutoff_km"]),
        fault_prior_odds=float(fixed["fault_prior_odds"]),
        event_neighbors=event_neighbors,
    )
