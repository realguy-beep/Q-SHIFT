# Comparator set and fairness rules

## Arms

| Arm | Definition | Deployable | Information |
|---|---|---|---|
| A_nom | Nominal fixed PyMatching (correlations off), built from the nominal DEM | yes | nominal model |
| A_corr | Strong correlated PyMatching. q_dec and the correlation flag are selected on **val** per condition family | yes | nominal model + val selection |
| A_pool | Pooled detector-calibrated matching: one DEM re-weighted from pooled calibration detector rows (the Stage 5 / strong-fixed method) | yes | calibration detectors |
| L2_fix | Strong fixed BP+OSD (serial, product-sum, OSD_CS-10 or the val-selected search variant), static prior | yes | nominal model + val selection |
| L2_pool | L2 on a DEM re-weighted once from pooled calibration detectors (incl. the robust background scale) | yes | calibration detectors |
| L2_recal | Periodically recalibrated L2: refit every K blocks on the last W blocks' detectors, without change detection | yes | streaming detectors |
| ENS | Non-adaptive ensemble: per shot, the most likely prediction among {A_corr, L2_fix} by the decoders' own reported costs, or a majority of 3 where feasible | yes | as members |
| **Q** | Adaptive Q-SHIFT (`ADAPTIVE_ARCHITECTURE.md`) | yes | streaming detectors (+ labeled calibration shots **only if** every deployable arm gets the same shots) |
| Q0 | Ablation: Q's decoder family with its controller frozen after the initial calibration | yes | same as Q |
| O_true | Oracle: DEM from the true p and the true burst support | **no** (reference) | privileged |
| O_regime | Oracle regime label fed to Q's decoder map | **no** (reference) | privileged |

**S\*** is the best deployable static arm among {A_corr, A_pool, L2_fix, L2_pool, ENS}. It is selected **on val** by pooled val LER and frozen before eval. Q is compared against S\*, never against A_nom.

## Fairness rules

1. **Equal calibration budget.** Every calibrated arm (A_pool, L2_pool, L2_recal, Q, Q0) gets the same calibration rows per condition and the same streaming blocks.
2. **Equal information.**
   - If Q uses labeled calibration shots (needed for burst-flip resolution, see `ADAPTIVE_ARCHITECTURE.md`), the same labeled shots are available to A_pool and L2_pool. For those arms that means a labeled q-fit or support fit, as in Phase C.
   - Otherwise no arm gets labels.
3. **Equal decoder family where the question is adaptiveness.** G_ADAPT compares Q with Q0, which shares Q's decoders, so the adaptive contribution is isolated from decoder strength.
4. **Compute disclosed, not equalized by fiat.** Report CPU ms/shot for every arm. Q's advantage is reported both raw and against an arm with ≥ Q's compute budget (L2_fix with the higher-order search variant), to rule out "more compute" as the explanation.
5. **Oracles are references only.** They never enter S\* or any gate. Their only role is to bound the attainable gain (O_true − S\*) and the share captured by Q.
6. **Same rows.** All arms decode the same sampled detector rows (paired), as in every historical study.

## Attribution ablations (where an improvement comes from)

| Contrast | Isolates |
|---|---|
| L2_fix − A_corr | better inference (hypergraph vs matching) |
| L2_pool − L2_fix | calibration |
| Q0 − L2_pool | decoder selection without online adaptation |
| Q − Q0 | online adaptation |
| Q − O_regime | cost of regime-estimation error |
| O_true − Q | remaining information gap |

An apparent gain that disappears when labels or compute are equalized is reported as an **information or compute difference**, not as an adaptive gain.
