# ROB1 protocol: does IDENT1's local-pair result survive weak bursts, wider noise and rare counts?

**Status: draft 2, build approved by the owner and built (`BUILD_NOTES.md`). Not run.** Analytic only: no sampler is compiled. "build ROB1" and "run ROB1" are separate approvals.

Draft 2 replaces draft 1 (commit aacb27a1e) after a review by its own author, Claude. **That review is not independent**; Codex was unavailable. The noise grids, targets and 90/50 cut-offs are unchanged. Section 11 lists the changes.

ROB1 follows IDENT1 stage 1 (`STAGE1_RESULTS.md`, commit ec637595f). It is exploratory and can only weaken or qualify that result. It cannot confirm it, open HELD, or support a performance claim. DB8 stays VOID with numerical NO ADVANCE; CF2 stays NOT CONFIRMED. IDENT1's harm measure stays withheld.

## 1. Questions

| Q | Question | Stage 1 gap |
|---|---|---|
| R1 | Do pairs still separate when the unknown burst is weak? | computed for F0 only |
| R2 | Do they when the bank states' noise range is wider? | 96% of F1 minima on the grid edge |
| R3 | Is there a rejection bound that needs no Gaussian or χ² approximation for rare pair counts? | F1's M2 unvalidated |

## 2. Disclosure

Written after reading stage 1 in full. The grids, test and criteria below were chosen knowing that F1 minima sit at q = 0.005, that weak bursts hurt F0, and that 16 + 1 classes were accepted under F1. No value for any unknown X under the new grids, model or test has been computed. The review compared the old and new noise models (section 4) for OFF and the four bank states at the nominal point only.

## 3. Targets

- **Primary:** the 418 DESIGN classes of weight 1-3.
- **Descriptive:** the 84 SEEN classes, and 200 DESIGN weight-4 classes, the first 200 by SHA-256 of `qshift-rob1:<sorted supports>`.
- HELD is excluded by the same code path and assertion as IDENT1.

Families F0 and F1 as in IDENT1, unchanged (m = 120 and 2,138 features). F2 is not used.

## 4. Noise model and grids

**Model.** IDENT1 used Stim's `approximate_disjoint_errors`, which treats the exclusive outcomes of `PAULI_CHANNEL_2` as independent (`CORRECTION_1.md`; corrected during the build, draft 2 said `PAULI_CHANNEL_1/2`). Every such channel in this circuit has equal probabilities, so ROB1 replaces each with `DEPOLARIZE1/2` of the same total probability and requires Stim's strict mode. A channel with unequal probabilities stops the run. Moments are then exact for the circuit.

**Main grid.**

| | Stage 1 | ROB1 |
|---|---|---|
| Background p / p₀ (gate and measurement together) | 0.90-1.10, 5 points | **0.70-1.30, 7 points** (0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30) |
| Bank burst strength q | 0.005-0.02, 5 points | **0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.04** |
| Unknown X | p₀, q = 0.01 | p₀ with **q_X ∈ {0.0025, 0.005, 0.01, 0.02}**, each reported on its own |

This is 7 × (4 × 7 + 1) = 203 bank points.

- **Second slice:** bank states at q = 0.01 and OFF, gate and measurement p varied separately over {0.8, 1.0, 1.2}², for F0 and F1. X as in the main grid.
- **The headline uses the main grid only.** The second slice is never merged into it: T1 and T2 are computed on the slice alone and reported beside the headline, with their own T2 intervals.
- The grid is not widened again, whatever is seen.
- As q_X falls to zero every burst becomes OFF, so loss of separation from OFF at low q_X is expected and is not a failure. The output is the smallest q_X in the list at which each class separates.

## 5. Measures

**T1 separation (secondary).** IDENT1's M1 (A2): J of w = Σ_s⁻¹δ, minimised over the bank grid. Same labels (10.8, 21.6). Same Gaussian caveat.
*Edge rule for T1:* a minimum at p / p₀ of 0.70 or 1.30, or at q = 0.0025 or 0.04, is *edge-limited*, counted beside the headline.

**T2 exact rejection bound (primary).** For one feature f, a single detector's firing or a pair's co-firing, the count in n rows is exactly binomial under any model here, because rows are independent.

1. m is the number of features in the family. For each bank state s, grid point θ and feature f, take the exact two-sided binomial acceptance interval with each tail at most 0.005 / (2m).
2. The acceptance set A_f(s) is the single range from the smallest to the largest value of these intervals over all θ in the main grid.
3. The test accepts s if every feature's count lies in A_f(s). By the union bound it wrongly rejects s, at any grid point, with probability at most 0.005. This needs no normal approximation and no independence between features.
4. **B(X, s) = min over f of P(count_f ∈ A_f(s) | X)**, exact binomial. Since accepting needs every feature to accept, P(test accepts X as s) ≤ B(X, s).

*Edge reporting for T2:* T2 takes no minimum over θ. For the feature that attains B, record which grid points set the lower and upper ends of A_f(s), and count those at a grid edge as defined for T1 (for OFF, p only).

T2 is valid only for models on the grid (grid points, not between them). It is deliberately weak: a large B does not mean the states are hard to tell apart, because it uses one feature at a time.

