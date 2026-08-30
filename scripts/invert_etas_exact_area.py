#!/usr/bin/env python3
"""Run pinned academic ETAS while replacing polygon area with an exact mask area."""

from __future__ import annotations

import json
import logging
import sys

from etas import set_up_logger
from etas.inversion import ETASParameterCalculation


def main() -> int:
    set_up_logger(level=logging.DEBUG)
    with open(f"config/{sys.argv[1]}.json", encoding="utf-8") as handle:
        config = json.load(handle)
    exact_area = float(config.pop("exact_area_km2"))
    calculation = ETASParameterCalculation(config)
    calculation.prepare()
    calculation.area = exact_area
    calculation.invert()
    calculation.store_results(config["data_path"], store_pij=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
