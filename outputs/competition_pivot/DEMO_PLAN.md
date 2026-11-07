# Competition-ready demonstration plan

## Demonstration goal

Show what Q-SHIFT currently does and what the evidence says, without suggesting that confidence gating improves decoding. Present a replayable simulation experiment as a scientific investigation: some decoder choices differ, a detector-only gate can fall back, and the saved development evaluation did not show a benefit over the strongest fixed decoder.

## Proposed 3–5 minute flow

1. **Problem picture:** repeated stabilizer checks create a detector pattern; a decoder maps that pattern to a logical correction estimate.
2. **Show one saved trial:** display the 40-bit detector vector as a compact time-by-check heat map, the pooled and calibration-selected predictions, their agreement/disagreement, the actual simulated observable, and whether each prediction was right. Label the actual observable as evaluator-only information; do not expose it to the controller.
3. **Show confidence gate:** display calibration score margin, predicted utility confidence, chosen action (fixed fallback or candidate), and why a decoder switch occurred. Use only features from the saved calibration/detector data. If showing the outcome, reveal it after the decision as audit feedback.
4. **Show aggregate chart:** fixed 681/98,304 errors; calibration-selected 672; calibration gate 686; current-syndrome gate 684. Mark all as exploratory development results with wide uncertainty and no confirmed gain.
5. **Explain limitations:** only 225/98,304 predictions differed between candidate and pooled; current gate requires both decoder outputs; no hardware integration or independent gate test has been performed.

## Implementation constraints for a later demo

- Replay saved samples from outputs/conditional_go_resolution/DEVELOPMENT_RAW_EVIDENCE.npz; never hardcode example numbers or claim it is a live quantum processor.
- Keep evaluator labels hidden in the controller UI until after the gate decision is logged.
- Add a visible label “simulation replay — exploratory, not hardware-tested”.
- Provide a fixed-decoder-only mode and show that fallback is a policy choice, not a guarantee of no loss.
- Export the seed, source manifest, circuit configuration, and sample index with each displayed trial.
- Do not show a “success” animation as if the physical state was repaired; show the simulated observable residual only.

## Competition message

The honest result is itself demonstrative: Q-SHIFT built a reproducible simulator and a testable detector-only switching pipeline, then found that confident noise identification did not reliably imply a better logical correction. The competition presentation can emphasize experimental discipline, paired comparisons, and safe fallback behavior while clearly stating that the adaptive candidate did not beat the fixed method in this gate pilot.
