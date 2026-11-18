# Claude handoff — interim research checkpoint

This is an interim advisory note from isolated branch `codex/qshift-independent-research-v1`. The current research checkpoint is not an integration request or a performance claim.

## Most useful finding

The proposed correlation-mechanism follow-up requiring a non-approximated DEM cannot be implemented for Phase 2B's categorical `PAULI_CHANNEL_2` circuits through Stim's circuit-to-DEM API. A deterministic check failed on all six basis/composition conditions because Stim requires `approximate_disjoint_errors=True`. That conversion check itself generated no shots. A later BP+LSD development screen sampled 30,000 original-circuit events while both decoders used the same approximate DEM; it is described below. Do not replace the channel with independent Pauli faults and keep the same hypothesis.

## Prior Q-SHIFT evidence

- The 720,000-shot correlation-mode development pilot already exists and was independently rescored. Correlated mode made 3,349 versus 3,532 pooled-fixed errors, but its primary interval did not meet the preregistered practical margin and two same-name strata were worse. This supports a condition-dependent association only.
- The existing uncertainty-selection review reports no-go results, including weak calibration-utility prediction and a below-chance current-syndrome signal.
- The exact categorical reference is validated on tiny toys. Full d=3 enumeration covers 2^609 fault assignments and is infeasible.
- A new generic loopy sum-product Bethe prototype passed a hand tree control but had LER 0.057354 versus exact MAP 0.002646 on one exact toy, and only matched the other toy. It is stopped before circuit evaluation.
- A paired BP+LSD screen on 5,000 distance-3 circuit samples in each of six Phase 2B conditions found 321 errors per tested LSD variant versus 138 for correlation-enabled PyMatching. All returned fault estimates reproduced their observed detector syndromes, and BP+LSD was worse in every condition. The screen uses one approximate DEM threshold and one fixed min-sum/LSD configuration; treat this as a negative development result, not a general BP+LSD conclusion.
- The exact-categorical sampler instrumentation was validated on synthetic channels and independently crosschecked against unmodified Stim circuits (max absolute standardized LER difference 0.701). A global fivefold odds tilt gave direct/weighted agreement, but in 16 replicates its six-condition macro SD was 12% higher; results varied substantially by stratum. It is a correct weighting framework, but this proposal is not a robust efficiency gain and should not be integrated as such.
- A forward-KL cross-entropy proposal built from weighted failure-conditioned categorical marginals also failed its predeclared variance gate in all six fresh validation conditions; several strata had very low failure-weight ESS. Do not tune it on those validation outcomes. A future rare-event proposal likely needs joint fault structure/progress, with a new independent validation split.
- Same-resource memory-basis analysis of two independent exact circuit sample sets supports matching the stored logical basis to known bias: 80.6% fewer failures for X-memory under X bias and 91.0% fewer for Z-memory under Z bias; balanced noise showed no meaningful difference. This is a static known-profile configuration baseline only and does not establish adaptive tracking or scalability.
- A d=5/9-round extension showed the same alignment direction under X/Z bias with 36×–45× lower observed LER, using matched 64-qubit/216-detector resources. Each aligned cell had six failures in 50k shots, so absolute rates remain coarse; this is not a threshold result.
- Intermediate d=3 bias ratios add a static configuration baseline: at 2:1, the matched memory basis had 26–35% fewer errors; at 5:1, it had 68–76% fewer. The data do not pinpoint a crossover or validate runtime adaptation.
- A d=7 (13-round) extension under known 10:1 bias preserved matched circuit resources (118 qubits, 624 detectors, 2,184 two-qubit channel pairs) and the same direction: aligned LER 5/500k under X bias and 3/500k under Z bias, versus 1,009 and 1,227 mismatched failures. Exact rate-ratio intervals remain broad because aligned counts are sparse. This is stronger finite-distance static co-design evidence, but it does not validate unknown-profile adaptation or give a threshold.
- qecsim fixed-χ=16 planar MPS beat qecsim MWPM at d=3 and d=5 on ideal-syndrome IID depolarizing samples at p=.05 (123 vs 206 and 30 vs 92 failures in 5,000 paired shots). It cost 13.74 ms/sample at d=5 versus 0.507 ms for the Python MWPM path. Treat this as a promising code-capacity result only; repeated noisy-circuit compatibility is untested and latency is high.
- A frozen two-class detector-only LDA trained on d=3 ratio-10 profiles generalized to ratio 2/5/10 and distances 3/5/7. At ratio 2, direction accuracy with 500 calibration shots was 94.9%, 99.3%, and 99.35%; at ratios 5 and 10 it was 100% on the tested windows. A separate balanced-vs-biased three-class model did not generalize well to moderate bias, so magnitude detection remains a different unresolved task.
- The frozen classifier was evaluated end to end on independent d=3 calibration and logical streams: with 500 detector shots per job it reduced equal-prior LER versus fixed Z by 16.6% at ratio 2, 52.4% at ratio 5, and 71.7% at ratio 10, with cluster-bootstrap intervals below zero for policy-minus-fixed LER. This is a synthetic development result under stable, exactly specified profiles. Calibration overhead, drift, model mismatch, and hardware transfer remain untested. One initial implementation pass inverted the score-to-basis sign; it is explicitly preserved as invalid and excluded. The corrected code checks training-label polarity.
- The direct LER comparison is per logical shot. Each 100-shot selected-memory batch used a separate 500-shot calibration window, while static Z required no calibration; this test did not equalize total circuit-shot cost or evaluate amortization across longer stable runs.
- A further rate-shift check retained 12.2/50.6/71.0% LER reductions versus static Z at ratios 2/5/10 when calibration stayed at p=.003 and logical runs doubled to p=.006, with bias direction unchanged. All arms used approximate DEM threshold .004 because .0018 could not convert the high-rate channels. This only demonstrates limited stable-direction robustness; it does not test an X↔Z change point or hardware drift.

