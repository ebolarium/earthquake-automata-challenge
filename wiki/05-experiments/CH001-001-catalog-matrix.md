# CH001-001: Leakage-Free Catalog Grid Matrix

## Question

Can the first challenger receive reproducible daily catalog features and target
labels on the exact CSEP grid without any target-window event entering its
features?

## Contract

- Challenge: `configs/challenge/challenge-v1.json`.
- Matrix config: `configs/challenge/ch001-matrix-v1.json`.
- Grid: pinned pyCSEP 0.6.3 California RELM grid, 7,682 cells at 0.1 degrees.
- Issue period: 2007-01-01 through 2022-12-31, covering only challenger fit and
  development-validation splits.
- History: rounded `M >= 2.5` events strictly before each `00:00Z` issue.
- Targets: cell counts for `M >= 2.5`, `M >= 3.5`, and `M >= 4.0` in the next
  half-open UTC day.

## Features

Exact-cell and eight-neighbor activity counts are retained for 3, 7, 30, and
90 days. Continuous features contain 30-day excess over a training-only
background, 7-versus-30-day acceleration, cell and neighbor recency capped at
365 days, and the smoothed daily background rate.

The background uses only 1981-2006 events. Empty cells receive an empirical
Bayes prior equivalent to 365 days at the global cell rate. The current day's
target events update rolling state only after its feature snapshot has been
emitted.

## Storage

Each calendar month is an independent compressed NPZ shard under the ignored
`artifacts/ch001-matrix-v1/` directory. Count features and targets use
`uint16`; continuous features use `float32`. The completed manifest records
every shard hash and is the only generated matrix artifact admitted to Git.

NPZ members are written with fixed ZIP metadata in a fixed order. The canonical
matrix was generated in the pinned Python 3.11.11 reference container and then
read back shard by shard to validate hashes, shapes, dtypes, finite values,
global day continuity, and target totals.

## Result

| Measure | Value |
|---|---:|
| Issue days | 5,844 |
| Grid cells | 7,682 |
| Cell-day rows | 44,893,608 |
| Monthly shards | 192 |
| Compressed size | 86 MB |
| `M >= 2.5` targets | 17,331 |
| `M >= 3.5` targets | 2,670 |
| `M >= 4.0` targets | 707 |

The 2,162 catalog events reported outside the RELM grid are retained in the
source catalog but excluded consistently from matrix features and labels.

## Boundary

This experiment creates catalog features and labels only. It does not yet
contain the frozen ETAS cell-rate offset, fit a challenger, open the locked
retrospective test, or make a performance claim.
