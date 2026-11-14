# Research direction decision

## Current evidence

The method-landscape package contains deterministic theory for a specific synthetic distance-3 circuit: exact categorical feature expectations, finite-difference local identifiability, a continuous exact-circuit mean envelope, and one-sided e-process/delay constructions. It contains no measured detector-history accuracy, logical-error improvement, deployed controller behavior, or hardware evidence. Checkpoint 133's alpha crossing count was based on the wrong threshold and is superseded only by the new v1 correction.

## Four candidate tracks

| Track | Assessment | Decision |
|---|---|---|
| Deterministic theory/methodology paper | Some algebraic results are defensible under explicit synthetic-model assumptions; broad novelty is not established, several numerical certificates were not independently regenerated, and the checkpoint-133 correction must be incorporated. A narrow methods note could describe a finite-code certificate only after a clean independent derivation, source verification and literature review. No adaptive-decoder performance claim is available. | Not publication-ready now; preserve as a candidate, not a claimed contribution. |
| Bounded development-only estimator study | Scientifically useful to measure finite-history estimation, nuisance mismatch, threshold calibration and abstention. Must hold out seeds/parameters, compare to a pooled fixed decoder, and report estimation plus paired logical errors separately. | Most defensible next empirical question after review and a new authorization; do not run under this audit. |
| Adaptive decoder experiment | Generic syndrome-only estimation and adaptive matching weights are already established. Q-SHIFT's one-sided certificates do not solve state transitions, repeated false switches, physical-vs-model mismatch, DEM transfer, or decoder utility. | Not ready; controller HOLD. A separately versioned redesign is required before any adaptive experiment. |
| BeliefMatching feasibility | Distinct algorithmic comparison; it must remain separate from e-process theory and preserve identical information/DEM provenance. No results from this audit alter its status. | Continue only under its own current authorization and review gates; this audit supplies no performance support. |

## Closest prior work and novelty boundary

- Spitz et al., [“Adaptive weight estimator for quantum error correction in a time-dependent environment”](https://arxiv.org/abs/1712.02360), use syndrome-derived statistics to adapt matching weights and state a condition relating environmental drift time to error-correction-cycle duration and error rate. Generic online matching-weight adaptation is therefore prior art.
- Wagner et al., [“Pauli channels can be estimated from syndrome measurements in quantum error correction”](https://arxiv.org/abs/2107.14252), establish identifiability results for Pauli channels from syndrome data under code/noise conditions and give practical estimation methods. Syndrome-only noise identifiability is not a new premise by itself.
- Bhardwaj et al., [“Adaptive Estimation of Drifting Noise in Quantum Error Correction”](https://arxiv.org/abs/2511.09491), report syndrome-statistics sliding-window estimation, multi-frequency drift tracking, circuit-level simulations, and comparisons of estimated, ground-truth, and static decoder models (notably their Sections III–IV.5). Generic drift estimation/tracking and adaptive decoding are not novelty claims for Q-SHIFT.
- The package also records adjacent decoder switching work, which selects weak/strong decoders from reliability signals rather than estimating a physical noise cause. Switching as such is not novel.
- Sequential e-process theory supplies general statistical machinery; applying a known inequality to a synthetic detector statistic is not, by itself, a distinct quantum-decoding contribution.

A possible narrow contribution would need to show a rigorously useful, source-specific detector statistic with validated finite-sample operation, fair comparison to current adaptive-weight methods, and paired decoder utility. The present record has not done so. No defensible novelty claim beyond a candidate finite-code analysis has been established.

## Decision and next gate

Recommended decision: **CORRECTIONS_REQUIRED** for the mathematical package; controller readiness is separately **HOLD**. Complete independent verification of source-to-certificate calculations, incorporate the corrected checkpoint-133 result, and obtain a targeted novelty review before claiming a theory paper. If authorized later, the next empirical study should first estimate finite-history bias and false alarm under declared gate/readout nuisance, with a fixed decoder fallback; decoder utility remains a separate endpoint. Do not use development results as confirmation.
