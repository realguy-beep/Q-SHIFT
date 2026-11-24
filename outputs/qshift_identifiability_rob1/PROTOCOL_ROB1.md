# ROB1 protocol: does IDENT1's local-pair result survive weak bursts, wider noise and rare counts?

**Status: draft for the owner's approval. Nothing is built or computed.** Analytic only: no sampler is compiled. "build ROB1" and "run ROB1" are separate approvals.

ROB1 follows IDENT1 stage 1 (`STAGE1_RESULTS.md`, commit ec637595f). It is exploratory and can only weaken or qualify that result. It cannot confirm it, open HELD, or support a performance claim. DB8 stays VOID with numerical NO ADVANCE; CF2 stays NOT CONFIRMED. IDENT1's harm measure stays withheld.

## 1. Questions

| Q | Question | Stage 1 gap |
|---|---|---|
| R1 | Do pairs still separate when the unknown burst is weak? | computed for F0 only |
| R2 | Do they when the bank states' noise range is wider? | 96% of F1 minima on the grid edge |
| R3 | Is there a rejection bound that needs no Gaussian or χ² approximation for rare pair counts? | F1's M2 unvalidated |

## 2. Disclosure

Written after reading stage 1 in full. The grids, test and criteria below were chosen knowing that F1 minima sit at q = 0.005, that weak bursts hurt F0, and that 16 + 1 classes were accepted under F1. No value under the new grids or the new test has been computed.

## 3. Targets

- **Primary:** the 418 DESIGN classes of weight 1-3.
- **Descriptive:** the 84 SEEN classes, and 200 DESIGN weight-4 classes, the first 200 by SHA-256 of `qshift-rob1:<sorted supports>`.
- HELD is excluded by the same code path and assertion as IDENT1.

Families F0 and F1 as in IDENT1, unchanged. F2 is not used.

## 4. Noise grids

| | Stage 1 | ROB1 |
|---|---|---|
| Background p / p₀ (gate and measurement together) | 0.90-1.10, 5 points | **0.70-1.30, 7 points** (0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30) |
| Bank burst strength q | 0.005-0.02, 5 points | **0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.04** |
| Unknown X | p₀, q = 0.01 | p₀ with **q_X ∈ {0.0025, 0.005, 0.01, 0.02}**, each reported on its own |

- **Second slice, at nominal burst strength:** gate and measurement p varied separately over {0.8, 1.0, 1.2}², for F0 and F1.
- **Edge rule.** Every result whose minimum is at the edge of the p range or at q = 0.0025 or 0.04 is counted as *edge-limited* and shown beside the headline. The grid is not widened again, whatever is seen.
- As q_X falls to zero every burst becomes OFF, so loss of separation from OFF at low q_X is expected and is not a failure. The output is the smallest q_X in the list at which each class separates.

## 5. Measures

**T1 separation.** IDENT1's M1 (A2): J of w = Σ_s⁻¹δ, minimised over the bank grid. Same labels (10.8, 21.6). Same Gaussian caveat.

**T2 exact rejection bound (new, primary).** For one feature f, a single detector's firing or a pair's co-firing, the count in n = 2,000 rows is exactly binomial under any model here, because rows are independent.

1. m is the number of features in the family. For each bank state s, grid point θ and feature f, take the exact two-sided binomial acceptance interval with each tail at most 0.005 / (2m).
2. The acceptance set A_f(s) is the union of these intervals over all θ, taken as the single range from the smallest to the largest value.
3. The test accepts s if every feature's count lies in A_f(s). By the union bound it wrongly rejects s, at any grid point, with probability at most 0.005. This needs no normal approximation and no independence between features.
4. **B(X, s) = min over f of P(count_f ∈ A_f(s) | X)**, exact binomial. Since accepting needs every feature to accept, P(test accepts X as s) ≤ B(X, s).

T2 is valid only for models on the grid (grid points, not between them). It is deliberately weak: a large B does not mean the states are hard to tell apart, because it uses one feature at a time.

**n = 2,000** primary; 4,000 and 12,000 descriptive, for T2 as well.

## 6. Predeclared reading (primary targets, F1, n = 2,000, B ≤ 0.05 against *every* bank state)

| q_X | SURVIVES | PARTIAL | FAILS |
|---|---|---|---|
| 0.01 | ≥ 90% of 418 | 50-90% | < 50% |
| 0.005 | reported with the same cut-offs; does not change the reading at 0.01 | | |

- **SURVIVES:** the pair result holds up without approximations at nominal burst strength, on this grid.
- **PARTIAL:** report which classes fail; no general statement.
- **FAILS:** the stage 1 rejection numbers for F1 are not supported by an exact test. They remain approximate indications and are presented only with that sentence. T1 is still reported.

Also reported: the same for F0; T1 counts per q_X; the distribution of the smallest separating q_X; edge-limited counts; the 17 classes accepted in stage 1, named; X09, E, V06 and X03 (SEEN); which feature attains B, as detector distance and time difference only.

## 7. Checks before results are read (stop if any fails)

| Check | Rule |
|---|---|
| No sampling; HELD closed | as IDENT1 |
| Stage 1 reproduced | with stage 1's grid, T1 equals `F1.json` J for 20 SEEN classes to 1e−6 relative |
| Pair rates | co-firing rates from parities equal brute force on the IDENT1 toy DEM to 1e−12; every rate in [0, 1] |
| Binomial intervals | coverage at the true rate at least 1 − 0.005/m for 200 random (rate, m) pairs, by direct summation |
| Union bound | on a 4-detector toy, the exact probability that T2 rejects the true model is at most 0.005, by enumeration of the multinomial at n = 12 |
| Own states | each bank state at each of its own grid points: the intervals contain its exact mean count for every feature |
| Repeatability | two runs byte-identical |

## 8. Rules

New folder only. Inputs: IDENT1's code at its freeze, imported unchanged, and the files it lists. Freeze before running. Amendments say which sections they override. A failed check is kept and reported. External limits: 4 hours, 8 GB private memory. Expected cost, timed on random matrices of the real sizes: T1 under F1 about 15 minutes for 203 bank points and 2,808 unknown models, plus the second slice; T2 seconds to minutes. If T1 under F1 exceeds them, T1 is reported as not computed and T2 stands alone. No push, PR or merge without approval.

## 9. What ROB1 cannot show

Performance of a controller (T2 is a bound for a test that knows the bank models and grid exactly); harm; anything between or beyond grid points; correlated rows; hardware; other distances. T2 says nothing about exact look-alikes, which no detector test can resolve.

## 10. Decisions for the owner

1. The wider ranges (p ±30%, q 0.0025-0.04).
2. The 90% / 50% cut-offs.
3. Whether Codex reviews this protocol before the build. Recommended: yes, since stage 1 has been seen and IDENT1's protocol needed two amendments.
