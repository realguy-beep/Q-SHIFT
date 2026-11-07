# Correlation-aware PyMatching development pilot results

## Status

The complete bounded development pilot was executed and independently recomputed from the saved raw NPZ bundles. This is not a confirmatory experiment.

## Primary pooled-fixed ablation

- Pooled fixed, uncorrelated: **3,532/720,000** errors (LER 0.490556%).
- Pooled fixed, correlated: **3,349/720,000** errors (LER 0.465139%).
- Equal-stratum paired difference (correlated − uncorrelated): **-0.00025417** (-0.025417 percentage points).
- Regime-stratified root-bootstrap 95% CI: **[-0.00035000, -0.00016250]**.
- Root-cluster sign-flip p=0.000839992; shot-level McNemar p=6.57052e-07 (descriptive only).
- Paired shot discordances: standard-only failures 763; correlation-aware-only failures 580; prediction disagreements 1,343.
- Frozen development gate: **FAIL** (margin 0.0002 LER; upper 95% bound ≤ −0.0002; at least four of six strata favorable; all leave-one-stratum-out aggregates remain favorable).

## Results by stratum

| Stratum | Raw observable | Pooled off | Pooled on | Regime-informed off | Regime-informed on | Paired Δ pooled (95% root CI) | Standard-only / correlation-only |
|---|---:|---:|---:|---:|---:|---:|---:|
| x_x_biased | 3330/120000 | 100 (0.0833%) | 122 (0.1017%) | 100 (0.0833%) | 122 (0.1017%) | +0.000183 [+0.000033,+0.000317] | 32/54 |
| x_balanced | 7331/120000 | 727 (0.6058%) | 629 (0.5242%) | 727 (0.6058%) | 713 (0.5942%) | -0.000817 [-0.001225,-0.000450] | 242/144 |
| x_z_biased | 8897/120000 | 1070 (0.8917%) | 984 (0.8200%) | 999 (0.8325%) | 986 (0.8217%) | -0.000717 [-0.000892,-0.000533] | 148/62 |
| z_x_biased | 9118/120000 | 938 (0.7817%) | 884 (0.7367%) | 865 (0.7208%) | 912 (0.7600%) | -0.000450 [-0.000650,-0.000250] | 129/75 |
| z_balanced | 7266/120000 | 575 (0.4792%) | 550 (0.4583%) | 559 (0.4658%) | 807 (0.6725%) | -0.000208 [-0.000425,+0.000000] | 172/147 |
| z_z_biased | 3384/120000 | 122 (0.1017%) | 180 (0.1500%) | 122 (0.1017%) | 180 (0.1500%) | +0.000483 [+0.000317,+0.000642] | 40/98 |

## Interpretation and limitations

The primary comparison changes only whether PyMatching uses the correlation metadata in the same pooled-fixed DEM; regime-informed results are secondary and use the simulated generating regime as privileged information. The experiment does not validate an adaptive controller.

Stim’s DEM conversion of mutually exclusive categorical Pauli-channel outcomes is approximate (`approximate_disjoint_errors=True`). The paired ablation isolates correlation use conditional on that same approximate DEM; it cannot measure information lost by the conversion. Twelve roots per cell make the pilot useful for feasibility but leave seed-level uncertainty limited. No hardware was used.

## Reproducibility

Run `python preflight_correlation_pilot.py` for deterministic smoke/preflight checks. After verifying `PRETEST_FREEZE.json`, run `python run_correlation_pilot.py`. Independently re-decode and analyze with `python analyze_correlation_pilot.py`. See `REPRODUCE.md` and the SHA-256 manifest.
