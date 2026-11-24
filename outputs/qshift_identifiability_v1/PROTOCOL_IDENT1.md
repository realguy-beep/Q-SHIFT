# IDENT1 protocol: when can detector data tell an unknown burst from a bank state, and does it matter?

**Status: draft for the owner's approval. Nothing is built or computed.** IDENT1 is analytic: Stim builds circuits and detector error models (DEMs), and no sampler is ever compiled. Two separate approvals:

1. **"build IDENT1":** code, tests and freeze. No result is computed for any support, except in the named checks of section 8.
2. **"run IDENT1":** stage 1 only. Stage 2 (the held-out half) needs a third approval.

IDENT1 gives no decoder performance claim, and cannot advance or confirm anything. DB8 stays VOID under its section 8, with descriptive numerical NO ADVANCE. CF2 stays NOT CONFIRMED.

## 1. Questions

| Q | Question |
|---|---|
| Q1 | Which bursts give *exactly* the same detector statistics as each other but need opposite logical corrections? |
| Q2 | For other bursts, how much separation from each bank state do 2,000 detector rows contain, using single-detector, local-pair and all-pair parities, when background and burst strength are uncertain? |
| Q3 | How much of that separation remains for a test that does not know the unknown burst in advance? |
| Q4 | Where a burst is ambiguous with a bank state, would acting on that state harm decoding? |

## 2. What is already known (disclosure)

- All 44 public supports (V01-V12, W01-W16, X01-X16) are **SEEN**. Their marginal distances to the bank were computed for DB8's selection, and some were sampled.
- DB8's U_NEAR harm (X09 read as B) and Codex's post-study X09/B calculation (D117, D119) motivated this study. Neither sets a feature, threshold or range below.
- The nuisance ranges, thresholds and harm cut-off are fixed here. They were written knowing DB1's risk table and DB6-DB8's development results, so stage 1 is exploratory for the SEEN set.

## 3. Model

- d = 5, 5 rounds, 120 detectors, 25 data qubits. Background p₀ = 0.003 for gates and measurement; burst = one correlated X error with probability q = 0.01 after each measurement round (`model_v14.build_candidate_circuit`).
- DEMs use `decompose_errors=False, approximate_disjoint_errors=True`, as in DB8's selection. All statements are about these DEMs.
- Bank: OFF, A, B, C, D. Reference means come from the models, not from DB1's sampled templates. Template error is a separate, reported sensitivity.

**Parity moments.** For a detector set S, m_S = E[(−1)^(parity of S)] = Π(1 − 2p_e) over DEM errors e that flip S an odd number of times. The covariance of two parities is m_(S△T) − m_S m_T. Both are exact for the DEM, so no covariance is estimated.

## 4. Supports: exhaustive, no hand-picking

- **Catalogue:** all 1,003 detector-signature classes (2,621 supports of weight 1-3) in `CLASSES_D5.json`. Supports in one class share a signature, so Q2 and Q3 are computed once per class.
- **Weight 4:** all 12,650 four-qubit supports, grouped by signature in the same way.
- **Split, before any computation:** group classes by orbit under the eight symmetries of the 5×5 data-qubit grid, so that mirror images fall in the same half. A class belongs to the orbit of every support in it, and linked orbits are merged. Sort each merged group's supports and hash `qshift-ident-v1:<sorted supports>` with SHA-256: even first byte = **DESIGN**, odd = **HELD**. If one merged group holds more than 20% of the classes, stop and report; the split rule must then be amended before anything else is computed.
- A class with a SEEN support, and its whole group, is **SEEN**. SEEN is reported separately and never in headline counts.
- Stage 1 computes DESIGN, SEEN and the bank. **HELD is not computed until a decision rule is fixed in writing (stage 2).** Q1 uses catalogue structure only, so it covers everything and is exempt.

## 5. Features, fixed by geometry

