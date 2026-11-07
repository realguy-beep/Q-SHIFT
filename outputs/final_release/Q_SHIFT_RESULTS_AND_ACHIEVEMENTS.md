# Q-SHIFT Results and Achievements

## Overall finding

The project built a reproducible simulation prototype for comparing fixed, condition-calibrated, and detector-adaptive decoding. Adaptive superiority is not established. Calibration helped versus nominal fixed matching in a measurement-heavy condition, but Phase 4C Stage 2 found no equal-regime advantage against pooled fixed.

## Verified phase record

| Phase | Evidence and result | Interpretation |
|---|---|---|
| Starter audit | 150,000 legacy rows, 8 detector bits, 61 unique patterns | Repeated rows undermine split validity; conversation-only classifier results are not decoder evidence. |
| Phase 1 | Reported recognition 94.4%; guarded adaptation made zero switches and tied fixed | Recognition alone did not improve decoding. Report and JSON disagree on per-regime totals. |
| Phase 2 | 10 seeds, 6 conditions, fixed and specialist PyMatching | Validation chose fixed in all 60 seed/condition choices; no specialist passed its gate. |
| Phase 3A | 36,000 corrected pilot shots; X specialist 2,520 vs fixed 2,528 | Unadjusted p=.0386; multiplicity-adjusted p≈.463. v2-v4 reuse pilot seeds; v1 is excluded. |
| Phase 3B | 20 roots, 600,000 X-biased paired shots | Fixed 43,673 vs specialist 43,675; McNemar p=.9374. Pilot gain not replicated. |
| Phase 4A | 600,000 measurement-heavy shots | Fixed 1,118 vs calibrated 940; discordances 80/258; p=5.600789e-23. Static only. |
| Phase 4B | 20 roots, 600,000 measurement-heavy shots | Fixed 1,165 vs calibrated 1,008; discordances 99/256; p=3.73072e-17. Audit PASS WITH DEVIATION: fresh templates used instead of planned reuse. |
| Phase 4C Stage 2 | 60 roots, 1,800,000 paired held-out shots | Calibrated 12,435 vs pooled 12,407; equal-regime difference=+0.00001556; seed-bootstrap 95% CI [-0.00004889,+0.00007667]; sign-flip p=.66658. |
| Phase 5 v3 | 7 exploratory schedules, 61,440 paired shots | Utility adaptive 435 vs pooled 425; ML adaptive 441 vs pooled 425. Development only. |
| Phase 5E executed audit | 4 schedule families x 3 repeats x 12 x 256 = 36,864 dynamic shots | Adaptive-labelled paths stayed at pooled decoder #1, zero switches, 298 errors each, tied with pooled. |

## Phase 5E count reconciliation

Executed runner and JSON agree on 4 dynamic families x 3 repetitions. Pairwise disagreement sampling was 6 x 5,000 per regime (30,000 per regime; 90,000 total). Calibration used 45,000 shots; stationary evaluation used 90,000; dynamic evaluation used 36,864. The experiment log instead says 7 families, 4 repeats, and 90,000 pairwise shots per regime. Those numbers conflict with source/JSON and are not used. In the Phase 5E runner, `adaptive_utility` shares the ML choice path. Hidden-regime and hindsight diagnostics use unavailable test information and are not deployable methods.

## Achievements

- Stim surface-code simulation with detector and logical-observable output; nine-model PyMatching bank.
- Detector-only model calibration and a causal estimator/controller with pooled-fixed fallback.
- Paired evaluation, seed-level uncertainty, frozen baseline selection, reproducibility manifests, and independent audits of saved predictions.
- Evidence that noise recognition and decoder specialization are distinct: model weights can differ without changing corrections, and changed corrections do not guarantee improvement.
- Negative findings, protocol deviations, and reporting defects preserved rather than removed.

## Evidence boundary

All results are simulated. Phase 4C Stage 2 predictions were independently re-decoded, but calibration samples were not saved, so fitted choices cannot be fully reconstructed. There is no hardware integration, latency test, or confirmatory adaptive test.
