# Reference Runner

The upstream repositories will be checked out under `reference/upstream/` at
the commits recorded in `data/manifests/reference-comcat25.json`.

The container runs as `linux/amd64`, matching the upstream `linux-64`
environment even when the host is ARM64.

The first reference run will:

1. verify every downloaded artifact checksum;
2. create an isolated Python 3.11 environment;
3. install the pinned ETAS and SeismoStats compatibility commits;
4. run the unmodified EarthquakeNPP ComCat_25 inversion and evaluation;
5. write outputs under `artifacts/reference-comcat25/`;
6. compare generated parameters and likelihoods with the committed contract.

No upstream source file will be edited to force alignment.

Likelihood replay and fresh parameter inversion use separate ignored
workspaces. The inversion workspace deliberately excludes the checked-in
`parameters_0.json`, preventing a reference result from being mistaken for a
fresh optimizer output.

## Version Caveat

EarthquakeNPP installs `ss15859/etas` from an unpinned branch. Its recorded
environment uses Python 3.11.11, while the historical ETAS package metadata
declares Python 3.12 or newer. The reference container retains Python 3.11.11
and installs the inferred compatibility commit with
`--ignore-requires-python`. This is an explicit reproduction hypothesis to be
accepted or rejected by the checked-in numerical outputs.

ETAS imports SeismoStats during likelihood evaluation but omits it from its
package metadata. The reference image installs the exact SeismoStats commit
named by the historical ETAS requirements file. It remains confined to this
offline reference runner; see `THIRD_PARTY.md`.
