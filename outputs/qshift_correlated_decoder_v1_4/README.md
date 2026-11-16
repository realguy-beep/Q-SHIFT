# Q-SHIFT correlated decoder V1.4

**Goal:** at least 90–95% logical-error reduction against the *strong* matching baselines (best static and mode-switching), in a regime where common-cause bursts dominate the error budget. At d=3, p=0.003 this is impossible: the q=0 background floor (0.501%) caps any burst decoder at about 64% against the best static matcher (1.392%), and V1.3's Boff reached 47%.

## Status: Phase A complete (no sampling)

- `model_v14.py` is the distance-general model. It covers:
  - the Phase 2B circuit at any odd d;
  - burst-support families and event extraction;
  - the five-factor decoder in both residual modes;
  - the estimator.

  Tests pin it to reproduce V1.1 exactly at d=3: circuit text, events, estimator, and predictions in both modes.
- **Burst support** is a geometric rule fixed before any d≥5 sampling. `BURST_SUPPORT.json` records its output for d = 3, 5, 7:
  - `scaled_v1` = (0,m), (d−1,m), (0,m+1), which is V1.1's X8 X12 X15 at d=3;
  - `centre_row` is a robustness family.

  All events are logically trivial.
- `headroom_gate.py` (Phase B) is written and tested, but **not run**. `GATE_SEEDS.json` holds 54 seeds, screened against 497 prior values with 0 collisions.

## Phase B (needs owner authorization: about 1.08M development shots, matching only)

```powershell
py -3.12 outputs/qshift_correlated_decoder_v1_4/headroom_gate.py            # dry run
py -3.12 outputs/qshift_correlated_decoder_v1_4/headroom_gate.py --execute  # writes HEADROOM_GATE.json once
```

For each of 18 cells (d ∈ {3,5,7} × p ∈ {0.001, 0.002, 0.003} × 2 families), the gate computes:

ceiling = 1 − floor / static_best

Here floor is the best matcher's LER at q=0. That is exactly a burst oracle's LER, because known, logically trivial burst signatures XOR out. static_best is the best static matcher at nonzero q over mode × q, chosen in-sample, which is conservative.

A cell qualifies if the ceiling's conservative lower bound is at least 0.97 and static_best has at least 100 nonzero errors. The gate also times the five-factor decoder per shot, for pilot sizing. Gate shots are development data and are never reused for evaluation.

**Stop rule (from the plan):** if no cell qualifies, or a later pilot shows less than 85% reduction, stop and diagnose; don't run a frozen evaluation chasing the number.

## Tests

```powershell
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_v1_4/tests -v
```
