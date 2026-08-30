# FERN-002: Exposure-Normalized Renewal

## Question

Can one outcome-free regional time-scale calibration preserve CH-008's Region A
renewal signal while activating a comparable renewal clock in Regions B and C?

## Single Candidate

For each region, the ETAS direct-background mass per 0.5-degree cell is summed
from the train-only ETAS fit. One fixed scale is calculated so that the mean
cell accumulates exactly one expected renewal-exposure unit from the auxiliary
start to the validation boundary:

```text
scale_r = 1 / (mean_cell_background_mass_r * prevalidation_days)
```

The scale multiplies both expected renewal hazard and observed marked renewal
reset mass. Frailty, ETAS triggering, total background mass, geometry, and all
frozen CH-008 parameters remain unchanged. There is no outcome fit, parameter
search, or alternate candidate.

## Boundary

Only 1996-2003 development validation is scored. The script truncates every
catalog before 2004 before calculating ETAS event rates or replay state. The
pre-Tohoku period is forbidden. Because FERN-002 was conceived after FERN-001
outcomes were opened, even a passing result is development evidence rather than
independent validation.

## Admission

All three regions must have positive mean IGPE and positive 30-day bootstrap
lower bounds; 90-day lower bounds must be nonnegative. Failure of any gate ends
this normalization experiment.

## Run

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace -e PYTHONPATH=src \
  etas-challenge-inversion-arm64 \
  python scripts/evaluate_fern_ch008_normalized_validation.py
```

The result will be written to
`data/manifests/fern-ch008-exposure-normalized-validation-v1.json`.

## Result

FERN-002 passed every pre-registered admission gate:

| Region | Scale | Validation IGPE | Relative factor | 30-day lower | 90-day lower |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 0.2989 | +0.010242 | 1.010295 | +0.006743 | +0.006797 |
| B | 2.2241 | +0.001134 | 1.001135 | +0.000841 | +0.000792 |
| C | 14.3378 | +0.001342 | 1.001343 | +0.000832 | +0.000795 |

The normalization preserved a strong Region A gain and changed Regions B and
C from neutral/negative to small but bootstrap-supported positive gains. The
manifest records `forbidden_period_accessed: false`; no event at or after the
2004 boundary entered rate calculation, replay, scoring, or diagnostics.

The candidate is admitted as a successful multi-region development model. It
is not independently validated because its mechanism was designed after the
FERN-001 outcomes were known. A future claim requires a newly locked temporal
or geographic evaluation that has not informed this model family.
