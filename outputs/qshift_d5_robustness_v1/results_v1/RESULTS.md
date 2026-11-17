# d=5 robustness, Step E: frozen evaluation results

**Verdict: ROBUST.** All three conditions are GO. Each passes the Bonferroni (98.33%) co-primary CI and the q=0 safety check.

## Run record

- **Run:** single attempt, frozen at `4d77c2d9e896f4193614e3e9325c1abaf90e7fb9`, protocol `PROTOCOL.md`.
  - Started 2026-11-17T07:28:39Z and finished 10:00:10Z, about 2.5 h wall time. The preflight projected 3.7 h; the budget was 5 h.
  - 216 of 216 jobs returned code 0.
  - In total 1,800,144 shots: 200,016 per (condition, q), across 24 roots.
- **Integrity:**
  - `analyze.py` verified the seeds, the archive SHA-256s and the recorded counts.
  - A second analysis into a separate folder was byte-identical, for both `ANALYSIS.json` and `paired_roots.csv`.
  - `recount.py` (`RECOUNT.json`) independently recounted every total, which matched `ANALYSIS.json`. It also re-decoded root 0 of all 9 (condition, q) cells; predictions were bit-identical for all four arms.

## Co-primary: L2s − Astar, equal-weight over q ∈ {0.01, 0.02}

| Cond | Change vs Phase 2 | LER Astar | LER L2s | Δ (95% CI) | 98.33% CI | R = 1 − L2s/Astar (95% CI) | Decision |
|---|---|---:|---:|---|---|---|---|
| F2 | burst family → centre_row | 1.100e-3 | 0.870e-3 | −2.30e-4 [−3.15, −1.42]e-4 | [−3.32, −1.22]e-4 | **20.9%** [13.3, 28.0] | GO |
| P2 | p → 0.002 | 0.800e-3 | 0.175e-3 | −6.25e-4 [−7.05, −5.42]e-4 | [−7.22, −5.22]e-4 | **78.1%** [71.8, 83.8] | GO |
| P4 | p → 0.004 | 3.602e-3 | 1.557e-3 | −2.04e-3 [−2.23, −1.85]e-3 | [−2.28, −1.81]e-3 | **56.8%** [53.0, 60.3] | GO |

For reference, the d=5 Phase 2 result (scaled_v1, p=0.003) was R = 64.8% [61.2, 68.4].

## q=0 safety

The check uses the 95th percentile of L2s − Astar at q=0. It passes if that value is ≤ 0 or below 5% of Astar's q=0 LER.

| Cond | q=0 LER Astar | q=0 LER L2s | Δ estimate | 95th pct | Margin | Pass |
|---|---:|---:|---:|---:|---:|---|
| F2 | 1.010e-3 | 0.720e-3 | −2.90e-4 | −1.85e-4 | 5.05e-5 | yes |
| P2 | 0.475e-3 | 0.150e-3 | −3.25e-4 | −2.60e-4 | 2.37e-5 | yes |
| P4 | 2.840e-3 | 1.490e-3 | −1.35e-3 | −1.21e-3 | 1.42e-4 | yes |

In every condition, L2s is also better than Astar at q=0, i.e. on burst-free noise.

## Error counts (200,016 shots per cell; q = 0 / 0.01 / 0.02)

| Cond | Astar | L2s | L2o | A_nominal |
|---|---|---|---|---|
| F2 | 202 / 207 / 233 | 144 / 173 / 175 | 132 / 173 / 166 | 244 / 1336 / 2265 |
| P2 | 95 / 141 / 179 | 30 / 29 / 41 | 29 / 32 / 38 | 60 / 564 / 1031 |
| P4 | 568 / 691 / 750 | 298 / 317 / 306 | 291 / 317 / 312 | 549 / 1572 / 2448 |

## Secondary contrasts (reported, not gated)

- **L2s − L2o** (static prior vs true-q oracle), nonzero q:
  - F2: +2.2e-5 [0.0, +4.5e-5];
  - P2: 0.0 [−1.2e-5, +1.0e-5];
  - P4: −1.5e-5 [−3.5e-5, +0.5e-5].

  So the static prior costs essentially nothing relative to knowing q. At q=0, L2o is slightly better in F2 and P4, because its DEM then has no burst terms.
- **L2s − A_nominal** is strongly negative everywhere at nonzero q. This is expected: A_nominal ignores the bursts.
- **P2:** Astar's selected q_dec of 0.0025 makes it worse than A_nominal at q=0 (95 vs 60 errors). This is the price of the in-sample Step D rule, which minimizes total errors over all three q values. L2s beats both.

## Cost

These are mean per-shot decode times in the job, measured under 8-way contention.

| Arm | F2 | P2 | P4 |
|---|---:|---:|---:|
| L2s | 15.4 ms | 13.3 ms | 31.0 ms |
| L2o | 15.4 ms | 13.7 ms | 30.4 ms |

Astar and A_nominal each take well under 0.01 ms per shot. L2s is roughly three to four orders of magnitude slower than matching.

## Interpretation

- The d=5 Phase 2 gain of serial BP+OSD with a static prior over the re-selected strongest static matcher holds under each of three single-factor changes: a different burst family, and lower or higher base noise.
- The size of the gain depends on the regime:
  - **Largest at low p (P2, 78%):** background errors are rare there, so the bursts dominate the error budget.
  - **Smallest for centre_row (F2, 21%):** these bursts have 2-detector signatures, which correlated matching already handles well. Its errors rise only from 202 to about 220 across q.
- None of the conditions reaches the earlier 90–95% target.

## Claim boundaries

- d=5 only, simulation only, and one burst weight (3). The noise model is `model_v14` with 5 rounds of Z-memory.
- ROBUST means the gain holds across these three changes, not across all noise.
- The comparator and the L2s prior for each condition were selected in-sample on Step D development shots. Evaluation used fresh, screened seeds, and nothing was tuned on these results.
- The d=7 STOP stands. These results say nothing about d=7 or about scaling with distance.
- This is not independent confirmation: the same team built and ran the study, from one codebase.
