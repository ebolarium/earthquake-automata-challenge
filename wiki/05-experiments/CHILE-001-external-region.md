# CHILE-001: Chile External-Region Test

## Question

Does the single frozen exposure-normalized CH-008 model beat a train-only academic ETAS fit in a non-Japan Chilean subduction corridor?

## Recorded protocol

- Rectangle: 76-66 W and 56-17 S, represented at 0.5 degrees.
- USGS ComCat earthquakes, M4.5+, depth below 100 km.
- ETAS fit: 2000-01-01 through 2014-12-31 UTC.
- External evaluation: 2015-01-01 through 2025-12-31 UTC.
- No CH-008 parameter refit; only train-data exposure normalization.
- One public 2025 M4 power count preceded the lock; no M4.5 historical event data or score was opened.

## Success rule

Mean IGPE must be positive, the 30-day block-bootstrap 95% lower bound must be positive, and the 90-day lower bound must be nonnegative.

## Commands

```bash
PYTHONPATH=src python scripts/fetch_chile_catalog.py
PYTHONPATH=src python scripts/prepare_chile_etas_workspace.py
docker run --rm -v "$PWD:/workspace" -w /workspace/artifacts/chile-etas/workspace/Experiments/ETAS etas-challenge-inversion-arm64 python invert_etas_exact_area.py CHILE
docker run --rm -v "$PWD:/workspace" -w /workspace -e PYTHONPATH=src etas-challenge-inversion-arm64 python scripts/evaluate_chile_ch008_external.py
```

## Result

Completed as exploratory external evidence. The catalog contained 3,622 fit events and 1,909
external-evaluation events. CH-008 achieved:

- mean IGPE: `+0.009718`;
- relative event-location intensity: `1.009766`;
- total log-likelihood gain: `+18.552482`;
- 30-day bootstrap 95% lower bound: `+0.006862`;
- 90-day bootstrap 95% lower bound: `+0.006321`.

All eleven annual IGPE values from 2015 through 2025 were positive and all three
recorded gates passed. However, the adapter freeze and result artifacts first
appeared in the same Git commit, so repository ordering cannot establish
confirmatory independence. This is exploratory retrospective
external-geography evidence; it is not pre-registered or prospective evidence.
