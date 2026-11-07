# Latency, memory, and equal-resource design

## Measured rebuild prototype

On the installed Stim 1.16.0 / PyMatching 2.4.0 stack, the small distance-3, five-round Z-memory fixture took **2.291 ms median** and **2.401 ms p95** for DEM plus matching construction over 25 rebuild probes. One 2,048-shot `decode_batch` call took 0.95 ms for the updated matcher and 1.67 ms for the old matcher in that run; this difference is too small and too noisy to interpret as a decoder speed difference. The measurements are saved in [FIXTURE_RESULTS.json](FIXTURE_RESULTS.json).

The process working-set delta was **3.09 MiB** across three persistent model versions plus temporary rebuild probes. This includes native libraries, allocator behavior and process state. It is not an isolated PyMatching graph allocation estimate. Native objects are included in the Windows process working-set reading; separate per-object native memory accounting is unavailable through this PyMatching API.

PyMatching 2.4.0 has no public in-place `set_edge` API. The supported and tested path is constructing a fresh DEM/matcher and atomically swapping references at a completed-block boundary. The code checks detector and observable dimensions before publication. The unit tests reject swaps during an active block.

These timings are a feasibility indication for one small simulated circuit, not hardware-real-time performance. A 2.3 ms rebuild could exceed a short hardware deadline; the actual target controller, block duration, compiler/runtime overhead and activation deadline are unspecified.

## Resource-matched comparison protocol required before any adaptive test

The present feasibility run did **not** execute a periodic baseline. Before a benchmark, freeze and report the following for every policy:

1. **Identical information:** all policies receive the same detector matrices, same completed-history cutoff and same trailing-window length. They never receive the generating regime, current/future detector block, observable labels or simulator parameters.
2. **Estimator work:** run the same estimator/statistic at the same block boundaries for both event-driven and periodic policies. The periodic policy may ignore the trigger output; this makes the trigger-evaluation overhead explicit instead of granting one method extra detector access.
3. **Calibration and data acquisition:** count the exact number of syndrome shots/cycles used for warm-up and each history window. Both policies share the same causal input history and cannot obtain extra calibration shots without charging them.
4. **Graph work:** record DEM-generation calls, matcher-build calls, number of model versions retained, discarded candidate builds, and activation delay. Choose the periodic cadence on independent development schedules so its expected rebuild count matches the event-driven policy’s development mean, subject to the same hard per-schedule update cap. Do not tune cadence on held-out outcomes.
5. **Compute and memory:** record estimator CPU, DEM/matcher build CPU, decode CPU, queue/wait time, peak process working set, maximum simultaneously retained matchers and bytes in the detector ring buffer. Report both permitted budget and realized use.
6. **Latency:** measure event detection time, graph-construction time, validation time and block-boundary activation time separately; include p50/p95/max and censored updates. A proposed requirement is that any accepted model be ready before the next block begins; hardware compatibility cannot be inferred from simulator wall time.

## Remaining resource imbalance

Even with a matched expected rebuild count, an event-driven policy has variable update timing and may use fewer builds on a stationary schedule than a periodic baseline. That is an intended policy difference, but realized CPU and number of active model versions must be reported. Matching expected counts does not make realized resources identical on each test schedule. A second cap-matched analysis should report quality at a shared maximum compute budget. If the relevant budget cannot be matched, the result must be described as a quality-versus-resource trade-off, not a pure policy effect.
