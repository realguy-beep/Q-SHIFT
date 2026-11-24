# IDENT1: build status and proposed amendment A2

**Status: proposed. Not approved.** The build is stopped before the freeze. M1 and M2 are not implemented, and no separation or rejection value has been computed for any support.

## Section 8 checks so far

| Check | Result |
|---|---|
| No sampling | pass |
| Moments and covariance against brute force (11-error DEM, all 15 parities) | pass, below 1e−12 |
| Covariance symmetric and positive semidefinite (F0, five bank states) | pass |
| Class invariance (F1 moments) | pass for all 1,008 DESIGN classes with more than one support; first and last support of each compared, not every support |
| Symmetry and split (A1) | pass: 1,182 DESIGN, 1,297 HELD, 84 SEEN |
| **Harm proxy against DB1's risk table** | **FAIL: 16 of 20 entries within 0.005; 18 required** |
| Gaussian approximation, repeatability | not run: need M1 |

`test_ident1.py`: 7 of 7 in 208 s. The harm check is `harm.bank_check()`.

## Finding 1: the harm proxy fails

All four failures are state B decoded with another key: proxy 0.000, risk table about 0.010. The proxy decodes burst signatures alone. B's harm does not appear there, so it must come from what the proxy leaves out, such as background errors occurring with a burst. The 12 other entries that pass outside state A compare values of at most 0.002, so they say little.

**Consequence, by section 8:** M3 and every HARMFUL result are withheld and reported as failed. The proxy is not adjusted to pass: any change made now would be chosen after seeing this table. B is also the state DB8's question turned on, so this proxy would have been misleading exactly there.

## Finding 2: sections 6 and 9 contradict each other

M1 averages the covariances of X and s, so it needs a new factorisation for every X, state and grid point: about 128,000. Section 9 costed at most 125. Measured on random matrices on this machine: one F1 system (2,138 features) takes about 7 s by eigendecomposition, so F1 alone would take about 250 hours. F2 is worse. Free memory was 9.5 GB, below section 9's 12 GB limit.

## Proposed change

**Overrides: section 1 (Q4), section 5 (singular-direction rule), section 6 (M1, M2, M3, second pass), section 7 (HARMFUL and the headline table), section 8 (harm-proxy row: closed as failed; Gaussian row: as below), section 9 (cost and memory). Section 11 stands.**

1. **Q4, M3 and HARMFUL are removed** from IDENT1 and reported as failed. A better harm measure would need its own protocol, written without further looks at this table. IDENT1 then says where states are ambiguous, not where that matters.
2. **M1 becomes an achievable linear statistic.** For each s and grid point: w = Σ_s⁻¹δ. With σ_s² = wᵀΣ_s w and σ_X² = wᵀΣ_X w, J = 4n(wᵀδ)² / (σ_s + σ_X)², minimised over the grid. It equals the old J when the covariances agree. It is a valid lower bound on what some linear statistic achieves, under the Gaussian approximation. The thresholds 10.8 and 21.6 are unchanged.
   - It can call a pair AMBIGUOUS that a different statistic would separate.
3. **M2** uses Σ_s, with noncentrality nδᵀΣ_s⁻¹δ. It ignores X's different covariance; this is stated beside the numbers.
4. **Second pass** (X over the grid): F0 only.
5. **Linear algebra:** Cholesky when the estimated reciprocal condition number is above 1e−9; otherwise section 5's eigenvalue rule.
6. **Headline table:** for each family and bank state, the number of DESIGN classes that are AMBIGUOUS, MARGINAL or SEPARATED, and REJECTABLE or not, with the same for SEEN. The readings of section 7 stand.
7. **Gaussian check:** the single best F0 detector for each ordered bank pair, M1 restricted to it against the exact binomial, within a factor of 2 wherever the exact error is at least 1e−6.
8. **Memory limit** 8 GB. F2 runs last, on catalogue classes only, and is reported as not computed if it exceeds 4 hours or 8 GB.

Expected cost: F0 minutes; F1 about half an hour; F2 unknown, probably one to three hours.

## Disclosure

A2 was written after seeing the harm-proxy table and timings on random matrices, and before any M1 or M2 value existed. No feature, threshold or nuisance range changes.
