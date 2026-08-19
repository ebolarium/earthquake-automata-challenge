# Evaluation Protocol

Reference reproduction measures implementation alignment, not forecast
superiority. Model comparisons begin only after the baseline is frozen.

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

