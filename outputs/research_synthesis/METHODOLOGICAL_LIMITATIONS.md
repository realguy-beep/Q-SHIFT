# Methodological limitations and claim boundaries

## Circuit scale and physical scope

Core studies use Stim simulation, mainly distance-3 repetition memory (three rounds) or distance-3 rotated surface-code memory (five rounds). Phase 2B includes X and Z memory; main adaptation results do not establish code-distance scaling, long-run performance, logical gates, or generality across circuits. No processor, real-time control path, firmware, cryogenic system or hardware decoder was integrated.

Most dynamic studies switch conditions between shots or blocks. Each individual multi-round circuit still uses a stationary noise model. This does not test drift within a syndrome-extraction run, leakage trajectories, non-Markovian effects, coherent errors or correlated bursts.

## Noise-model and decoder fidelity

Phase 1/2 noise insertion applies single-qubit Pauli channels to gate participants and, in some conditions, readout flips; this is not a fully correlated two-qubit gate-error model. Phase 2B samples categorical Pauli noise but exports its DEM with approximate disjoint errors enabled. A DEM is a list of independent error mechanisms, and the documented conversion can approximate custom categorical channels. Correlated matching can use decomposition hints but is still constrained by that DEM. Phase 4A/B uses native DEPOLARIZE1/2 plus measurement noise; do not attribute Phase 2B's approximation to those later studies without checking the circuit.

PyMatching outputs a logical-observable frame prediction from the supplied graph. Residual error is sampled observable XOR predicted flip. Most saved data are predictions, not physical correction chains applied to a live quantum state. Say “logical correction estimate,” not “the decoder physically fixed the qubit.” Minimum-weight matching is not generally maximum-likelihood logical decoding.

Phase 2C's random forest predicts an observable label from finite training samples. It does not calculate the exact conditional posterior for full circuit histories or have an approximation-error bound. Its underperformance cannot isolate DEM approximation as the cause.

## Statistics, selection and multiplicity

The seed root or independently generated schedule is the main generalization unit; many shots do not create many independent noise models. Shot-level paired McNemar tests are useful for discordance but should not substitute for root-cluster inference. Phase 2C's four roots/cell are particularly weak for generalization.

Retrospective test-best rankings and per-shot oracle selectors use the labels they score and must remain upper-bound diagnostics. Multiple decoder comparisons require their predeclared correction families. The starter CSV has severe repetition and missing provenance. Phase 3A corrected versions are repeated checkpoints on the same raw samples, not replications. Phase 5 early v1 output had a policy-label mapping defect and is superseded by corrected versions.

A nonsignificant p-value does not establish equivalence or prove that adaptive and fixed decoding are the same. For example, Phase 4C's p=.6666 and confidence interval crossing zero indicate no detected improvement; whether practically important gains are excluded depends on a predeclared effect margin and interval width. Future null claims need a smallest effect size of interest and a powered equivalence or interval analysis.

Selection among nine candidates on calibration data can overfit calibration noise. Independent validation/test protects the final comparison only when all choices and selection rules are frozen beforehand. Test-best candidate counts and oracle diagnostics are not valid policy estimates.

## Integrity and evidence gaps

- Phase 4A's three Markdown hash mismatches were resolved by an independent reaudit as documentation-only; scientific evidence passed.
- Phase 4B test predictions were independently re-decoded. The audit returned PASS WITH DEVIATION because fresh templates were generated despite protocol text specifying reuse. Records support but do not cryptographically prove the full freeze chronology.
- Phase 4C Stage 2 has 60 independently re-decoded checkpoints/1.8 million tests, but calibration detector arrays and scoring traces are absent. Calibration fitting cannot be independently refit. RNG rules were prospectively amended after the original freeze, so do not call it an unqualified preregistered experiment.
- Phase 2C's first seed inventory omitted six derived forest seeds; supplemental audit found no collision. A later analysis implementation correction did not change aggregates, but is an auditability caveat.
- Early Phase 1 aggregate report inconsistencies are documented; rely on audited reports and avoid reconstructing undocumented totals from obsolete summaries.

## Baseline comparability

Phase 4A/B compare calibration with nominal fixed matching and show a measurement-heavy benefit. Phase 4C compares against a stronger pooled development-selected model and finds no benefit. These results use different baseline strengths and estimands; do not pool them or summarize them as “calibration always works” or “calibration never works.”

## Supported statements

“In the specified simulated distance-3, five-round Z-memory measurement-heavy condition, detector-calibrated weights lowered LER versus nominal PyMatching in Phase 4A and a Phase 4B replication with a template-protocol deviation.” “A stronger pooled fixed comparison in Phase 4C found no significant improvement.” “The adaptive prototype uses causal detector information and a fixed fallback, but adaptive superiority has not been demonstrated.”

Unsupported: Q-SHIFT beats PyMatching; Q-SHIFT adapts on real hardware; the RF is an exact maximum-likelihood decoder; DEM approximation caused Phase 2B's result; Phase 4 proves adaptive improvement; Q-SHIFT improves thresholds; or distance-3 findings generalize to all codes/noise.
