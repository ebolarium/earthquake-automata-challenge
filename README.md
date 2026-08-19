# Earthquake Automata Challenge

An independent, reproducibility-first project for implementing and testing a
published earthquake forecasting baseline before developing challengers.

The only target model in the baseline phase is the spatial-temporal
Epidemic-Type Aftershock Sequence (ETAS) model used by EarthquakeNPP. This
repository does not import code, databases, predictions, or runtime state from
`earthquake-automata-core`.

## Current Milestone

Reproduce the EarthquakeNPP `ComCat_25` ETAS experiment with locked inputs and
expected outputs. Then implement ETAS independently from the published
equations and align the native implementation with the reference.

The baseline is not considered reproduced until parameter estimates,
event-based likelihood scores, and simulation summaries satisfy the tolerances
defined in `wiki/03-reproduction/reference-alignment.md`.

## Locked Reference

- EarthquakeNPP commit: `26d18048e1ca8ff2b02c7016b993de48ed0760f5`
- ETAS compatibility commit: `51e0c8e419197df3f88349035a682b90fbd4dfb5`
- Dataset: EarthquakeNPP `ComCat_25`
- Python: `3.11.x`
- Reference manifest: `data/manifests/reference-comcat25.json`

The ETAS commit is the last fork commit predating the checked-in reference
output timestamp. EarthquakeNPP did not pin this dependency itself; that
upstream reproducibility gap is recorded explicitly in the manifest and wiki.

## Repository Layout

```text
artifacts/       Generated outputs, never committed
configs/         Immutable experiment configurations
data/            Local catalogs, with committed manifests only
reference/       Reference-run instructions and temporary upstream checkout
src/             Native implementation
tests/           Contract, formula, and alignment tests
wiki/            Literature, decisions, protocols, and experiment records
```

## Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m etas_challenge.contracts data/manifests/reference-comcat25.json
```

Reference dependencies are intentionally not installed in the scaffold step.
Their installation and the first upstream run form the next controlled
milestone.

## Scientific Boundary

This is a research forecast experiment, not an earthquake warning or a claim
of deterministic earthquake prediction.