| Family | Parities |
|---|---|
| F0 | the 120 single detectors (what DB8's fit used, as rates) |
| F1 | F0 plus every pair with time difference 0 or 1 and spatial offset at most 4 in each detector coordinate |
| F2 | F0 plus all 7,140 pairs (an upper reference, catalogue only) |

No family may be changed or pruned after a result is seen. Nearly singular directions are handled by one rule: eigenvalues below 1e−9 of the largest are dropped and the number dropped is reported.

## 6. Measures

n = 2,000 rows (one block). n = 4,000 and 12,000 are descriptive only.

**Nuisance grid for bank states:** gate and measurement p ∈ {0.90, 0.95, 1.00, 1.05, 1.10}·p₀ jointly, q ∈ {0.005, 0.0075, 0.01, 0.015, 0.02}. OFF has no q. The unknown X is at (p₀, 0.01). A second pass also varies X over the same grid and reports the worst case.

**M1 separation (X known).** J(X, s; F) = min over the grid of n·δᵀ Σ⁻¹ δ, with δ the difference in parity means and Σ the average of the two single-row covariances. The Gaussian approximation to the equal-prior error is Φ(−√J / 2).

**M2 open-set rejection (X unknown).** For the goodness-of-fit statistic against bank state s at its best grid point: the probability of accepting X at the threshold that accepts s itself with probability 0.995. Computed with noncentral χ², with degrees of freedom equal to the retained dimension.

**M3 harm proxy.** Feed each of X's noiseless burst signatures (one per round) to the actual BP+OSD decoder built for bank key k, and to nothing else. ρ(X, k) = 0.01 × (number of rounds decoded to the wrong observable). This is a deterministic decode, not a logical error rate. It ignores background errors and burst pairs.
- Harm of acting on s rather than on static key A: h(X, s) = ρ(X, s) − ρ(X, A).

## 7. Predeclared categories and outputs

| Label (per X, s and family) | Rule |
|---|---|
| ALIASED | identical signatures (Q1) |
| AMBIGUOUS | J < 10.8 (each error above about 5%) |
| MARGINAL | 10.8 ≤ J < 21.6 |
| SEPARATED | J ≥ 21.6 (each error at most about 1%) |
| REJECTABLE | M2 acceptance ≤ 0.05 (reported beside the label above) |
| HARMFUL | h(X, s) ≥ 0.01, at least one extra wrong round |

Reported, for DESIGN and SEEN separately and for weights 1-3 and 4 separately:

1. Q1: the number of classes holding both observable flips, and which bank states are in one.
2. Counts of each label per bank state and family; each X's nearest bank state.
3. **Headline table:** classes not SEPARATED from some s *and* HARMFUL for that s, under F0, F1 and F2. The same table for REJECTABLE.
4. How much F1 and F2 change over F0, with and without nuisance.
5. Pre-labelled reading of the headline table:

| Result | Reading |
|---|---|
| F1 or F2 separates, M2 also rejects | pair features are worth a prospective rule |
| separates in M1, M2 does not reject | an open-set rule needs a restricted alternative set; say so |
| neither | under these features and ranges, abstention is the defensible option |

Counts cover an enumerated set of supports. They are not probabilities that nature produces a burst, and no p values or intervals are attached.

## 8. Checks before results are read (stop if any fails)

| Check | Rule |
|---|---|
| No sampling | every Stim sampler raises in every process |
| Moments | on a small hand-built DEM (at most 12 errors), all m_S equal brute-force enumeration to 1e−12 |
| Covariance | equal to brute force on the same DEM; Σ symmetric and positive semidefinite |
| Class invariance | supports in one class give equal moments to 1e−12, for every class of size > 1 in DESIGN |
| Symmetry | the 5×5 grid map is a bijection on the data qubits and every group lies in exactly one half |
| Harm proxy | on the bank, ρ(s, k) − ρ(s, s) against DB1's 5×5 risk table: at least 18 of the 20 off-diagonal entries within 0.005. If not, M3 and all HARMFUL results are withheld and reported as failed |
| Gaussian approximation | for the bank pairs, M1's error on the single best F0 detector agrees with the exact binomial to a factor of 2. Otherwise M1 is reported as an index only |
| Repeatability | two runs are byte-identical |

X09 against B is run as a named check only to confirm that the code reproduces λ = 28.2 (DB8) and Codex's published rates, after the freeze.

## 9. Rules

- New folder only (`outputs/qshift_identifiability_v1/`). Nothing in v1-v11 or the hotfix is modified.
- Inputs: `CLASSES_D5.json`, the three public burst files, DB1's `TRAINING.json` (risk table, templates), `model_v14`, BP+OSD. No records, archives, seeds, CF1/CF2 data or seal material.
- The freeze pins code, inputs, the split's hash list (names only), package versions and this protocol.
- Any failed check or crash is kept and reported. A rerun after a code fix needs a written amendment approved first. **An amendment must say which sections it overrides, including this one.**
- The hotfix lifecycle is not used: there is no sampling, worker pool or retry. Results are written once to a new folder.
- Resource limits: 4 hours wall clock, 12 GB memory, set from outside. If F2 exceeds either, F2 is reported as not computed.
- Expected cost, unmeasured: F0 and F1 minutes to an hour; F2 up to a few hours (125 dense systems of about 7,260 unknowns at most). A timing rehearsal uses random DEM-free matrices.
- Commit locally, push on request, no PR or merge.

## 10. What IDENT1 cannot show

- **That two bursts cannot be told apart**, except in Q1's exact case. Higher-order parities, time structure across blocks and labelled rows are not studied. AMBIGUOUS means "not separated by this family in this range".
- That a practical controller would reach M1. M1 assumes a known alternative and the best linear statistic.
- Logical error rates, retention, latency, hardware, drift within a block, other distances, or noise outside the grid.
- How often such bursts occur.

## 11. After stage 1

Only if the headline table supports it: write a decision rule (features, thresholds, abstention) using DESIGN and SEEN, freeze it, then ask to open HELD once. A sampled study would still need the P1 items closed, independent verification, its own protocol and approval.

## 12. Decisions for the owner

1. The nuisance ranges (±10% in p, 0.5 to 2 times q).
2. The harm cut-off: one wrong round (0.01).
3. Whether to include weight 4.
4. Whether Codex reviews this protocol before "build".
