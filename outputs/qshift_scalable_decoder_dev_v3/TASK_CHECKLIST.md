# V3 task checklist (BP+OSD)

- Branch: `codex/qshift-correlated-decoder-v1-6`. Start HEAD: `09d57f27772e65dbabbd9824e52ae29562d0b434`.
- Remote is 7 commits behind (Codex V1.6b replay, scalable V1/V2), all unpushed.

- ☑ Recovered Git state: clean tree; local HEAD 7 ahead of origin.
- ☑ Reviewed the V1.6b replay closure, scalable V1/V2 protocol, root cause, deterministic results and recommendation.
- ◐ Pre-register the V3 protocol (`PROTOCOL.md`) before implementation and benchmarks.
- ☐ Implement `dem_matrix.py`, `bp.py`, `osd.py` and `decoder.py` (pure NumPy).
- ☐ Correctness gates C1–C4, including the cross-check against V2 `FactorBPV2`.
- ☐ d=3 quality benchmark on 72,000 already-exposed V1.5 rows.
- ☐ d=3/5/7 runtime and memory on deterministic syndromes.
- ☐ Decision (GO/REVISE/STOP), report and local commit (no push).
