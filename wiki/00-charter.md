# Project Charter

## Question

Can a new model add reproducible forecast skill beyond a correctly implemented
literature baseline, especially for low-background or emergence events?

## Baseline Phase

The sole model is spatial-temporal ETAS. No challenger, RQ model, strain
feature, or custom reranker enters the repository until the ETAS alignment gate
is complete.

## Rules

- Forecasts use only information available at the forecast issue time.
- Every dataset, dependency, configuration, seed, and output is versioned or
  checksummed.
- Reference code remains unmodified.
- Native formulas have unit and numerical integration tests.
- Failed and negative experiments are retained in the experiment index.
- Performance claims require benchmark comparisons and uncertainty intervals.
- The project does not issue earthquake warnings.

## Separation

This repository is a sibling of `earthquake-automata-core`. It does not read
the core application's databases at runtime and does not share scheduled tasks,
models, APIs, or deployment state.

