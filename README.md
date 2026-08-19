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
- SeismoStats commit: `4d617d6b54a57898f9ccae56ea24f4a071924dc3`
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

## Reference Environment

The benchmark runtime is isolated because the host Python is not part of the
experiment contract.

```bash
sh scripts/fetch_reference.sh
python3 scripts/verify_reference_artifacts.py
docker build --platform linux/amd64 -f docker/reference.Dockerfile -t etas-challenge-reference .
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" etas-challenge-reference
python3 scripts/prepare_reference_workspace.py
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" \
  -w /workspace/artifacts/reference-comcat25/workspace/Experiments/ETAS \
  etas-challenge-reference python predict_etas.py ComCat_25
python3 scripts/compare_reference_likelihood.py
```

The full parameter inversion uses a separate workspace that never receives
the checked-in reference parameters:

```bash
python3 scripts/check_reference_resources.py
python3 scripts/prepare_reference_inversion.py
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" \
  -w /workspace/artifacts/reference-comcat25/inversion-workspace/Experiments/ETAS \
  etas-challenge-reference python invert_etas.py ComCat_25
python3 scripts/report_reference_inversion.py
```

The upstream optimizer does not expose checkpoints. A completed
`parameters_0.json` is preserved and the preparation command will not replace
it; an interrupted run must restart from the locked initial values.

The full ComCat_25 distance preparation exceeded an 8 GiB Docker allocation.
The preflight requires at least 12 GiB and recommends 14 GiB. On Docker
Desktop, adjust this under **Settings > Resources > Advanced > Memory** before
starting the inversion.

The Docker build documents one upstream inconsistency: EarthquakeNPP records
Python 3.11.11 while its unpinned ETAS dependency later declared Python 3.12+
in package metadata. We preserve the recorded 3.11 runtime and bypass only the
package metadata guard for the historically compatible ETAS commit.

The reference image is fixed to `linux/amd64`, matching EarthquakeNPP's
recorded `linux-64` environment and the binary availability of its exact
Cartopy version.

ETAS evaluation imports SeismoStats without declaring it in package metadata.
The container therefore pins the commit named by the historical ETAS
requirements file. See `THIRD_PARTY.md` for the license boundary.

## Scientific Boundary

This is a research forecast experiment, not an earthquake warning or a claim
of deterministic earthquake prediction.
