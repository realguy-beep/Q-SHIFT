# Overnight Training Readiness

## Decision: NO-GO for unattended scale-up

The worker now has streaming data generation, separate train/validation/test seed streams, resumable optimizer/scheduler/RNG checkpoints, atomic writes, best-validation checkpoint restoration, a per-invocation wall-clock limit, and resource telemetry. The 100K prospective configuration passes a collision screen with 397 unique derived seeds and no detected collisions. Its 15,000-shot test allocation is marked reserved and the structured worker has no test-sampling implementation.

Those engineering controls are not enough to justify unattended training. The only real structured-model run used 6,000 training and 3,000 validation shots, one root per regime, and at most two epochs. Direct MLP and unweighted CNN had zero positive recall. The weighted CNN did not produce a useful selected threshold. Residual MLP exactly copied PyMatching and tied its validation LER. The run has not demonstrated a learnable signal or useful advantage. Validation metrics were used for model/threshold selection and are not an independent test.

The 8.91-second run is too short to establish sustained GPU throughput or long-run thermal/resource stability. Peak host RSS was ~1.21 GiB and overall system memory utilization was high during the run. Resume equivalence passed on a small CPU fixture, but a CUDA interruption/restart drill and a multi-hour unattended failure-recovery test have not been performed.

## Recommended next configuration

Do not launch the 100K run overnight yet. First diagnose the class-imbalance and target-learning failure in a bounded development iteration, retain PyMatching as the performance anchor, and use multiple independent train/validation roots. Once the learning path no longer collapses on development data, use the prepared 100K protocol as a supervised, wall-limited run. Keep its 15K test partition unopened until architectures and thresholds are frozen. Do not promote to 1M, 10M, or 100M based on this run.

When later authorized and after the learning gate passes, use `official_100k_config.json`, which currently specifies batch size 128, six candidates, two epochs maximum, checkpoint every 8 steps, and an 8-hour invocation ceiling. The 100K config is prepared only; no 100K shots were generated. Run first with a foreground/supervised session, confirm checkpoint progress and telemetry, and pause cleanly before any unattended continuation.

## Timing estimates and limits

Measured throughput was 9,095 shot presentations/second over 81,000 presentations on the RTX 4050. It includes data generation, matching, four fits, validation, evidence output, and checkpoints, but this is a short-run average and samples were reused across candidates. Approximate scale projections from presentation counts are ~2–6 minutes for the configured 100K budget, ~20 minutes for 1M, ~3.4 hours for 10M, and ~34 hours for 100M. These estimates are highly uncertain and may be optimistic; 100M does not fit a typical overnight window at linear scaling. No 1B mode is implemented or recommended.

## Readiness checklist

| Requirement | Status |
|---|---|
| Structured CNN integrated in dashboard worker | PASS |
| Geometry, round channels, occupancy mask retained | PASS |
| Streamed batch generation; no full-set RAM/VRAM materialization | PASS in tested path |
| Separate, collision-screened train/validation/reserved-test streams | PASS for generated inventories; historical seed coverage is limited to recoverable records |
| Best-validation weights saved and restored | PASS, independently recomputed on validation batches |
| Optimizer, scheduler, RNG, progress checkpoint state | PASS in implementation and unit/resume fixture |
| Deterministic pause/resume equivalence | PASS on tiny CPU fixture; CUDA/long-run crash test remains unverified |
| GPU forward/backward/update | PASS on RTX 4050 |
| Sustained end-to-end throughput / thermal soak | NOT ESTABLISHED |
| Positive-class learning | FAIL in current development run |
| Evidence for superiority over PyMatching | NONE |
| Unattended overnight safety | NO-GO |

No large training job was started. The test stream remains unopened.
