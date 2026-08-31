# Earthquake Automata Challenge

[![Test](https://github.com/ebolarium/earthquake-automata-challenge/actions/workflows/test.yml/badge.svg)](https://github.com/ebolarium/earthquake-automata-challenge/actions/workflows/test.yml)

An independent, reproducibility-first project for implementing and testing a
published earthquake forecasting baseline before developing challengers.

The only target model in the baseline phase is the spatial-temporal
Epidemic-Type Aftershock Sequence (ETAS) model used by EarthquakeNPP. This
repository does not import code, databases, predictions, or runtime state from
`earthquake-automata-core`.

## Current Milestone

CH-008 is the frozen leading challenger. It preserves ETAS triggering,
magnitude distribution, and total expected count while redistributing only a
bounded fraction of direct-background mass using causal renewal and discounted
Gamma-Poisson frailty states.

The following stages are complete:

- locked EarthquakeNPP `ComCat_25` reproduction and native ETAS alignment;
- clean local catalog export and leakage-free daily replay;
- pyCSEP integration and reference consistency checks;
- CH-008 fit, one-use development validation, locked retrospective evaluation,
  mechanism ablations, and external-region tests in New Zealand and Chile;
- PostgreSQL/S3 daily collection, state, publication, and scoring pipeline;
- bilingual live dashboard and complete Turkish/English method pages.

The three-region 14-day operational dry run is active. Its first issue was
`2026-08-31T00:05:18Z` for the target day beginning `2026-09-01T00:00:00Z`.
California, New Zealand, and Chile each published six forecast artifacts before
the target window. The committed operational record is
`data/manifests/ch008-three-region-dry-run-activation-v1.json`.

Dry-run scores are scientifically discarded. The separate 365-day, minimum
500-event prospective claim has **not** started and still requires
`data/manifests/prospective-challenge-v1.json` before its first target window.
No forecast may be backfilled, and any model, feature, threshold, or geometry
change requires a new protocol identity.

CH-001 through CH-009, including negative results and stopped candidates, are
preserved in [`wiki/05-experiments/INDEX.md`](wiki/05-experiments/INDEX.md).
The external-review dossier is
[`wiki/07-scientific-review/CH008-scientific-dossier-tr.md`](wiki/07-scientific-review/CH008-scientific-dossier-tr.md).

## CH-008 Evidence

| Domain | Evaluation period | Events | IGPE over ETAS |
| --- | --- | ---: | ---: |
| California | 2019-2022 | 5,204 | +0.005213 |
| California | 2023-2026-08-18 | 3,995 | +0.007865 |
| New Zealand CSEP | 2008-2025 | 2,270 | +0.018561 |
| Chile subduction corridor | 2015-2025 | 1,909 | +0.009718 |

These are retrospective results, not a claim that CH-008 will outperform ETAS
prospectively or predict the exact time, location, or magnitude of an
earthquake. See the dossier and the bilingual method page for metrics,
uncertainty, catalog contracts, and limitations.

## Prospective Runtime

The production worker uses PostgreSQL for catalog identities, model states,
forecast runs, scores, and incidents. Large immutable payloads are written to
S3-compatible object storage with SHA-256 metadata.

The daily schedule is:

1. collect rolling FDSN catalogs at `00:05 UTC`;
2. causally advance each regional state to UTC midnight;
3. publish ETAS and CH-008 forecasts for the next UTC day by `00:15 UTC`;
4. score completed target days provisionally;
5. freeze final scores after the seven-day catalog revision window.

The production command is:

```bash
python scripts/collect_prospective_catalogs.py --lookback-days 30 && \
python scripts/advance_prospective_daily_states.py && \
python scripts/publish_prospective_forecasts.py && \
python scripts/score_prospective_forecasts.py
```

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
data/            Locked small runtime inputs and committed manifests
db/              Append-only PostgreSQL migrations
docker/          Reference, web, and prospective production images
prospective_web/ Bilingual live dashboard and scientific method pages
reference/       Reference-run instructions and temporary upstream checkout
scripts/         Reproduction, fitting, evaluation, and operations commands
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
PYTHONPATH=src python3 scripts/verify_prospective_protocol.py
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

## Citation and License

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). Original
project code is available under the [MIT License](LICENSE); third-party
software and reference environments retain their own licenses as documented in
[`THIRD_PARTY.md`](THIRD_PARTY.md).

Scientific questions, criticism, and collaboration: `hello@bboga.com`.

## Scientific Boundary

This is a research forecast experiment, not an earthquake warning or a claim
of deterministic earthquake prediction.
