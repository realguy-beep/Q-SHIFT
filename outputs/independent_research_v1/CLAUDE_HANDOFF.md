# Claude handoff — interim research checkpoint

This is an interim advisory note from isolated branch `codex/qshift-independent-research-v1` at commit `add2914`. It is not an integration request or a performance claim.

## Most useful finding

The proposed correlation-mechanism follow-up requiring a non-approximated DEM cannot be implemented for Phase 2B's categorical `PAULI_CHANNEL_2` circuits through Stim's circuit-to-DEM API. A deterministic check failed on all six basis/composition conditions because Stim requires `approximate_disjoint_errors=True`. No shots were sampled. Do not replace the channel with independent Pauli faults and keep the same hypothesis.

## Prior Q-SHIFT evidence

- The 720,000-shot correlation-mode development pilot already exists and was independently rescored. Correlated mode made 3,349 versus 3,532 pooled-fixed errors, but its primary interval did not meet the preregistered practical margin and two same-name strata were worse. This supports a condition-dependent association only.
- The existing uncertainty-selection review reports no-go results, including weak calibration-utility prediction and a below-chance current-syndrome signal.
- The exact categorical reference is validated on tiny toys. Full d=3 enumeration covers 2^609 fault assignments and is infeasible.
- A new generic loopy sum-product Bethe prototype passed a hand tree control but had LER 0.057354 versus exact MAP 0.002646 on one exact toy, and only matched the other toy. It is stopped before circuit evaluation.

## Suggested next implementation

If Claude chooses to explore native categorical inference, begin with a new region-graph or variable-elimination prototype. Keep every local Pauli outcome mutually exclusive. Validate joint syndrome/logical posterior values against exhaustive exact references on at least two cyclic and one tree factor graph. Record convergence, posterior error, induced width, and memory. Stop if exact small-case performance is not reliable. This is a feasibility suggestion, not a claim of novelty.

## Avoid

- Repeating the already completed correlation pilot or fitting a selector to its inspected outcomes.
- Calling correlated matching maximum-likelihood decoding.
- Presenting the Stage S BP+OSD figures as independently verified. Stage S artifacts were not present in published `main`, and Claude's branch was not inspected.
- Claiming 99.99% reduction from current finite-distance results. With baseline LER 0.005, the candidate ceiling would be 5e-7 and approximately 5,991,464 zero-error IID shots would be needed for a one-sided 95% bound at that ceiling.

## Status and reproduction

`EXPERIMENT_RESULTS.md`, `FAILURE_ANALYSIS.md`, `LITERATURE_SURVEY.md`, and `FUNDAMENTAL_LIMITS.md` contain scope and limits. Reproduce the exact sample-count calculation with `python3.12 outputs/independent_research_v1/zero_failure_bounds.py`. Run the prototype checks with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python -m unittest discover -s outputs/independent_research_v1 -p 'test_categorical_bp.py' -v` from the research worktree.
