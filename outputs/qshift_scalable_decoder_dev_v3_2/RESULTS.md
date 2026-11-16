# Scalable decoder V3.2 (compiled BP+OSD, `ldpc==2.4.1`): results

**Pre-registered decision: GO** for the scalable-decoder development milestone: K1, K2 and K3 all pass. This is development evidence only. The d=3 quality figures use already-exposed V1.5 arrays, and **d ≥ 5 accuracy is not measured**.

## Environment

`ldpc==2.4.1` was installed with owner approval. Exact delta (`ENVIRONMENT_DELTA.txt`): `+ldpc 2.4.1`, plus the transitive `+sinter 1.16.0`, `+pytest 9.2.0`, `+pluggy 1.7.0` and `+iniconfig 2.3.1`, which the approval request did not anticipate. NumPy, SciPy, Stim and PyMatching are unchanged. To roll back, run `py -3.12 -m pip uninstall ldpc sinter pytest pluggy iniconfig`.

## K1 correctness (`test_ldpc_bposd.py`, 2/2 pass)

- Every fault estimate is syndrome-consistent on every syndrome of the three toy DEMs.
- At d=3, 5 and 7: the all-zero syndrome decodes to 0, and every pure burst syndrome yields a consistent estimate and its exact logical effect.

**Upstream edge case found:** ldpc 2.4.1 crashes the process at teardown (exit code 127) when `osd_order` exceeds the number of non-pivot columns (n − rank). The adapter clamps the order to n − rank. That only ever binds on tiny toys; every real d=3/5/7 DEM uses the frozen order 10, which a test asserts.

## K3 feasibility (same 200 deterministic syndromes per distance as V3; single-shot calls, one process)

| d | Median ms/shot | p95 | Max | tracemalloc peak | RSS after | Agreement with V3 (first 50) |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 2.9 | 3.4 | 4.6 | 0.07 MiB | 81 MiB | 0.88 |
| 5 | 25.3 | 27.4 | 28.7 | 0.60 MiB | 86 MiB | 0.94 |
| 7 | **10.0** ✔ | 89.5 | 109.0 | 2.58 MiB | 99 MiB | 1.00 |

The d=7 median is well under the 50 ms gate (V3 was 60.7 ms; V3.1 97.4 ms). The p95 of 89.5 ms reflects shots where BP fails and OSD-CS runs. On real d=3 evaluation rows the mean is **0.22 ms/shot**.

## K2 d=3 quality (same 72,000 already-exposed V1.5 rows, frozen per-root q̂)

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero LER |
|---|---:|---:|---:|---:|
| Astar | 200 | 284 | 381 | 1.385% |
| BoffStatic | 143 | 167 | 165 | 0.692% |
| Bexact (exact reference) | 91 | 125 | 123 | 0.517% |
| V3 (NumPy BP+OSD) | 95 | 124 | 127 | 0.523% |
| **V3.2 (ldpc BP+OSD)** | **132** | **137** | **141** | **0.579%** |

**V3.2 contrasts** (root-paired, 95% CI):

| Contrast | Nonzero | 95% CI | q=0 |
|---|---:|---|---:|
| V3.2 − Astar | **−0.806 pp** | [−0.885, −0.727] | −0.283 pp |
| V3.2 − BoffStatic | −0.112 pp | [−0.167, −0.062] | −0.046 pp |
| V3.2 − Bexact | **+0.063 pp** | [+0.031, +0.096] | +0.171 pp |
| V3.2 − V3 | **+0.056 pp** | [+0.031, +0.081] | +0.154 pp |

Gap recovery is G = 0.928 against the ≥ 0.50 threshold. Agreement is 99.86% with V3 and 99.81% with Bexact.

## Interpretation

- **The compiled implementation solves feasibility at a measurable accuracy cost.** It is about 6× faster than V3 at the d=7 median and about 25× faster on real d=3 rows. But on d=3 it is significantly worse than V3, by 0.056 pp nonzero, and especially at q=0 (132 vs 95 errors).
- **The likely cause is the pre-registered differences.** ldpc has no message damping, and its OSD-CS candidate set differs from V3's. Where BP doesn't converge (common at q=0), the BP posteriors that order OSD's search are worse.
- **It is still a strong decoder.** It beats the strongest static matcher by 0.81 pp and the best V1.3 decoder by 0.11 pp, and recovers 93% of the gap to exact.
- **ldpc settings were not tuned on these data.** A different BP method, schedule or scaling would need a separate pre-registration evaluated on different development data.
