# Stage 1 full-pipeline resource projection

This projection uses the successful small benchmark in `BENCHMARK_RESULTS_V4.json`; it is not a full-scale execution result. The 3,500 benchmark-only shots used five fresh seeds and did not enter the 3,660,000-shot study allocation.

## Measured bounds

- Benchmark wall time: 3.31 s; the full pipeline projection applies a 2× multiplier to the component sum.
- Conservative full allocation estimate: **133.33 seconds** versus the 7,200-second limit. The projection includes Stim sampling (templates, calibration, scoring), nine-grid and five-arm paired PyMatching decoding, 600 per-root matcher constructions, per-root/pooled profile estimation, representative compressed writes and hashes, and seven 100,000-resample bootstrap contrasts.
- Peak observed process RSS: **708,390,912 bytes** during a synthetic 1.2-million-row detector-feature estimate, below the 2 GiB process limit. Current available RAM after benchmark: 6,047,703,040 bytes.
- Available disk: **264,150,786,048 bytes** after the benchmark.
- Compressed archive-size projection: **11,281,679 bytes (10.76 MiB)**, calculated as 3 template archives + 800 calibration archives + 200 scoring archives + 200 candidate-prediction archives + 600 final evaluation archives, with an additional 2 KiB per each of 1,803 commit markers.
- The configured 5 GiB free-disk reserve is enforced at runtime.

The projection uses a short benchmark and cannot model long-duration thermal throttling, antivirus/indexing delays, or unusual filesystem contention. The runner checks its two-hour limit, RSS ceiling, and free-disk reserve during execution. This supports a bounded development run; it does not demonstrate that the full experiment will necessarily finish in the projected time.

## Sampling accounting

- Benchmark v1: 3,500 non-study shots, successful small path check.
- Benchmark v2: 3,500 non-study shots, failed allocation-accounting step; see `BENCHMARK_FAILURE_V2.md`.
- Benchmark v3: 3,500 non-study shots, failed role-name lookup; see `BENCHMARK_FAILURE_V3.md`.
- Benchmark v4: 3,500 non-study shots, successful full-path/resource projection.
- Stage 1 study shots generated at this report: **0**.
- Stage 5 evaluation shots generated in this task: **0**.

