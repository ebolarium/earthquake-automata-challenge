#!/usr/bin/env python3
"""Export the pinned pyCSEP California RELM grid as integer cell origins."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import csep
import numpy as np
from csep.core import regions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/grids/california-relm-v1.json"),
    )
    args = parser.parse_args()

    region = regions.california_relm_region()
    if region.num_nodes != 7_682 or not np.isclose(region.dh, 0.1):
        raise ValueError("pinned pyCSEP California RELM grid changed")
    origins = region.origins()
    origin_units = np.rint(origins / region.dh).astype(int)
    if not np.allclose(origin_units * region.dh, origins, atol=1e-12):
        raise ValueError("grid origins are not aligned to the declared spacing")

    payload = {
        "schema_version": 1,
        "grid_id": "pycsep-california-relm-0.1-v1",
        "source": {
            "package": "pycsep",
            "version": csep.__version__,
            "factory": "csep.core.regions.california_relm_region",
        },
        "coordinate_order": "longitude,latitude",
        "boundary_policy": "(origin, origin + cell_size]",
        "cell_size_degrees": float(region.dh),
        "coordinate_units_per_degree": int(round(1.0 / region.dh)),
        "num_cells": int(region.num_nodes),
        "origin_units": origin_units.tolist(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    os.replace(temporary, args.output)
    print(f"exported {region.num_nodes} cells to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
