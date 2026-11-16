# Scalable decoder V3.1: batched BP (engineering revision; protocol)

**Committed before any V3.1 code or measurement.** V3 (`outputs/qshift_scalable_decoder_dev_v3/`, decision REVISE at `febae33e0`) is unchanged and remains the record.

## Scope

V3.1 changes **implementation only**: BP messages are computed for a batch of shots at once (2-D arrays and sparse incidence products) instead of one shot at a time. The algorithm, settings, per-shot early-stopping rule, OSD-CS, cost function and variants are all unchanged. V3 failed only its d=7 runtime gate (60.7 ms/shot against 50 ms), and its diagnosis attributed 43.8 ms of that to single-shot BP overhead.

## Equivalence gate (must pass before any timing counts)

- **E1:** on all 72,000 V3 d=3 benchmark rows, V3.1 predictions are identical to the stored V3 predictions for both variants.
- **E2:** on all 600 V3 feasibility syndromes (d=3/5/7), V3.1 predictions equal V3's, and posterior LLRs agree within 1e-8. Summation order changes, so floating point is not required to be bit-identical.
- **E3:** the V3 correctness tests (C1–C4) still pass, and V3.1 passes the same C2/C3 checks.

## Feasibility gate (identical thresholds)

On the same 200 deterministic syndromes per distance:
- per-shot time = (batch BP wall time ÷ batch size) + that shot's own OSD time, if OSD ran;
- the median at d=7 must be at most **50 ms/shot**;
- peak traced memory must be at most **1 GiB**.

The p95 and the maximum are also reported.

## Decision

- **GO** (scalable-decoder development milestone): E1–E3 pass, the feasibility gate passes, and V3's quality criteria hold unchanged (they follow from E1).
- **REVISE:** the equivalence gates pass but feasibility still fails. The next option is a compiled `ldpc` implementation, which requires dependency approval.
- **STOP:** an equivalence gate fails and can't be repaired without changing the algorithm.

This GO concerns the development milestone only: correct, scalable to d=7 in runtime and memory, and near-exact at d=3 on exposed data. It is not evidence of accuracy at d ≥ 5, which needs separately authorized sampling.
