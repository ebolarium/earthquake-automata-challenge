# CH-008 OSF Preregistration Form Answers

This file maps the frozen protocol to the standard **OSF Preregistration**
fields. The complete registration narrative is
[`ch008-osf-preregistration-v1.md`](ch008-osf-preregistration-v1.md).

**Public registration:** https://osf.io/u6yte/  
**DOI:** https://doi.org/10.17605/OSF.IO/U6YTE

## Metadata

### Title

CH-008 versus ETAS: A Frozen 365-Day Prospective Earthquake Forecast Evaluation

### Description

This preregistration defines a 365-day prospective comparison of frozen CH-008
and frozen ETAS next-day earthquake-rate forecasts in California, New Zealand,
and Chile. CH-008 preserves ETAS triggering and total expected event rate while
causally reallocating a bounded fraction of direct-background probability using
magnitude-marked renewal and discounted frailty states. The primary endpoint is
pooled final paired information gain per earthquake. The test begins with the
target day of 24 September 2026 and uses fixed event-count, temporal-block
bootstrap, operational-eligibility, no-refit, and no-backfill rules.

### License

CC0 1.0 Universal.

### Subjects

Physical Sciences and Mathematics; Earth Sciences; Geology; Geophysics and
Seismology, selecting the closest labels exposed by the OSF subject tree.

### Tags

earthquake forecasting, ETAS, seismology, prospective evaluation, information
gain, preregistration, renewal process, frailty

## Overview

### Research Questions Or Hypotheses

Primary research question: Under a fixed 365-day next-day forecasting protocol,
does frozen CH-008 assign higher probability density than frozen ETAS to
prospectively observed target earthquake locations, pooled across California,
New Zealand, and Chile, while preserving ETAS's total expected event rate?

Directional hypothesis: pooled final paired information gain per earthquake
(IGPE) for CH-008 relative to ETAS is positive. The claim is supported only if
at least 500 final-scored target earthquakes are observed, mean pooled final
IGPE is greater than zero, and the 95% lower bounds from both 30-day and 90-day
stationary daily block bootstraps with 10,000 replicates are greater than zero,
while all three regions remain operationally eligible. A positive point
estimate alone does not support the claim.

### Foreknowledge Of Data Or Evidence

Select: **Data does not yet exist.**

The data used in the registered primary endpoint are earthquakes occurring in
the future formal target period, beginning 24 September 2026. None of those
target outcomes exists at registration time.

### Explanation Of Foreknowledge And Managing Unintended Influences

The author has observed earlier retrospective and operational evidence that
informed development of CH-008. Known results include California 2019--2022
(N=5,204, IGPE +0.005213), California 2023--18 August 2026 (N=3,995, IGPE
+0.007865), exploratory New Zealand 2008--2025 (N=2,270, IGPE +0.018561), and
exploratory Chile 2015--2025 (N=1,909, IGPE +0.009718). A non-claim operational
dry run covered 1--14 September 2026; on 16 September it contained 38
provisional events with pooled IGPE +0.021934 and 12 then-final events with
pooled IGPE +0.032431. These earlier outcomes are explicitly excluded from the
registered endpoint. Before the formal period, model parameters, ETAS fits,
regional adapters, thresholds, geometries, primary metric, success gates,
downtime policy, duration, and no-backfill rule were frozen and content-hashed.
Dry-run results cannot be used for refitting or selection. Any scientific model
change requires a new protocol identity.

## Research Design

### Study Type

Select: **Non-randomized study** and **Descriptive study**.

### Intention For Causal Interpretation

Select: **No causal relationship inferred.**

### Blinding Of Experimental Treatments

Select: **No blinding is involved.**

### Additional Blinding During Research Or Analysis

