"""Generate the synthetic native-alignment oracle with the locked ETAS image."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import quad

from etas.evaluation import ETASLikelihoodCalculation


PARAMETERS = {
    "log10_mu": -6.3329886729199405,
    "log10_iota": None,
    "log10_k0": -2.6717871682913943,
    "a": 1.5556888441764327,
    "log10_c": -2.79828186440062,
    "omega": -0.06185408129678495,
    "log10_tau": 3.723786279418681,
    "log10_d": -0.7725791509539909,
    "gamma": 1.010873536606162,
    "rho": 0.5565963092026862,
}
EVENTS = [
    ("source-a", "2020-01-02T00:00:00", 34.00, -118.00, 3.2, "history"),
    ("source-b", "2020-01-08T12:00:00", 34.12, -118.18, 4.1, "history"),
    ("target-a", "2020-01-11T06:00:00", 34.08, -118.10, 2.8, "target"),
    ("target-b", "2020-01-13T18:00:00", 34.20, -118.05, 3.0, "target"),
    ("target-c", "2020-01-18T03:00:00", 33.95, -118.25, 2.7, "target"),
]
WINDOW_START = pd.Timestamp("2020-01-10T00:00:00")
AREA = 1_000.0
M_REF = 2.5
EARTH_RADIUS = 6_378.1


def exact_integral(calculation, values):
    return np.array(
        [quad(calculation.time_decay, 0.0, float(value))[0] for value in values]
    )


def published_compensator(calculation, target_index, interval_start):
    interval_end = calculation.times[target_index]
    duration = _days(interval_end - interval_start)
    value = calculation.mu * AREA * duration

    for source_index in range(target_index):
        upper = _days(interval_end - calculation.times[source_index])
        lower = max(0.0, _days(interval_start - calculation.times[source_index]))
        if upper <= lower:
            continue
        time_term = quad(calculation.time_decay, lower, upper)[0]
        value += (
            calculation.aftershock_number(calculation.magnitudes[source_index])
            * calculation.space_integral(calculation.magnitudes[source_index])
            * time_term
        )
    return value


def _days(delta):
    return float(delta / np.timedelta64(1, "D"))


def main():
    catalog = pd.DataFrame(
        EVENTS, columns=["id", "time", "latitude", "longitude", "magnitude", "role"]
    )
    catalog["time"] = pd.to_datetime(catalog["time"])
    metadata = {
        "name": "Synthetic native alignment oracle",
        "id": "NATIVE-ALIGN-001",
        "catalog": catalog.drop(columns="role"),
        "auxiliary_start": "2020-01-01T00:00:00",
        "timewindow_start": "2020-01-05T00:00:00",
        "timewindow_end": WINDOW_START.isoformat(),
        "testwindow_end": "2020-01-20T00:00:00",
        "delta_m": 0.0,
        "mc": M_REF,
        "m_ref": M_REF,
        "coppersmith_multiplier": 100,
        "earth_radius": EARTH_RADIUS,
        "area": AREA,
        "beta": 2.1471442086213064,
        "final_parameters": PARAMETERS,
    }
    calculation = ETASLikelihoodCalculation(metadata)
    calculation.times = catalog.time.to_numpy()
    calculation.magnitudes = catalog.magnitude.to_numpy()
    calculation.lat_rads = np.radians(catalog.latitude.to_numpy())
    calculation.long_rads = np.radians(catalog.longitude.to_numpy())
    calculation.indexes_in_test_window = [2, 3, 4]
    calculation.integral_time_decay = lambda values: exact_integral(
        calculation, values
    )

    reference_compensators = calculation.Lambda()
    point_intensities = calculation.lambd()
    temporal_intensities = calculation.lambd_star()
    targets = []
    interval_start = WINDOW_START.to_datetime64()
    for index in calculation.indexes_in_test_window:
        published = published_compensator(calculation, index, interval_start)
        reference = float(reference_compensators[index])
        point = float(point_intensities[index])
        temporal = float(temporal_intensities[index])
        targets.append(
            {
                "id": catalog.iloc[index].id,
                "point_intensity": point,
                "temporal_intensity": temporal,
                "published_compensator": published,
                "reference_compensator": reference,
                "reference_ll": float(np.log(point) - reference),
                "reference_tll": float(np.log(temporal) - reference),
                "reference_sll": float(np.log(point) - np.log(temporal)),
            }
        )
        interval_start = calculation.times[index]

    epoch = pd.Timestamp("2020-01-01T00:00:00")
    payload = {
        "fixture_id": "NATIVE-ALIGN-001",
        "generator": str(Path(__file__).relative_to(Path.cwd())),
        "reference": {
            "earthquake_npp_commit": "26d18048e1ca8ff2b02c7016b993de48ed0760f5",
            "etas_commit": "51e0c8e419197df3f88349035a682b90fbd4dfb5",
        },
        "units": {"time": "days", "distance": "km", "area": "km^2"},
        "epoch": epoch.isoformat(),
        "window_start": _days(WINDOW_START.to_datetime64() - epoch.to_datetime64()),
        "area": AREA,
        "earth_radius": EARTH_RADIUS,
        "m_ref": M_REF,
        "parameters": PARAMETERS,
        "events": [
            {
                "id": row.id,
                "time": _days(row.time.to_datetime64() - epoch.to_datetime64()),
                "latitude": row.latitude,
                "longitude": row.longitude,
                "magnitude": row.magnitude,
                "role": row.role,
            }
            for row in catalog.itertuples(index=False)
        ],
        "targets": targets,
        "known_reference_behavior": {
            "first_interval_triggered_compensator_omitted": True
        },
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
