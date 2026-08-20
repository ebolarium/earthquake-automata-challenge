# Experiment Index

| ID | Status | Question | Data | Result |
| --- | --- | --- | --- | --- |
| REF-001 | Completed | Can the pinned ETAS compatibility commit reproduce the checked-in EarthquakeNPP ComCat_25 outputs? | EarthquakeNPP ComCat_25 | Parameters and likelihood aligned |
| NATIVE-001 | Completed | Does the native event likelihood align with the pinned ETAS oracle? | Five synthetic events | Aligned except documented first-interval reference behavior |
| NATIVE-002 | Completed | Does native ETAS reproduce the full reference likelihood replay? | ComCat_25, 92,263 events | Strict scores aligned; corrected first interval quantified |
| REPLAY-001 | Completed | Can native ETAS be replayed daily without origin-time leakage? | Local California V1, 7,170 days | Deterministic replay complete; revision-history limitation recorded |
| EVAL-001 | Completed | Can native ETAS and Poisson forecasts pass the pinned day-7 pyCSEP consistency pipeline? | Local California V1, 10,000 catalogs per model | All four tests valid; neither model rejected; no superiority claim |
| WEB-001 | Completed | Can the native ETAS baseline publish an independent inspectable forecast? | Local California V1, 10,000 catalogs | Responsive forecast page and production image complete |

Each experiment receives a dedicated document before execution. The document
must state the hypothesis, frozen inputs, command, environment, metrics,
acceptance criteria, outputs, and conclusion.
