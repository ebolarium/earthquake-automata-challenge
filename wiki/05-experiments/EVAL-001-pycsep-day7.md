# EVAL-001: pyCSEP Day-7 Consistency Gate

## Question

Can the native ETAS continuation and a training-only Poisson control be passed
through the pinned EarthquakeNPP pyCSEP protocol without catalog, clock, grid,
magnitude, or empty-simulation loss?

This is an integration and consistency gate. One active day with three events
cannot establish forecast superiority or long-run calibration.

## Frozen Inputs

- issue time: `2007-01-08T00:00:00Z`, EarthquakeNPP test day 7;
- target window: `[2007-01-08T00:00:00Z, 2007-01-09T00:00:00Z)`;
- history: clean local California V1 events strictly before issue time;
- parameters and beta: locked ComCat_25 REF-001 fit;
- branching ratio: `0.947304`, finite but close to the critical value of 1;
- completeness and reference magnitude: `Mc = Mref = 2.5`;
- simulations: 10,000 per model with catalog-independent deterministic seeds;
- spatial region: pyCSEP `california_relm_region`, 7,682 cells at 0.1 degrees;
- magnitude bins: 2.5 through 7.6 at 0.1, with the final bin extending upward;
- pyCSEP: 0.6.3 in Python 3.11.11.

The observed target contains three earthquakes after the same spatial and
magnitude filters.

## Forecasts

The native continuation samples all direct offspring from pre-issue history,
then simulates background events and every descendant generation through the
end of the day. Triggered events outside the target polygon remain capable of
producing later descendants; only the reported forecast catalog is spatially
filtered. This is a predictive catalog simulation, unlike REPLAY-001's frozen
conditional-intensity approximation.

The Poisson control uses the rate estimated only from 1971-2007 training data,
uniform polygon locations, and the same fitted exponential magnitude law.

Empty simulations are written explicitly. All 10,000 catalog IDs therefore
reach pyCSEP, including trailing empty catalogs that an event-only CSV can
otherwise lose.

## Reference Boundary

The simulation follows the native mathematical model used by the aligned
likelihood: constant spatial background `mu`, `Mref = 2.5`, normalized
whole-plane triggering kernels, and spherical destination coordinates.

EarthquakeNPP's auxiliary simulation helper is not a bitwise oracle for this
step. It resamples fitted background-event locations with Gaussian smoothing,
passes the lower magnitude-bin edge (`2.45`) as its simulation reference, uses
a local degree-distance approximation, and reseeds from operating-system
entropy. Those implementation choices are not silently copied into the native
model. A strict simulation-compatibility comparison, if needed, must be kept as
a separate experiment from this published-model consistency gate.

## Results

| Model | Mean count | Count variance | Empty | Count 2.5%-97.5% |
| --- | ---: | ---: | ---: | --- |
| Native ETAS | 2.7186 | 5.2594 | 1,318 | 0-8 |
| Poisson | 2.4115 | 2.4128 | 898 | 0-6 |

ETAS has the expected extra-Poisson count dispersion from within-window
cascades. The observed count is 3.

| Test | ETAS quantiles | Poisson quantiles | Rejected at 5% |
| --- | --- | --- | --- |
| Number | 0.4121, 0.7394 | 0.2943, 0.8759 | Neither |
| Spatial | 0.3414, 0.6586 | 0.6468, 0.3639 | Neither |
| Pseudolikelihood | 0.6080, 0.3920 | 0.8187, 0.1906 | Neither |
| Magnitude | 0.8723, 0.1299 | 0.9460, 0.0565 | Neither |

The spatial and pseudolikelihood observed statistics are less negative for
ETAS than for Poisson, but consistency-test quantiles are not a paired model
comparison. No skill claim is made from them.

## Reproduction

```bash
PYTHONPATH=src python3 scripts/generate_pycsep_forecasts.py
docker build --platform linux/amd64 -f docker/reference.Dockerfile \
  -t etas-challenge-reference .
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" \
  etas-challenge-reference python scripts/run_pycsep_evaluation.py
```

Forecasts and full test distributions remain ignored under
`artifacts/pycsep-day7-v1/`. The checksummed result contract is committed at
`data/manifests/pycsep-day7-v1.json`.

## Conclusion

The day-7 native ETAS and Poisson forecasts pass all four pyCSEP consistency
tests, retain all 10,000 simulations, and use the frozen evaluation contract.
EVAL-001 completes the pyCSEP integration milestone. Long-run calibration and
paired skill uncertainty remain requirements for any later superiority claim.