**n = 2,000** primary; 4,000 and 12,000 descriptive, for T1 and T2.

## 6. Predeclared readings (primary targets, F1, n = 2,000, q_X = 0.01)

| | SURVIVES | PARTIAL | FAILS |
|---|---|---|---|
| Classes of 418 that pass | **377 or more** | **209 to 376** | **208 or fewer** |

- **T2 (the reading of ROB1):** a class passes if B ≤ 0.05 against *every* bank state, OFF included.
- **T1 (secondary; cannot change the T2 reading):** a class passes if it is SEPARATED (J ≥ 21.6) from every bank state. Read in the same way, as "approximate".
- At q_X = 0.005 the same counts are shown for both. They do not change any reading.

T2 reading:

- **SURVIVES:** the pair result holds up without distributional approximations at nominal burst strength, on this grid and model.
- **PARTIAL:** report which classes fail; no general statement.
- **FAILS:** the stage 1 rejection numbers for F1 are not supported by an exact test. They remain approximate indications and are presented only with that sentence. T1 is still reported.

Also reported: the same for F0; T1 and T2 counts per q_X; the distribution of the smallest separating q_X (T1 and T2 apart); edge counts; the second slice; the 17 classes accepted in stage 1, named; X09, E, V06 and X03 (SEEN); which feature attains B, as detector distance and time difference only.

## 7. Checks before results are read (stop if any fails)

| Check | Rule |
|---|---|
| No sampling; HELD closed | as IDENT1 |
| Exact model | strict mode succeeds for every bank state and 20 SEEN classes; on a one-gate toy circuit with each channel, parities equal direct summation over the exclusive outcomes to 1e-12 |
| Additivity | base plus burst equals the full exact model, for means and covariance, at four points with gate p ≠ measurement p, to 1e-10 |
| Stage 1 reproduced | with **IDENT1's old noise model** and stage 1's grid, T1 equals `F1.json` J for 20 SEEN classes to 1e-6 relative |
| T1 variance | any fast expansion equals the direct covariance product to 1e-8 relative for 20 (X, point) pairs (a full expansion has 32 terms, not 16) |
| Pair rates | co-firing rates from parities equal brute force on the IDENT1 toy DEM to 1e-12; every rate in [0, 1] |
| Binomial intervals | for 200 random (rate, m) pairs: each tail is at most 0.005 / (2m), and equal ends from a second method (direct summation of the probability mass function) |
| T2 probabilities | B for 50 SEEN (X, s) pairs equals a separate per-feature loop using direct summation to 1e-9 absolute |
| Union bound | 3-detector toy at n = 12, all 50,388 count vectors: the test rejects the true model with probability at most its stated limit, and **rejects a stated wrong model with probability at least 0.5**. The toy's limit and wrong model are fixed in the test file before the freeze. The wrong model's acceptance probability is at most B |
| Broken versions must fail | each of these, inserted on purpose, must make a named check fail: tails of 0.005 without dividing by 2m; interval ends shifted by one; max instead of min over f; one grid point dropped from the union; parity used in place of co-firing |
| Repeatability | two runs byte-identical |

## 8. Rules

New folder only. Inputs: IDENT1's code at its freeze, imported unchanged, and the files it lists. The exact model and separate gate and measurement p are new ROB1 wrappers; IDENT1 files are not edited. Freeze before running. Amendments say which sections they override. A failed check is kept and reported. No push, PR or merge without approval.

External limits: 4 hours, 8 GB private memory. **Cost must be re-timed during the build, on random matrices only, and written into the freeze.** Draft 1's 15-minute figure for T1 under F1 used 16 expansion terms. IDENT1's stored-statistic layout would need about 9.8 GB of disk at ROB1's size, so it must be processed in blocks. If the re-timed T1 under F1 exceeds the limits, T1 is reported as not computed and T2 stands alone.

## 9. What ROB1 cannot show

Performance of a controller (T2 is a bound for a test that knows the bank models and grid exactly); harm; anything between or beyond grid points; correlated rows; hardware; other distances. T2 says nothing about exact look-alikes, which no detector test can resolve.

## 10. Decisions for the owner

1. Build from this draft. The ranges (p ±30%, q 0.0025-0.04) and the 90% / 50% cut-offs, now as counts, stand as in draft 1.
2. Whether to wait for an independent review. Without one, every ROB1 result says the protocol had none.

## 11. Changes from draft 1

| # | Section | Change |
|---|---|---|
| 1 | 4, 7, 8 | Exact noise model in place of the independence approximation; stage 1 is reproduced with the old model |
| 2 | 4, 5 | Headline on the main grid only; second slice separate |
| 3 | 6 | T1 given a predeclared secondary reading |
| 4 | 5 | Edge rule limited to T1; T2 reports the points that set its intervals |
| 5 | 7 | "Own states" check removed (it passed by construction); independent recalculation and broken versions added |
| 6 | 7 | Union check on 3 detectors, and it must reject a wrong model |
| 7 | 6 | Cut-offs as counts |
| 8 | 7, 8 | Cost to be re-timed; separate gate and measurement p need a wrapper; additivity and T1 variance checks added |
