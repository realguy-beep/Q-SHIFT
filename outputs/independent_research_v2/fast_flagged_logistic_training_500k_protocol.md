# Prospective 500k-shot selector training budget

## Motivation

A previous nested 100k screen stopped at fit readiness: X-memory/X-biased had 93 flagged rows versus the frozen minimum of 100, and the run's partial validation was excluded. This follow-up tests a single prospectively chosen 500k budget (five times the flag floor, half the established 1M training volume); it is not a threshold sweep or a reuse of the partial validation stream.

## Frozen design

- Six d3 Phase 2B conditions, nominal gate/measurement p=.003 and bias ratio 10.
- Generate one independent 1M training stream per condition. Fit the fixed 42-feature L2 logistic model on flagged rows from both the 500k prefix and the full 1M stream. Use the same objective, initialization, L-BFGS-B settings, and feature construction as `fast_flagged_logistic.py`.
- Check the 500k prefix in all six conditions before opening any validation data. Each prefix must have >=100 flagged rows and both logical classes.
- Only after all six training gates pass, evaluate both frozen fits on the same fresh 500k validation shots per condition. Baseline: correlation-enabled PyMatching. Compare both candidate and full-fit reference on identical validation shots.
- Preflight: 5,000 shots per condition to check circuit geometry, noiselessness, feature/matcher shapes, and projected runtime <=300s.
- Seeds: preflight 2026121901–1906; training 2026121911–1916; validation 2026121921–1926.

## Advancement gate

The 500k candidate advances as a training-efficient alternative only if it retains >=80% of the full 1M fit's absolute macro LER reduction, independently reduces macro LER by >=10%, harms no condition by >5%, and full inference cost is <2x correlated matching. Report paired intervals, per-cell metrics, flagged counts/classes, fit times, and runtime. No tuning, threshold adjustment, or further budget choices on this validation stream. Development only; no sealed or confirmatory data.
