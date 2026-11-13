# NS-4A V2 Engineering Feasibility

**Review basis:** committed V2 runner/statistics and V7 watchdog at `033e98e873d503056b9e9b05a496c3b7cff06ccc`. No runner, sampler, or benchmark was executed.

## V6 benchmark evidence and its availability

The V6 benchmark's expected report path is `outputs/ns4a_v2_final_readiness_v6/benchmark_runs/ce7f2c8c36a86c2f/BENCHMARK_REPORT.json`. It is not present in this active checkout, was absent from the known Q-SHIFT worktrees checked by exact path, and GitHub's committed-file lookup returned 404. V6 run artifacts were local/ignored evidence, not part of the V7 commit. Therefore this pass could not independently re-open or re-hash the actual report.

The preceding review-session record contains these extracted values from that report; they are reproduced here as **previously observed, not freshly verified**:

| V6 measurement | Previously recorded value | Scope / limitation |
|---|---:|---|
| Total wall through archive verification | 10.562 s | One 6,000-shot readiness run, six conditions, not statistical analysis |
| Throughput | 568.1 shots/s | Includes its construction, six sample calls, decoder work and archive/audit path |
| Peak working set | 134,963,200 bytes | One runner process; not aggregate process-tree memory |
| Model catalog construction | 2.536 s | One construction pass |
| BeliefMatching decode time | 0.818 s | Five-arm path's BM arm across 6,000 detector shots |
| Selected PM decode time | 0.0134 s | Same 6,000-shot timing workload |
| Other-mode selected-DEM PM | 0.0189 s | Same workload |
| Nominal correlation PM | 0.0211 s | Same workload |
| Nominal ordinary PM | 0.0142 s | Same workload |
| Archive recovery verification | 0.0254 s | Six detector-only benchmark archives |
| Archives and markers, excluding report | 55,239 bytes | Labels/LER were intentionally absent |

Because the source report is unavailable for reinspection, these values are not sufficient by themselves for a signed readiness or exact reproducibility claim. Recover an independently verifiable copy of the existing V6 report and manifest from its original evidence location; do not recreate or rerun it.

## Workload comparison and runtime uncertainty

The 6,000-shot V6 benchmark performed six 1,000-shot Stim calls, 12 candidate PM decodes per condition (72,000 candidate-prediction rows total), five evaluation-arm decodes per condition (30,000 rows), model construction, archive writes, and recovery verification. It saved detectors and predictions only; no observable labels, logical errors, statistics, or model-selection decision were produced.

V2 would perform 48 selection-root calls over 64,000 shots, decode each selection batch with all 12 candidates (768,000 prediction rows), then 60 evaluation-root calls over 240,000 shots and five arms (1,200,000 prediction rows). Total planned decoder output is 1,968,000 rows versus 102,000 rows in V6, about 19.3 times as many prediction rows. V2 also introduces 108 root transactions, persisted labels and predictions, an independent audit, 100,000 primary bootstrap replicates, primary sign-flip analysis, three 100,000-assignment secondary sign-flips, and a 20,000-replicate selection-rank bootstrap.

A naive total-shot scaling of V6 is `10.562 × 304,000 / 6,000 ≈ 535 seconds`. This is **not a conservative runtime estimate**: V2 has 18 times as many sampler calls, 19.3 times as many decoder-output rows, 108 archive/checkpoint transactions rather than six, and an analysis/finalization phase absent from V6. Root and per-call overhead, file-system latency, and bootstrap time have not been measured on the full path. V6 decoder timings suggest the BM arm is substantially more expensive than individual PM arms, but they do not bound V2 end-to-end time. Full runtime and a high-confidence upper bound remain **UNKNOWN**.

Initialization, sampling, inference, analysis, and archive stages are distinct:

- **Initialization:** V6 reported about 2.536 s for model catalog construction and roughly 0.6 s for evaluation-bank construction across conditions (the latter figure is from the previous session record and not freshly reverified). V2 uses a similar catalog plus six condition-specific evaluation banks, but actual combined time is unmeasured.
- **Sampling:** V6 generation was reported as only milliseconds for six batches; scaling that microbenchmark to 108 root calls is particularly unsafe because fixed per-call, circuit compile, and write costs dominate.
- **Decoding:** V6 reported BM 0.818 s / 6,000 shots and PM arms in the 0.013–0.021 s range / 6,000 shots. V2's unequal selection/evaluation multipliers and extra root boundaries invalidate one-factor scaling.
- **Analysis:** V6 did no inferential analysis. V2's resampling and saved-array audit are unbenchmarked.
- **Persistence:** V6's tiny detector-only archives do not represent V2 archives, which include observables, five-arm predictions, sample IDs, root markers and checkpoint updates.

For decoder-call workload alone, simple per-shot scaling of the previously recorded V6 timing values gives about 32.7 s for the V2 BM arm over 240,000 evaluation shots; about 2.7 s combined for the four PM evaluation arms; and roughly 0.7–0.9 s for the 12 candidate decoders over 64,000 selection shots. This suggests about 36 s for decoder calls, excluding decoder construction, Python/root-call overhead, input copies, saving, auditing and inference-cost variability. It is arithmetic from the prior session record, not a measured V2 workload or a safe deadline bound, and inherits the V6 report availability limitation above.

