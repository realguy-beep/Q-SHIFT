# Nested training shot efficiency for the d3 flagged logistic selector

## Question and hypothesis

Does the current selector need 1,000,000 labeled training shots per d3 condition, or does a 100,000-shot nested prefix retain most of its utility? The working hypothesis is that the flag rate (~0.3–0.5%) leaves several hundred labeled flagged rows in 100k shots, enough for a fixed 42-feature, L2-regularized logistic model.

## Frozen design

- Six existing d3 Phase 2B conditions at gate and measurement p=.003, ratio 10.
- Per-condition training stream: 1,000,000 shots. Fit two models on nested prefixes of 100,000 and 1,000,000 shots; only flagged rows are used to fit either model. Same feature definition, penalty, optimizer, initialization, and stopping settings as `fast_flagged_logistic.py`.
- Independent validation: 500,000 fresh shots per condition, shared across the two models and correlated-matching baseline. No validation outcomes enter fitting or model selection.
- Preflight: 5,000 shots/condition to verify geometry, noiselessness, decoder shape, and projected full run <=300 seconds. During the single nested 1M training stream, stop before validation if any 100k prefix has fewer than 100 flagged rows or fewer than two logical classes.
- Seeds: preflight 2026121801–1806; training 2026121811–1816; validation 2026121821–1826.

## Metrics and advancement gate

Report macro and per-condition LER, paired selector-minus-correlated intervals, flagged counts/classes, fit/runtime, and end-to-end inference cost. The low-shot model advances as a sample-efficient alternative only if: (a) it retains >=80% of the full model's absolute macro LER reduction on the shared validation stream; (b) it independently reduces macro LER by >=10%; (c) no condition is >5% worse than correlated matching; and (d) full inference cost is <2x correlated matching. This is a development feasibility result, not confirmatory evidence.

No other model/budget/feature choices will be tried on this validation stream. No sealed data, branch switching, or change to existing protocols.
