# Q-SHIFT CNN Improvement — Prospective Development Protocol

**Status: proposed, not frozen and not executed.** This document does not authorize training. It is a reviewable plan for deciding whether either architecture warrants a separate development run. It excludes every independent-test allocation.

## Scientific question

Can a compact position-preserving residual CNN learn useful parity corrections from syndrome data beyond the current residual-position CNN, under ordinary nominal noise and the declared synthetic spatial-burst extension, while remaining competitive with strong PyMatching baselines?

The primary risk is not inability to fit a label. It is that a rare residual correction has low precision: the prior five-root residual-position CNN changed only 62 of 150,000 decisions and added 36 net logical failures. The experiment therefore prioritizes paired harmful/useful corrections, not raw accuracy or recall.

## Conditions and comparator arms

Use the same rotated surface-code Z-memory, distance 3, five rounds, 40 detectors, one observable, Phase 2B balanced Pauli noise (`gate_p=0.003`, `measurement_p=0.003`, bias ratio 10) in both conditions:

1. No added cross-location burst (`p_burst=0`).
2. Phase 3A synthetic common-cause X burst on data qubits 8 and 10 after each MR boundary, independent per round with `p_burst=0.01`.

Compare on paired detector/observable arrays:

1. Frozen no-burst Phase 2B PyMatching.
2. Burst-informed PyMatching built from the declared burst-inclusive DEM. This receives true synthetic burst probability/location at model construction and is a privileged model-informed reference, not a deployable detector-only policy.
3. Existing direct `PositionPreservingConv3DDecoder`.
4. Existing `ResidualPositionCNN` (the 13,429-parameter reference CNN).
5. `ResidualPositionCNNV2`.
6. `FactorizedSpatialTemporalResidualCNN`.

The two direct/residual target conventions must remain distinct. Direct CNNs predict the observable bit from detector bits. Residual CNNs predict `observable XOR frozen no-burst PyMatching` and are scored after XOR with that same fixed prediction. The burst-informed matcher is a comparator, not a target-generating model. No neural model receives hidden condition/burst labels or observable labels at inference.

All matching DEMs must use the Phase 2B/Phase 3A conversion settings (`decompose_errors=True`, `approximate_disjoint_errors=True`); report that the mutually exclusive categorical Pauli faults are approximated in DEM construction. Keep the circuit, detector order, observable index, and shot arrays identical across all applicable decoders per root/condition.

## Proposed bounded splits

Five independent development roots, each with disjoint seed streams for:

- Training: 10,000 shots per condition (20,000/root; pool conditions 1:1 for neural fitting).
- Monitor: 2,000 per condition for early stopping and best-checkpoint selection.
- Probability calibration: 2,000 per condition for temperature choice.
- Threshold selection: 2,000 per condition for a single decision threshold.
- Final development evaluation: 10,000 per condition, sampled or loaded only after model, checkpoint, temperature, and threshold choices are frozen.

This is 260,000 total unique shots across the five development roots if all partitions are retained. A lower bounded allocation may be proposed before freezing only if diagnostics show unstable class counts; test data cannot be used to size or tune it. Five roots support only low-powered descriptive development uncertainty, not a confirmatory claim.

Use the same training arrays and optimizer-step budget for all neural comparators. Preserve the prior reference defaults initially: balanced minibatches, batch size 256, AdamW lr 0.003, weight decay 0.0001, StepLR step size five epochs/gamma 0.5, max 10 epochs, patience 3. Restore best checkpoint by equal-condition monitor NLL. If balanced sampling is used, correct logits back to the natural training prevalence before probability calibration. Temperature is chosen by equal-condition NLL on calibration only. A single threshold is selected by equal-condition logical error on threshold-selection only; ties prefer the threshold closest to 0.5, then the lower threshold. Do not inspect final-development labels until every choice is saved.

Seed inventory, code/configuration hashes, exact source tree, and resource limits must be separately frozen before any prospective training sample is generated. The diagnostic seeds in this Stage 1 directory are not valid training, calibration, threshold, or final-development seeds.

## Endpoints and decision rule

Per root and condition, report shots, raw observable positives, prediction distribution, residual LER/count, positive recall/precision, calibration metrics, paired discordances versus each PyMatching arm, and prediction disagreement. For each paired comparator report neural-only failures and matcher-only failures. Summarize root-level effects and a descriptive 95% interval across independent roots; shot-level intervals must not be substituted for root variability. Report exact per-root values.

Development-only gate to propose a new independent study: at least one candidate must reduce equal-condition mean LER by at least 0.0002 absolute versus frozen PyMatching, be favorable in at least 4/5 root-level paired means, and avoid a >0.0002 absolute LER harm in either condition. Also compare against burst-informed matching on burst samples and report whether any neural gains remain after this privileged comparator. This is a feasibility gate, not a hypothesis test; no p-value from this development selection validates superiority. If the gate fails, stop architecture expansion and keep PyMatching as the supported default.

## Audit and stop conditions

Before any future run, verify no seed collisions with recoverable historical seeds, no split overlap, Stim/DEM/decoder dimensions, noiseless behavior, paired shot hashes, natural prevalence, model parameter/inference budgets, and absence of independent-test paths in the runner. Stop on invalid labels, shape mismatch, hash failure, non-finite training values, insufficient residual positives in a root/condition, or unavailable burst graph representation. Preserve failed data and reports. Do not increase to 100K+ training, use new test data, or start a confirmatory experiment under this protocol.

## Unresolved limitations

The burst mechanism is synthetic and its 1% probability is a stress setting. The graph DEM inherits `approximate_disjoint_errors=True`. The burst-informed matching baseline has privileged model information. Only one memory basis, distance, and round count are proposed. Existing five-root neural findings are development-only. No hardware integration is demonstrated.
