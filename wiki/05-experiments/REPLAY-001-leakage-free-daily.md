# REPLAY-001: Leakage-Free Daily Replay

## Question

Can the frozen native ETAS baseline be scored on a daily clock while ensuring
that no event affects a forecast before its origin time?

## Frozen Inputs

- Config: `configs/replay/comcat25-daily-v1.json`.
- Catalog: Local California V1.
- Catalog SHA-256:
  `0f05fcdbf1315a23ace109d1248848ca0cff9dde8cfdd6299bde128116a4d399`.
- Config SHA-256:
  `5ac9ebe57025707a52667759d928085b64382cb01667938ad6db596a2ebfe0a0`.
- ETAS parameters: frozen REF-001 values; no replay-window fitting.
- Poisson fit: 31,876 local events from 1971-01-01 through 2007-01-01.
- Issue range: 2007-01-01 through 2026-08-18 UTC.
- Horizon: one day.
- Completeness: `Mc = M_ref = 2.5`.
- Platform: `linux/amd64`, Python 3.11.11, NumPy 1.26.4, SciPy 1.15.1.

## Leakage Gates

Tests establish that issue-time events are targets rather than history, window
end is exclusive, tied events do not trigger one another, and mutating events
at or after window end cannot alter the current score.

The completed 7,170-day output has a continuous daily clock, zero history-chain
breaks, and no non-finite values. Daily history obeys

```text
history[t+1] = history[t] + targets[t].
```

## Results

| Property | Value |
| --- | ---: |
| Replay days | 7,170 |
| Days with events | 6,050 |
| Zero-event days | 1,120 |
| Target events | 24,498 |
| Initial history | 31,876 |
| Final history after replay | 56,374 |

| Lane | Expected events | Observed / expected | Total log likelihood | Mean LL/event |
| --- | ---: | ---: | ---: | ---: |
| Frozen issue-time | 19,563.2583 | 1.25225 | -233,849.2294 | -9.54565 |
| Sequential ETAS | 26,106.1282 | 0.93840 | -203,352.3374 | -8.30077 |
| Uniform Poisson | 17,381.6199 | 1.40942 | -333,136.2553 | -13.59851 |

Sequential ETAS gains `129,783.9179` log units over uniform Poisson, or
`5.2977352` per observed event. This is a diagnostic on the frozen retrospective
snapshot, not yet a superiority claim: paired tests, clustering-aware
uncertainty, and pyCSEP consistency tests remain pending.

The sequential expected count includes triggered mass from events observed
inside each day. It is valid for point-process likelihood but must not be read
as a day-ahead count forecast available at issue time. The frozen lane is the
strict issue-time view but omits unobserved descendant generations.

## Determinism

Two complete runs in the locked environment produced byte-identical outputs:

- Daily CSV SHA-256:
  `770898ac35ee49755e505c9fbca6d47d85e8ad10441a8b2da11c9584e48efa60`.
- Summary SHA-256:
  `9eed092dbb0f09ba66c75fac8148695f82bad63861c76ff30246d444e864625b`.

Generated outputs remain ignored. Their hashes and result summary are committed
in `data/manifests/daily-replay-v1.json`.

## Limitation

The legacy catalog lacks historical payload revisions for most events. The
replay enforces strict origin-time ordering but cannot reconstruct the exact
magnitude and location values available on each historical issue date. This is
a retrospective as-of-snapshot replay, not an operational prospective record.

## Conclusion

Stage 7 is complete. The native baseline now has a deterministic daily scoring
stream suitable for pyCSEP adaptation, with the frozen and sequential lanes
kept explicitly separate.
