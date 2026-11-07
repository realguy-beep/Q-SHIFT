# Direction B — Controlled correlation-aware decoding comparison

## Question

For the existing controlled surface-code Pauli-noise families, does PyMatching’s correlation-aware two-pass decoding mode reduce logical-observable errors compared with ordinary matching when the DEM, matching weights, detector shots, and labels are otherwise identical?

## Established methods

The importance of correlations in surface-code decoding is established. In the CSS surface code, Y faults connect X- and Z-type syndrome effects; circuit faults can create multi-detector patterns that become correlated graph components after decomposition. Higgott et al.’s belief-matching and belief-find work explicitly uses circuit-level factor-graph information and reports a threshold increase for its specified model from 0.817(5)% for MWPM to 0.940(3)% for belief-matching ([*Phys. Rev. X* 13, 031007 (2023)](https://doi.org/10.1103/PhysRevX.13.031007)). Paler and Fowler developed a pipelined correlated-MWPM method and evaluated it on rotated, unrotated, and toric codes under depolarizing noise ([*Quantum* 7, 1205 (2023)](https://doi.org/10.22331/q-2023-12-12-1205)). PyMatching has a simpler correlated-matching option since v2.3: a standard pass is followed by correlation-conditioned reweighting and another matching pass ([official PyMatching documentation](https://pypi.org/project/PyMatching/)).

These prior works mean “correlations help decoding” or “use correlated matching” is not a novel algorithm claim. The project’s narrower, testable question is whether the specific decomposition correlations retained by Stim/PyMatching affect LER for the project’s categorical X-, balanced-, and Z-biased gate channels, when the exact same DEM weights and paired circuit samples are used.

## Why this is the best immediate direction

The existing Phase 2B bank constructs all models with `enable_correlations=True` at matcher construction and at decode time. Thus its 1.2 million paired held-out shots, despite rich provenance, contain no off/on ablation. The saved DEMs have hundreds of decomposition separators, so the feature is present rather than hypothetical. An off/on comparison can hold the Stim circuit, approximate DEM, edge weights, seeds, detectors, and observable outcomes fixed. This isolates decoder use of the available correlation metadata far better than comparing different weight models or different noise generators.

## Scientific limits

This does not test an adaptive policy, hardware calibration, all correlated-noise types, or an exact categorical-channel posterior. The generated Pauli-pair event is categorical within a gate, but Stim’s conversion to independent DEM mechanisms is approximate. A positive result would support the value of this software option under the tested approximation and conditions; it would not show that all physical correlations are captured. A null result would not show that correlations are irrelevant in general.

A recent October 2026 arXiv preprint reports distance-scaling failures for a standard correlation-reweighting rule and proposes regularization ([de la Fuente et al., arXiv:2610.26785](https://arxiv.org/abs/2610.26785)). It is a new preprint, not settled consensus, and its algorithm should not be conflated with PyMatching’s implementation. It is a reason to measure both accuracy and failure configuration patterns rather than presume correlation handling always helps.

## Feasibility

- **Reuse:** Very high; keep Phase 2B’s simulator, DEM construction, model weights, matched-shot sampling, paired statistics, and seed discipline.
- **Implementation:** Low-to-moderate; build two matchers from each same frozen DEM with correlation use off/on, confirm whether current PyMatching 2.4.0 accepts and applies both settings consistently, and rescore identical detector arrays.
- **Compute:** Low-to-moderate at d=3 and a bounded sample. Correlated mode makes an extra matching pass; runtime must be measured.
- **Measurability:** High for paired correction changes and residual logical-error differences. There may still be little headroom or sparse failures.
- **Competition value:** High. A simple diagram can show the same syndrome going through ordinary and correlation-aware matching, with an honest paired tally and uncertainty interval.
- **Novelty:** Low as an algorithm, modest as a carefully controlled, reproducible condition-specific comparison. Present as an investigation, not a new decoder invention.

## Recommended role

Select as the primary bounded feasibility pilot, with a fixed decoder as the practical comparator and a noise-informed DEM as a clearly labeled reference. If the effect is absent, retain the result and move to the code-distance operating-limits fallback rather than layering on an adaptive selector.

