# Open Freeze Decisions after Supervisor Review #8

No item below is approved by this review package. No experiment may start until relevant decisions are recorded, source/configuration hashes are frozen, an independent audit passes, and separate explicit authorization is issued.

## Scientific question and margins

1. Confirm ordinary MWPM as sole primary mode and event-minus-pooled-static as sole primary contrast; keep correlation-aware results secondary.
2. Decide if the practical absolute LER margin is 0.0001, 0.0002, 0.0005, another value, or if no meaningful practical margin can yet be justified. Provide a pre-data deployment utility/cost rationale. Current evidence does not justify exactly 0.0002.
3. Approve a stationary non-harm margin and its uncertainty rule independently of the primary efficacy margin.
4. Approve equal weighting of the four nonstationary schedules and separate treatment of stationary and measurement-mismatch strata.

## Circuit, schedules and identifiability

5. Preserve the d=3, five-round rotated Z-memory and `X8 X10` event unless a separately versioned review changes the scientific object. Freeze exact burst probabilities, step times, smooth schedule, transient duration, stationary probability, gate/readout model and p-grid before generation.
6. Decide whether one stationary point is enough for the stated robustness claim; if multiple are required, increase all relevant evaluation and tuning counts.
7. Approve the independent mismatch condition: burst p=.008, measurement p=.006 generated, estimator/decoder assumed .003, no mismatch flag to online controller, fresh independent roots.
8. Commission the deterministic DEM feature-expectation/Jacobian rank and conditioning check. Decide what condition number or profile collision makes burst p unidentifiable or too weakly identified. State explicitly that full-distribution identifiability is not established by mean-feature rank.
9. Confirm whether explicit correlation-aware mode is a secondary estimand and require source audit at both matcher construction and every decode call. Graphlike structure alone does not demonstrate incremental decoder benefit.

## Baseline, calibration and tuning

10. Approve primary pooled-static calibration: equal detector-shot mix across four primary strata, 1,000 shots/root; roots per stratum as budget option; 45 features; eleven-point grid 0 to .020 step .002; standardized mean-squared profile residual; SD floor .001; lower-p tie-break. If a different fit objective is desired, freeze before evaluation.
11. Approve template amount 6,000 shots/grid point and confirm model-specific profile templates can be reused from eligible development material. If reused, independently verify source/model compatibility and reduce the budget transparently; do not overwrite old data.
12. Approve tuning candidate spaces and tuning criteria for trailing window, EWMA, periodic and event methods; prohibit evaluation-based selection. Clarify whether schedule labels may be used only by offline tuning selection (proposed yes) while remaining hidden from online methods.
13. Decide whether to include the supervised label-selected static arm as a privilege-labeled secondary reference; it is not the detector-only primary comparator.

## Inference, budget and compute

14. Accept the conditional inferential target (one frozen shared template/calibration/tuning bundle) or fund independent outer bundles to include training/calibration randomness. One bundle cannot estimate between-bundle variability.
15. Review the stratified Welch stream-mean t interval and its finite-cluster limits. Decide minimum streams and sparse-discordance reporting gate. The distribution-free Hoeffding reference is too wide for the target margin; no interval method gives guaranteed useful finite-cluster coverage under the present sparse design without assumptions.
16. Choose budget A=486k, B=1.406M, a redesigned option, or stop. A is plumbing only; B is development variance/resource reconnaissance; C=10.666M is not justified and remains a future candidate only.
17. Choose deployment horizon H based on expected use (reported sensitivity points are H=160 and H=1,000), determine whether calibration/data-acquisition costs count in deployment CPU, and approve the proposed all-in CPU gate event ≤ pooled-static and event ≤ EWMA at H.
18. Approve runtime/RSS/storage caps and whether a separate resource preflight is allowed. Existing hardware context is not an end-to-end benchmark.

## Integrity and governance

19. Specify who certifies development-root separation from protected evaluation material without opening or revealing it.
20. Identify independent protocol, code, chronology, correlation-flag, statistical implementation and final artifact reviewers.
21. Approve a fresh development shot allocation; Pilot 2 budget was consumed and cannot silently be reused. No PR, merge, V2.4 modification, Stage 5 access or experiment authorization is included in this request.
