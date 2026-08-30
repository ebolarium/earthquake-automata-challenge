"""Regional-grid transport of the fit-locked CH-008 mechanism."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.sparse import csr_matrix

from etas_challenge.fault_frailty import discounted_gamma_poisson_update
from etas_challenge.fault_frailty import positive_frailty_score
from etas_challenge.fault_frailty import posterior_log_frailty
from etas_challenge.readiness_fit import information_gain_per_event
from etas_challenge.renewal_quiescence import bpt_overdue_score
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age
from etas_challenge.residual_emergence import bounded_background_mixture


@dataclass(frozen=True, slots=True)
class RegionalGrid:
    longitude_edges: np.ndarray
    latitude_edges: np.ndarray
    areas_km2: np.ndarray
    transition: csr_matrix

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.latitude_edges) - 1, len(self.longitude_edges) - 1

    def cells(self, latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
        rows = np.searchsorted(self.latitude_edges, latitudes, side="right") - 1
        columns = np.searchsorted(self.longitude_edges, longitudes, side="right") - 1
        rows = np.clip(rows, 0, self.shape[0] - 1)
        columns = np.clip(columns, 0, self.shape[1] - 1)
        return (rows * self.shape[1] + columns).astype(np.int32)


def regional_grid(
    longitude_bounds: tuple[float, float],
    latitude_bounds: tuple[float, float],
    spacing_degrees: float = 0.5,
) -> RegionalGrid:
    """Build equal-angle cells and a row-normalized eight-neighbor graph."""

    lon_edges = np.arange(longitude_bounds[0], longitude_bounds[1] + 1e-9, spacing_degrees)
    lat_edges = np.arange(latitude_bounds[0], latitude_bounds[1] + 1e-9, spacing_degrees)
    rows, columns = len(lat_edges) - 1, len(lon_edges) - 1
    radius = 6378.1
    longitude_width = math.radians(spacing_degrees)
    row_areas = radius * radius * longitude_width * (
        np.sin(np.radians(lat_edges[1:])) - np.sin(np.radians(lat_edges[:-1]))
    )
    areas = np.repeat(row_areas, columns)
    graph_rows: list[int] = []
    graph_columns: list[int] = []
    graph_values: list[float] = []
    for row in range(rows):
        for column in range(columns):
            source = row * columns + column
            neighbors = [
                other_row * columns + other_column
                for other_row in range(max(0, row - 1), min(rows, row + 2))
                for other_column in range(max(0, column - 1), min(columns, column + 2))
                if (other_row, other_column) != (row, column)
            ]
            weight = 1.0 / len(neighbors)
            graph_rows.extend([source] * len(neighbors))
            graph_columns.extend(neighbors)
            graph_values.extend([weight] * len(neighbors))
    transition = csr_matrix(
        (graph_values, (graph_rows, graph_columns)), shape=(rows * columns, rows * columns)
    )
    return RegionalGrid(lon_edges, lat_edges, areas, transition)


@dataclass(frozen=True, slots=True)
class RegionalEvaluation:
    event_gains: np.ndarray
    challenger_rates: np.ndarray
    background_probabilities: np.ndarray


def evaluate_frozen_ch008(
    *,
    event_days: np.ndarray,
    event_cells: np.ndarray,
    event_magnitudes: np.ndarray,
    etas_rates: np.ndarray,
    etas_mu: float,
    beta: float,
    magnitude_reference: float,
    grid: RegionalGrid,
    issue_day_start: int,
    issue_day_end_exclusive: int,
    parent_parameters: dict[str, float],
    ch008_parameters: dict[str, float],
) -> RegionalEvaluation:
    """Replay CH-008 causally; forecasts precede all observations from that day."""

    days = np.asarray(event_days, dtype=np.int64)
    cells = np.asarray(event_cells, dtype=np.int32)
    magnitudes = np.asarray(event_magnitudes, dtype=float)
    baseline = np.asarray(etas_rates, dtype=float)
    count = len(days)
    if any(len(value) != count for value in (cells, magnitudes, baseline)):
        raise ValueError("regional CH-008 event arrays disagree")
    background_mass = etas_mu * grid.areas_km2
    event_background = np.divide(etas_mu, baseline, out=np.zeros_like(baseline), where=baseline > 0)
    expected_mark = expected_reset_weight_gr(
        beta,
        magnitude_reference,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    marks = magnitude_reset_weight(
        magnitudes,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    expected = background_mass
    expected_hazard = expected * expected_mark
    age = np.zeros_like(expected)
    exposure = np.zeros_like(expected)
    roots = np.zeros_like(expected)
    challenger = baseline.copy()

    for day in range(issue_day_start, issue_day_end_exclusive):
        start = int(np.searchsorted(days, day, side="left"))
        end = int(np.searchsorted(days, day, side="right"))
        neighbor_age = grid.transition @ age
        context_age = (
            (1.0 - parent_parameters["graph_neighborhood_mix"]) * age
            + parent_parameters["graph_neighborhood_mix"] * neighbor_age
        )
        overdue = bpt_overdue_score(context_age, parent_parameters["bpt_aperiodicity"])
        log_frailty = posterior_log_frailty(exposure, roots, ch008_parameters["prior_exposure"])
        frailty = positive_frailty_score(
            log_frailty,
            grid.transition @ log_frailty,
            ch008_parameters["frailty_neighborhood_mix"],
            ch008_parameters["minimum_log_frailty"],
        )
        score = (
            ch008_parameters["renewal_weight"] * overdue
            + ch008_parameters["frailty_weight"] * frailty
        )
        adjusted_mass = bounded_background_mixture(
            background_mass,
            score,
            ch008_parameters["background_mixture_fraction"],
            1.0,
            4.0,
        )
        if end > start:
            selected_cells = cells[start:end]
            challenger[start:end] += (
                adjusted_mass[selected_cells] - background_mass[selected_cells]
            ) / grid.areas_km2[selected_cells]
        observed = np.zeros_like(expected)
        observed_marked = np.zeros_like(expected)
        if end > start:
            np.add.at(observed, cells[start:end], event_background[start:end])
            np.add.at(
                observed_marked,
                cells[start:end],
                event_background[start:end] * marks[start:end],
            )
        age = update_expected_hazard_age(age, expected_hazard, observed_marked)
        exposure, roots = discounted_gamma_poisson_update(
            exposure,
            roots,
            expected,
            observed,
            ch008_parameters["memory_half_life_days"],
        )
    return RegionalEvaluation(
        information_gain_per_event(challenger, baseline), challenger, event_background
    )
