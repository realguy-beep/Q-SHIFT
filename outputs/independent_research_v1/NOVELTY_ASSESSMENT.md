# Novelty and overlap assessment

## Established directions with direct overlap

- **Per-syndrome ensemble selection:** directly established in peer-reviewed neural ensemble decoding. Q-SHIFT's local selector feasibility was also negative. A general claim of novel decoder routing is unsupported.
- **Confidence-gated selective decoding:** established in selective acceptance, adaptive-window decoders, and recent meta-decoder work. Q-SHIFT would need a materially narrower problem and a useful calibrated signal.
- **Belief-assisted/correlated matching:** established in peer-reviewed work and implemented by PyMatching. Q-SHIFT's 720,000-shot pilot is a context-specific ablation, not an algorithmic invention.
- **Tensor-network ML decoding and noise adaptation:** established under specified surface-code noise models. Full circuit feasibility and equal-resource comparisons remain open for Q-SHIFT.
- **Neural surface-code decoding:** broad family is established, with recent strong hardware-informed evidence. Q-SHIFT's existing CNN is development-only and inferior to PyMatching.
- **Bias-tailored code structures and distance scaling:** established code-design and threshold directions. Any gain requires separate qubit, round, and circuit resource accounting.

## Potentially useful but not yet novel

A native categorical factor graph could preserve mutually exclusive Pauli gate outcomes and avoid the approximate independent DEM representation. This is a methodological direction, not a novelty claim. Exact toy posterior tools already exist locally. The current sum-product prototype's poor one-qubit toy result shows that a naive Bethe approximation is inadequate. A contribution would require a validated, scalable inference method, a literature overlap review using accessible primary sources, and a fair strong-baseline comparison.

The practical use of an independent-root LER gate for correlation-aware decoding may yield an empirical systems result, but a 720,000-shot Q-SHIFT development pilot already exists and failed its practical-effect gate. Repeating it or presenting it as a newly discovered decoder would have no novelty.

Memory-basis alignment under known Pauli bias is established bias-aware code configuration, not a novel decoder. The new distance-3 measurements provide Q-SHIFT-specific matched-resource evidence (5.2×–11.1× lower LER in the aligned biased conditions), but novelty would require a new code/circuit schedule, a robust policy under bias drift, or a resource-aware scaling result. No such claim is supported here.

## Publication boundary

No publication-level novelty claim is justified by this expedition checkpoint. The current supported contribution is a negative feasibility result: the proposed non-approximated DEM follow-up cannot pass Stim conversion for Phase 2B's categorical `PAULI_CHANNEL_2` circuits, and an initial generalized sum-product Bethe approach failed an exact toy topology. External literature retrieval was partially blocked, so the broader novelty assessment remains provisional.
