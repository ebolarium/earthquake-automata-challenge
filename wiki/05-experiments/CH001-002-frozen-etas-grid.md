# CH001-002: Frozen ETAS Grid Offset

## Question

Can the pinned EarthquakeNPP ETAS catalog-continuation forecast be converted to
reproducible positive daily rates on every CH-001 RELM cell without a large
memory requirement or target-window leakage?

## Frozen Method

- Configuration: `configs/challenge/ch001-etas-grid-v1.json`.
- Issue period: 2007-01-01 through 2022-12-31, matching CH001-001.
- Forecast: 10,000 one-day native ETAS catalog continuations per issue time.
- History: events strictly before `00:00Z`; simulated within-window descendants
  remain part of the forecast, as in EarthquakeNPP.
- Randomness: NumPy `SeedSequence` from the locked seed, absolute issue day, and
  simulation ID.
- Grid: pinned pyCSEP 0.6.3 California RELM grid with 7,682 cells.

The direct uniform-background roots normally sampled in every continuation are
marked and removed from the gridded sample. Their expectation is then added
exactly as `mu * spherical cell area`. Descendants of those roots are retained.
This Rao-Blackwellization does not alter the direct-background expectation and
guarantees a positive physical floor in every cell; it also avoids arbitrary
pseudocount smoothing.

## Storage And Recovery

Only one simulated catalog and one calendar month of rate rows are held in
memory. A deterministic compressed NPZ shard is written atomically after each
month. Existing canonical shards are reused only when their period, simulation
count, and configuration hash match, so an interrupted run can resume safely.

Generated shards and logs remain ignored under
`artifacts/ch001-etas-grid-v1/`. The completed manifest will commit every shard
hash, dtype, period, and aggregate count.

## Commands

```bash
PYTHONPATH=src python3 scripts/generate_ch001_etas_grid.py
PYTHONPATH=src python3 scripts/verify_ch001_etas_grid.py
```

For a detached run, progress can be inspected without a Codex session:

```bash
tail -f artifacts/ch001-etas-grid-v1/run.log
cat artifacts/ch001-etas-grid-v1/run.pid
ps -p "$(cat artifacts/ch001-etas-grid-v1/run.pid)" -o pid,etime,%cpu,%mem,command
```

## Preflight Result

A two-day, 100-continuation smoke run passed the complete artifact verifier. A
full 10,000-continuation benchmark for 2007-01-01 produced a mean RELM-region
rate of `2.479148` events and took `2.09` seconds on the local host. The full
5,844-day run is therefore expected to take roughly 3.5 hours on one CPU core
with low memory usage.

## Boundary

This artifact supplies the frozen ETAS spatial offset for challenger fitting.
It is not a challenger forecast, does not open the locked retrospective split,
and contains no performance comparison.
