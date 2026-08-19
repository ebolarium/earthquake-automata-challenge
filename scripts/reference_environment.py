"""Smoke-check the isolated reference runtime and its critical imports."""

from __future__ import annotations

import importlib.metadata
import json
import platform

import geopandas
import cartopy
import jinja2
import joblib
import matplotlib
import numpy
import pandas
import requests
import scipy
import shapely
from etas.evaluation import ETASLikelihoodCalculation
from etas.inversion import ETASParameterCalculation
from seismostats import ForecastCatalog


def main() -> int:
    report = {
        "machine": platform.machine(),
        "python": platform.python_version(),
        "etas": importlib.metadata.version("etas"),
        "seismostats": importlib.metadata.version("SeismoStats"),
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
        "requests": requests.__version__,
        "scipy": scipy.__version__,
        "geopandas": geopandas.__version__,
        "cartopy": cartopy.__version__,
        "jinja2": jinja2.__version__,
        "joblib": joblib.__version__,
        "matplotlib": matplotlib.__version__,
        "shapely": shapely.__version__,
        "imports": {
            "ETASParameterCalculation": ETASParameterCalculation.__name__,
            "ETASLikelihoodCalculation": ETASLikelihoodCalculation.__name__,
            "ForecastCatalog": ForecastCatalog.__name__,
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
