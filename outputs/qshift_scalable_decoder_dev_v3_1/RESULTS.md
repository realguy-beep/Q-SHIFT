# Scalable decoder V3.1 (batched BP): results

**Pre-registered decision: REVISE.** The equivalence gates pass exactly, but batching made BP slower, so the d=7 runtime gate still fails. This is a recorded negative engineering result. The V3 diagnosis that blamed per-call NumPy overhead was **wrong**: single-shot BP is compute-bound.

## Equivalence (`V3_1_GATES.json`, `test_bposd_batched.py`)

| Gate | Result |
|---|---|
| **E1:** 72,000 d=3 benchmark rows, predictions vs stored V3 | **0 mismatches** (min and lc) ✔ |
| **E2:** 600 feasibility syndromes (d=3/5/7), predictions and LLRs vs V3 | 0 mismatches; max abs LLR difference **0.0** ✔ |
| **E3:** unit tests (V3.1 tree marginals, V2/V3 cross-checks, toy predictions; plus all 8 unchanged V3 C1–C4 tests) | **11/11 pass** ✔ |

V3.1 is therefore decision-equivalent to V3, and V3's d=3 quality result applies to it unchanged.

## Feasibility (same 200 deterministic syndromes per distance; single process)

Per-shot time is batch BP time ÷ 200, plus that shot's OSD time.

| d | V3 median | **V3.1 median** | V3.1 p95 | V3.1 batched BP alone | Peak traced memory |
|---:|---:|---:|---:|---:|---:|
| 3 | 23.5 ms | 22.1 ms | 26.3 ms | 10.8 ms/shot | 42 MiB |
| 5 | 34.6 ms | 38.2 ms | 82.9 ms | 38.2 ms/shot | 177 MiB |
| 7 | 60.7 ms | **97.4 ms** ✗ | 195.8 ms | 97.4 ms/shot | 403 MiB |

BP did not converge on 170 of 200 d=7 syndromes in either version.

## Why batching failed

Each BP iteration makes about 20 elementwise passes over the edges (tanh, log, exp, arctanh, sums). At d=7 that is about 50 × 20 × 11,432 ≈ 11 million operations per shot. Single-shot V3 was already limited by this arithmetic, not by Python call overhead. Batching kept the same arithmetic and added larger working sets (memory traffic grew to 403 MiB) plus sparse-product overhead, so it got slower.

## Remaining routes to d=7 feasibility

1. **Compiled BP+OSD (`ldpc`, the standard Roffe et al. implementation).** It keeps the algorithm and doubles as an independent implementation cross-check. It needs dependency approval.
2. **Algorithm changes:** min-sum BP, which avoids tanh/arctanh, or fewer BP iterations, since OSD does the decisive work when BP doesn't converge. Either is a new algorithm, so it needs its own pre-registered d=3 quality re-check against exact.
