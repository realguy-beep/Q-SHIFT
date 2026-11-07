# Proposed paper outline (future work)

## Working title

**Calibration Headroom and Causal Decoder Selection under Changing Surface-Code Noise: A Multi-Distance Benchmark**

## Abstract

State the problem, narrow question, simulator/circuit family, decoder bank, split protocol, primary endpoint and exact result. Include interval and test. End with the scope of inference. Do not write an adaptive-superiority conclusion before the test exists.

## 1. Introduction

Explain physical errors, detector signals and logical decoding in accessible terms. Distinguish estimating a logical-frame correction from physically applying a correction. Review noise-aware calibration, bias-tailored codes, learned/near-ML decoders and hardware adaptation. State the gap as usable calibration headroom over a strong fixed baseline.

## 2. Questions and frozen hypotheses

Define the null, practical effect margin, evaluation domain, calibration utility gate and causal information boundary. Explain which regime-matched/oracle comparators are diagnostics.

## 3. Methods

### Circuits and noise
Give Stim circuit, distances/rounds, memory basis, gate/readout channels and injection sites. Define probability conventions and omitted physical mechanisms.

### Decoder bank and calibration
Describe DEM construction, matching assumptions, correlated mode, pooled model and candidate weights. Validate any reference likelihood decoder on exhaustive toy circuits before use.

### Causal policy and data separation
Specify profile estimator, block order, hysteresis, dwell and fallback. State that selection uses completed prior blocks; labels select only during development calibration; held-out labels are scoring only.

### Statistical analysis
Define paired test samples, root as cluster, primary equal-regime effect, confidence interval, permutation test, secondary multiplicity family, transition censoring and runtime boundaries.

## 4. Results

Report circuit validation; calibration utility/headroom with uncertainty; static fixed/regime-informed performance; primary adaptive-versus-strongest-fixed test; transition delays, false switches and performance over time; decoder disagreement; runtime and memory. Show per-root outcomes and separate shot-level paired statistics from seed-level inference.

## 5. Discussion

Explain whether adaptation exploited measured headroom and whether estimator uncertainty or switching delay limited it. Compare nominal and pooled baselines. Relate to calibrated matching, biased-noise tailoring, near-ML learning and hardware adaptive work. Interpret a null without claiming universal impossibility.

## 6. Limitations and conclusion

State simulated channel scope, distances, DEM approximation, no hardware, runtime environment and rare-event limitations. Answer only the frozen question.

## Supplementary material

Provide configs, seed derivations, hashes, source versions, per-root results, raw evidence, failed/negative runs, test commands, analysis code and deviations.
