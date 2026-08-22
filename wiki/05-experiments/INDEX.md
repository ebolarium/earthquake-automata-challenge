# Experiment Index

| ID | Status | Question | Data | Result |
| --- | --- | --- | --- | --- |
| REF-001 | Completed | Can the pinned ETAS compatibility commit reproduce the checked-in EarthquakeNPP ComCat_25 outputs? | EarthquakeNPP ComCat_25 | Parameters and likelihood aligned |
| NATIVE-001 | Completed | Does the native event likelihood align with the pinned ETAS oracle? | Five synthetic events | Aligned except documented first-interval reference behavior |
| NATIVE-002 | Completed | Does native ETAS reproduce the full reference likelihood replay? | ComCat_25, 92,263 events | Strict scores aligned; corrected first interval quantified |
| REPLAY-001 | Completed | Can native ETAS be replayed daily without origin-time leakage? | Local California V1, 7,170 days | Deterministic replay complete; revision-history limitation recorded |
| EVAL-001 | Completed | Can native ETAS and Poisson forecasts pass the pinned day-7 pyCSEP consistency pipeline? | Local California V1, 10,000 catalogs per model | All four tests valid; neither model rejected; no superiority claim |
| WEB-001 | Completed | Can the native ETAS baseline publish an independent inspectable forecast? | Local California V1, 10,000 catalogs | Responsive forecast page and production image complete |
| CH001-001 | Completed | Can CH-001 receive leakage-free daily grid features and targets? | Fit and validation periods, California RELM grid | 5,844 days and 44,893,608 cell-days generated and verified |
| CH001-002 | Completed | Can the frozen EarthquakeNPP ETAS forecast be converted to positive daily RELM cell rates with bounded memory? | Fit and validation periods, 10,000 continuations per day | 5,844 positive daily grids generated and all 192 shards verified |
| CH001-003 | Completed, not promoted | Can a fixed linear catalog residual improve ETAS spatial allocation without changing daily counts? | CH001-001 features and CH001-002 rates | Validation IGPE +0.01359 with CI crossing zero; low-ETAS IGPE -0.06610 |
| CH002-001 | Contract implemented | Can latent fault readiness alter only ETAS direct-background allocation while preserving triggering and total count? | Frozen ETAS decomposition, synthetic margins | Numerical component and state-transition contract implemented; no skill result |
| CH002-002 | Completed | Which fault-system inputs can enter a leakage-controlled retrospective model? | UCERF3, ComCat product documentation, NSHM23 provenance | UCERF3 admitted from 2014-01-07; modern/revision-prone sources deferred |
| CH002-003 | Completed | Can admitted UCERF3 sections be parsed and represented on the RELM grid without model fitting? | 350 UCERF3 sections, 7,682 RELM cells | Eight loading branches retained; deterministic four-nearest-section geometry generated |
| CH002-004 | Completed | Can initial stress-minus-strength uncertainty be represented without one asserted stress map? | UCERF3 pair geometry, 256 seeded particles | Geometry-weighted graph and centered unit-variance latent ensemble frozen; no target read |
| CH002-005 | Contract implemented | Can daily loading, background-weighted assimilation, and rupture depletion remain leakage-free? | Synthetic events, eight loading branches | Daily next-issue transition and probabilistic off-fault assignment tested; no fit |
| CH002-006 | Completed | Can fit events receive same-day frozen ETAS background posteriors without validation access? | 2014-2018 catalog and 60 frozen ETAS shards | 3,619 RELM events across 1,820 fit days; posterior background mass 522.76 |
| CH002-007 | Completed, not admitted | Can latent readiness improve ETAS on fit-only selection and report-only holdout periods? | Locked CH002-003 through CH002-006 inputs | Best selection IGPE +0.000335; 2018 holdout IGPE -0.011573; validation remained unopened |
| CH003-001 | Contract implemented | Can ETAS-compensated fault-network emergence remain neutral without evidence and bound its downside? | Synthetic innovations and fault graphs | CUSUM, coherence, consensus, and bounded-mixture invariants implemented; no catalog score |
| CH003-002 | Completed | Can observed posterior root mass and expected ETAS background mass share exactly the same section geometry? | Locked fit inputs, UCERF3 branches, RELM grid | 1,820 branch-aware days; mass conserved within 6.82e-13; no CH-003 score |
| CH003-003 | Completed, not admitted | Can coherent ETAS residual emergence improve next-day forecasts robustly across years and low-ETAS events? | CH003-002 and frozen ETAS fit inputs | 20 active candidates; none passed annual robustness or low-ETAS veto; exact ETAS control selected |
| CH004-001 | Contract implemented | Can ETAS-normalized quiescence form a magnitude-marked renewal clock without absolute stress or hard declustering? | Synthetic marked resets and hazard ages | GR expectation, soft reset, and BPT-inspired overdue components implemented; no catalog score |

Each experiment receives a dedicated document before execution. The document
must state the hypothesis, frozen inputs, command, environment, metrics,
acceptance criteria, outputs, and conclusion.
