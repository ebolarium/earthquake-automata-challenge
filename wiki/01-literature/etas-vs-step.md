# Decision Context: ETAS vs STEP

Both ETAS and STEP are established short-term earthquake forecasting models.
ETAS was selected as the sole baseline because it has:

- a modern open implementation connected to peer-reviewed work;
- inversion, likelihood evaluation, and catalog simulation;
- a published benchmark dataset and checked-in reference outputs;
- direct compatibility with point-process and CSEP evaluations;
- a clear path from reference reproduction to independent implementation.

STEP remains literature context only. It will not be implemented during the
baseline phase and cannot silently become a second target model.

