# EarthArXiv Submission Metadata

## Title

CH-008: Causal Renewal-Frailty Reallocation of ETAS Background Seismicity Across California, New Zealand, and Chile

## Author

- Given names: Saban Baris
- Family name: Boga
- Affiliation: Independent Researcher
- Location: Adana, Turkiye
- ORCID: https://orcid.org/0009-0000-9076-946X
- Corresponding email: hello@bboga.com

## Article Type

Research article / methods and pre-prospective evidence

## Suggested Subjects

- Geophysics and Seismology
- Earth Sciences
- Statistical Models
- Statistics and Probability

## Keywords

earthquake forecasting; ETAS; renewal process; frailty; information gain; prospective evaluation; CSEP

## Abstract

Epidemic-Type Aftershock Sequence (ETAS) models provide a strong, interpretable baseline for short-term earthquake forecasting, but their direct background component is commonly treated as stationary after fitting. We present CH-008, a causal post-ETAS model that preserves the fitted ETAS triggered component and the total expected event rate while reallocating a fixed fraction of direct background probability in space. The reallocation is driven by two pre-event state variables: a magnitude-marked Brownian renewal score, representing elapsed loading since local reset, and a decaying frailty score, representing persistent excess or deficit of posterior background-event mass relative to ETAS expectation. Parameters were selected using California data from 2014--2018 after an unscored warm-up from 2007. Evaluation was then performed on California development validation (2019--2022), a later California retrospective period (2023--18 August 2026), and exploratory external-region transfers to New Zealand (2008--2025) and Chile (2015--2025). Mean information gain per earthquake relative to frozen ETAS was +0.00521 in California validation (N=5,204), +0.00786 in the later California period (N=3,995), +0.01856 in New Zealand (N=2,270), and +0.00972 in Chile (N=1,909); 30-day and 90-day stationary-block bootstrap lower bounds were positive in all four evaluations. The California frailty increment over renewal alone was also positive in both evaluation periods. These results are supportive but not a confirmatory prospective claim: the later California interval is not pristine with respect to the preceding model-development sequence, and the New Zealand and Chile adapters were frozen in the same commits as their result artifacts. A public, frozen, daily three-region protocol will therefore compare CH-008 with frozen ETAS for 365 days. Its primary endpoint is pooled final paired information gain per earthquake, subject to predeclared event-count, uncertainty, operational-eligibility, and no-backfill rules.

## Conflict of Interest

The author declares no competing interests.

## Funding

This independent research received no external funding.

## Data Availability

Source code, frozen configurations, model files, region definitions, result manifests, tests, and protocol documentation are available at https://github.com/ebolarium/earthquake-automata-challenge. Public operational status and machine-readable prospective-test summaries are available at https://etas.bboga.com/. Input earthquake catalogs are obtained from the USGS ANSS ComCat and GeoNet FDSN Event Web Services. Large catalog snapshots and binary daily forecast artifacts are not currently deposited with EarthArXiv; their provenance and SHA-256 identities are recorded by the operational system.

## License

CC BY 4.0

## Peer-Review Status

This manuscript is a non-peer-reviewed preprint. It has not been submitted to a peer-reviewed journal as of 16 September 2026.

## Before Submission

- Add `hello@bboga.com` to the ORCID record used for EarthArXiv and ensure it matches the submitting account.
- Add `Independent Researcher` as a current or recent affiliation/activity in ORCID.
- Review the PDF one final time after the dry-run final scores settle if those numbers are to remain in the manuscript.
- Preferably archive the exact code release with Zenodo and replace the Git commit-only citation with the resulting DOI.
- Upload only `output/pdf/ch008-preprospective-manuscript-v0.1.pdf`; EarthArXiv requires one PDF.
