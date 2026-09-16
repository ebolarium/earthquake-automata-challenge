# CH-008 Three-Region Prospective Evaluation: Preregistration

**Registration version:** 1.0, prepared 16 September 2026  
**Author:** Saban Baris Boga, Independent Researcher, Adana, Turkiye  
**ORCID:** https://orcid.org/0009-0000-9076-946X  
**Contact:** hello@bboga.com  
**Repository:** https://github.com/ebolarium/earthquake-automata-challenge  
**Live study:** https://etas.bboga.com/  
**Public OSF registration:** https://osf.io/u6yte/  
**DOI:** https://doi.org/10.17605/OSF.IO/U6YTE  

## 1. Study title

CH-008 versus ETAS: a frozen 365-day prospective evaluation of causal
renewal-frailty background reallocation across California, New Zealand, and
Chile.

## 2. Research question

Under a fixed 365-day next-day forecasting protocol, does frozen CH-008 assign
higher probability density than frozen ETAS to prospectively observed target
earthquake locations, pooled across California, New Zealand, and Chile, while
preserving ETAS's total expected event rate?

## 3. Hypothesis and decision rule

The directional hypothesis is that the pooled final paired information gain
per earthquake (IGPE) of CH-008 relative to ETAS is positive.

The primary claim is supported only if all of the following prespecified gates
are satisfied:

1. At least 500 pooled target earthquakes are available in final scores.
2. Pooled mean final IGPE is greater than zero.
3. The lower bound of the 95% stationary daily block-bootstrap interval is
   greater than zero with a mean block length of 30 days.
4. The corresponding lower bound is greater than zero with a mean block length
   of 90 days.
5. Both bootstrap analyses use 10,000 replicates.
6. All three regions remain operationally eligible under the frozen downtime
   policy.
7. No region is excluded post hoc and the calendar is not extended.

If the study is operationally eligible and reaches 500 final target events but
one or more statistical gates fail, the primary hypothesis is not supported.
If the event gate is not reached, a region is operationally invalidated, or
final scoring cannot be completed under the frozen contract, the pooled
primary result is reported as inconclusive rather than failed or supported.
A positive live point estimate alone is not a successful result.

## 4. Design and timing

This is a prospective, paired, observational forecast comparison. ETAS and
CH-008 issue forecasts for the same next-UTC-day target windows and are scored
on the same earthquakes.

- Activation issue date: 23 September 2026 UTC.
- First scored target window: 24 September 2026 00:00:00 UTC through
  25 September 2026 00:00:00 UTC.
- Fixed duration: 365 target days.
- Last target window ends: 24 September 2027 00:00:00 UTC.
- Final catalog revision delay: seven days; completion of the final endpoint
  is therefore expected no earlier than 1 October 2027 UTC.
- Forecast frequency: daily.
- Publication deadline: 00:15 UTC before the target day.
- History boundary: catalog information strictly before issue time.
- Retrospective forecast backfill: prohibited.
- Early stopping for performance: prohibited.

The transition from the preceding operational dry run transfers the latest
causal model state through the ordinary daily advance path. It does not refit
the model or select parameters.

## 5. Forecast regions and target catalogs

### California RELM

- Catalog: USGS ANSS ComCat FDSN Event Web Service.
- Threshold: magnitude 2.5 or greater.
- Region: frozen 7,682-cell RELM mask at 0.1-degree spacing.
- CH-008 geometry: UCERF3 fault network.
- Baseline: frozen California ETAS fit.

### New Zealand CSEP

- Catalog: GeoNet FDSN Event Web Service.
- Threshold: magnitude 4.0 or greater and depth in [0, 40) km.
- Region: frozen 6,343-cell published CSEP mask at 0.1-degree scoring spacing,
  with a 0.5-degree latent CH-008 grid.
- CH-008 geometry: latent-cell neighborhood.
- Frozen regional exposure normalization: 0.4772598372902653.
- Baseline: frozen New Zealand ETAS fit.

### Chile subduction corridor