There are no treatments or human analysts assigning outcomes. Protection
against outcome-dependent decisions is procedural: both models issue forecasts
for identical future target windows; target outcomes are unavailable when a
forecast is persisted; forecasts after the 00:15 UTC deadline are rejected;
backfill is prohibited; final scores use a fixed seven-day catalog-settlement
delay; and the analysis and success gates are frozen before the target period.
Live results may be viewed during the study, but they cannot change the model,
regions, endpoint, duration, or decision rule.

### Study Design

This is a paired prospective forecast comparison using naturally occurring
earthquakes. Every eligible region-day has two spatial rate forecasts, frozen
ETAS and frozen CH-008, generated from the same causal event history for the
same next-UTC-day window. CH-008 preserves the ETAS triggered component and
domain-integrated expected count and changes only the spatial allocation of a
bounded fraction of direct-background mass. Target events are scored under
both forecasts. Final event-level log-density ratios are pooled across the
three fixed regions and divided by the pooled event count. The calendar is 365
fixed target days, beginning 24 September 2026. The detailed protocol, model
identities, region definitions, and SHA-256 values are recorded in the attached
registration narrative and public repository.

### Randomization

None. Earthquakes are naturally occurring events and both forecasts are scored
on every included event.

## Sampling

### Data Collection Procedures

Each day the system collects causally available events from USGS ANSS ComCat
for California and Chile and from GeoNet FDSN for New Zealand. Forecast history
is restricted to data strictly before issue time. Forecasts must be persisted
by 00:15 UTC before the target window. Target events are selected using frozen
region masks and thresholds: California RELM M>=2.5; New Zealand CSEP M>=4.0
and depth [0,40) km; Chile longitude [-76,-66], latitude [-56,-17], M>=4.5 and
depth [0,100) km. First-observed scores are provisional; the same forecast is
rescored after seven days against a settled catalog and labeled final. Raw
responses, identities, checksums, states, forecasts, scores, and incidents are
retained under the protocol's PostgreSQL and object-storage contracts.

### Sample Size

The fixed sample comprises all eligible target earthquakes during 365 calendar
days in the three prespecified regions. Earthquake occurrence cannot be fixed
in advance. The primary event-count gate is at least 500 pooled final-scored
target earthquakes. Each region has 365 scheduled region-days; missed
publications are handled under the frozen downtime policy.

### Sample Size Rationale

The 365-day duration is a fixed prospective horizon chosen before formal
activation. The minimum of 500 pooled events prevents a superiority claim from
being made on a very small event sample while retaining a fixed calendar that
cannot be extended after seeing performance. This is a prespecified evidence
gate, not a conventional power calculation. If fewer than 500 events occur,
the result is inconclusive and the study is not extended.

### Starting And Stopping Rules

The operational dry run ends before the registered endpoint and contributes no
events. The formal protocol activates on the 23 September 2026 UTC issue cycle;
the first target window is 24 September 2026 00:00 UTC. Collection stops after
365 fixed target days, with the last target window ending 24 September 2027
00:00 UTC. Final scoring completes after the seven-day catalog-settlement delay.
There is no performance-based early stopping and no calendar extension.

## Variables

### Manipulated Variables

None. This is a paired observational forecast evaluation without randomized
treatments.

### Measured Variables

For each target event: target date, region, catalog event identity, origin time,
latitude, longitude, magnitude, depth, ETAS forecast density at the observed
event, CH-008 forecast density at the observed event, and paired natural-log
density ratio. For each region-day: forecast publication status and time,
catalog snapshot and cutoff, event count, summed paired gain, provisional/final
revision, state and artifact checksums, retry attempts, incident class, deferred
scoring status, and publication-miss status. Operational summaries include
missed region-days, consecutive missed days, invalidation status, and open
incidents.

### Indices

For event i, IG_i = ln(lambda_CH008(i) / lambda_ETAS(i)). Pooled IGPE =
(1/N) * sum_i IG_i across final-scored events in all three fixed regions.
Relative factor = exp(IGPE). CH-008 preserves the domain-integrated ETAS daily
rate, so the paired point-process compensator difference is zero by
construction. Daily paired gains form the time series used in 10,000-replicate
stationary daily block bootstraps at mean block lengths of 30 and 90 days.

