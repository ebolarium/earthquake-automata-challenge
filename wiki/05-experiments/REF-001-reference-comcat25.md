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

This is an infrastructure failure, not a numerical mismatch. The rerun must
use the same locked AMD64 image and inputs with at least 12 GiB Docker memory;
14 GiB is recommended. Native ARM execution is not substituted because it
would change the reference platform.

## Conclusion

Likelihood replay is aligned at an absolute tolerance of `1e-10`. This
supports the inferred ETAS compatibility commit. REF-001 remains open until a
fresh parameter inversion reproduces the checked-in beta and nine fitted
parameters.
