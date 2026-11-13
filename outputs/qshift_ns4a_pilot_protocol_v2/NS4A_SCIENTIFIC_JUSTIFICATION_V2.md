# NS-4A Scientific Justification V2

**Document-only prospective rationale. No outcomes, performance estimates, samples, or decoder runs were consulted or generated.**

## Scope decision: keep the two noise questions separate

NS-4A should stay focused on Pauli-composition settings and the Phase 3A synthetic spatial-burst mechanism. Native gate/measurement rate asymmetry is a different intervention and belongs in a separate protocol.

| Design candidate | Scientific question | Model and information-parity implications | Interpretability |
|---|---|---|---|
| A. Native rate asymmetry | How does reliability change when post-Clifford gate depolarization and measurement-flip probabilities move among the three documented rate pairs? | Uses Phase 4C's native Stim depolarizing and measurement channels and its own DEM-conversion path. A new comparator-selection and model-identity plan is needed. | Clean gate-versus-measurement rate question, but “data-heavy” must not imply that only data-qubit gates are noisy. |
| B. Pauli composition plus spatial burst (NS-4A) | How do categorical Pauli-axis composition and an explicitly injected cross-location pair fault affect a decoder comparison? | Uses Phase 2B's categorical channels plus Phase 3A's burst extension. The two decoder arms must receive the same concrete DEM and declared provenance; the alias-collision guard must remain active. | Two interpretable mechanisms, but the retained six cells are a finite, incomplete factorial. They do not estimate the Pauli-bias-by-burst interaction. |

Combining A and B now would introduce a third factor, a second native noise construction, and a different DEM approximation path. It would make a modest feasibility study harder to interpret and require new information-parity and compatibility work. A full cross would have 3 rate pairs × 3 Pauli compositions × 4 burst levels = 36 cells, before roots and decoder arms; the current six cells intentionally do not claim that design. Keep A as a separately scoped future study, not a hidden extension of NS-4A.

## Source-supported generator facts

- Phase 4C uses Stim surface_code:rotated_memory_z, distance 3, five rounds, with native after_clifford_depolarization and before_measure_flip_probability. Its three rate pairs are gate/measurement (0.006, 0.001), (0.003, 0.003), and (0.001, 0.006). “Data-heavy” names a relative gate-versus-measurement rate, not a data-only fault location.
- Phase 2B exposes balanced, x_biased, and z_biased Pauli composition. Its categorical one-qubit channel partitions gate fault mass among X/Y/Z; its two-qubit categorical channel partitions mass across the ordered 15 non-identity Pauli pairs. The documented composition does not change total gate mass or measurement probability. Distinct gate locations are not made cross-correlated by that channel.
- Phase 3A adds CORRELATED_ERROR X8 X10 after each MR boundary. The per-boundary event is an explicit synthetic common-cause pair fault, independent across five boundaries. Its source checks the detector and observable counts against the Phase 2B base. That count check alone does not prove detector order or DEM semantics.
- The Phase 3A matching helper converts with decompose_errors=True, approximate_disjoint_errors=True; its own comment identifies categorical PAULI_CHANNEL_2 as requiring the approximation. The Phase 4C Stage 1 source uses decompose_errors=True for the native depolarizing generator without setting that option. This supports keeping these generator families separate here.

No DEM conversion, alias-guard invocation, sampler call, stochastic check, training, or decoder comparison was performed for this revision. The cited source path supports the proposal's parameterized generator, not end-to-end validity at each proposed probability. A future, separately authorized deterministic preflight must check conversion success, detector/observable IDs and order, graph compatibility, exact assumed-model provenance, and the unchanged alias guard before any sampling.

## Why the six cells are useful but limited

The six cells retain a small set of separate contrasts: three Pauli compositions at zero burst, then three burst probabilities under balanced composition. This allows an exploratory finite-set report of the two mechanisms without pretending that the interaction is measured. It leaves out biased-plus-burst cells and cannot answer whether the burst effect changes under X or Z bias. Results must be reported cell-by-cell and as the predeclared equal-cell-weighted finite-set estimand; they must not be generalized to a population of physical devices or to untested burst locations.

## Strong fixed comparator and its uncertainty

A static PyMatching comparator is necessary because a weaker or nominal-only baseline could overstate the value of an alternate decoder. The revised proposal selects one PyMatching configuration from a predeclared 12-member grid: six assumed-model families corresponding to the six evaluation cells, crossed with ordinary and correlation-enabled modes. It uses separate selection roots from every one of the six conditions and the same equal-condition weighting as the primary estimand. The selected decoder is one global configuration and is never switched by cell at evaluation.

This is an appropriately demanding comparator **within that finite candidate grid and finite target set**. It is not proof of the globally strongest static decoder. It may miss other DEM assumptions, burst patterns, weights, or decoder configurations. Selection uses only 64,000 calibration/selection shots and eight independent roots per cell; a 12-way ranking may be unstable. Report every candidate's selection score and bootstrap rank frequency, plus ties. If rank stability is weak, describe the selected baseline as uncertain and limit interpretation; do not select a replacement from evaluation outcomes.

## Why retain 304,000 shots and no automatic expansion

The 240,000 evaluation shots and six-by-ten root structure stay unchanged. The 64,000 selection shots are rebalanced over all six conditions (eight roots/cell, 1,333 base shots/root, 16 deterministic extra shots) so the selected static comparator targets the same equal-cell estimand. The lower per-cell selection count is a tradeoff for broader condition coverage. The total remains 304,000 and is not a power claim.

A favorable root-level interval is an exploratory feasibility signal only. It cannot be described as confirmation or used to trigger an automatic larger run. At most it can support a separate supervisor review of whether another protocol is warranted. Stage 5 and the sealed independent-test boundary remain untouched.
