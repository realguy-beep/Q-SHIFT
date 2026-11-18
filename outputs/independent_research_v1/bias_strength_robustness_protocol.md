# Bias-strength decoder robustness screen

## Hypothesis

The current adaptation work estimates X/Z bias direction, while reliably distinguishing moderate bias strengths is harder. If correlation-enabled matching changes little when its assumed bias ratio is imperfect, Q-SHIFT may need less precise magnitude calibration. Conversely, strong regret under a plausible ratio mismatch would identify a real calibration requirement. This tests decoder model robustness on a fixed memory task; it does not test a selector or an adaptive policy.

## Fixed design

- Source: d=3 rotated-memory Stim circuit, five rounds, gate and measurement p=.003. Actual X- or Z-biased profile ratios are 2, 5, and 10; both memory bases are tested (12 actual circuit conditions).
- For each actual condition, generate one independent 100-shot preflight stream and then 100,000 fresh main shots. Preflight seeds 2026112301–2026112312; main seeds 2026112321–2026112332 in actual-ratio/profile/basis order.
- Decode every detector sample with three matching models for the same profile/basis, built under assumed ratios 2, 5, and 10. The observed logical target is fixed within each actual circuit; every decoder sees identical detector shots. Build matching using `approximate_disjoint_errors=0.0018` and correlation-enabled decoding.
- Preflight requires the circuit to have 40 detectors/one observable, identical geometry resources within each actual ratio, matching batch/scalar agreement on all preflight shots, and projected main build/sample/decode time below five minutes. Stop before main sampling if any check fails.
- Primary comparisons: paired per-condition LER difference of the fixed assumed-ratio-5 decoder versus the correctly specified ratio decoder; and equal-weight macro LER for each fixed assumed ratio. The correctly specified decoder is a reference configuration, not a guaranteed lower bound or deployable selector. Report paired standard errors and per-condition rates. Macro intervals quantify Monte Carlo variation over these fixed conditions only, not generalization to new profiles.
- Also report circuit resources, build/decode time, and the ratio-5 mismatch regret. No training, ratio selection, post-hoc thresholding, distance scaling, or confirmatory data.

## Scope and stop rule

This is one synthetic development screen of known stationary Pauli channels. It isolates bias-strength misspecification while holding bias direction, memory basis, circuit, and decoder family fixed. It does not model uncertainty in spatial correlations, hardware drift, or channel families absent from the source. A small or null difference would support robustness only over these tested ratios and conditions.
