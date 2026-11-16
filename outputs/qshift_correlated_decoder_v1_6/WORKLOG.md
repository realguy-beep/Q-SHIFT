# V1.6 work log

1. 2026-11-16: Sealed the hidden second burst before any learner code existed (`seal_hidden_burst.py`; commitment SHA-256 `caa9fd07b823b8844408fb8ea9f210d149e4c23ad2c6e6761db1dbf6b85fd0e5`; commit `23c0e219b`).
   - **Location correction:** the sealed plaintext is at `C:\Users\LENOVO\Documents\Codex\qshift_v1_6_hidden_burst_SEALED.json`, one level above the worktree folder `2026-11-15/`. The commitment's `sealed_location` text ("beside the worktrees") is imprecise. The hash is unaffected. The file (174 bytes) was listed but never read.
2. Built `learner.py`: signature classes, the Stage 1 parity-moment learner, and the Stage 2 exact-likelihood flip.
   - `tests/test_learner.py` (7 tests, synthetic DEM data only) confirms:
     - the 119 → 15 class collapse, with every class logically ambiguous;
     - the min-weight heuristic is wrong for the known burst;
     - the exact parity factorization;
     - recovery of class and q;
     - "none" is selected on burst-free data;
     - both logical effects are recovered.
   - One fixture bug (a tiny DEM declared no observable) was fixed before the tests passed.
3. Pre-registered the development gate (`PREREGISTRATION_DEV.md`, `dev_gate.py`) before any statistic was computed on real data.
4. Ran the development gate once (300 s). **FAIL on G1** (76.4% vs 95%); G2 98.6% and G3 100% pass. Cause: 500 detector-only rows per root are too few at q=0.01 (22 below threshold, 12 wrong class). The pooled learner was correct in 3/3 studies. Stopped per the pre-registration; see `DEV_GATE_RESULT.md`. The hidden burst is unused and still sealed.
5. Owner approved V1.6b (device-level support). Pre-registered its development gate (`PREREGISTRATION_DEV_V1_6B.md`, `dev_gate_v1_6b.py`) before computing anything. G2' was adjusted to 8 disjoint q=0 pools per study (24 in total), because only 96,000 q=0 rows exist per study.
