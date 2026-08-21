# Earthquake Automata Challenge

An independent, reproducibility-first project for implementing and testing a
published earthquake forecasting baseline before developing challengers.

The only target model in the baseline phase is the spatial-temporal
Epidemic-Type Aftershock Sequence (ETAS) model used by EarthquakeNPP. This
repository does not import code, databases, predictions, or runtime state from
`earthquake-automata-core`.

## Current Milestone

The locked EarthquakeNPP `ComCat_25` reproduction, native likelihood alignment,
clean local catalog export, leakage-free daily replay, documented pyCSEP day-7
consistency gate, and independent ETAS forecast page are complete. Challenge V1
is now frozen. The current milestone is `CH-001`, an ETAS residual-emergence
spatial challenger developed only on the admitted fit and validation splits.

The frozen retrospective test can promote a model to prospective evaluation;
it cannot by itself support a scientific ETAS-superiority claim. That claim
requires the separate one-year prospective gate in the challenge contract.

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
web/             Independent ETAS forecast server and static application
wiki/            Literature, decisions, protocols, and experiment records
```

## Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m etas_challenge.contracts data/manifests/reference-comcat25.json
PYTHONPATH=src python3 scripts/verify_challenge_freeze.py
```

Generate the leakage-free catalog feature matrix admitted for `CH-001`:

```bash
PYTHONPATH=src python3 scripts/generate_ch001_matrix.py
PYTHONPATH=src python3 scripts/verify_ch001_matrix.py
```

Generate the matching frozen ETAS cell-rate offset. The run is resumable at
calendar-month boundaries and uses the same 10,000-catalog continuation method
as the pinned EarthquakeNPP evaluation:

```bash
PYTHONPATH=src python3 scripts/generate_ch001_etas_grid.py
PYTHONPATH=src python3 scripts/verify_ch001_etas_grid.py
```

Direct background roots are integrated analytically per spherical grid cell;
all triggered events and descendants remain Monte Carlo estimates. This keeps
the reference expectation while removing random zero-rate cells.

The canonical low-memory run uses the pinned Python 3.11 container and can be
followed independently of a Codex session:

```bash
docker logs --tail 20 ch001-etas-grid
docker stats --no-stream ch001-etas-grid
```

The native package currently includes physical parameter conversion, the
space-time triggering kernels, closed-form kernel integrals, branching ratio,
conditional intensity, and low-memory catalog replay. Its formula tests do not
import reference code.

The full native/reference catalog comparison is resumable and writes only
ignored artifacts:

```bash
PYTHONPATH=src python3 scripts/compare_native_reference_catalog.py
```

The clean local catalog can be reproduced from the locked source snapshot:

```bash
PYTHONPATH=src python3 scripts/export_clean_catalog.py
```

The resumable daily replay uses the committed clock and scoring contract:

```bash
PYTHONPATH=src python3 scripts/run_daily_replay.py
```

The pyCSEP integration gate generates 10,000 deterministic native ETAS and
Poisson catalogs for the documented EarthquakeNPP day-7 window:

```bash
PYTHONPATH=src python3 scripts/generate_pycsep_forecasts.py
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" \
  etas-challenge-reference python scripts/run_pycsep_evaluation.py
```

Generate and inspect the independent daily ETAS forecast page:

```bash
PYTHONPATH=src python3 scripts/generate_web_snapshot.py
PYTHONPATH=src python3 web/server.py --port 8080
```

The production image generates the same snapshot from a read-only mounted
catalog before serving it on port 8080:

```bash
docker build --platform linux/amd64 -f docker/web.Dockerfile \
  -t etas-challenge-web .
docker run --rm --platform linux/amd64 -p 8080:8080 \
  -v "$PWD/data/local/california-earthquakes-v1.sqlite:/data/california-earthquakes.sqlite:ro" \
  etas-challenge-web
```

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

The full ComCat_25 distance preparation exceeded both an 8 GiB allocation and
a later 16 GiB allocation with the default 1 GiB swap. The preflight requires
at least 14 GiB memory and 6 GiB swap; 16 GiB memory and 8 GiB swap are
recommended. On Docker Desktop, adjust both values under
**Settings > Resources > Advanced** before starting the inversion.

Docker Desktop may cap its swap setting below the required amount. In that
case, the following privileged helper adds an 8 GiB swap file inside the
Docker VM without changing the host operating system:

```bash
sh scripts/start_reference_swap.sh
python3 scripts/check_reference_resources.py
# Run the inversion and fresh-fit likelihood evaluation.
sh scripts/stop_reference_swap.sh
```

The helper consumes 8 GiB disk space and must be stopped after the run. Heavy
disk paging makes the reference inversion substantially slower but leaves the
upstream numerical code unchanged.

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
