# WEB-001: Independent ETAS Forecast Page

## Question

Can the frozen native ETAS baseline publish an inspectable daily forecast page
without reading from or changing `earthquake-automata-core`?

## Architecture

The web application has three independent layers:

- `scripts/generate_web_snapshot.py` creates an immutable forecast snapshot;
- `web/server.py` serves the snapshot and static assets using the Python
  standard library;
- `web/static/` renders the forecast as a responsive canvas application.

There is no core database, API, scheduled-task, frontend package, CDN, or map
provider dependency. The clean California catalog is mounted read-only. The
generated forecast JSON stays under ignored `artifacts/`; only its manifest and
SHA-256 are committed.

## Frozen Snapshot

- issue time: `2026-08-19T00:00:00Z`;
- horizon: 24 hours, end exclusive;
- issue-time history: 56,374 events at `M >= 2.5`;
- last history event: `2026-08-18T21:54:59.120000Z`;
- simulation count: 10,000 full ETAS catalog continuations;
- grid: 0.2 degree cells;
- magnitude views: `M >= 2.5`, `M >= 3.0`, and `M >= 4.0`;
- canonical runtime: Python 3.11.11, NumPy 1.26.4, SciPy 1.15.1.

For every grid cell and magnitude threshold, the snapshot records both the
mean event count and the fraction of simulated catalogs containing at least
one event.

## Forecast Summary

| Threshold | Mean count | At least one | 95% count interval |
| --- | ---: | ---: | ---: |
| M >= 2.5 | 4.3373 | 0.9601 | 0-11 |
| M >= 3.0 | 1.4922 | 0.7131 | 0-5 |
| M >= 4.0 | 0.1795 | 0.1552 | 0-1 |

These are retrospective snapshot values produced from history strictly before
issue time. They are not an earthquake warning.

## Interface

The first view is the forecast itself, not a landing page. It includes:

- threshold and map-metric segmented controls;
- expected count, at-least-one probability, interval, and M4 summary values;
- an actual forecast grid clipped to the California model polygon;
- optional 30-day historical seismicity;
- ranked high-rate cells and snapshot provenance;
- pyCSEP consistency and replay views;
- the complete frozen ETAS parameter set.

The map uses no external tiles. Desktop and true 390 by 844 mobile emulation
were checked with Chrome. The mobile document had `scrollWidth = 390`; its
canvas was 360 by 429 CSS pixels and a canvas pixel sample contained 163
distinct colors, confirming that the forecast was nonblank. All three tabs,
all four pyCSEP rows, all nine parameters, and forecast control changes were
also exercised through Chrome DevTools Protocol.

## Local Run

```bash
PYTHONPATH=src python3 scripts/generate_web_snapshot.py
PYTHONPATH=src python3 web/server.py --port 8080
```

## Container Run

```bash
docker build --platform linux/amd64 -f docker/web.Dockerfile \
  -t etas-challenge-web .
docker run --rm --platform linux/amd64 -p 8080:8080 \
  -v "$PWD/data/local/california-earthquakes-v1.sqlite:/data/california-earthquakes.sqlite:ro" \
  etas-challenge-web
```

The production entrypoint generates the snapshot before opening the server.
For Coolify, use `docker/web.Dockerfile`, expose port `8080`, and mount the
catalog read-only at `/data/california-earthquakes.sqlite`. The frozen config
verifies the exact catalog hash; a newer catalog or issue date requires a new
versioned web config and manifest rather than silently replacing this record.

## Result

The independent ETAS page is complete, responsive, containerized, and served
from a reproducible native forecast snapshot. It does not modify or depend on
the production core system.
