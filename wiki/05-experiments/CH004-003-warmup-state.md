# CH004-003: Unscored Warmup-State Anchors

## Question

Does the seven-year warmup produce a useful, nondegenerate renewal-age
distribution across plausible magnitude-reset scales before model fitting?

## Pre-Registered Anchors

Three anchors use `M_full` values 4.0, 5.0, and 6.0 with magnitude exponent
0.5. They are diagnostics, not candidates, and no anchor is selected here.
Expected reset marks are integrated under the frozen Gutenberg-Richter beta.
Observed marks use event-level ETAS root posteriors and the same four-neighbor
branch geometry as the expected analytical background.

The warmup snapshot is taken immediately before 2014-01-07 observations. A BPT
aperiodicity of 0.5 is used only to report how many active sections have a
positive overdue score.

## Results

| `M_full` | Expected GR reset mark | Median active age | 99th percentile | Maximum age | Positive overdue fraction |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4.0 | 0.33725 | 0.2103 | 1.0005 | 1.6007 | 11.22% |
| 5.0 | 0.11585 | 0.0857 | 0.4505 | 0.5624 | 0.32% |
| 6.0 | 0.03771 | 0.0291 | 0.1719 | 0.2075 | 0.00% |

The M6-scale anchor is structurally inactive after the available warmup, and
the M5-scale anchor is nearly inactive. This conclusion uses state coverage
only, not forecast outcomes. A future fit should concentrate reset magnitude
support near the M4-scale range and retain an explicit no-op control instead of
spending most candidates on unobservable long-cycle states.

The ignored artifact is `data/local/ch004-warmup-state-v1.npz`, SHA-256
`758b527a47ebbf1040fee1498066a833bc1f36b9d63c20d80d82b8f2b9ff9cb4`.

## Status

Completed without selecting an anchor or evaluating a forecast score.

## Next Step

CH004-004 will freeze the daily fit replay around the observable reset range.
It must preserve the exact ETAS control, report state activation separately
from skill, and apply the same annual-robust and low-ETAS vetoes as CH-003.
