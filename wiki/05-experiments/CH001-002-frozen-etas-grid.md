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

The canonical run uses the pinned Python 3.11.11 container. It was started as
the named detached container `ch001-etas-grid`, so progress can be inspected
without a Codex session:

```bash
docker logs --tail 20 ch001-etas-grid
docker logs -f ch001-etas-grid
docker stats --no-stream ch001-etas-grid
```

## Preflight Result

A two-day, 100-continuation smoke run passed the complete artifact verifier. A
full 10,000-continuation benchmark for 2007-01-01 produced a mean RELM-region
rate of `2.479148` events. It took `2.09` seconds on the local host and about
`4.4` seconds in the canonical emulated `linux/amd64` container. The full
5,844-day Docker run is therefore expected to take roughly seven hours on one
CPU core. Initial observed memory use was about 66 MiB.

The host and pinned Docker runtimes then generated the same 10,000-continuation
2007-01-01 shard independently. The files were byte-identical with SHA-256
`a32cbe254bb2944b201577cf1a8f3fa546881cbb3dcec8404576f09a375cd021`.
This is an implementation reproducibility check, not an accuracy result.

## Boundary

This artifact supplies the frozen ETAS spatial offset for challenger fitting.
It is not a challenger forecast, does not open the locked retrospective split,
and contains no performance comparison.
