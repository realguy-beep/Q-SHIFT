# Phase 5E findings

Development-only audit; Stage 2 and all confirmatory data were untouched. The prior Phase 5D disagreement matrix was accumulated across regimes and therefore repeated as a pooled matrix; Phase 5E recomputes separate matrices.

## Graph audit

| ID | Parameters | edges | edge-weight signature | DEM hash |
|---:|---|---:|---|---|
| 0 | [0.001, 0.001] | 142 | 8c3ef0fff10a | 955fe2cb4cc1 |
| 1 | [0.001, 0.003] | 142 | 65b5aaaece54 | e52a6d13c1e5 |
| 2 | [0.001, 0.006] | 142 | d5ff763841bc | 94f8dbf675c0 |
| 3 | [0.003, 0.001] | 142 | 6b8eda8b8da8 | 5e9161d22b88 |
| 4 | [0.003, 0.003] | 142 | 2d23fcb8e295 | 9d2b75aa2bf8 |
| 5 | [0.003, 0.006] | 142 | 2a424b0d4358 | 8cf1dc393d6d |
| 6 | [0.006, 0.001] | 142 | 785f534ace7d | cfa9d0f5e193 |
| 7 | [0.006, 0.003] | 142 | 9d69b7525168 | 3df9e388c0e9 |
| 8 | [0.006, 0.006] | 142 | f87d771c51ad | 5204e1ab17ca |

All nine graph signatures and DEM hashes are distinct; several prediction behaviors are equivalent on sampled syndromes but graph construction is not identical. Zero sampled disagreement is evidence only for those sampled distributions.

## Per-regime performance

### data_heavy: 30000 shots

| Decoder | Errors | LER |
|---:|---:|---:|
| 0 | 430 | 0.014333 |
| 1 | 434 | 0.014467 |
| 2 | 471 | 0.015700 |
| 3 | 404 | 0.013467 |
| 4 | 430 | 0.014333 |
| 5 | 434 | 0.014467 |
| 6 | 418 | 0.013933 |
| 7 | 405 | 0.013500 |
| 8 | 430 | 0.014333 |
### nominal: 30000 shots

| Decoder | Errors | LER |
|---:|---:|---:|
| 0 | 150 | 0.005000 |
| 1 | 146 | 0.004867 |
| 2 | 147 | 0.004900 |
| 3 | 155 | 0.005167 |
| 4 | 150 | 0.005000 |
| 5 | 150 | 0.005000 |
| 6 | 161 | 0.005367 |
| 7 | 154 | 0.005133 |
| 8 | 150 | 0.005000 |
### measurement_heavy: 30000 shots

| Decoder | Errors | LER |
|---:|---:|---:|
| 0 | 66 | 0.002200 |
| 1 | 64 | 0.002133 |
| 2 | 57 | 0.001900 |
| 3 | 82 | 0.002733 |
| 4 | 66 | 0.002200 |
| 5 | 66 | 0.002200 |
| 6 | 86 | 0.002867 |
| 7 | 82 | 0.002733 |
| 8 | 66 | 0.002200 |

Calibration selected indices: {"data_heavy": 3, "nominal": 0, "measurement_heavy": 1}. A single global fixed candidate selected: 0. Calibration used three roots/regime; rankings remain uncertain.

## Replicated schedule summaries

| Schedule | Policy | LER |
|---|---|---:|
| stationary | pooled_fixed | 0.004557 |
| stationary | best_global_fixed | 0.004774 |
| stationary | calibrated_regime_policy | 0.004774 |
| stationary | regime_matched | 0.004774 |
| stationary | hindsight_diagnostic | 0.003689 |
| stationary | adaptive_ml | 0.004557 |
| stationary | adaptive_utility | 0.004557 |
| slow | pooled_fixed | 0.011068 |
| slow | best_global_fixed | 0.010959 |
| slow | calibrated_regime_policy | 0.010851 |
| slow | regime_matched | 0.010308 |
| slow | hindsight_diagnostic | 0.009006 |
| slow | adaptive_ml | 0.011068 |
| slow | adaptive_utility | 0.011068 |
| rapid | pooled_fixed | 0.008138 |
| rapid | best_global_fixed | 0.008247 |
| rapid | calibrated_regime_policy | 0.008681 |
| rapid | regime_matched | 0.008898 |
| rapid | hindsight_diagnostic | 0.007595 |
| rapid | adaptive_ml | 0.008138 |
| rapid | adaptive_utility | 0.008138 |
| random | pooled_fixed | 0.008572 |
| random | best_global_fixed | 0.008572 |
| random | calibrated_regime_policy | 0.008464 |
| random | regime_matched | 0.009115 |
| random | hindsight_diagnostic | 0.007595 |
| random | adaptive_ml | 0.008572 |
| random | adaptive_utility | 0.008572 |

## Decision

Recommendation: **B. Redesign decoder bank or noise-model representation before investing further in switching.** Decoder correction differences are real but sparse and regime rankings conflict with the preselected regime-matched IDs. The regime-matched mapping and adaptive ML are not guaranteed optimal. The hindsight diagnostic is intentionally optimistic. Four development replicates/schedule with short schedules do not establish superiority. The current bank has nine distinct DEM/weight graphs, so observed equivalences are decoding-decision equivalences on sampled syndromes rather than duplicate graph construction.

No confirmatory experiment was run. Stim only models Pauli channels here; correlated/burst noise was not added in this sprint.
