# Novelty and feasibility assessment

## Established context

The existing Q-SHIFT literature synthesis documents established noise-aware and calibrated matching, bias-tailored surface-code decoding, belief/correlation-aware matching, syndrome-based estimation, and adaptive decoder hardware. That prior review cites, among others, Stim and PyMatching, calibrated matching, surface-code biased-noise tailoring, belief-matching, tensor-network decoding, and recent adaptive hardware decoding. This audit does not repeat a broad literature search; it checks whether the project evidence distinguishes itself from that established context. See `outputs/research_synthesis/LITERATURE_REVIEW.md`, `outputs/conditional_go_resolution/SUPPLEMENT_LEVEL_LITERATURE_AUDIT.md`, and `outputs/matching_representation_investigation/NOVELTY_CHECK.md`.

Using a new combination of a detector classifier and a matching decoder is not by itself a novelty claim. A credible contribution would need a sharply specified benchmark or method and evidence that its result changes what can be concluded about deployable decoding.

## Feasibility of the three directions

### A. Adaptive selection among the existing decoder bank — not ready

**Support:** Paired banks contain complementary errors; same-shot hindsight gaps are often material. For example, the Phase 4C five-comparator sample oracle is 0.001422 LER below pooled fixed.

**Contrary evidence:** The oracle relies on true test labels. Calibration-selected candidates often equal the pooled fixed selection, the 36-cell multi-distance gate fails, Stage 2 calibrated selection is slightly worse than pooled fixed, and detector-based gates fail to improve the best fixed baseline. Prototype dynamic blocks either never switch or have small, schedule-dependent results.

**Feasibility/novelty:** A causal online selector is technically implementable, but evidence does not show that observable confidence predicts decoder utility with enough accuracy/lead time. The general “estimate regime and switch” theme overlaps existing methods. No next adaptive selector experiment is justified.

### B. Adaptive calibration / matching-weight updates — not ready

**Support:** A small prototype rebuilds a matcher from an earlier completed block and swaps it atomically at a boundary; detector estimates can change predictions.

**Contrary evidence:** Utility difference is -0.0000916 with 95% CI [-0.000417,+0.000234], below a practical benefit gate and uncertain. False-update validation fails to certify the schedule-level target. There is no matched, equal-resource periodic recalibration comparison including estimator work, history access, rebuild CPU/memory, and activation latency.

**Feasibility/novelty:** Rebuilding models is technically feasible in small tests, but online noise/weight calibration is established. No evidence-based basis exists to authorize a large adaptive test. The critical comparison is also absent.

### C. New structured decoder, adaptation later — technically intriguing, presently blocked

**Support:** Exact categorical toys and reduced surface fragments show that channel exclusivity and DEM decomposition can affect decisions. A graphlike rewrite is valid for a restricted support pattern.

**Contrary evidence:** The Phase 2C learned reference is much worse than PyMatching; full five-round categorical state spaces are far beyond dense enumeration; hyperedges defeat the graphlike rewrite; local refinement has narrow coverage and no full-circuit advantage. There is no scalable, validated exact/structured decoder for the full target circuit.

**Feasibility/novelty:** This is more technically distinct than switching, but the necessary inference algorithm and full-circuit utility are missing. It should not be sold as exact MAP or a likely performance improvement.

## Resource decision

The archived experiments have already used substantial simulation effort, yet the missing evidence is not simply more shots. It is the missing causal link between available detector information and a decoder’s *future paired utility* against a properly selected fixed model, after delay and compute cost. The headroom gate and test data do not support that link. Additional sample volume on the same weak bank would not fix the selection-utility issue.

