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

Completed. No 2019 onward CH-008 outcome was read.

## Result

The matched expanded search selected candidate 43 by the unchanged robust
annual rule:

| Quantity | CH-008 | CH-007 fit ablation |
| --- | ---: | ---: |
| Mean IGPE | +0.005311 | +0.003622 |
| Robust annual IGPE | +0.002347 | +0.001399 |
| Low-ETAS IGPE | +0.017572 | +0.012113 |
| Parent IGPE factor | 20.85x | 14.22x |

CH-008 improves mean fit IGPE by 46.6% and robust annual IGPE by 67.7% over
the locked CH-007 fit ablation. Every annual score remains positive:

- 2014: `+0.003192`.
- 2015: `+0.004388`.
- 2016: `+0.001935`.
- 2017: `+0.011742`.
- 2018: `+0.011270`.

The selected `renewal_weight` is `2.9262` under the expanded `4.0` cap, and its
background mixture is `0.2759` under the expanded `0.5` cap. The robust winner
is therefore interior to both new ranges rather than pinned to either new upper
boundary. In contrast, the highest-mean candidate 23 lies near both expanded
caps but loses under the unchanged annual-risk selection rule.

A fixed fit-only mechanism diagnostic gives `+0.004348` for renewal-only,
`+0.001004` for frailty-only, and `+0.005311` for the full candidate. Unlike the
earlier CH-006 winner, this selected point contains fit contribution from both
components. This diagnostic is exploratory and does not reopen validation.

## Conclusion

The original bounds were consequential: widening them exposed a materially
stronger and more annually robust fit region. The selected robust point no
longer presses against the expanded caps, so another immediate bound increase
is not indicated by this check. CH-008 remains fit-only and cannot supersede
validated CH-007 without a separately locked future-data test.