- Catalog: USGS ANSS ComCat FDSN Event Web Service.
- Threshold: magnitude 4.5 or greater and depth in [0, 100) km.
- Region: longitude [-76, -66], latitude [-56, -17], represented by 1,560
  0.5-degree cells.
- CH-008 geometry: latent-cell neighborhood.
- Frozen regional exposure normalization: 4.261045999817415.
- Baseline: frozen Chile ETAS fit.

Region definitions, magnitude and depth thresholds, catalog sources, model
fits, and normalization constants will not be changed during this protocol.

## 6. Models

ETAS is the frozen baseline. CH-008 retains ETAS's triggered component,
magnitude treatment, and domain-integrated expected event count. It changes
only the spatial allocation of a bounded fraction of direct-background mass.
The reallocation uses two causal pre-event state variables:

1. a magnitude-marked Brownian renewal score representing elapsed loading
   since local reset; and
2. a discounted Gamma-Poisson frailty score representing persistent local
   excess or deficit of posterior background-event mass relative to ETAS
   expectation.

Because the ETAS triggering calculation and total expected daily count are
preserved, this experiment isolates whether the CH-008 background allocation
contains additional conditional spatial information. It is not a test of exact
earthquake time, location, or magnitude prediction.

No parameter, feature, model weight, regional adapter, or ETAS fit will be
selected or refitted using formal target-period outcomes.

## 7. Primary outcome and analysis

For target earthquake `i`, let `lambda_C(i)` and `lambda_E(i)` be the CH-008
and ETAS forecast densities at its observed time and location. The paired event
score is

```text
IG_i = ln(lambda_C(i) / lambda_E(i)).
```

The pooled primary endpoint is

```text
IGPE = (1 / N) * sum_i IG_i,
```

where `N` is the number of final-scored target earthquakes from all eligible,
non-missed region-days in the three fixed regions. Units are natural-log units
per earthquake. `exp(IGPE)` is reported as the relative geometric-mean density
factor.

CH-008 preserves each ETAS forecast's domain-integrated expected rate, so the
paired point-process compensator difference is zero by construction. The event
log-density ratio is consequently the full paired log-likelihood gain for this
comparison. Implementation diagnostics will still report the compensator
contract.

Daily paired gains are resampled using a stationary daily block bootstrap,
separately at mean block lengths of 30 and 90 days, with 10,000 replicates and
95% intervals. The analysis uses catalog-settled `final` scores, not first-seen
`provisional` scores.

## 8. Secondary and descriptive analyses

The following do not replace or modify the pooled primary endpoint:

- final IGPE, event count, total gain, relative factor, and bootstrap interval
  by region;
- provisional-versus-final catalog revision summaries;
- calendar-time trajectories and annual summaries;
- operational coverage, missed region-days, deferred scores, incidents, and
  forecast freshness; and
- magnitude or ETAS-density strata clearly labeled exploratory.

Regional findings are secondary evidence and will be reported without
post-hoc exclusion. No claim of broad geographic generalization will be based
only on the pooled mean.

## 9. Missing data, outages, and invalidation

The frozen downtime policy distinguishes failures before and after forecast
publication.

- Publication has at most three attempts with 60- and 300-second backoffs. No
  attempt may cross the 00:15 UTC deadline.
- A forecast not persisted before the deadline is `publication_missed`, is not
  backfilled, and is excluded from both the primary numerator and `N`. It is
  never imputed as zero IGPE.
- If an on-time forecast exists but catalog or scoring service access fails,
  scoring is deferred and completed against the original forecast and
  protocol-defined catalog window. Such a day is not a publication miss.
- No missing-at-random assumption is made. Causes, affected dates, event
  counts, attempts, resolution, and UTC timestamps are logged and reported.
- A region is invalidated for primary promotion after 19 publication-missed
  days out of 365, or after seven consecutive publication-missed days.
- Regional invalidation makes the pooled three-region claim inconclusive. The
  region continues running and is reported as secondary evidence.
- The 365-day calendar is not extended and missed days are not replaced.

## 10. Existing data and prior knowledge

CH-008 was developed and selected before this registration. The author has
already observed retrospective and operational results; this registration
does not represent a blind first test of the general research program.

