# Reference Decoder Validation

## Exact toy checks

`exact_toy.py` exhaustively enumerates finite categorical event outcomes and combines detector and observable effects by XOR. Four tests pass: a hand-computable categorical posterior (`P(L=1|D=1)=1/3`), independent-event composition, invalid probability-mass rejection, and a sampled-forest known-map sanity case. These validate the toy enumerator and implementation interfaces, not the full circuit posterior.

## Circuit and evidence checks

`validate_source.py` passed all six basis/regime cases. Replacing Phase 2B's custom one- and two-qubit channel lines with the original depolarizing lines reproduces Stim's generated circuit text exactly. Therefore the generated measurement flips, circuit schedule, detector/observable definitions and non-noise operations are unchanged. Both bases have 40 detectors and observable id 0; all six DEMs and matching graphs construct successfully. `PREFLIGHT_VALIDATION.json` records zero-noise determinism, nonzero-noise sensitivity, channel mass, graph sizes and DEM conversion flags.

`verify_phase2c_evidence.py` independently read all 24 pilot NPZs, checked their SHA-256, metadata, 40-detector arrays, binary labels and predictions, decoded stored detector samples again with all six frozen decoders, recomputed the calibration matrices/selections, and matched every root and aggregate error count. It passed for 120,000 paired shots. The saved posterior probabilities were independently recomputed within 1e-14; maximum observed numerical difference was one floating-point ulp (`2.22e-16`). Binary decoder predictions matched exactly.

## Held-out predictive quality

Across the 120,000 pilot samples, the logical-observable prevalence was 5.3925%. The three random-forest posterior surrogates achieved Brier scores 0.02048–0.02176 and log loss 0.0756–0.0782 nats, better than the constant-prevalence reference (Brier 0.05102, log loss 0.2099 nats). Their 10-bin ECE was 0.0269–0.0343. Thus the scores contain information about the observable but show material probability miscalibration. At the frozen 0.5 threshold, selected-reference LER was 2.149%, versus 0.523% for regime-matched Phase 2B PyMatching.

Proper-score improvement over a constant predictor is an empirical predictive-quality measure, not a bound on the difference between estimated and true full-circuit posterior probabilities. The exact full-circuit posterior is unavailable in this pilot. No claim of exact ML decoding is made.

## Analysis implementation note

The first report attempt rejected probabilities because a bitwise-equality check was stricter than floating-point reproducibility; the maximum discrepancy was 2.22e-16 while predicted bits matched exactly. The independent analyzer was corrected to use a 1e-14 probability tolerance while preserving exact prediction checks. Exact McNemar p-values are also retained as decimal strings because their floating-point representation underflows to 0. See `ANALYSIS_IMPLEMENTATION_CORRECTION.md`. These fixes changed only verification/report representation, not pilot samples, decoder selection, threshold, estimand, or statistical method.
