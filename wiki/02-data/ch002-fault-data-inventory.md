# CH-002 Fault Data Inventory

## Purpose

This inventory decides which fault-related inputs may enter CH-002 before any
data are downloaded or any validation score is computed. Scientific relevance
alone is insufficient: a source must also have defensible version and
availability dates.

## Decision Summary

| Input | Candidate | Retrospective decision |
| --- | --- | --- |
| Fault geometry and section attributes | [UCERF3 time-independent model](https://pubs.usgs.gov/of/2013/1165/) fault-section data | Admit from 2014-01-07 issue dates onward |
| Slip/loading alternatives | UCERF3 deformation-model branches and geologic constraints | Admit as an ensemble, not one true loading map |
| Most-recent-event dates | [UCERF3 time-dependent model](https://wgcep.org/UCERF3-Time-Dependent-Rate-Calculator.html) | Exclude from first candidate; later ablation may begin in 2016 |
| Event mechanisms and moment tensors | [USGS ComCat products](https://earthquake.usgs.gov/data/comcat/) | Exclude until product creation/update history is snapshotted |
| Modern fault and slip database | [NSHM23 western U.S. geology inputs](https://www.usgs.gov/data/earthquake-geology-inputs-us-national-seismic-hazard-model-nshm-2023-western-us-ver-30) | Prospective-only; not available during fit or validation |
| Legacy Automata stress ledger | Local production/research artifacts | Exclude values; retain only the loading-release-transfer hypothesis |

## UCERF3 Geometry and Loading

USGS Open-File Report 2013-1165 was first posted on 2013-11-05 and its index
records a 2014-01-06 modification. It supplies fault-section data and documents
alternative fault and deformation models. To avoid arguing over same-day
availability, CH-002 uses a conservative first eligible issue date of
2014-01-07.

Consequences:

- The unchanged Challenge V1 fit split remains 2007-2018, but CH-002 training
  uses only 2014-01-07 through 2018-12-31.
- Validation remains 2019-2022 and the locked retrospective period remains
  unopened.
- Fault Models 3.1 and 3.2 and admitted deformation alternatives remain an
  epistemic ensemble. Selecting the best branch on validation is forbidden.
- Geometry, strike, dip, rake, slip rate, and aseismicity are inputs or priors;
  none directly establishes initial stress or effective strength.

The report emphasizes that the inversion is underdetermined and samples a
range of models. CH-002 must propagate that uncertainty rather than collapse it
into a visually convenient single map.

## Initial State

There is no admitted observation of absolute initial stress. Each particle is
initialized as a correlated dimensionless field along the fault graph:

```text
margin_s(2014-01-07) = regional_offset + correlated_section_effect_s
```

The distribution hyperparameters may be fitted only on the CH-002 fit
sub-window. Particle identity is fixed by a committed seed. State values are
centered for identifiability because adding a constant to every margin is
absorbed by the mass-preserving normalization.

## Rupture Release and Transfer

The first candidate uses only fields already present in the issue-time catalog:
origin time, location, magnitude, and depth where available. An event is mapped
probabilistically to nearby fault sections with an explicit off-fault option.
Magnitude controls a dimensionless release amplitude; it is not converted into
a claimed Coulomb stress change.

Directional transfer is deferred until its receiver geometry and source-plane
ambiguity can be represented without current-product leakage. A first
`no-transfer` model and a geometry-only transfer ablation must be reported
before adding ComCat mechanism products.

## Rejected Shortcuts

- Do not use NSHM23 geometry or slip constraints to explain 2019-2022 outcomes.
- Do not treat the static Automata `strain` grid as observed GNSS strain.
- Do not treat the Automata `cfs` proxies as Coulomb failure stress.
- Do not initialize each section at a hand-selected stress value.
- Do not assign every earthquake deterministically to the nearest mapped fault.
- Do not tune a fault-model branch after reading validation performance.

## Acquisition Gate

Before CH002-003 starts, the exact UCERF3 files must be downloaded from the USGS
report release, stored outside Git when large, and recorded with source URL,
retrieval time, byte size, SHA-256, license/terms, parser version, and extracted
field schema. A parser fixture containing only synthetic or redistributable
minimal records may be committed for tests.
