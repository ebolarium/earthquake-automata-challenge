# NATIVE-002: ComCat_25 Full-Catalog Alignment

## Question

Does the independent native ETAS implementation reproduce event-level and
aggregate likelihood results across the full locked `ComCat_25` replay?

## Frozen Inputs

- Date: 2026-08-20.
- Platform: `linux/amd64`.
- Python: `3.11.11`.
- NumPy: `1.26.4`.
- SciPy: `1.15.1`.
- Catalog events: `92,263`.
- Test targets: `21,889`.
- Augmented catalog SHA-256:
  `63380cae37341610196afd2be16cd887ed0ceaa6001c06e667aa1623351185cd`.
- Parameter file SHA-256:
  `90c19386be2d11aa590a6380dc7ef327a367afa2c4d3869e63f957d34456df65`.

Generated catalog data and the JSON report remain ignored artifacts. The
committed replay command, equations, environment lock, hashes, and results are
the reproducibility record.

## Method

The catalog was replayed sequentially with vectorized history calculations.
Only one target's history vectors were allocated at a time. Atomic checkpoints
were written every 500 targets and the detached Docker run resumed from target
5,500 after an intentional process handoff.

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" -w /workspace \
  -e PYTHONPATH=src etas-challenge-reference \
  python scripts/compare_native_reference_catalog.py --checkpoint-every 500
```

Native temporal compensators use the published closed form. Stored reference
values use the reference package's one-million-sample interpolation mesh.

## Event-Level Results

| Component | Maximum absolute delta | Mean absolute delta |
| --- | ---: | ---: |
| Point intensity | 7.11e-15 | 3.43e-17 |
| Temporal intensity | 4.55e-13 | 2.84e-15 |
| Strict-reference compensator | 4.58e-6 | 3.41e-8 |

All event-level acceptance gates passed. The larger compensator delta is
expected from interpolation versus closed-form integration and remains below
the frozen `1e-5` threshold.

## Aggregate Results

| Mode | NLL | TLL | SLL |
| --- | ---: | ---: | ---: |
| Stored reference | 7.2554275527265855 | 1.4343428345122435 | -8.689770387238827 |
| Native strict-reference | 7.255427553073218 | 1.4343428341656106 | -8.689770387238827 |
| Native corrected first interval | 7.255531979846477 | 1.4342384073923515 | -8.689770387238827 |

Strict-reference NLL and TLL differ from stored output by `3.47e-10`, below
the `1e-9` aggregate gate. SLL matches exactly because the compensator cancels
between LL and TLL.

## First-Interval Correction

| First-event compensator | Value |
| --- | ---: |
| Stored reference | 0.4793879227800062 |
| Native strict-reference | 0.4793879227854312 |
| Native published correction | 2.7651855626515736 |

Restoring the omitted pre-window triggered mass changes aggregate NLL by
`+0.00010442677325883665` and TLL by the opposite amount. SLL is unchanged.

## Conclusion

The native event likelihood is aligned with the full external baseline. The
only substantive semantic difference is the already isolated first-interval
reference behavior. Stage 5 is complete; subsequent prospective evaluation
will use the published corrected compensator and report compatibility scores
separately when needed.
