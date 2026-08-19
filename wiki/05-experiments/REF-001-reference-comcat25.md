# REF-001: EarthquakeNPP ComCat_25 Reference

## Hypothesis

The inferred historical ETAS commit and its pinned dependency chain reproduce
the checked-in EarthquakeNPP ComCat_25 outputs without modifying upstream
source code.

## Frozen Inputs

- Manifest: `data/manifests/reference-comcat25.json`
- Platform: `linux/amd64`
- Python: `3.11.11`
- EarthquakeNPP: `26d18048e1ca8ff2b02c7016b993de48ed0760f5`
- ETAS: `51e0c8e419197df3f88349035a682b90fbd4dfb5`
- SeismoStats: `4d617d6b54a57898f9ccae56ea24f4a071924dc3`

All five source artifacts passed the committed SHA-256 contract immediately
before the run.

## Run 1: Likelihood Replay

Date: 2026-08-19

The unmodified upstream `predict_etas.py` was run in the reference container
using the checked-in fitted parameters. Inputs and scripts were copied into an
ignored workspace so the upstream checkout remained unchanged.

Runtime on an ARM host using AMD64 emulation: 5 minutes 49 seconds. Observed
peak sample during the run: approximately 254% CPU and 2.19 GiB memory.

| Model | Component | Expected | Actual | Absolute delta |
| --- | --- | ---: | ---: | ---: |
| ETAS | nll | 7.2554275527505645 | 7.2554275527265855 | 2.4e-11 |
| ETAS | tll | 1.4343428344882627 | 1.4343428345122435 | 2.4e-11 |
| ETAS | sll | -8.689770387238827 | -8.689770387238827 | 0 |
| Poisson | nll | 13.261863460288378 | 13.261863460288378 | 0 |
| Poisson | tll | 0.5126406686259881 | 0.5126406686259881 | 0 |
| Poisson | sll | -13.774504128914366 | -13.774504128914366 | 0 |

The upstream code emitted divide-by-zero and invalid-subtraction warnings for
individual zero-intensity samples. They did not alter the aggregate values and
are retained as an upstream numerical-behavior finding.

## Run 2: Fresh Inversion, Insufficient Memory

Date: 2026-08-19

The unmodified upstream `invert_etas.py` was started in a separate workspace
that contained no reference parameter file. Preparation reproduced the
expected catalog invariants:

- 70,374 sources;
- 55,442 targets;
- beta `2.147144208621307`;
- region area `959822.9591782562` square km.

During source-target distance preparation, memory rose from approximately
2.15 GiB to 6.65 GiB and the process was killed with exit code 137 by the
Docker VM. Docker had 7.65 GiB available plus a 1 GiB swap file. No completed
parameter output was written.

This is an infrastructure failure, not a numerical mismatch. The initial
mitigation was to retain the same locked AMD64 image and raise Docker memory.
Native ARM execution was not substituted because it would change the
reference platform.

## Run 3: Fresh Inversion, Transient Memory Spike

Date: 2026-08-19

Docker memory was increased to 15.60 GiB while swap remained at 1 GiB. The
same locked command and parameter-free workspace were used. Distance
preparation passed the previous 8 GiB boundary and reached an observed sample
of 9.85 GiB. It was then killed with exit code 137 during a transient memory
spike before the first optimization iteration. No completed parameter output
was written.

Docker Desktop later proved to cap swap at 4 GiB on this host. The successful
rerun therefore retained 16 GiB memory and 4 GiB configured swap, then added a
temporary 8 GiB swap file inside the Docker VM. This preserved the reference
model, catalog, platform, and numerical code while allowing the temporary
matrix copy to spill to disk.

## Run 4: Fresh Inversion, Aligned

Date: 2026-08-19

Docker Desktop exposed 15.60 GiB memory and its maximum 4 GiB swap. A
privileged helper added a temporary 8 GiB swap file inside the Docker VM. This
kept the upstream source and all scientific inputs unchanged while allowing
the transient distance-matrix allocation to page to disk.

The run completed after 15 iterations and reproduced all structural
invariants:

- 55,442 target events;
- beta absolute delta `4.44e-16`;
- maximum fitted-parameter absolute delta `2.88e-5`;
- `n_hat` absolute delta `0.00523`;
- maximum fresh-fit ETAS likelihood absolute delta `9.94e-7`;
- all three Poisson likelihood components matched exactly.

The inversion ran from 14:34:40 to 17:51:08 UTC, approximately 3 hours 16
minutes. The output file appeared at 20:51:08 in the Europe/Istanbul host time
zone. Heavy paging made the run substantially slower than an in-memory
execution. A subsequent likelihood evaluation with the freshly fitted
parameters completed normally and retained the upstream zero-intensity runtime
warnings already observed in Run 1.

## Conclusion

REF-001 is complete. Likelihood replay aligned at `1e-10`; the fresh inversion
aligned at `5e-5` for transformed parameters, `0.01` for `n_hat`, and `2e-6`
for likelihood components. The result supports the inferred historical ETAS
commit and establishes the external baseline for native implementation.
