# CH003-002: Branch-Aware Section Compensator

## Question

Can observed ETAS posterior root mass and expected analytical background mass be
projected to fault sections with exactly the same leakage-free geometry?

## Pre-Registered Construction

For each of eight UCERF3 loading branches, every event contributes its frozen
ETAS direct-background posterior through the branch-aware event-to-fault
probabilities. The analytical direct-background grid is projected through the
same four-neighbor count, bandwidth, cutoff, prior odds, active-section mask,
and off-fault term. Although the event input retains eight neighbors for older
experiments, CH-003 truncates it to four to match the frozen grid artifact.

The artifact stores daily observed section mass, static expected daily section
mass, off-fault mass, active masks, branch loading, and the frozen graph. It
contains no CH-003 score or fitted parameter.

## Results

| Quantity | FM3.1 branches | FM3.2 branches |
| --- | ---: | ---: |
| Issue days | 1,820 | 1,820 |
| Total observed posterior root mass | 522.756190 | 522.756190 |
| Total expected root mass | 639.271395 | 639.271395 |
| Fault-assigned observed mass | 291.143652 | 292.715494 |
| Fault-assigned expected mass | 253.836704 | 253.827239 |
| Maximum observed conservation error | 6.82e-13 | 6.82e-13 |
| Maximum expected conservation error | 0 | 0 |

The total observed posterior root mass is below the ETAS analytical expectation,
while the fault-assigned portion is higher. This is an input diagnostic, not a
forecast-skill result: it may reflect spatial residual structure, catalog
sampling, or remaining point-versus-cell geometry effects. CH-003 must earn any
claim through causal next-day scores.

The ignored artifact is
`data/local/ch003-section-compensator-v1.npz`, SHA-256
`13dee5359f05c6a70fc0d7cd05d3d886160b21934df9b21ecc0f62655ea00900`.
Its committed manifest binds the generator and all source artifacts.

## Status

Completed without evaluating a CH-003 candidate or information-gain score.

## Next Step

CH003-003 will pre-register a computationally small candidate replay over this
compensator. Candidate selection will penalize unstable annual gains and retain
the zero-mixture ETAS control.
