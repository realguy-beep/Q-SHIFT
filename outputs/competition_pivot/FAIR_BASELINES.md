# Fair baseline definitions

## Results on the existing paired evidence

| Policy name | Operational definition on these files | Errors / 98,304 | Notes |
|---|---|---:|---|
| Strongest pooled fixed / no-update | Frozen Phase 4C Stage 1 pooled decoder (grid index 1) on every sample; no updates | 681 | Strong fixed comparator from frozen development selection. This is also the no-update baseline; the two labels are not separate policies. |
| Always-adaptive | Use the calibration-selected candidate decoder’s saved output on every shot | 672 | Only 9 fewer errors than pooled; saved root-wise. |
| Existing calibration-selected decoder | Select grid model from the root’s detector-only calibration prefix, then use it for its paired evaluation block | 672 | Exactly the same output mapping as “always-adaptive” in these saved arrays; must not be double-counted as an independent comparator. No within-block change was evaluated. |
| Calibration-confidence gate | Leave-one-root-out model from detector calibration score margin and selected-minus-pooled score; choose candidate if predicted candidate-better probability ≥ 0.5, otherwise pooled | 686 | 21 candidate roots, 3 fallback roots; worse by 5 errors. Cross-validated development diagnostic only. |
| Current-syndrome confidence gate | Leave-one-root-out model on detector-only per-shot features, conditional on candidate/fixed predictions disagreeing; cutoff 0.5 | 684 | 131 candidate and 94 fixed decisions among 225 disagreements; requires both decoder predictions before gating. |
| Simple likelihood threshold | Choose candidate when its current syndrome has higher factorized detector-marginal likelihood than pooled | 672 | Chose candidate on all disagreement shots; exactly duplicates always-adaptive here. |

The gated models were trained across other development roots, with each scored root held out from feature-to-utility fitting. Because the same 24 roots were used to construct and inspect these exploratory policies, these numbers are not an independent final evaluation and do not authorize a confirmatory test.

## Required controls for any new experiment

- Generate a paired immutable set of detector matrices and observable labels, then run every policy on exactly those samples.
- Freeze the strongest pooled fixed decoder using calibration data only. Preserve the nominal fixed decoder as a reference, but do not call it strongest unless selected as such.
- Give always-adaptive and confidence-gated policies identical causal calibration histories and the same candidate bank.
- Use a fixed fallback baseline with the same input samples, history access, and allowed compute budget.
- Add a periodic recalibration comparator with the same total number of detector-history observations, DEM/matching builds, and maximum rebuild budget as event-triggered gating. Report realized differences in rebuild timing and compute; equal expected counts are not exact per-schedule resource equality.
- Charge for both candidate and fallback decoding if a per-shot policy needs both outputs to compute disagreement/confidence. Report p50/p95/worst latency, memory, rebuild/activation delay, false switches, and fallback rate.
- Keep development, policy selection, threshold calibration, and final test roots disjoint. Do not choose the gate threshold from the final paired test outcomes.
