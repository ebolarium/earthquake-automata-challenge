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

Pre-registered and unrun.
