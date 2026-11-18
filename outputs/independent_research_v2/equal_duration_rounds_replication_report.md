# Equal-duration syndrome schedule: fresh-seed replication

## Replication result

The independent seed stream reproduced the direction in both aligned workloads. The X-aligned cell had 575/500,000 failures for three rounds plus idle versus 635/500,000 for five active rounds, rate ratio .906 (95% log-normal interval .809–1.014). The Z-aligned cell had 456 versus 711 failures, rate ratio .641 (.570–.721). The equal-weight mean cell ratio was .773, compared with .762 in the initial stream. Both cell point estimates and the macro estimate favored the idle schedule; the X cell alone remained uncertain. The preregistered directional and same-positive-gate criteria passed.

The replication used fresh preflight seeds 2026113801–04 and main seeds 2026113811–14, 500,000 shots/arm/cell, the identical circuit/noise/decoder construction, and no tuning. All geometry, source-builder, terminal readout, deterministic circuit, and scalar/batch checks passed. Total independent replication sampling was 2,000,400 shots including preflight.

## Interpretation

Two development streams now support a finite d3 simulator result: with the assumed biased p=.003 idle channel on data qubits, fewer active syndrome rounds plus idle time can outperform five active rounds at the same modeled duration and reduce two-qubit interaction opportunities. Evidence is strongest for Z alignment; the X cell is directionally consistent but its replication interval includes no difference. This still does not establish hardware utility, scaling, or a general schedule. The idle-channel model needs a declared robustness challenge before the result is suitable for integration guidance.
