# Scalable correlated-noise decoder: milestone decision (V3 + V3.1)

**Decision: REVISE.** This covers a candidate that is correct and accurate at d=3 but not yet feasible at d=7.

## Starting state

The branch `codex/qshift-correlated-decoder-v1-6` had local HEAD `09d57f277`, 7 commits ahead of origin (`1202ef0b5`), from Codex's work: the V1.6b replay and reconstruction, and scalable decoder V1/V2 (factor BP, REVISE). The tree was clean. All work below was added as new versioned directories; no frozen evidence was modified.

## What was learned

1. **Why factor BP (V2) failed, and what to do instead.**
   - V2 used BP's product-of-marginals as its logical output, which can be badly wrong (0.58 error vs exact at d=3).
   - Its q=0 nonconvergence is intrinsic to these dense loopy hypergraphs.
   - BP+OSD uses BP only to rank mechanisms and makes an exact GF(2) solve, so neither failure applies.
2. **BP+OSD is correct.** Correctness gates C1–C4 pass, including a cross-implementation match with V2 BP at d=3/5/7 to 1e-6.
3. **BP+OSD is near-exact at d=3** (already-exposed V1.5 data, 72,000 rows): nonzero LER 0.523%, against 0.517% for the exact logical-class decoder and 1.385% for the strongest static matcher. Gap recovery is 0.993, and it agrees with exact on 99.92% of shots. The LC variant matches exact (0.517%, 99.99% agreement).
4. **Scientific finding:** most of the exact decoder's advantage over matching comes from **faithful hyperedge (correlated-mechanism) representation, not degeneracy summation**. A most-probable-fault decoder on the full hypergraph nearly matches marginalization. This is consistent with V1.4B's null result for mask marginalization.
5. **Feasibility.**
   - Memory is fine: 6.8 MiB for V3 at d=7.
   - The runtime gate fails: the d=7 median is 60.7 ms/shot, against the required ≤ 50 ms.
   - **V3.1 (batched BP) was exactly equivalent but slower** (97.4 ms), which disproved the overhead hypothesis: pure-NumPy sum-product BP is compute-bound at d=7.

## Limitations

- The d=3 quality evidence is development-only: already-exposed data, the known burst support, and DEM-level modelling with `approximate_disjoint_errors`.
- **No accuracy at d=5/7 has been measured.** There are no exposed d≥5 arrays, and the V1.4 gate showed that weight-3 bursts mostly stop mattering at larger d. Any d≥5 benefit would have to come from the general hyperedge gain, and that is untested.
- Timing is single-process NumPy on one machine.

## Dependency request

**Install `ldpc==2.4.1`**, the standard compiled BP+OSD (Roffe et al.), into the project's Python 3.12 environment. It is needed to reach d=7 runtime feasibility without changing the algorithm, and it gives an independent implementation to cross-check V3 against.

Proposed plan, pending approval:
1. `py -3.12 -m pip install ldpc==2.4.1`. A cp312 Windows wheel exists on PyPI (about 1.7 MB); a probe download was made without prior approval and deleted, and nothing was installed. ldpc depends on NumPy and SciPy, which are already present. Record the resulting `pip freeze` delta.
2. Pre-register V3.2: an `ldpc.BpOsdDecoder` on the same H/L/p matrices (product-sum BP, the same iterations and damping where ldpc exposes them, OSD-CS order 10).
3. Equivalence: prediction agreement with V3 on the 72,000 d=3 rows and 600 syndromes. Differences are expected, because ldpc's OSD details differ; report them rather than force them to zero.
4. Rerun the unchanged feasibility gate.
5. Roll back with `pip uninstall ldpc` if it is rejected.

## Next experiment requiring approval

Only after a feasibility GO: a pre-registered, fresh-seed **d=5/d=7 development evaluation**. BP+OSD would be compared with the strongest static matcher (and BoffStatic) on the known-burst family, with paired roots, the bootstrap, and a sampling budget set in the protocol. No exact reference exists at d≥5, so the claims would be relative to matching only.
