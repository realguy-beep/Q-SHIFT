# Next-method recommendation

## Decision: stop this particular scalar-burst adaptation setting

Do not spend the next development cycle refining only the detector-only estimate of this one burst probability with the expectation of a material logical-error reduction. The 45-feature model finds more burst information than the 40 detector marginals, but per-root estimates remain near `0.008`; changing the regularization objective barely affects held-out calibration error. Even the privileged true-`p` matcher differs from the pooled matcher on only 10 of 80,000 nonzero-condition predictions. A much better `p_hat` alone cannot help rows on which the decoder's logical prediction is already invariant to `p`.

This recommendation selects **“stop this particular burst/noise setting and select a separately justified research direction.”** It does not reject detector-only adaptation in general, and it does not claim that a new decoder will improve performance.

## Separately justified direction

If further research is pursued, first define a noise family in which the correlated events are not already captured as five graphlike pair edges—for example, physically motivated events with multi-detector support or temporally coupled burst patterns. The prospective decoder must preserve that event structure rather than reduce it to independent pair weights. Then establish, on deterministic model construction and saved development-only data, that:

1. detector-only summaries distinguish the prespecified noise regimes on independent calibration roots;
2. an oracle/model-informed decoder changes a nontrivial, preregistered fraction of decisions relative to a strong static PyMatching baseline;
3. the new decoder receives no more noise information than the deployable estimator-assisted arm (with any oracle arm clearly marked privileged); and
4. only after those feasibility gates pass, a separate paired, root-level development evaluation is designed with frozen conditions, allocation, uncertainty method and stop rules.

These are design criteria, not authorization to implement or execute such a study. The current pair-burst mechanism is graphlike, so choosing a hypergraph or other more expressive decoder solely because it is more complex would not be justified by this diagnostic.

## What remains unproven

- Whether a sufficient-statistic, likelihood, or hierarchical detector-only estimator can materially improve `p` estimation on new independent calibration batches.
- Whether a different correlated-noise family would alter logical decoder decisions enough to create headroom.
- Whether another decoder would lower LER under any such family.
- Any hardware performance or generalization beyond this simulated circuit and saved development partitions.

No 50% improvement is promised. No new sampling or training is recommended on the current burst setting. The appropriate immediate next action is to preserve these negative mechanistic findings and require a separately reviewed noise-model rationale before opening a new experiment.
