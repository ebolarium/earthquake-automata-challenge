# Reference Runner

The upstream repositories will be checked out under `reference/upstream/` at
the commits recorded in `data/manifests/reference-comcat25.json`.

The first reference run will:

1. verify every downloaded artifact checksum;
2. create an isolated Python 3.11 environment;
3. install the pinned ETAS compatibility commit;
4. run the unmodified EarthquakeNPP ComCat_25 inversion and evaluation;
5. write outputs under `artifacts/reference-comcat25/`;
6. compare generated parameters and likelihoods with the committed contract.

No upstream source file will be edited to force alignment.

