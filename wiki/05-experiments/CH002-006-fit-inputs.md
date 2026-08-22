# CH002-006: Fit-Only ETAS Background Posteriors

## Question

Can each admitted CH-002 fit event be joined to its issue-day frozen ETAS
decomposition without opening validation?

## Period and Inputs

- Fit issues: 2014-01-07 through 2018-12-31, 1,820 UTC days.
- Frozen local California catalog, rounded to 0.1 magnitude and `M >= 2.5`.
- Frozen CH001-002 ETAS daily RELM grids.
- Exact direct background `mu * spherical_cell_area` from the locked ETAS
  parameters.

The script rejects any end date other than 2019-01-01 and requires
`validation_opened: false`. All 60 monthly ETAS shards used by fit events are
verified against the committed manifest before their rates are read.

## Event Contract

For an event in cell `i` on issue day `t`, the assimilation weight is

```text
P(direct background | event cell, frozen ETAS)
    = lambda_background(i) / lambda_ETAS(i,t)
```

This is not a declaration of the event's true genealogy. It is the frozen ETAS
posterior weight used to prevent ordinary high-intensity aftershocks from
dominating the slow readiness update.

Each event also stores its eight nearest UCERF3 trace sections and exact
point-to-trace distances. These remain geometry-only inputs; branch
compatibility, assignment weights, and off-fault probability are applied later
from the frozen state contract.

## Results

| Quantity | Value |
| --- | ---: |
| Issue days | 1,820 |
| Selected events before RELM filtering | 3,978 |
| Outside RELM grid | 359 |
| Fit events | 3,619 |
| Event-bearing days | 1,352 |
| `M >= 3.5` | 466 |
| `M >= 4.0` | 126 |
| Median background posterior | 0.01143 |
| Mean background posterior | 0.14445 |
| Posterior background event mass | 522.76 |

The low median and larger mean show the intended separation: most events are
strongly explained by ETAS triggering, while a smaller group receives much
higher slow-field authority.

## Boundary

This milestone creates replay inputs only. No CH-002 parameter was optimized,
no information-gain score was computed, and neither development validation nor
the locked retrospective period was read.

## Next Step

CH002-007 will run fit-only daily replay and optimize the four pre-registered
state gains plus the background-tilt sensitivity. Model and optimizer artifacts
must be locked before any 2019-2022 validation command is admitted.
