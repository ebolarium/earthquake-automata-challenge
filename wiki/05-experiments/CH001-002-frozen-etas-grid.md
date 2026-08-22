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
`artifacts/ch001-etas-grid-v1/`. The committed manifest records every shard
hash, dtype, period, and aggregate count.

## Commands

```bash
PYTHONPATH=src python3 scripts/generate_ch001_etas_grid.py
PYTHONPATH=src python3 scripts/verify_ch001_etas_grid.py
```

The canonical run used the pinned Python 3.11.11 container. After four monthly
shards were completed sequentially, the remaining period was divided into six
non-overlapping month-aligned workers. A seventh low-resource container waited
for all 192 atomic shards, rebuilt the canonical manifest, and ran the complete
artifact verifier.

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

## Result

| Measure | Value |
|---|---:|
| Issue days | 5,844 |
| Grid cells | 7,682 |
| Cell-day rows | 44,893,608 |
| Monthly shards | 192 |
| Compressed artifacts | 37 MB |
| Simulated non-background events | 181,910,017 |
| Simulated events inside RELM grid | 169,675,750 |
| Mean expected events per day | 3.254666 |
| Median expected events per day | 2.774698 |
| Maximum expected events per day | 59.714448 |
| Minimum cell rate | 0.0000421337 |

All six workers and the finalizer exited with code zero. The verifier checked
all shard hashes, dtypes, shapes, finite positive rates, expected-count sums,
and global day continuity. The committed manifest SHA-256 is
`5cfb842067907d5285162aa64c00d42696f31e2ffe0daa3c1cbbfe2acd1b5e6d`.

## Conclusion

The frozen ETAS offset is ready to join CH001-001 by issue day and cell index.
The next experiment may fit a spatial residual using only the challenger-fit
split, then select and calibrate it on development validation. The locked
retrospective period remains unopened.

## Boundary

This artifact supplies the frozen ETAS spatial offset for challenger fitting.
It is not a challenger forecast, does not open the locked retrospective split,
and contains no performance comparison.
