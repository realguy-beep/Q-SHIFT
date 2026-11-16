# Scalable decoder development V3: BP+OSD (protocol)

**Committed before any V3 benchmark statistic is computed.** This is a development-only protocol. It authorizes no new sampling, blind evaluation, sealed-data access or dependency installation.

- Branch: `codex/qshift-correlated-decoder-v1-6`, from HEAD `09d57f27772e65dbabbd9824e52ae29562d0b434` (scalable V2 recorded REVISE).

## Why BP+OSD (selection rationale)

V2 found that synchronous factor BP fails to converge on these dense, loopy DEM graphs at q=0 (1/6 fixtures at every d). Its product-of-marginals logical output was badly wrong at d=3 (up to 0.58 error vs exact). BP+OSD avoids both failure modes:
- BP is used only to **rank** mechanisms by posterior fault probability. Convergence is not required.
- The output is a **syndrome-consistent fault vector** from an exact GF(2) solve (ordered statistics decoding). The logical prediction is its exact parity L·e, not a product of marginals.

The DEM maps to a parity-check matrix whose columns are full mechanism signatures. Hyperedges and burst mechanisms stay as single columns, and the logical bit is kept per column. Identical (detectors, logical) mechanisms are merged exactly (XOR of independents). Columns with the same detectors but different logical bits stay separate, which keeps degeneracy visible.

**Not selected:**
- BeliefMatching: unavailable, and its hyperedge semantics are unverified here.
- Tensor-network or exact elimination at d≥5: the measured elimination width is 28 at d=5 and 53 at d=7.

**No new dependency:** the implementation is pure NumPy, so `ldpc` is not installed. It would offer speed, not capability.

## Implementation (V3, frozen settings)

- **BP:** sum-product in the LLR domain, synchronous flooding, damping 0.5, 50 iterations, and the prior LLR log((1−p)/p). These are the same settings as V2, so the two implementations can be cross-checked.
- **Early exit:** if the BP hard decision satisfies the syndrome, it is the solution and OSD is skipped.
- **OSD ranking:** columns are ranked by posterior fault probability, descending. Gaussian elimination over GF(2) picks the pivot set.
- **OSD-CS(λ = 10):** the OSD-0 solution plus every weight-1 flip of the first 60 non-pivot columns and every weight-2 flip within the first 10. The candidate cost is the **prior** weight Σ_{e_j=1} log((1−p_j)/p_j), which is the joint most-probable-fault objective. The minimum-cost candidate is chosen.
- **Variant LC** (pre-declared secondary): among the unique OSD-CS candidates, sum exp(−cost) per logical class and choose the larger class. This is a local degeneracy approximation.
- **Infeasible syndromes**, outside the GF(2) column space, raise an error. p=0 mechanisms are removed; p=1 mechanisms become a fixed affine offset.

## Correctness gates (deterministic; all must pass)

- **C1:** on toy DEMs (at most 12 mechanisms), OSD with exhaustive order returns exactly the brute-force most-probable fault vector for every feasible syndrome, and OSD-CS always returns a syndrome-consistent vector.
- **C2:** V3 BP marginals equal exact enumeration on tree factor graphs, to within 1e-9.
- **C3:** V3 BP posterior LLRs equal Codex V2 `FactorBPV2` posteriors on the V2 deterministic fixtures, to within 1e-6. This is a cross-implementation check.
- **C4:** the H and L columns equal the DEM signatures. Hyperedges stay single columns, and same-detector/different-logical columns are kept. Impossible syndromes raise an error.

## Development benchmark (pre-registered; no sampling)

**Quality, d=3:** the first 1,000 rows of each of the 72 V1.5 evaluation archives (72,000 rows; already-exposed development data; known burst).
- V3 builds the DEM at each root's frozen V1.5 q̂ (`models_frozen.json`), the same model information as V1.5's Bexact.
- It is compared with the saved predictions of Astar (strongest static matcher), BoffStatic (best V1.3) and **Bexact**, the exact logical-class reference at the same q̂.
- **Metrics:** equal-weight nonzero LER, q=0 LER, a root-paired bootstrap (20,000 replicates, seed 20261116), the agreement rate with Bexact, and the **gap recovery** G = (LER_Astar − LER_V3)/(LER_Astar − LER_Bexact).

**Feasibility, d=3/5/7:** runtime and peak memory (tracemalloc) per shot on 200 deterministic syndromes per distance, built by XOR-ing fixed mechanism index patterns (no RNG, no sampler). The model is the known-burst-family DEM at q=0.01.

## Decision rules (prospective; primary = plain OSD-CS)

- **GO:**
  - V3 − Astar nonzero 95% CI entirely below 0;
  - G ≥ 0.50;
  - V3 q=0 LER no more than 0.05 pp above Astar's;
  - median runtime ≤ 50 ms/shot at d=7;
  - peak memory ≤ 1 GiB;
  - C1–C4 pass.
- **REVISE:** C1–C4 pass, but a quality or feasibility criterion fails while V3 still beats Astar (CI < 0).
- **STOP:** any correctness gate fails after repair attempts, or V3 is not better than Astar.

Variant LC is reported against the same criteria but has no decision role.

## Boundaries

- d=3 quality uses already-exposed development data, so it is not independent evidence.
- d=5/7 accuracy is **not** measured, because no exposed d≥5 arrays exist; that requires a separately authorized sampling study.
- All arms here use the known burst support and the DEM's `approximate_disjoint_errors` model.