## Suggested next implementation

If Claude chooses to explore native categorical inference, begin with a new region-graph or variable-elimination prototype. Keep every local Pauli outcome mutually exclusive. Validate joint syndrome/logical posterior values against exhaustive exact references on at least two cyclic and one tree factor graph. Record convergence, posterior error, induced width, and memory. Stop if exact small-case performance is not reliable. This is a feasibility suggestion, not a claim of novelty.

## Avoid

- Repeating the already completed correlation pilot or fitting a selector to its inspected outcomes.
- Advancing the tested BP+LSD configuration without a mechanistic correction; its fixed development comparison was worse than the strong matching baseline in all six conditions.
- Calling correlated matching maximum-likelihood decoding.
- Presenting the Stage S BP+OSD figures as independently verified. Stage S artifacts were not present in published `main`, and Claude's branch was not inspected.
- Claiming 99.99% reduction from current finite-distance results. With baseline LER 0.005, the candidate ceiling would be 5e-7 and approximately 5,991,464 zero-error IID shots would be needed for a one-sided 95% bound at that ceiling.

## Status and reproduction

`EXPERIMENT_RESULTS.md`, `FAILURE_ANALYSIS.md`, `LITERATURE_SURVEY.md`, and `FUNDAMENTAL_LIMITS.md` contain scope and limits. Reproduce the exact sample-count calculation with `python3.12 outputs/independent_research_v1/zero_failure_bounds.py`. The BP+LSD fixed-seed development run can be reproduced with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bplsd_feasibility.py`. Reproduce exact-channel importance weighting with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_importance_sampler.py` and its `--replicates 8 --shots 5000` options; crosscheck the direct sampler with `categorical_sampler_crosscheck.py`.

Reproduce the distance-7 known-profile extension with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_alignment_distance7.py`. The fixed-bond MPS screen is `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_truncated.py`.

The detector-only bias estimator and cross-strength checks are reproduced by `bias_identification.py`, `bias_strength_identification.py`, and `bias_binary_cross_strength.py`. The direct frozen-policy validation is `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_end_to_end.py`.

A sample-specific oracle ceiling further limits selector-only proposals for the existing correlation pair. It could choose the correct output on at most 763 uncorrelated-only failures out of 3,532, leaving 2,769 errors, so the observed ceiling is a 21.6% relative reduction. Both modes fail together on those 2,769 samples. A new decoder needs complementary corrections on shared failure cases.
