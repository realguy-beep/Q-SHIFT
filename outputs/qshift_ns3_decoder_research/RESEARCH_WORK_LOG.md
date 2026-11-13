# NS-3 research work log

## Clock and scope note

- Time-managed continuation start: 2026-11-12 22:07:42.655 Asia/Kolkata (2026-11-12 16:37:42.655 UTC).
- Windows monotonic Stopwatch at start: 271945181862 ticks; frequency 10,000,000 ticks/s.
- The NS-3 mission had begun before this added timing directive, so elapsed time before this recorded point is not recoverable from an actual clock reading and is excluded from the timed continuation. No elapsed time will be inferred from tokens or task count.
- Available command limits observed: Windows PowerShell execution; individual commands through the workspace tool return after at most 30 seconds before yielding; web search available. No Linux/container/Bazel toolchain. No agent delegation, sampling, training, or system installation.
- Work is in `the standalone NS-3 research workspace (absolute path omitted)`, a separate filesystem directory with only named source inputs copied in. No Git worktree or object database is used for NS-3 files.

## Phase 1 — environment and evidence boundary (timing begins at recorded continuation)

- Start timestamp: 2026-11-12 22:07:42.655 Asia/Kolkata.
- End timestamp: pending.
- Actual elapsed: pending clock sample.
- Completed: read NS-3 mission and AGENTS.md; relied on existing transcript for NS-1S branch/commit; copied only the Phase 2B and Phase 3A circuit builder files and three relevant NS-1R reports into this isolated directory; inventoried Python/library availability and machine resources.
- Environment evidence: Windows 11 Home build 26300; 16 logical processors; approximately 16 GiB RAM; Python 3.10.18 parser environment has Stim, NumPy, NetworkX but not PyMatching/SciPy; Python 3.12.10 environment has Stim, NumPy, NetworkX, PyMatching, SciPy, but not ldpc or Sinter. WSL2 has no Linux distribution. Docker, Podman, Bazel, Bazelisk, compilers, CMake and Ninja unavailable. No installation attempted.
- Protected data: no protected directory, outcomes, V2.4 artifacts or Stage 5 content accessed by NS-3. The prior NS-1S incident remains preserved and is not edited.
- Tests: no NS-3 tests yet.
- Remaining: targeted literature review, ranking, mathematical model, implementations, deterministic tests, benchmarks, protocol/paper strategy, reproducibility and handoff.
- Decision: work from a source-limited directory because the linked Git worktree shares an object database implicated in the prior incident.

## NS-3A — bounded deterministic decoder development

- Continuation completion observed: 2026-11-13 07:32 Asia/Kolkata (02:02 UTC). An exact start clock sample for this continuation was not taken, so elapsed wall time is not reported.
- Completed: reviewed the preserved checkpoint, prototype, test suite, benchmark, Q-SHIFT builder and NS-1R DEM/information-parity audits; improved the independent-Bernoulli DEM BP prototype with stable log-domain parity messages, damping, convergence diagnostics, iteration limits, deterministic ties and fail-closed decoding; retained a bounded exact logical-class MAP oracle.
- Deterministic tests: final run `python -m unittest -v test_decoder_prototypes` — 22 passed in 0.251 s. Includes independent Fraction enumeration on all syndromes in a tiny model and tree BP/MAP agreement. An earlier mistaken expected parity and a benchmark fixture syntax failure are recorded in the corresponding reports.
- Fixed-fixture benchmark: completed `benchmark_fixed_fixtures.py`; JSON validated. On five fixed Q-SHIFT rows, 40 detectors / 448 BP DEM mechanisms, all five BP rows converged at 50 iterations. BP batch time 0.520604 s; PyMatching ordinary 0.00000880 s and correlation-enabled 0.00001027 s. All three outputs agreed on these five rows. Synthetic cycle DEM results range 0.012350–0.111907 s for BP across 10–80 detectors. These are deterministic runtime/prediction checks, not sampled accuracy results.
- Corrected benchmark generator: removed invalid synthetic detector declaration syntax; split memory tracing from timing; kept the correlation flag consistent at graph construction and decode. Preserved interrupted zero-byte artifacts and the failed benchmark attempt.
- Research/protocol: produced focused alternative decoder assessment and a proposed, unexecuted development-only comparison plan. Recommended a pinned belief-matching feasibility candidate with PyMatching sparse blossom as baseline; no superiority claim.
- No Stim sampling, training, protected-outcome access, evaluation seed creation, package installation, Git operation, or change to NS-1S/other worktrees occurred.
- Remaining: supervisor review; owner to approve practical margin and later study protocol. No stochastic experiment is authorized by this report.
