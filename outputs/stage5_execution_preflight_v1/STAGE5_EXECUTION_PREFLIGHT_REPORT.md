# Stage 5 Execution Preflight Report

## Decision

**NO-GO for Stage 5 sampling with the current runner.** The benchmark supports the frozen allocation's runtime, memory, and disk feasibility, but the production runner has unresolved execution-safety gaps: concurrent launches are not excluded, the two-hour limit is not enforced through final aggregation, and abrupt interruption inside a sampler call can consume a stream without a durable checkpoint. Repair and revalidate these operational properties in a separately versioned runner before seeking sampling authorization. This is not a change to the frozen scientific protocol.

No Stage 5 evaluation shots were generated. The Stage 5 result directory was absent at the final check. No Stage 5 result data or sealed historical test outcomes were opened. The disposable benchmark did not use Stage 5 seed values. The required Stage 5 no-sampling preflight internally loaded its frozen seed inventory to validate allocation integrity; it did not print or pass those values to a sampler. That preflight behavior is recorded here for transparency.

## Freeze and configuration audit

- Repository branch: `main`.
- Local HEAD and `origin/main`: `ec4e657b3133978d5c12bc2146f9473709b9b227`.
- Stage 5 v2 pre-test freeze: `PRETEST_FROZEN_NOT_AUTHORIZED`; all **53/53** frozen SHA-256 entries matched at the final check. No drift was found in the configuration, protocol, statistical code, source, seed inventory, or frozen Stage 5 evidence.
- Frozen allocation: 1,210 roots in each of five conditions; 6,050 roots; 2,000 calibration plus 2,500 paired evaluation shots per root; 27,225,000 unique shots.
- Frozen primary endpoint: equal-weight mean of four nonzero-condition root-paired adaptive-minus-fixed LER differences, boundary −0.0002, planning alternative −0.0003, one-sided alpha 0.05. The p=0 no-harm endpoint and six-family finite-envelope secondary procedure with Holm correction remain unchanged.
- Frozen resource limits: 7,200 seconds, 2 GiB RSS, and 512 MiB free-disk reserve.
- The earlier 100-root sign-flip/bootstrap method remains historical and is not the active n=1,210 procedure.

## End-to-end benchmark

The benchmark was frozen before sampling in `BENCHMARK_FREEZE.json` and used the production Stage 5 `execute()` path with only the benchmark output location, root count, seed map, and benchmark-only aggregator replaced. It included Stim circuit/sampler setup and sampling, detector-only profile estimation, matcher construction/update, three decoder arms, decoding, validation, compression, atomic checkpoint/status writes, and saved-root aggregation.

- 20 benchmark roots across the five configured probabilities; 2,000 calibration and 2,500 evaluation shots per root; **90,000 unique benchmark-only shots**.
- Fresh benchmark seeds were screened against 11,446 recoverable historical integers in 25 nonsealed metadata sources; no collision was found. The benchmark allocation is disjoint from the Stage 5 reserved allocation. Seed details are confined to the benchmark inventory.
- Planned interruption after the first durable calibration checkpoint: 2,000 shots persisted, 1 calibration sampler call, no in-flight stream left in status. Resume completed the remaining 88,000 shots without resampling calibration. Independent audit verified all 20 roots, 90,000 samples, archive hashes, and predictions by re-decoding: **PASS**.
- Resume invocation: 88,000 shots in 3.415 seconds, 26,352 shots/second, peak RSS 89,014,272 bytes. Timed components included decoder builds 1.913 s, compressed atomic NPZ I/O 0.354 s, atomic JSON I/O 0.191 s, profile estimation 0.185 s, decoding 0.140 s, and Stim sampling 0.019 s.
- Statistics-only synthetic aggregation probe: 226.8 seconds and 115,445,760 bytes peak RSS; the saved frozen no-sampling preflight's 253.35-second runtime is used as the conservative analysis allowance.
- 20 benchmark archives occupied 193,099 compressed bytes (about 9.65 KB/root), projecting to about 58.4 MB compressed at 6,050 roots. The frozen uncompressed upper estimate is about 1.15 GB. Available disk was about 274.8 GB, well above the 512 MiB reserve.

## Runtime and resource projection

