# NS-3 continuation checkpoint — mission stopped by user

Stop recorded: 2026-11-12 22:15:45.035 +05:30 (Asia/Kolkata). Monotonic timestamp: 276768930703 ticks at 10000000 ticks/s. Timed continuation elapsed from the recorded start (2026-11-12 22:07:42.655 +05:30; 271945181862 ticks): 482.375 seconds. Work begun before the timing directive is not included because no start clock was recorded for that earlier interval.

## Current state and integrity

- NS-3 files live in the separate filesystem directory the standalone NS-3 research workspace (absolute path omitted); it is not a Git worktree and has no branch. Source context came from qshift-ns1s-hamld-build-recovery at 3e748c208822bac38a6699017a791857328186dd.
- The NS-1S linked worktree remains on branch qshift-ns1s-hamld-build-recovery at that same commit, with its seven incident/report files staged as previously recorded. NS-3 made no Git, index, commit, push, merge, or PR changes there.
- No protected Stage 5, V2.4 evidence, or outcome files were inspected for NS-3. No sampling, training, or decoder inference was run. No dependencies or system software were installed.
- Preserve the prior NS-1S incident documentation and possible shared-object exposure; no cleanup was attempted.

## Completed

- Read the NS-3 mission and repository instructions.
- Recorded the timed continuation start and machine/environment: Windows 11 build 26300; Python 3.10.18 isolated parser environment and Python 3.12.10 system environment; 16 logical CPUs; approximately 16 GiB RAM. Python 3.12 had Stim 1.16.0, PyMatching 2.4.0, NumPy, SciPy and NetworkX; the isolated Python 3.10 environment had Stim, NumPy and NetworkX. No LDPC package, WSL distribution, Docker/Podman, Bazel/Bazelisk or native compiler toolchain was available.
- Created a source-limited standalone workspace; copied only the Phase 2B
oise_model.py, Phase 3A simulator.py, and three relevant NS-1R reports.
- Made first-pass literature queries covering sparse blossom/PyMatching, belief matching, BP-OSD, union-find, HyperBlossom, Tesseract, tensor-network/MPS, graph neural networks, and learned prior calibration. A complete reviewed literature matrix and citation audit were not finished.
- Implemented a bounded exact MAP logical-class oracle for tiny independent-Bernoulli DEMs and a loopy sum-product factor-graph BP logical-marginal prototype in decoder_prototypes.py.
- Ran python -m unittest -v test_decoder_prototypes from the prototype directory: **15 tests passed** in 0.249 s, including boundaries, logical faults, hyperedges, a degenerate oracle case, exact tie behavior, tree-graph BP/oracle agreement, shape/binary/order validation, immutability, repeatability, zero-probability rejection, and oracle cap. The first attempted test invocation used the wrong module path and failed with ModuleNotFoundError; the corrected command passed.
- Inspected PyMatching 2.4.0 signatures: Matching.from_detector_error_model(..., enable_correlations=...), decode(..., enable_correlations=...), and decode_batch(..., enable_correlations=...) are available.

## Interrupted task / artifact

- enchmark_fixed_fixtures.py was launched to benchmark deterministic fixed-syndrome fixtures and compare ordinary/correlation-enabled PyMatching with the BP prototype. The command was terminated at the user's stop request before completion.
- Its redirection target outputs/qshift_ns3_decoder_research/benchmark_results.json may be empty or incomplete. Its contents were not inspected after termination; treat it as an interrupted, unverified artifact. Do not use any values from it.

## Files created in the standalone workspace

- inputs/ns1r/HAMLD_DEM_SEMANTICS_AUDIT.md
- inputs/ns1r/HAMLD_DETERMINISTIC_DECODER_TESTS.md
- inputs/ns1r/HAMLD_INFORMATION_PARITY.md
- outputs/phase2b_pauli_bias/noise_model.py
- outputs/phase3a_correlated_noise_preflight/simulator.py
- outputs/qshift_ns3_decoder_research/RESEARCH_WORK_LOG.md
- outputs/qshift_ns3_decoder_research/decoder_prototypes.py
- outputs/qshift_ns3_decoder_research/test_decoder_prototypes.py
- outputs/qshift_ns3_decoder_research/benchmark_fixed_fixtures.py
- outputs/qshift_ns3_decoder_research/benchmark_results.json (interrupted/unverified)

## Unfinished

Candidate matrix and scoring; source-verified literature review of at least ten approaches; NS-1 input/output contract tests; model comparison on deterministic fixed fixtures; exhaustive-oracle expanded tests; runtime and memory benchmark results; statistical protocol/power and paper-direction reviews; final reports, source manifest and full reproducibility/privacy audit. No conclusions about decoder superiority or experimental performance were reached.

## Resume instructions

Wait for explicit authorization before resuming. Keep working in this standalone directory (not a linked Git worktree). First preserve this checkpoint and inspect only the interrupted benchmark artifact if authorized; rerun it only after checking script correctness and the user authorizes continuation. Do not fetch, traverse, or enumerate repository objects or protected directories. Continue with deterministic fixtures only; no stochastic shots, training, dependency installation, commit, push, merge, or PR unless separately authorized.

## NS-3A bounded continuation handoff (2026-11-13)

The user authorized this bounded deterministic decoder milestone. Work completed in the same standalone directory; NS-1S remains untouched. The earlier resume instruction above is historical and is superseded only for this NS-3A scope.

- Final deterministic suite: 22 tests passed (`python -m unittest -v test_decoder_prototypes`, 0.251 s).
- Exact small-instance MAP was cross-checked against an independent `Fraction` enumeration across all four syndromes of a four-mechanism model. BP agrees with exact MAP on all syndromes of one small tree graph. Exact MAP remains capped and is not practical on the 448-mechanism Q-SHIFT DEM.
- The repaired fixed-fixture benchmark successfully produced `benchmark_results_ns3a.json`. Q-SHIFT model: 40 detectors, 448 undecomposed approximate DEM mechanisms for BP, 591 decomposed approximate DEM error instructions for PyMatching; five deterministic syndrome rows; 50 BP iterations, 5/5 converged; BP batch 0.520604 s; ordinary/correlation-enabled PyMatching 0.00000880/0.00001027 s. Predictions agreed on these rows only. This is not a truth/accuracy or LER comparison.
- The first benchmark failed because synthetic DEM detector annotations used invalid Stim text syntax; the corrected fixture omits declarations and uses detector IDs targeted in mechanisms. The parser error is in the session transcript. Two subsequent low-iteration benchmark outputs are preserved as `benchmark_results_ns3a_attempt2.partial` and `benchmark_results_ns3a_attempt3.partial`; they show BP nonconvergence at the tested low iteration cap. The older `benchmark_results.json` and `benchmark_results_ns3a.json.partial` remain untouched zero-byte interrupted outputs. No incomplete output was used as final evidence.
- Reports added in this package document correctness, exact-oracle scope, fixed-fixture results, model representation parity, limitations, alternatives and a proposed unexecuted development-only protocol. Recommended next candidate: pinned belief matching, subject to input/output and information-parity preflight. No performance advantage is claimed.
- Last clock sample during completion: 2026-11-13 02:02:19 UTC (07:32:19 Asia/Kolkata). Start of this continuation was not sampled, so elapsed time is unknown and not estimated.
- No sampling, training, protected-data access, seeds, package installs, Git operations, commit, push, merge or PR. Await supervisor review before any further study.
