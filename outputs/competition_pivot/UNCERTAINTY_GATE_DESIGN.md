# Candidate causal uncertainty gate

This design records what a defensible test would require. It is **not** an approved or validated decoder policy.

## Allowed information and timing

For each future block, use only a completed detector-history/calibration prefix and any model state frozen before that block. The policy may use:

- detector-only calibration likelihood scores and their margin/uncertainty;
- current-block detector data only if the protocol explicitly allows a per-shot gate after those detections are available;
- corrections/predictions from both candidate and fallback decoders if the extra decode cost is charged.

It may never use the generating-regime label, true observable/logical outcome, future detector samples, or post-test error counts. A block-level gate should decide before decoding that block; a shot-level gate can decide after current detectors are available but before correction is committed.

## Utility gate, not regime classifier

The target is expected incremental logical utility relative to the fixed fallback, not probability of the noise family. A detector profile can identify a regime without identifying which decoder has lower logical error. Train an offline mapping on independent development roots to predict the distribution of paired candidate-minus-fixed residual risk from detector-only features. Keep calibration-estimation uncertainty and root-level utility uncertainty separate.

For candidate j, define Δⱼ = LER(fixed) − LER(candidate j), estimated from development roots. For an upcoming block, switch only if a **prevalidated lower confidence bound** for Δⱼ exceeds a predeclared practical margin plus the estimated switching/decode cost. Otherwise retain pooled fixed. Use one predeclared calibration prefix, a one-sided risk bound calibrated on independent stationary schedules, and a frozen rule for how often it may be re-evaluated. Hysteresis may prevent repeated switching, but it does not itself establish a false-update rate.

The 0.5 model-probability cutoffs in the exploratory analysis are not a validated safe bound. In particular, “confidence” must be calibrated for the event “this model choice reduces logical failure,” not merely for predicting a noise label or selecting the best detector fit.

## Fallback safeguards for a future study

1. Fixed decoder remains the default and every unrecognized/low-confidence condition returns to it.
2. No candidate is enabled unless it passed an independent development utility gate against the strongest fixed decoder.
3. Enforce maximum switch rate and minimum dwell; include the full estimator, DEM/matching reconstruction, activation, memory, and decode cost in policy comparison.
4. Calibrate the schedule-wide false-switch probability under stationary controls, accounting for overlapping windows and repeated looks.
5. Log detector-only features, frozen model version, decision, selected decoder, and timing so every decision is auditable.

These safeguards reduce the chance of an unsupported switch but cannot guarantee “no worse than fixed” without a formal risk bound or sufficiently powered validation under the deployment distribution.