Known pre-registration evidence includes:

- California 2019--2022 development validation: 5,204 events, IGPE +0.005213.
- California 2023--18 August 2026 supportive retrospective evaluation: 3,995
  events, IGPE +0.007865.
- New Zealand 2008--2025 exploratory transfer: 2,270 events, IGPE +0.018561.
- Chile 2015--2025 exploratory transfer: 1,909 events, IGPE +0.009718.

The New Zealand and Chile results are labeled exploratory because each adapter
freeze and its evaluation artifact shared a commit. They are not treated as
preregistered confirmation. The California evidence is also not promoted to
confirmatory status because it belongs to the wider iterative model-development
program.

A 14-day operational dry run covered target days 1--14 September 2026. Twelve
days were scored and two early software-failure days were marked missed without
backfill or zero imputation. As recorded on 16 September, 38 provisional events
had pooled IGPE +0.021934 and 12 then-final events had pooled IGPE +0.032431.
These values were visible before registration, are excluded from the formal
endpoint, and will not be used to refit or select any formal-test component.

The formal target period begins after this registration. Only its 365 fixed
target days count toward the primary claim.

## 11. Deviations and software changes

The frozen forecast and scoring definitions are authoritative. Any change to
model mathematics, parameters, feature definitions, ETAS fits, catalog
thresholds, regional geometry, normalization, primary metric, success gates,
or target calendar requires a new protocol identity and cannot be silently
included in this registration's primary claim.

Operational fixes are permitted only when they do not alter the mathematical
forecast, retroactively create a missed forecast, change a stored on-time
forecast, or use target outcomes for model decisions. Every production change
and incident will retain its Git commit and timestamped operational record. If
a defect changes formal forecast values or prevents the frozen analysis from
remaining comparable, the primary result will be labeled inconclusive or a
new preregistered protocol will be started. Deviations will be disclosed, not
silently repaired.

## 12. Frozen materials and provenance

The prospective protocol first entered the repository in commit
`e7196c99b5e508ea7504ffac34ee77e61f041f38` and the automatic formal-launch
contract was committed as
`6206583376cf6385a0504d85065f25bffa985544`. The public repository snapshot
immediately before preparation of this registration is
`b1717ca337a7b6f6467c204bea4e907bb2b512ee`.

Authoritative frozen files and SHA-256 identities:

- `configs/prospective/ch008-three-region-prospective-v1.json`  
  `7e2f83025498c16387791e9e7bbfe14cfd26bf1f107e51e763b1a2aa3f6b0acd`
- `configs/challenge/ch008-downtime-policy.json`  
  `94c5a450b37b65a2e918ac19ea787cc888caf37298b88678c185045feb189254`
- `models/ch008-boundary-sensitivity-v1.json`  
  `72e030a4d61c512bb096c1469a409c1cf3d9206fc0d9580f2352e0d604e3fa27`
- `src/etas_challenge/frailty_renewal_fit.py`  
  `004bb95b64789bd909e408e3d220bae4982284d85e6925202566e2776c4015cf`
- `src/etas_challenge/fern_ch008_normalized.py`  
  `a85e8da1b501e5c43d3374714d9014683bb37b40c33bee179ae2dd7e2a7b7f16`
- `src/etas_challenge/etas_native.py`  
  `a833974874e05dcd4f24d914b405da37ee83f99e744cf5c503ec73d886812161`

The protocol JSON additionally records each regional mask, ETAS parameter
file, adapter, and checksum. Forecast artifacts are stored with SHA-256
metadata; PostgreSQL stores catalog identities, model states, forecast runs,
scores, and incidents. Public live state and a machine-readable evaluation are
available at https://etas.bboga.com/api/evaluation.json.

## 13. Interpretation boundary

Passing every gate would constitute prospective evidence that this frozen
CH-008 configuration improves conditional spatial likelihood over these frozen
ETAS baselines under this protocol. It would not establish deterministic
earthquake prediction, universal superiority over ETAS, operational hazard
utility, causal tectonic truth, or replication by an independent group.
