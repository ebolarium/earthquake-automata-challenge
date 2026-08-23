# CH006-001: Discounted Fault Frailty

## Question

Can a sequential estimate of fault susceptibility produce a materially larger
and more stable gain than CH-004 while retaining its ETAS-normalized renewal
clock?

## Hypothesis

CH-004 treats every mapped fault section as equally productive conditional on
its ETAS background exposure and renewal age. CH-006 adds a discounted
Gamma-Poisson state. For each UCERF3 branch and section it compares accumulated
posterior direct-root mass with the direct-root mass expected by ETAS.

The posterior mean is a latent rate multiplier, not a claim of measured stress.
Its positive log excess is interpreted as observational evidence of persistent
fault susceptibility. Old evidence decays with a fitted half-life, allowing the
state to adapt rather than becoming a permanent historical label.

## Forecast Contract

- Forecasts are issued before same-day observations update either state.
- ETAS triggering, daily expected count, and magnitude distribution are unchanged.
- Only a bounded fraction of direct background mass is redistributed.
- Renewal age and frailty are updated exclusively from earlier events and ETAS
  posterior direct-root probabilities.
- Zero frailty weight with the locked amplitude reproduces CH-004 exactly.

## Pre-Registered Fit Gate

The unscored warmup remains 2007-01-01 through 2014-01-06. Sixty-four scrambled
Sobol candidates and the exact CH-004 control are evaluated on 2014-2018 only.
A non-control candidate opens 2019-2022 validation only if it:

- reaches at least `1.25x` CH-004 fit IGPE;
- has robust annual IGPE at least as large as CH-004;
- has low-ETAS IGPE at least as large as CH-004;
- is positive in every fit year.

Selection among passing candidates uses robust annual IGPE. No 2019 onward
CH-006 forecast or score may be read before the model is locked.

## Status

Fit completed and development validation admitted. No 2019 onward CH-006
forecast or score has been read.

## Fit Result

Candidate 23 won the pre-registered robust annual rule over 3,619 events:

| Quantity | CH-006 | CH-004 parent |
| --- | ---: | ---: |
| Mean IGPE | +0.003620 | +0.000255 |
| Parent factor | 14.21x | 1.00x |
| Robust annual IGPE | +0.001397 | +0.000113 |
| Low-ETAS IGPE | +0.012071 | +0.000868 |

Every annual score from 2014 through 2018 was positive. The selected state has
a 475-day evidence half-life, combines local and neighboring fault evidence,
and may redistribute at most 28.35% of direct background mass.

The result is materially larger on fit development, but remains a fit result.
Before validation, fixed full, renewal-only, and frailty-only ablations must be
registered so amplitude and genuinely new state information can be separated.

## Mechanism Ablation

The fit-only fixed ablation rejected the proposed mechanism:

- Full CH-006: `+0.003620` IGPE.
- Frailty disabled: `+0.003622` IGPE.
- Renewal disabled: `+0.0000004` IGPE.

The large fit gain comes from stronger renewal amplitude and a larger bounded
background fraction, not the new frailty state. CH-006 is therefore not a
frailty discovery. The renewal-only forecast is frozen separately as CH-007
before any 2019 onward CH-007 outcome is read.
