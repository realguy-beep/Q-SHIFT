# Retrospective audit of the previous hybrid residual CNN

**Scope:** read-only, descriptive audit of the already completed 750K development run. It verifies the frozen threshold and prediction pairing; no threshold is searched or changed. The independent test and its seed/sample files were not accessed.

Historical run manifest SHA-256: `b63413e5cda2961e4fbf6d1817937102bc555847c89f6f05bf3ff5eeb3dfd3ec`. Independent-test access in that manifest: `0`.

## Paired outcome

| Measure | Verified value |
|---|---:|
| Paired final-development shots | 150,000 |
| PyMatching logical errors / LER | 653 / 0.43533% |
| Hybrid logical errors / LER | 689 / 0.45933% |
| Difference (hybrid minus PyMatching) | +0.02400 percentage points |
| Residual corrections proposed at frozen threshold 0.5 | 62 |
| Helpful / harmful corrections | 13 / 49 |
| Correction precision (Wilson 95% interval) | 21.0% ([12.7%, 32.6%]) |
| Residual recall | 1.99% ([1.17%, 3.38%]) |
| Residual-target prevalence | 0.4353% (653 / 150,000) |
| Probability ranking AUC / Brier score | 0.9413 / 0.004254 |

The hybrid worsened the paired total by 36 errors: 49 false residual corrections introduced errors, while 13 corrected PyMatching errors. It left 640 of 653 PyMatching residual-error labels uncorrected.

## Regime and root distribution

| Generating regime | Shots | PyMatching errors | Hybrid errors | Helpful | Harmful | Paired LER difference |
|---|---:|---:|---:|---:|---:|---:|
| x_biased | 50,000 | 338 | 355 | 4 | 21 | +0.0340 pp |
| balanced | 50,000 | 250 | 265 | 7 | 22 | +0.0300 pp |
| z_biased | 50,000 | 65 | 69 | 2 | 6 | +0.0080 pp |

| Root | PM errors | Hybrid errors | Helpful | Harmful | Paired error difference |
|---:|---:|---:|---:|---:|---:|
| 0 | 125 | 124 | 1 | 0 | -1 |
| 1 | 134 | 150 | 2 | 18 | +16 |
| 2 | 139 | 147 | 8 | 16 | +8 |
| 3 | 136 | 143 | 2 | 9 | +7 |
| 4 | 119 | 125 | 0 | 6 | +6 |

Across five roots, the mean paired difference was +0.02400 percentage points (descriptive root-t 95% interval [-0.00107, +0.04907]); exact two-sided root sign-flip p=0.1250. With five clusters, inferential resolution is coarse.

## Confidence and syndrome diagnostics

The mean saved probability among helpful corrections was 0.601; among harmful corrections it was 0.621. Thus the 0.5 tail did not separate useful from harmful events. AUC of 0.941 describes broad ranking over all scores; it does not imply that the operating tail is safe.

Helpful corrections involved 12 distinct detector patterns among 13 events; harmful corrections involved 46 among 49. No pattern appeared in both groups in this finite sample. Median detector-event count was 6.0 for helpful and 6.0 for harmful events, with overlapping ranges. These sparse descriptive patterns do not establish a syndrome-level mechanism.

| Frozen probability bin | N | Mean probability | Observed residual rate |
|---|---:|---:|---:|
| [0.5, 0.6) | 35 | 0.545 | 20.0% |
| [0.6, 0.7) | 14 | 0.646 | 21.4% |
| [0.7, 0.8) | 9 | 0.736 | 33.3% |
| [0.8, 0.9) | 3 | 0.854 | 0.0% |
| [0.9, 1.0] | 1 | 0.929 | 0.0% |

## Interpretation and use

Confirmed diagnosis: the residual target is rare, score ranking contains signal, but the frozen decision tail is poorly selective; 79.0% of attempted residual corrections were harmful. The probabilities of harmful and helpful corrections overlap substantially. The small helpful count and five-root design do not support regime-specific thresholds or a causal syndrome explanation.

This audit is retrospective and uses the previous final-development outcomes only to explain that prior run. Its findings were not used to alter the new sprint's frozen configuration, candidates, threshold grids, gates, seeds, or primary endpoint. The new sprint still requires execution in the user's PowerShell because the managed environment did not retain its detached child process.

Machine-readable results and per-root/per-regime tables: `prior_hybrid_audit/FAILURE_AUDIT.json`. Recompute: `python outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/audit_prior_hybrid_failures.py`.