The measured integrated throughput projects the 27.225M shots to 1,033 seconds. Adding 253 seconds for conservative statistical setup/aggregation gives **1,286 seconds (21.4 minutes)**. A separate descriptive bootstrap over 19 measured inter-root archive-completion intervals projected 751 seconds total, with a 95% bootstrap interval of 716–786 seconds and a 99% upper estimate of 793 seconds. This interval is a small-sample timing diagnostic, not a guarantee and was computed after the benchmark.

Sensitivity to slower end-to-end throughput, including the same 253-second analysis allowance:

| Slowdown | Projected elapsed time | Within 7,200 seconds? |
|---:|---:|:---:|
| 1× | 21.4 min | Yes |
| 2× | 38.7 min | Yes |
| 4× | 73.1 min | Yes |
| 6× | 107.5 min | Yes |
| 7× | 124.8 min | No |

Measured RSS and analysis RSS were far below 2 GiB. Runtime feasibility is therefore promising, with about 6.7× throughput degradation tolerated under the linear projection. This projection assumes similar per-root costs and does not resolve the timeout enforcement gap below.

## Runner safety audit

1. **Timeout does not cover finalization.** The runner checks elapsed time inside the root loop, then calls `summarize()`, computes archive hashes, writes the archive manifest, and marks the run completed without a deadline check after aggregation. A slow finalization can exceed the configured 7,200-second maximum.
2. **No inter-process lock.** Two authorized invocations can target the same `run` directory, read the same status/checkpoints, sample the same allocated stream, and race over fixed temporary file names. Atomic replacement protects a single completed file from partial reads, but does not provide mutual exclusion or prevent duplicate work.
3. **Interruption is fail-closed, not automatically replayable.** Calibration and evaluation checkpoints are atomically persisted after each completed sampler call. If interruption occurs after an in-flight marker is written but before its checkpoint is durable, resume validation rejects the unresolved in-flight state rather than silently resampling. This protects against undetected duplicates but requires manual investigation/recovery and can leave the authorized run incomplete.
4. **Atomic replacement is not power-loss durability.** Writes use a temporary path plus `os.replace`, without explicit file or directory `fsync`. Process interruption was tested; sudden power-loss durability was not.
5. **Two-hour limit is not hard-bounded across all steps.** Per-root time checks and the runtime projection are useful, but the finalization gap means the current implementation cannot guarantee the frozen wall-clock cap.

The benchmark interruption/recovery check passed for the intended interruption after a durable calibration checkpoint. It does not validate power loss, simultaneous-run exclusion, or recovery from interruption during an active Stim sampling call.

## Reproduction commands

From the repository root in PowerShell:

```powershell
python outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py --preflight
python outputs/stage5_execution_preflight_v1/benchmark_runner.py --interrupt-after-first-calibration
python outputs/stage5_execution_preflight_v1/benchmark_runner.py --resume
python outputs/stage5_execution_preflight_v1/audit_benchmark.py
python outputs/stage5_execution_preflight_v1/analyze_runtime.py
```

The first command must remain a no-sampling preflight. The benchmark commands only use the benchmark inventory and write below `outputs/stage5_execution_preflight_v1/benchmark_run/`. The first benchmark command intentionally returns the documented nonzero interruption code after writing its calibration checkpoint; on this tool invocation it was reported as exit 1, while a direct PowerShell native-exit probe confirmed the Python process returned 75. Do not run the production sampling flags as part of this preflight.

## Integrity and remaining risks

At completion, the 53 frozen Stage 5 hashes still matched, `STAGE5_PRETEST_FREEZE_V2.json` remained `PRETEST_FROZEN_NOT_AUTHORIZED`, `outputs/stage5_secondary_inference_repair_v1/run` did not exist, and the Stage 5 shot count remained zero. The Stage 5 scientific hypotheses, thresholds, allocation, manifest, and results were not modified. The Stage 4C evidence and separate website worktree were not touched.

Before Stage 5 can be considered execution-ready, a versioned runner repair should add an exclusive run lock, enforce the deadline across finalization and all expensive setup, define operator-safe recovery for an interrupted in-flight sampler stream, and strengthen durability if power-loss recovery is required. The repaired runner should pass isolated interruption, duplicate-launch, deadline, and independent saved-array audit tests on benchmark-only seeds. Any such repair requires its own source freeze and preflight; this report does not authorize sampling.
