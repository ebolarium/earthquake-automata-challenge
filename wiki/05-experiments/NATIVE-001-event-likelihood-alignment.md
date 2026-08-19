# NATIVE-001: Event Likelihood Alignment

## Question

Do native event-level spatial intensity, temporal intensity, compensator, and
likelihood components match the pinned ETAS reference implementation?

## Frozen Inputs

- Five synthetic events; no observed catalog records.
- REF-001 fitted ComCat_25 parameters.
- Region area: `1000 km^2`.
- Earth radius: `6378.1 km`.
- EarthquakeNPP: `26d18048e1ca8ff2b02c7016b993de48ed0760f5`.
- ETAS: `51e0c8e419197df3f88349035a682b90fbd4dfb5`.
- Fixture: `tests/fixtures/native-alignment-001.json`.
- Absolute tolerance: `1e-12`.

The oracle is reproducible with the locked reference image:

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" -w /workspace \
  etas-challenge-reference python scripts/generate_native_alignment_fixture.py
```

The generator replaces the reference's random interpolation mesh with adaptive
quadrature for temporal integrals. All model kernels, haversine distances, and
the event-interval algorithm remain those of the pinned reference package.

## Result

All three target events aligned for point intensity, temporal intensity, and
spatial log likelihood. The second and third event compensators and full
likelihood components also aligned within `1e-12`.

The first event exposed a reference implementation behavior:

| First-event component | Value |
| --- | ---: |
| Published interval compensator | 0.11154475061106447 |
| Reference interval compensator | 0.0005806592383328368 |

The reference subtracts a cumulative triggering integral evaluated at the
first target time from itself. This cancels all pre-window triggered mass, so
only `mu * area * interval_length` remains for that interval.

## Decision

Native ETAS keeps the mathematically published compensator. A compatibility
switch is not added because it would silently preserve a scoring artifact.
Future full-catalog alignment reports must show both strict-reference and
corrected-first-interval scores when comparing aggregate likelihood.

## Conclusion

The native kernels and event likelihood are aligned at the numerical level.
The only observed discrepancy is localized, explained, frozen in the fixture,
and deliberately not copied into the scientific implementation.
