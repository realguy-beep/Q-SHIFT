# Architecture Recommendations

## Proposed separation of concerns

```text
Completed shot detector vector X_t
             |
             +--> immutable causal history / feature extractor
                         |
                         +--> detector-only estimator (window / edge moments)
                         +--> model-adequacy and abstention guard
                         +--> optional one-sided alarm process
                                      |
                              state/risk supervisor
                                      |
                           cached decoder-bank selector
                                      |
                     future-shot decoder (t+1 onward)
```

The detector law is generated upstream of decoder choice in the current interface. A decoder selector cannot change the physical detector distribution. Decoder action therefore needs an externally justified model-to-decoder map or independently scored utility; detector statistics alone do not prove one decoder is better.

## Recommendations

- Keep strong selected/pooled static PyMatching as primary deployable comparator. Freeze candidate models, selection objective, calibration budget and tie-breaking.
- Keep privileged true-p and label-selected choices isolated and explicitly oracle/supervised.
- Preserve separate model identities for exact categorical circuit, undecomposed approximate DEM, and decomposed approximate DEM. Do not transfer validity claims between these laws without proof.
- Implement the edge-moment estimate as a transparent detector-only baseline only after minimum-history, boundary and nuisance policy is prespecified. Do not silently clip estimates.
- Treat the e-factor as an alarm-only component. Output alarm, evidence source, time, and validity state; it must not infer burst cause or set p to a hidden truth value.
- Add explicit **abstain/fallback** behavior in the indifference band and under model inadequacy. Do not automatically reset the opposite directional process after an alarm.
- Graph construction must use only approved model parameters and occur before affected scored shots. Cached graph switches affect t+1 or later.
- Give all policies the same chronological detector inputs, observation count, graph cache and calibration opportunities. Tune only on eligible development data; preserve a separate held-out development split.
- Keep decoder algorithm research separate from controller research. BeliefMatching or an ensemble can be a static algorithm arm; it cannot imply adaptation.

## Risk controller status

A one-sided e-process can be mathematically valid under its declared conditional null, but the up/down processes do not yet form a valid autonomous bidirectional state machine. The middle band has no unique certified action; a false alarm does not establish the alternate regime; reset-count alpha spending alone is insufficient. Current readiness is **HOLD** pending owner decisions on state recovery, reset authority, deployment horizon and false-switch loss.
