# Scalable decoder V3 (pure-NumPy BP+OSD): results

**Pre-registered decision: REVISE.**
- Correctness gates C1–C4 pass.
- The d=3 quality criteria pass by a wide margin.
- The **d=7 runtime gate fails**: the median is 60.7 ms/shot against the required ≤ 50 ms.

All quality evidence is development-only, on already-exposed V1.5 d=3 arrays. No new sampling took place and no new dependency was installed. The protocol is `PROTOCOL.md`, committed at `8e183c319` before any benchmark.

## Correctness (C1–C4): `test_bposd.py`, 8/8 pass

- **C1:** exhaustive-order OSD equals the brute-force most-probable fault vector for every feasible syndrome of three source-authored toy DEMs, and OSD-CS candidates are always syndrome-consistent.
- **C2:** BP marginals equal exact enumeration on tree factor graphs, to within 1e-9.
- **C3 (cross-implementation):** V3's vectorized BP posteriors equal Codex's scalable V2 `FactorBPV2` to within 1e-6 on all of V2's fixture syndromes at d=3, 5 and 7, q ∈ {0, 0.01}.
- **C4:** the matrix columns equal the DEM signatures. Hyperedges and burst mechanisms stay single columns; same-detector/different-logical columns are kept; exact merging and the separator semantics are correct. Impossible syndromes raise an error, and p=0/p=1 are handled. Pure-burst syndromes decode correctly in both variants.

One implementation defect was fixed before the first passing run: a non-contiguous bit-packed view.

## d=3 quality (`QUALITY_D3.json`)

The data are the first 1,000 rows of each of the 72 V1.5 evaluation archives (72,000 rows), with hashes checked against V1.5's committed status. Each root's DEM is built at its frozen q̂, the same model information as V1.5's Bexact.

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero LER |
|---|---:|---:|---:|---:|
| Astar (strongest static matcher) | 200 | 284 | 381 | 1.385% |
| BoffStatic (best V1.3) | 143 | 167 | 165 | 0.692% |
| Bexact (exact logical-class reference) | 91 | 125 | 123 | 0.517% |
| **V3 BP+OSD, primary (min)** | **95** | **124** | **127** | **0.523%** |
| V3 BP+OSD, LC variant | 92 | 125 | 123 | 0.517% |

**Primary variant (min):**
- V3 − Astar = **−0.863 pp**, CI [−0.942, −0.783]; at q=0 it is −0.438 pp.
- V3 − BoffStatic = −0.169 pp, CI [−0.221, −0.121].
- V3 − Bexact = +0.006 pp, CI [−0.017, +0.031].
- **Gap recovery G = 0.993** (threshold 0.50).
- It agrees with Bexact on **99.92%** of shots.

**LC variant:** G = 1.000, with 99.99% agreement. It is reported only and has no decision role.

**What this means:** at d=3 a hypergraph most-probable-fault decoder nearly equals exact logical-class marginalization. The exact decoder's large gain over matching therefore comes **mainly from representing correlated hyperedge mechanisms faithfully, not from degeneracy summation**. That matches V1.4B's finding that mask marginalization changed no prediction. Real d=3 shots needed OSD only 5.5% of the time, because BP's hard decision usually already satisfied the syndrome.

## Feasibility (`FEASIBILITY.json`)

There were 200 deterministic syndromes per distance, made by XOR-ing fixed mechanism patterns of 1–6 faults plus bursts (no RNG). The model is the known-burst-family DEM at q=0.01, on a single process.

| d | Columns | Edges | Median ms/shot | p95 | Max | OSD fraction | Peak traced memory |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 448 | 1,203 | 23.5 | 36.4 | 43.0 | 0.59 | 0.5 MiB |
| 5 | 1,682 | 5,024 | 34.6 | 82.7 | 95.4 | 0.30 | 2.2 MiB |
| 7 | 3,700 | 11,432 | **60.7** | 160.6 | 174.6 | 0.21 | 6.8 MiB |

The memory gate passes easily (≤ 1 GiB). The d=7 runtime gate fails.

**Diagnosis** (separate diagnostic, no decision role): at d=7, BP accounts for 43.8 ms/shot, and **176 of 200 syndromes ran the full 50 iterations without converging**. This is V2's convergence limitation showing up as cost. OSD-CS adds 30.1 ms when it runs. These synthetic syndromes are harder than real d=3 shots, which ran at 5.6 ms/shot with 5.5% OSD use, but the gate was pre-registered on them.

## Limitations

- The quality evidence is d=3 only and uses already-exposed data, so it is not independent.
- d=5/7 accuracy is **not measured**: no exposed d≥5 arrays exist.
- All arms use the known burst support and the DEM's `approximate_disjoint_errors` model.
- Timing is single-process Python/NumPy on this machine, not a latency claim.

## Next step

V3.1 is an engineering revision with identical gates. BP and OSD are batched across shots to remove per-call NumPy overhead, and the decision outputs must be bit-identical to V3. If d=7 still exceeds 50 ms/shot, the remaining option is a compiled implementation: `ldpc`, which requires dependency approval.
