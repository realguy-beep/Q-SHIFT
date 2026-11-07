# Q-SHIFT correlation-aware matching pilot

## Study status

This was the bounded, preregistered-by-freeze **development feasibility pilot** from the selected research direction. It compared PyMatching's correlation-disabled and correlation-enabled modes on paired samples. It is not a confirmatory experiment, does not test an adaptive controller, and does not justify a general claim that correlation-aware decoding is superior.

## Design

The study used Stim 1.16.0 and PyMatching 2.4.0, with the Phase 2B rotated surface-code generator: distance 3, five rounds, X-memory and Z-memory. Six strata crossed the memory basis with X-biased, balanced, and Z-biased categorical Pauli noise. Gate fault probability was 0.003 for both one- and two-qubit gates; measurement flip probability was 0.003. Pauli ratios were 10:1:1, 1:1:1, and 1:1:10. DEMs used `decompose_errors=True` and `approximate_disjoint_errors=True`.

There were 12 independent roots per stratum and 10,000 shots per root: 72 roots and **720,000 paired shots**. For each sampled detector array, four decoder outputs were saved: pooled fixed uncorrelated, pooled fixed correlated, regime-informed uncorrelated, and regime-informed correlated. The last two receive the generating regime and are privileged diagnostic references. The primary comparison is pooled-fixed correlated minus pooled-fixed uncorrelated, with an equal-weight mean over strata.

## Primary result

| Primary pooled-fixed arm | Logical errors | LER |
|---|---:|---:|
| Correlation disabled | 3,532 / 720,000 | 0.490556% |
| Correlation enabled | 3,349 / 720,000 | 0.465139% |

The paired difference was **-0.00025417 LER** (-0.025417 percentage points; approximately 5.18% relative error reduction from the uncorrelated arm). The regime-stratified root-cluster bootstrap 95% CI was **[-0.00035000, -0.00016250]**. The two-sided paired root-cluster sign-flip test gave **p = 0.000839992** (100,000 Monte Carlo assignments, add-one correction). The interval excludes zero, but its upper bound does **not** meet the frozen practically meaningful threshold of -0.0002.

At shot level, the paired predictions differed on 1,343 shots. Of these, correlation-disabled-only residual failures numbered 763; correlation-enabled-only failures numbered 580, for a net reduction of 183 errors. Exact paired-shot McNemar p = 6.57052e-7 is descriptive; root clusters are the independent units for the primary inference.

## Per-stratum primary outcomes

| Stratum | Uncorrelated errors | Correlated errors | Correlated − uncorrelated LER (root-bootstrap 95% CI) | Roots favoring / harming / tied |
|---|---:|---:|---:|---:|
| X-memory, X-biased | 100 | 122 | +0.000183 [+0.000033, +0.000317] | 1 / 9 / 2 |
| X-memory, balanced | 727 | 629 | -0.000817 [-0.001225, -0.000450] | 11 / 1 / 0 |
| X-memory, Z-biased | 1,070 | 984 | -0.000717 [-0.000892, -0.000533] | 12 / 0 / 0 |
| Z-memory, X-biased | 938 | 884 | -0.000450 [-0.000650, -0.000250] | 9 / 1 / 2 |
| Z-memory, balanced | 575 | 550 | -0.000208 [-0.000425, 0.000000] | 8 / 3 / 1 |
| Z-memory, Z-biased | 122 | 180 | +0.000483 [+0.000317, +0.000642] | 1 / 11 / 0 |

Four of six strata favored correlation-enabled matching. All six leave-one-stratum-out aggregate effects remained favorable, with differences from -0.0004017 to -0.0001417. Thus the direction is not caused by one stratum, but the practical-margin confidence requirement still fails. Benefit also varies strongly by basis and bias: the two extreme matched-bias strata are worse with the correlation option.

## Regime-informed secondary comparisons

These use known simulated regime information and are not deployable policies. The 12 prespecified regime-informed-minus-pooled comparisons were exact root-level sign-flip tests with Holm adjustment. Adjusted p-values below 0.05 occurred for four comparisons: X-memory balanced correlated (+0.000700, adjusted p=0.00586; worse), X-memory Z-biased uncorrelated (-0.000592, p=0.0352; better), Z-memory X-biased uncorrelated (-0.000608, p=0.0293; better), and Z-memory balanced correlated (+0.002142, p=0.00586; worse). The mixed direction reinforces that regime information alone does not guarantee a useful decoder choice.

## Frozen feasibility gate

The exact absolute practical margin was **0.0002 LER**. The gate required: (1) primary point estimate at or below -0.0002; (2) upper 95% confidence bound at or below -0.0002; (3) at least four favorable strata; and (4) favorable equal-stratum aggregate effects after omitting each stratum in turn.

**Overall gate: FAIL.** The point estimate, favorable-strata count, and leave-one-stratum-out conditions passed; the upper confidence bound (-0.00016250) did not meet -0.0002. The finding is evidence of a modest average difference under the tested simulation/DEM setup, not evidence that the predeclared practical gain has been established.

## Runtime and technical limits

- Decoder construction: 0.0387 s.
- Stim sampling: 0.1143 s.
- Decoder inference: pooled uncorrelated 0.2275 s; pooled correlated 0.6424 s; regime-informed uncorrelated 0.2121 s; regime-informed correlated 0.6043 s.
- Sampling/decode loop wall time: 3.0455 s on the recorded local environment.
- The correlated call took about 2.8× the pooled uncorrelated inference time in this small run. These are local software timings, not hardware latency guarantees.
- Peak RSS was not captured because `psutil` was unavailable.
- DEM conversion approximates mutually exclusive categorical Pauli events as independent mechanisms. Correlation-aware matching can use only correlations represented in the decomposed DEM; it cannot restore dependencies lost by conversion.

The independent recomputation is recorded in `AGGREGATE_RECOMPUTATION.md`/`.json`; detailed per-root, per-stratum, disagreement, seed, timing, and raw checkpoint evidence is retained alongside this report. See `REPRODUCE.md` and `MANIFEST.json`.
