# V3 task checklist (BP+OSD)

- Branch: `codex/qshift-correlated-decoder-v1-6`. Start HEAD: `09d57f27772e65dbabbd9824e52ae29562d0b434`.
- Remote is 7 commits behind (Codex V1.6b replay, scalable V1/V2), all unpushed.

- ☑ Recovered Git state: clean tree; local HEAD 7 ahead of origin.
- ☑ Reviewed the V1.6b replay closure, scalable V1/V2 protocol, root cause, deterministic results and recommendation.
- ☑ Pre-registered the V3 protocol (`PROTOCOL.md`, commit `8e183c319`).
- ☑ Implemented `bposd.py` (pure NumPy; DEM matrix, vectorized BP, bit-packed GF(2) OSD-CS, LC variant).
- ☑ Correctness gates C1–C4: `test_bposd.py`, 8/8 pass. One defect was fixed: a non-contiguous bit-packed view raised an error before the first pass.
- ☑ d=3 quality on 72,000 already-exposed V1.5 rows (`QUALITY_D3.json`): V3 0.523% vs Astar 1.385% vs Bexact 0.517%; G = 0.993; 99.92% agreement with Bexact.
- ⚠ d=3/5/7 feasibility (`FEASIBILITY.json`): d=7 median 60.7 ms/shot, above the 50 ms gate. BP non-convergence accounts for 44 ms. Memory 6.8 MiB.
- ☑ V3 decision: **REVISE** (`RESULTS.md`).
- ◐ V3.1: batched BP and OSD (engineering only; same gates; bit-identical outputs).
