# Stage 5 execution-path benchmark protocol v1

This is a disposable execution benchmark, not Stage 5 evaluation. It was prepared on `main` at `ec4e657b3133978d5c12bc2146f9473709b9b227`, after verifying the v2 readiness freeze and before generating benchmark samples. The frozen Stage 5 code, configuration, protocol, statistical decisions, and result directory are not modified.

## Fixed benchmark workload

- Reuse the v2 Stage 5 execution function in memory, with only its output path, root count, seed map, and diagnostic aggregator replaced for this benchmark.
- Circuit: the frozen rotated distance-3, five-round Z-memory; the five frozen burst probabilities; 40 detectors; one observable.
- Four benchmark roots at each of five conditions; 2,000 calibration detector shots and 2,500 paired evaluation shots per root.
- 20 roots, 90,000 unique **benchmark-only** Stim shots total. Evaluation observables are serialized only to exercise the production archive and aggregate path; they are not used for tuning or Stage 5 inference.
- Fresh benchmark RNG stream allocation: 40 Stim seeds plus one separate runtime-bootstrap seed in `BENCHMARK_SEED_INVENTORY.json`. Seeds are not taken from the Stage 5 inventory. Their numeric values are disjoint from the Stage 5 reserved allocation and from the recoverable nonsealed metadata scan recorded in that inventory.
- End-to-end path includes circuit/DEM construction, detector sampling, profile estimation, adaptive matcher rebuild/cache, fixed/adaptive/reference decoding, prediction validation, compressed atomic NPZ/status writes, and saved-root aggregation.
- A planned process interruption occurs immediately after the first durable calibration checkpoint. A second process must resume that root without sampling its calibration stream again, then finish the benchmark.
- A 300-second benchmark wall limit applies. If exceeded, the benchmark stops; it does not touch the Stage 5 output path.

## Analysis and exclusion

The benchmark reports throughput and resource usage only. It makes no decoder-performance claim. Its descriptive root aggregation uses the actual saved benchmark arrays. It does not call the frozen n=1,210 inferential procedure on an underpowered subset. The saved no-sampling preflight separately times the frozen construction/reference procedure; this benchmark adds that complete preflight duration as a conservative fixed overhead in runtime projections.

The Stage 5 manifest remains `PRETEST_FROZEN_NOT_AUTHORIZED`. The Stage 5 sampler is never invoked with its two guarded sampling flags. No Stage 5 evaluation samples, sealed outcomes, or sealed seed values are read. Benchmark samples remain under this directory and must never be pooled with Stage 5.

## Reproduction

From the repository root, after reviewing `BENCHMARK_FREEZE.json`:

```powershell
python outputs/stage5_execution_preflight_v1/benchmark_runner.py --interrupt-after-first-calibration
python outputs/stage5_execution_preflight_v1/benchmark_runner.py --resume
python outputs/stage5_execution_preflight_v1/audit_benchmark.py
```

The first command is expected to exit with the benchmark's documented interruption code after persisting one calibration batch. The second resumes. These commands do not invoke Stage 5 sampling.
