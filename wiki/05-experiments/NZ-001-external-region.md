# NZ-001: New Zealand External-Region Test

## Question

Does the single frozen exposure-normalized CH-008 model beat a train-only academic ETAS fit in the official New Zealand CSEP testing region?

## Frozen protocol

- Exact pyCSEP 0.6.3 `nz_csep_region` mask: 6,343 cells at 0.1 degrees.
- GeoNet FDSN earthquakes, M4+, depth below 40 km.
- ETAS fit: 1987-01-01 through 2007-12-31 UTC.
- External evaluation: 2008-01-01 through 2025-12-31 UTC.
- CH-008 parameters are unchanged; only the FERN-002 train-data exposure normalization is applied.
- The New Zealand result cannot select parameters, variants, periods, or thresholds.

This is a retrospective external-geography test. It is stronger than another California split, but it is not a pristine prospective claim because New Zealand's major sequences are already public knowledge.

## Success rule

Mean information gain per event must be positive, the 30-day block-bootstrap 95% lower bound must be positive, and the 90-day lower bound must be nonnegative.

## Commands

```bash
PYTHONPATH=src python scripts/fetch_geonet_nz_catalog.py
PYTHONPATH=src python scripts/prepare_nz_etas_workspace.py
docker run --rm -v "$PWD:/workspace" -w /workspace/artifacts/nz-csep-etas/workspace/Experiments/ETAS etas-challenge-inversion-arm64 python invert_etas_exact_area.py NZ_CSEP
docker run --rm -v "$PWD:/workspace" -w /workspace -e PYTHONPATH=src etas-challenge-inversion-arm64 python scripts/evaluate_nz_ch008_external.py
```

## Outputs

- `data/manifests/nz-csep-catalog-v1.json`
- `artifacts/nz-csep-etas/workspace/Experiments/ETAS/output_data_NZ_CSEP/parameters_0.json`
- `data/manifests/nz-ch008-normalized-external-v1.json`

## Result

Completed and admitted. The external period contains 2,270 events. CH-008
achieved mean IGPE +0.018561 (relative factor 1.018735) and total log-likelihood
gain +42.134. The 95% lower bounds were +0.012006 for 30-day blocks and
+0.011817 for 90-day blocks. All six three-year epochs were positive.

The frozen model therefore passed every pre-registered NZ-001 gate. This is
strong retrospective external-geography evidence, not prospective evidence.
