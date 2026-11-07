# Statistical and methodological audit

## Independent units and estimands

For stochastic circuit simulations, Stim seed roots or declared root clusters—not individual correlated shots—are the relevant replication units. Paired shotwise counts and exact McNemar tests are useful descriptive summaries because decoder predictions share the same detector and observable sample. They do not replace root-level uncertainty. Studies with 5 or 20 roots per condition have that many independent units even when they store hundreds of thousands of shots.

## Principal results

| Study | Paired scope | Primary inference / interpretation |
|---|---|---|
| Phase 2A | 20 roots × 3 regimes; 600k shots | Calibration-selected per-regime equals global fixed exactly: 4,192 vs 4,192 errors; root-cluster CI [0,0], sign-flip p=1.0. Twenty roots/regime. |
| Phase 2B | 20 roots × 6 basis-regime cells; 1.2M shots | Regime-informed calibration and basis-specific fixed predictions coincide; 5,532 vs 5,532 errors; CI [0,0], p=1.0. Six-cell primary, root is cluster. |
| Phase 4A | 20 roots each of 3 regimes; 1.8M shots | Measurement-heavy calibrated vs nominal: 940 vs 1,118 errors, candidate-only 80/fixed-only 258, exact McNemar p=5.600789×10^-23, 19/20 seed wins. Positive static result, specific to nominal baseline. |
| Phase 4B | 20 fresh roots; 600k measurement-heavy shots | Calibrated 1,008 vs nominal 1,165, candidate-only 99/fixed-only 256, McNemar p=3.730723×10^-17, 20/20 roots favor calibrated. Static replication; fresh-template deviation from protocol. |
| Phase 4C Stage 2 | 20 roots × 3 regimes; 1.8M shots | Calibrated-minus-pooled LER +0.00001556; 95% root-stratified cluster bootstrap [-0.00004889,+0.00007667]; frozen sign-flip p=.66658333. No detected improvement. |
| Correlation pilot | 12 roots × 6 strata; 720k shots | Pooled correlation-enabled minus uncorrelated ΔLER=-0.00025417; 95% root-stratified CI [-0.00035000,-0.00016250]; sign-flip p=.00083999. The frozen practical criterion was -0.0002 with CI upper ≤ -0.0002; CI gate failed. Four strata favorable, two harmful. |
| Multi-distance headroom | 5 roots per cell; 12 banks, 36 bank-regime cells | Calibration-selected specialist differed from pooled in 14 cells: 7 lower, 6 higher, 1 equal evaluation LER. One cell cleared its local gate, but no repeated regime pair at two distances; global NO-GO. |
| Phase 2C forest pilot | 4 roots × six cells; 120k shots | Exploratory paired prediction comparison. Forest reference 2,579 errors versus 628 for matched PyMatching. Shot-level p-values are descriptive; only four roots/cell. |
| Gate/online feasibility | 24-root saved paired dataset; online trigger 100 validation schedules | LOO gate comparisons are exploratory on one dataset; effect CI includes zero. Trigger false-update estimate 2/100, 95% interval .24%–7.04%, so a ≤5% schedule-wide target is not certified. |

## Bias, multiplicity, and selection

- Same-sample hindsight per-shot/per-regime oracles are selected and evaluated using the same labels. Their bootstrap intervals quantify cluster variation in an optimistic oracle statistic, not independent performance of an adaptive selector.
- The nine-candidate and 36-cell feasibility analyses have many comparisons. Candidate rankings with five calibration roots/cell are unstable; the official gate uses selection stability and distance replication, not unadjusted point winners. The one local passing cell was discovered in a development gate and is not confirmatory.
- The correlation pilot’s primary comparison is a single pooled fixed decoder ablation. It is statistically below zero, but practical effect criterion and uniform-condition checks were not met; the 4/6 favorable-stratum count must remain exploratory.
- Phase 4A/4B very small exact shot-level McNemar p-values can coexist with only 20 independent roots. They support a strong paired difference for that exact static, on-grid, nominal-baseline comparison, not general adaptation.
- Phase 4C p=.6666 is failure to detect improvement, not proof of equivalence. No equivalence claim is made.
- No Phase 2–5 cross-study pooling is valid: code/noise/basis, candidate sets, sample procedures, and estimands differ.

## Saved-array and test-label audit

Calibration labels are not model inputs in the detector-marginal Phase 4A/4B fit; fitting uses detector marginals, and labels support audit/validation. Phase 2A/2B calibration selection explicitly uses calibration outcomes, but the final test outcome arrays are used only for evaluation and retrospective oracle diagnostics. Stage 2 choices are preserved in checkpoints; missing calibration arrays prevent independent refitting but saved test arrays and predictions were independently re-decoded previously. In this audit, labels are used only to recompute error counts, paired errors, and clearly marked hindsight diagnostics; no new selector or decoder is tuned on test outcomes.

