# Representation and information parity audit

The deterministic comparison uses two distinct DEMs derived from the same Q-SHIFT circuit settings:

1. BP parses `decompose_errors=False, approximate_disjoint_errors=True` (40 detectors, one observable, 448 mechanisms at burst p=.01).
2. PyMatching parses `decompose_errors=True, approximate_disjoint_errors=True` (591 error instructions in the benchmark output; decomposed correlated components are represented differently).

The original Stim circuit uses categorical mutually exclusive gate outcomes. Its DEM conversion applies Stim's disjoint-error approximation. The undecomposed DEM retains multi-detector mechanisms; the decomposed DEM adds separator-marked graphlike components and possible correlation structure. Neither DEM should be described as the exact categorical circuit distribution, and the two representations are not interchangeable.

The benchmark sets PyMatching `enable_correlations=False` at both graph construction and decode for ordinary matching, and `True` at both points for the explicit correlation arm. The selected five deterministic syndrome rows yielded identical outputs for those two modes. This establishes only those fixtures; it does not show that correlation-aware decoding never helps.

All arms use the same fixed circuit settings in this test; no arm receives a hidden true parameter unavailable to another. The comparison is still algorithm-plus-representation: BP is a logical-marginal factor graph on the undecomposed DEM; PyMatching is matching on a decomposed DEM. A future scientific study must either construct a common supported representation or explicitly label the native-representation comparison and include a representation ablation.

Further source semantics and prior parser audit: `../../inputs/ns1r/HAMLD_INFORMATION_PARITY.md` and `../../inputs/ns1r/HAMLD_DEM_SEMANTICS_AUDIT.md`.
