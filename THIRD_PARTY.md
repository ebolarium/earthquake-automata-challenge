# Third-Party Software

The reference runner installs upstream software at immutable Git commits. The
challenge implementation must keep provenance and licensing visible whenever
code is reused or redistributed.

| Project | Role | License |
| --- | --- | --- |
| [EarthquakeNPP](https://github.com/ss15859/EarthquakeNPP) | Experiment scripts and checked-in reference outputs | MIT |
| [ETAS](https://github.com/ss15859/etas) | Reference model implementation | MIT |
| [SeismoStats](https://github.com/swiss-seismological-service/SeismoStats) | Forecast catalog type used by ETAS evaluation | AGPL-3.0 |
| [pyCSEP](https://github.com/SCECcode/pycsep) | Prospective testing framework recorded by EarthquakeNPP | BSD-3-Clause |

SeismoStats is installed as a runtime dependency of the isolated reference
container. Challenge-native code must not copy its implementation. Review the
AGPL network-use obligations before exposing that container as a service; the
initial benchmark runs it only as an offline scientific reproduction tool.
