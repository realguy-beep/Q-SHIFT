# V1.4B decision: GO (development), for a fresh bounded V1.5 evaluation of exact logical-class decoding

All evidence here is **development-only on already-exposed data** (S1 = V1.3 evaluation arrays, S2 = V1.2 evaluation arrays). It is not independent confirmation. Thresholds were committed in `PREREGISTRATION.md` (`c2ec653a7`) before any screen statistic was computed. Candidate C was specified in `WORKLOG.md` (`08652ea01`) before its screen. No new shots were sampled in V1.4B.

## 1. Mathematical analysis (full text: `MATH_ANALYSIS.md`)

- **Boff and BoffStatic are joint most-probable-fault decoders**, MAP over (burst mask, background error) under PyMatching's graph model. They are *not* logical-class MAP.
- The frozen V1.1/V1.2 decoder B (correlations ON) optimizes no fixed model, because its edges and its costs come from different graphs.
- **Gaps from logical-class MAP:**
  - (a) degeneracy (max instead of sum within a logical class);
  - (b) mask min instead of sum;
  - (c) the graph approximation: 254 of 448 d=3 DEM mechanisms are hyperedges, split into independent edges;
  - (f) the q̂ prior;
  - (g) the categorical → independent DEM conversion, which every decoder shares.
- **Correct as modeled:** burst normalization and burst independence.

## 2. Optimality reference and feasibility

- `mld.py` implements exact logical-class (maximum-likelihood) inference for the DEM by variable elimination in detector order.
  - It is checked against brute-force enumeration over every syndrome of 6 random DEMs (to 1e-12), plus merging and burst tests.
  - At d=3 the open width is 11, so the table has 4,096 entries. It runs at **6.5–8.7 ms/shot** single-process in NumPy (about 19 ms/shot with 8 processes contending).
- It is **exact for the DEM**, which approximates categorical two-qubit channels as independent mechanisms at O(p²). It is therefore not called optimal for the circuit.
- **Scaling:** width 28 at d=5 (a 5×10⁸-entry table) and 53 at d=7. So this is a d=3 method, not a scalable decoder.

## 3. Screen results (nonzero equal-weight LER; root-paired 95% CI, 20,000 bootstrap replicates)

| Decoder | S1 nonzero LER | S1 q=0 errors /96k | S2 nonzero LER | S2 q=0 errors |
|---|---:|---:|---:|---:|
| Astar (best static matching) | 1.392% | 786 | 1.421% | 835 |
| Boff | 0.734% | 481 | 0.715% | 461 |
| **BoffStatic (best V1.3)** | 0.725% | 574 | 0.705% | 552 |
| R_true (DEM-exact, true q; privileged reference) | 0.556% | 361 | 0.534% | 333 |
| **B: DEM-exact at detector-only q̂ (deployable)** | **0.553%** | **361** | **0.533%** | **333** |
| A: mask marginalization | 0.734% (= Boff on every shot) | 481 | 0.715% | 461 |
| C: correlated-consistent residual cost | 1.089% | 675 | not analyzed (stopped at 53/72 roots after C failed S1) | — |
| R_zero (DEM-exact, burst-blind) | 7.05% | 361 | 7.04% | 333 |

- **B − BoffStatic: −0.172 pp on S1** (CI [−0.200, −0.144]; −23.7% relative) and **−0.171 pp on S2** (CI [−0.203, −0.141]; −24.3%). At q=0, B is better by 0.22 pp on both sets.
- **B vs strong matching baselines:** −60.3% vs Astar on S1 (62.5% on S2) and −64.3% vs A2sw on S1.

**Pre-registered criteria for B:**
1. ≥10% reduction: ✔ (23.7%);
2. CI entirely below 0: ✔;
3. q=0 no harm: ✔ (better);
4. ≤50 ms/shot: ✔;
5. S2 same direction, ≥5%: ✔ (24.3%).

The **headroom check also passes** (R_true is 23.3% below best-V1.3). → **GO**.

## 4. Residual-error taxonomy (S1, nonzero q, 192,000 shots; reference R_true)

| Boff failures | Count | Burst-related* |
|---|---:|---:|
| Recoverable (Boff wrong, R_true right) | 551 | 118 (21%) |
| Inherent under DEM (both wrong) | 859 | 147 |
| *(Boff right, R_true wrong)* | 209 | 66 |

\*Burst-related means the burst-blind exact decoder disagrees with R_true on that shot. At q=0, all 186 recoverable Boff failures are background-only by construction.

- **About 80% of the recoverable gap is background inference** (degeneracy and hyperedges), not burst handling. Candidate A's null result confirms that how masks are combined isn't the bottleneck.
- B's 1,062 nonzero failures include 1,058 that R_true also makes. **B sits at the DEM-exact ceiling at d=3**, so further gains in this setup would need a more accurate noise model in the decoder (item g), not better inference.
- The remaining failures are "inherent": R_true is fairly confident on them (mean confidence 0.69) but the true class is the less likely one.

## 5. Candidate designs and negative findings

- **A, mask marginalization:** no effect. The minimum-cost mask carries essentially all of the mask probability mass here.
- **B, joint exact inference:** removes approximations a, b and c together. It is deployable, because it uses only detector-only q̂ and the known burst support, and it is the recommended candidate.
- **C, correlated-consistent residual cost:** much worse. PyMatching's correlation-reweighted solution weight is not a calibrated log-likelihood across masks. This is a recorded negative finding.
- **Not attempted:** BP+OSD and belief-matching, because no library is installed (installing one needs authorization), and tensor-network contraction for d≥5. These are the relevant directions if a *scalable* version of B is wanted.

## 6. Recommendation: bounded V1.5 (needs separate owner authorization)

Run a frozen, fresh-seed evaluation of **B (exact DEM logical-class decoder at per-root q̂)** on the same circuit and burst model as V1.3.
- **Allocation:** V1.3's (24 roots/q, 4,000 eval and 500 calibration shots per root; 324,000 new shots).
- **Arms:** Astar, A2sw and BoffStatic frozen at their V1.3 settings; B; and R_true as a privileged reference.
- **Co-primary, prospective:**
  - B − BoffStatic, with GO only if the 95% CI lies entirely below 0;
  - B − Astar.
- **Pre-registered target endpoint:** the relative reduction of B vs BoffStatic, with the 95% lower bound required to be at least 10%.
- **Safety:** q=0 B − BoffStatic below +0.05 pp.
- **Runtime:** about 288,000 × 7–20 ms ≈ 35–95 min for B, plus about 30 min more for R_true. Splitting across processes is needed, or R_true can be dropped. The cap comes from preflight.
- **Interpretation boundary:** d=3 only, oracle burst support, DEM-level exactness, one synthetic mechanism.

On the owner's 90–95% target: against the strongest matcher, B's development reduction is about 60% (vs Astar), and B is essentially at the DEM-exact ceiling. A larger reduction at d=3 isn't available from inference alone.
