# Redesign feasibility decision

## Outcome: CONDITIONAL GO — as a comparative validation study, not as a new adaptive-decoding method

### Why it is not a GO for a novel algorithm

Syndrome-derived matching-weight adaptation, drift tracking and decoder graph reweighting are already established. Particularly close work includes the 2018 adaptive weight estimator, 2023 DGR graph reweighting, the 2026 sliding-window drift-estimation paper, and 2026 experimental reinforcement-learning control with decoder steering. Q-SHIFT must not claim to invent online matching-weight adaptation, be the first adaptive decoder, or show improvement without a new independent test. See [LITERATURE_NOVELTY_GAP.md](LITERATURE_NOVELTY_GAP.md).

### Why a narrow feasibility study remains conditionally worthwhile

The existing Q-SHIFT classifier-and-switch bank failed its multi-distance utility-headroom gate. That is a meaningful warning, but it did not implement continuous causal parameter estimation and online MWPM weight updates. The local code has reusable Stim circuit/DEM construction and PyMatching evaluation. It can support a small software prototype, but the present PyMatching 2.4.0 Python object has no public in-place edge-weight setter, and direct graph reconstruction risks dropping DEM-derived correlations. Safe updates therefore require complete model reconstruction and validation at block boundaries. The current code simulates static noise per circuit; the first scope should be drift between shot batches, not within-shot variation.

The only potentially defensible research distinction is a **budget-matched head-to-head test** of online/event-triggered causal weight updates against the strongest pooled fixed decoder and an equally resourced periodic recalibration policy, including identifiability, tracking lag, full-schedule LER, runtime and memory. The literature review did not establish whether the closest 2026 article's full supplement already contains this exact comparison; that is a mandatory pre-implementation check. If already covered, this project should not proceed under a novelty claim.

### Required conditions before implementation

1. Complete full-text/supplement comparison with the closest 2026 syndrome-drift paper, DGR, and hardware-adaptation study; record the exact difference or conclude no novelty.
2. Freeze a decoder-relevant identifiability test and a concrete parameter-to-DEM-to-PyMatching mapping that preserves boundary, fault-ID and correlation information.
3. Demonstrate with software tests that immutable decoder reconstruction at block boundaries is valid and causally isolated.
4. On independent development roots, establish stable utility headroom over pooled fixed; choose windows and thresholds only there.
5. Require a powered final test feasible under the resource cap and compare with equal-budget periodic recalibration.

### Scope and integrity

No simulations were run for this assessment. No Phase 1–5 or headroom files were changed. This document is not a performance claim or authorization to run confirmatory samples. The historical evidence remains specific to its circuits and protocols: Phase 4A/4B calibration helped against nominal fixed on measurement-heavy data; Phase 4C Stage 2 showed no gain over the stronger pooled fixed baseline and lacks saved calibration arrays; the audited Phase 2–5/headroom work did not establish adaptive superiority.

## Final recommendation

**CONDITIONAL GO — Specific gaps must be resolved first.** Proceed only if the literature comparison leaves a genuine equal-budget evaluation gap and the estimator-to-matching update path passes the identifiability and model-integrity gates. Otherwise stop with **NO-GO** for this research direction. No claim of novelty or improvement is currently supported.
