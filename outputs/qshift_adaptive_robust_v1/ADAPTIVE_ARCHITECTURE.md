# Adaptive Q-SHIFT architecture (prototype)

## Pipeline (causal; block t is decided from blocks < t)

```
detector rows of block t
  │
  ├─► [decide]   SafeDecoderSelector.choose(t, proposal built from blocks ≤ t−1)      (qshift_core_v1, unchanged)
  │                 ↳ fixed fallback on: no proposal, low confidence, UNKNOWN regime, non-causal or invalid input
  │                 ↳ switch only after hysteresis_blocks agreeing proposals and minimum_dwell_blocks
  ├─► [decode]   registry[selected].decode(detectors) → logical-observable prediction
  └─► [feedback] estimators updated with block t DETECTORS only:
        estimation.py   robust per-class background scale + burst-detector outliers      (H-E1)
        changepoint.py  binomial CUSUM on block event counts; alarm clears the window      (H-E2)
        regime.py       posterior over known regimes + deviance fit test → label or UNKNOWN (H-E3)
        → SelectionProposal(decoder for regime, confidence, based_on_through_block = t)
```

Code: `adaptive/pipeline.py` (`AdaptiveController`), built on `qshift_core_v1.controller` without modifying it.

## Information boundary (enforced by API shape and tested)

- **What the controller receives:** `step(block, detectors)` only (`test_api_has_no_label_channel`). The controller never receives:
  - observables or logical labels;
  - true p or the true burst support;
  - condition IDs or split labels.
- **Where regime models come from:** the rate vectors in `RegimeClassifier` must come from DEMs the deployable system may know:
  - the nominal model;
  - models fitted on the calibration split from detector rows;
  - models fitted from *labeled calibration shots*, if the protocol grants them. That grant is a declared information channel, available to every comparator (`BASELINE_FAIRNESS.md`).
- **Privileged references:** oracle arms (true support, true p) are separate classes in the evaluation harness and are never registered in a deployable registry.

## Components and status

| Component | Hypothesis | Status | Known limitations |
|---|---|---|---|
| Robust background scale (`estimation.py`) | H-E1 | U: synthetic tests pass (recovers κ ∈ {0.83, 1, 1.17} within 0.02; ignores a 3-detector burst; per-class scales for bias) | Assumes detector rate ∝ mechanism rate (valid at low p); independent-Bernoulli synthetic data. Real circuits need a DEM re-weighted at κ·p, then the Phase C learner re-run on the rescaled base |
| Change detection (`changepoint.py`) | H-E2 | U: calibrated threshold; detects ±17% steps within 10 blocks on synthetic data | Global-rate CUSUM only. Localized bursts are caught by per-detector outliers, not by the CUSUM |
| Regime classifier (`regime.py`) | H-E3 | U: classifies 3 synthetic regimes; flags a structured out-of-family change as UNKNOWN | Independence approximation. Correlated data are flagged UNKNOWN more often, which is the safe direction but costs adaptation |
| Controller (`pipeline.py`) | integration | U: causal lag, hysteresis, fallback tests pass | Decoders in the tests are stubs. No real decoder yet registered through `DecoderProtocol` |
| Decoder bank | — | Existing: nominal PyMatching, correlated PyMatching, L2 BP+OSD (as study code, not yet `DecoderProtocol` adapters) | Writing the adapters is engineering work for the next milestone |

## Identifiability limits (documented, not hidden)

1. **Detector-only burst support is not uniquely identifiable** at d=3. V1.6 found every signature class ambiguous in its logical effect. Phase C resolved the ambiguity with labeled calibration shots. A deployable controller either gets such shots, which must be a protocol-declared channel, or must decode without resolving the flip.
2. **Global scale vs burst.** A global scale is identifiable from detector marginals when bursts are local. A chip-wide burst (cf. McEwen et al. 2022) is *not* separable from a background increase by marginals alone; time structure is needed (CUSUM onset, short duration).
3. **Bias.** One scale per detector class can absorb a uniform Z-bias only if the classes map to the error types. Under a non-uniform bias, the per-class model is misspecified and the deviance test should flag it.

## Neural components

None are proposed.
- **Record:** every neural candidate in this repository was worse than PyMatching.
- **Floor diagnosis:** the remaining failures are mostly MLE-consistent, so a learned decoder would need to beat the most-likely-error criterion through degeneracy. Established non-neural methods (ensembles, tensor-network maximum-likelihood decoding) target that directly.
- **When to revisit:** a neural component should be reconsidered only with a specific testable hypothesis, for example "a learned prior beats syndrome-MLE priors under drift", and a compute budget.
