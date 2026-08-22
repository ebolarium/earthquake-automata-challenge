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

## Status

Pre-registered and unbuilt. The generator must be committed before execution.