## Deadline mismatch: execution blocker

The V2 proposal sets `wall_clock_seconds = 1800`. The integrated runner's `ResourceGuard` checks a monotonic elapsed time and a persisted whole-run deadline at phase/root boundaries, and invokes checks around sampling, decoder construction, auditing, statistical analysis, and completion. It does not asynchronously interrupt a blocking Stim call, large analysis operation, filesystem call, or native decoder call while that operation is executing.

V7's Windows watchdog has `MAX_TIMEOUT_SECONDS = 600` and rejects timeouts above 600 seconds. It is a standalone general-process supervisor and the V2 runner does not invoke it. Thus the available audited watchdog cannot supervise the proposed 1,800-second run. Running without it would leave a gap between the cooperative guard checks; using it unchanged would impose a 600-second cap and can terminate a run that the protocol permits to continue. Resolve this with a separately versioned, integrated supervisor that enforces the unchanged 1,800-second bound through analysis/finalization, or obtain approval for a protocol amendment. No execution is ready until that is resolved.

## Memory and disk

V2 config names a 2 GiB `peak_rss_bytes` limit. In `qshift_ns4a_v2_runner/resource_guard.py`, the Windows path obtains `PROCESS_MEMORY_COUNTERS_EX.WorkingSetSize`, a **current process working-set snapshot**, not the peak high-water field and not a process-tree aggregate. Checks occur at explicit runner boundaries; transient peaks between checks can be missed. The Unix path returns `ru_maxrss`, so the semantics also differ by platform. The configured quantity and measured quantity do not match. V6 instead measured `PeakWorkingSetSize` for the runner process, but neither measurement is a Job-level aggregate cap.

The previously recorded V6 value of about 135 MB suggests substantial single-process headroom versus 2 GiB in that small run, but it does not establish V2's peak, a hard cap, or tree-wide usage. Disk reserve is 1 GiB; no current free-disk measurement or V2 full-workload archive total was performed in this review. V6 reported very large free space at the time, but that is historical and not current availability. V2 lacks a demonstrated full-output size budget.

## Checkpoint, seed and recovery controls

The code has meaningful fail-closed properties:

- The sampler capability is created only after a validated execution authorization; the default CLI mode is a deterministic dry rehearsal.
- Production execution checks exact Git HEAD and a clean worktree, immutable execution/protocol/seed bindings, six DEM identities, and the exact 304,000 allocation.
- Seed validation requires exact 48 selection and 60 evaluation root keys, six separately named analysis streams, unique values, and a complete historical collision screen supplied from an approved metadata audit. No such production inventory currently exists.
- A run-directory exclusive lock refuses stale-lock takeover. This is safe against concurrent writers, but a crash can leave a lock requiring reviewed manual recovery.
- Root archives and commit markers are hash-verified; checkpoints bind source/protocol/seed identities and exact sample IDs; the independent auditor reopens all 108 archives and recalculates selection and evaluation totals.
- The winner is written once after all 48 selection roots; evaluation checks the persisted winner and cannot replace it.
- Recovery accepts a committed archive/marker and exact root identity. An ambiguous in-flight call without a complete archive is not silently counted or resampled; it fails closed. This protects against double-counting but may require an owner-reviewed recovery disposition.
- Atomic helpers fsync file contents before `os.replace`; they do not establish full Windows directory-metadata durability under power loss. Treat power-loss durability as residual risk unless an additional validation/guarantee is documented.

These controls are stronger than a simple resumable script, but no full V2 interruption/recovery run was performed. The deterministic rehearsal cannot establish actual sampler interruption behavior or full-scale artifact durability.

## Deterministic full-run rehearsal evidence

The committed `DETERMINISTIC_REHEARSAL_RESULTS_FINAL.json` reports a 108-root, 304,000-row fixture rehearsal completing in 77.525 s, with a 169,439,232-byte resource snapshot and an independent saved-array audit PASS. It explicitly reports 0 Stim sampler calls, 0 generated experimental events, source-defined synthetic fixture rows, and temporary output cleanup. This is useful evidence that the orchestration, archive format, selection freeze, analyzer and auditor complete on deterministic fixtures. It is not a real-sampling benchmark, and the selected fixture candidate or any fixture-derived LER/statistics are not scientific outcomes. The resource field is an end-of-rehearsal snapshot, not measured peak memory or a V2 production bound. The large historical free-disk value in that record is not current capacity.

## Engineering disposition

The V2 software path is well structured for exact identities, paired evidence and fail-closed recovery. Actual V6 microbenchmark numbers are small-workload diagnostics only; the source report is currently unavailable for independent reinspection. Runtime remains unbounded relative to the evidence, the available watchdog is not compatible with the proposed deadline, and the memory guard's Windows metric is mislabeled/mismatched. Treat engineering readiness as **not passed** until these issues are corrected and tested on non-evaluation disposable fixtures, with no scientific protocol changes unless separately approved.