## Analysis Plan

### Statistical Models

The primary analysis is a paired forecast log-likelihood comparison. For every
final-scored target event, calculate the natural logarithm of CH-008 forecast
density divided by ETAS forecast density at the same observed time and
location. Sum all paired event gains from the three fixed regions and divide by
the pooled final event count. Temporal uncertainty is estimated by resampling
the daily paired-gain sequence with a stationary daily block bootstrap using
10,000 replicates, separately for mean block lengths of 30 and 90 days. Report
the pooled mean, total gain, event count, exp(IGPE), and two 95% intervals.
Regional versions are secondary and cannot replace the pooled endpoint.

### Transformations

Forecast-density ratios are transformed with the natural logarithm at event
level. The arithmetic mean of these log ratios is IGPE and its exponential is
reported as a descriptive relative geometric-mean density factor. No outcome-
dependent recoding, winsorization, outlier deletion, or region weighting will
be performed. Only protocol-defined catalog filtering and final-score revision
are used.

### Inference Criteria

Support for the directional primary claim requires all of the following:
N>=500 pooled final target earthquakes; mean pooled final IGPE>0; the 95% lower
bound from the 30-day stationary daily block bootstrap is >0; the 95% lower
bound from the 90-day bootstrap is >0; and all three regions remain
operationally eligible. Each bootstrap uses 10,000 replicates. No multiplicity-
adjusted confirmatory claims are made from regional or subgroup analyses. If
the study is eligible and reaches 500 events but any statistical gate fails,
the primary hypothesis is not supported. If N<500 or any region is invalidated,
the pooled result is inconclusive.

### Data Inclusion And Exclusion

Include every final-catalog earthquake within its frozen regional geometry,
magnitude threshold, depth interval, and one of the 365 fixed target windows
for which both ETAS and CH-008 were validly persisted before the deadline.
Exclude dry-run and retrospective events, events outside the fixed filters,
provisional revisions from the primary endpoint, and region-days with no valid
on-time paired forecast. No earthquake is excluded as an outlier and no region
may be removed because of its result. Duplicate catalog identities are resolved
by the frozen catalog-snapshot identity rules.

### Missing Data

A forecast not persisted before 00:15 UTC is a publication miss, is never
backfilled, and its region-day is excluded from both numerator and N rather
than scored as zero. No missing-at-random assumption is made. If a valid on-time
forecast exists but catalog or scoring access fails, scoring is deferred and
later completed against the original forecast and protocol-defined catalog
window; this is not a publication miss. A region is invalidated after 19 missed
publication days out of 365 or seven consecutive missed days, making the pooled
claim inconclusive. The calendar is not extended.

### Other Planned Analysis

Secondary reporting includes final IGPE, event count, total gain, relative
factor, and bootstrap intervals by region; provisional-to-final catalog
revisions; calendar-time and annual stability summaries; and operational
coverage and incidents. Magnitude strata, ETAS-density strata, maps, and other
diagnostics are exploratory. They cannot modify or substitute for the pooled
primary endpoint and will be labeled accordingly.

## Other

### Context And Additional Information

CH-008 was developed before this preregistration, and positive retrospective
and operational results are already known and fully disclosed above. This
registration therefore covers only the future 365-day formal target period and
does not relabel earlier evidence as confirmatory. Passing every gate would
support the narrow claim that this frozen CH-008 configuration improves
conditional spatial likelihood over these frozen ETAS baselines under this
protocol. It would not establish deterministic earthquake prediction,
universal ETAS superiority, operational hazard utility, causal tectonic truth,
or independent replication. Frozen source, configurations, hashes, limitations,
and live machine-readable status are available at
https://github.com/ebolarium/earthquake-automata-challenge and
https://etas.bboga.com/api/evaluation.json.
