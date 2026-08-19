# ETAS Baseline

The Epidemic-Type Aftershock Sequence model is a marked spatial-temporal point
process. Its conditional intensity is the sum of background seismicity and
triggering contributions from prior earthquakes.

The exact parameterization for this project is defined by the ETAS reference
implementation used by EarthquakeNPP, not by an informal ETAS-like equation.
The native implementation must document and test:

- background intensity and spatial density;
- event productivity as a function of magnitude;
- modified Omori temporal decay, including finite-time normalization;
- magnitude-dependent spatial kernel and normalization;
- exponential magnitude density above completeness magnitude;
- the point-process log-likelihood and compensator integral;
- boundary correction, auxiliary events, and source truncation;
- branching ratio and stability conditions;
- catalog simulation and continuation.

## Primary Sources

- Ogata, Y. (1988), Statistical Models for Earthquake Occurrences and Residual
  Analysis for Point Processes.
- Mizrahi, L., Nandan, S., and Wiemer, S. (2021), The Effect of Declustering on
  the Size Distribution of Mainshocks.
- Mizrahi, L., Nandan, S., and Wiemer, S. (2021), Embracing Data
  Incompleteness for Better Earthquake Forecasting.
- Stockman et al. (2026), EarthquakeNPP: Benchmark Datasets for Earthquake
  Forecasting with Neural Point Processes.

## Reference Software

- `https://github.com/ss15859/EarthquakeNPP`
- `https://github.com/ss15859/etas`
- ETAS software DOI: `10.5281/zenodo.6583992`

