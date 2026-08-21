# Evaluation Protocol

Reference reproduction measures implementation alignment, not forecast
superiority. Model comparisons begin only after the baseline is frozen. The
immutable split, metric, uncertainty, and promotion rules are recorded in
`configs/challenge/challenge-v1.json`.

The evaluation layer will support:

- event-based temporal, spatial, and normalized log-likelihood;
- information gain per earthquake against ETAS and a Poisson background;
- CSEP number, magnitude, spatial, and likelihood consistency tests;
- paired forecast comparison tests;
- Molchan miss-rate versus alarm-space analysis for top-N products;
- block-bootstrap uncertainty that respects sequence clustering;
- calibration and expected event-count diagnostics.

All candidate and baseline models receive the same catalog snapshot, region,
completeness threshold, forecast clock, horizon, and evaluation catalog.

## Daily Replay Clock

- Issue time is `00:00:00Z` each day.
- History is strictly earlier than issue time.
- The target window is `[issue_time, issue_time + 1 day)`.
- An event exactly at issue time is a target, not history.
- An event exactly at window end belongs to the next day.
- Events sharing an origin timestamp do not trigger one another.
- Magnitudes are rounded to `0.1` before applying `Mc = 2.5`.

Two scores are retained. The frozen lane uses only pre-issue events throughout
the day and is an issue-time conditional-intensity approximation. It does not
simulate descendant generations and is not the full ETAS predictive
distribution. The sequential lane is the standard ETAS point-process
likelihood: an observed event can affect only strictly later times.

Replay parameters and the local Poisson training rate are frozen at the first
issue date. No event in the evaluation window is used to refit either model.

## Retrospective Boundary

The clean snapshot prevents origin-time leakage, but most legacy events do not
have versioned payload history. Their final revised locations and magnitudes
may differ from values available operationally on the historical issue date.
Daily replay results are therefore retrospective as-of-snapshot evidence, not
prospective forecasts that were issued in real time.

## Catalog Consistency Gate

EVAL-001 reproduces the active day used in the EarthquakeNPP pyCSEP walkthrough:
test day 7, beginning `2007-01-08T00:00:00Z`. It uses 10,000 deterministic
catalog continuations, pyCSEP 0.6.3's 7,682-cell California RELM region, and
0.1-wide magnitude bins from 2.5.

Every simulation ID is represented explicitly, including empty catalogs. The
number, spatial, pseudolikelihood, and magnitude tests are two-sided at the 5%
level. These tests assess whether an observation is consistent with a model's
forecast distribution; they do not by themselves rank ETAS against Poisson.

One documented day is sufficient for the software integration gate, not for a
calibration or skill claim. Long-run claims require the daily replay, paired
information gain, and cluster-aware uncertainty already required above.
