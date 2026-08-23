# CH008-001: Boundary Sensitivity

## Question

Was the stronger renewal candidate truncated by the CH-006 search bounds?

## Fixed Comparison

CH-008 repeats the CH-006 fit on exactly the same 2014-2018 events and the same
64 scrambled Sobol unit points. Seed, parameter ordering, all other parameter
bounds, warmup, metrics, admission rules, and robust annual selection are
unchanged.

Only two upper bounds change:

- `renewal_weight`: `2.5` to `4.0`.
- `background_mixture_fraction`: `0.3` to `0.5`.

The exact CH-004 control remains candidate zero. Outputs use separate CH-008
paths and cannot overwrite CH-006 or CH-007 artifacts.

## Leakage Boundary

Only the unscored 2007-2014 warmup and 2014-2018 fit-development outcomes may
be read. This is a post-CH007 sensitivity analysis, not a new validation result,
and it cannot retroactively change CH-007. No 2019 onward CH-008 outcome may be
computed in this stage.

## Status

Pre-registered and unrun.
