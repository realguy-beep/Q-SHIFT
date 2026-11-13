# NS-4A Resource Estimate

**Estimate only. No sampler or performance benchmark was run for NS-4A.** Values below separate prior tiny-fixture observations from projections.

## Prior observations available

The NS-2D integration report records one construction observation of about 141.9 ms for BeliefMatching, 1.85 ms for ordinary PyMatching, and 2.19 ms for correlation-enabled PyMatching on one distance-3/40-detector DEM. For five fixed detector rows, decoder-reported times were about 0.608 ms for BM and 0.48 ms for correlated PM; the whole paired-harness wall observations were about 0.844 ms for BM and 0.773 ms for correlated PM. These are single tiny-fixture observations, not throughput benchmarks. The NS-3B feasibility report has a separate five-row warm batch observation around 0.363 ms for BM; the different setup and measurement path make it a sensitivity reference only. A fresh process took about 1.756 seconds to reach its first BM prediction, including imports/startup. Native RSS was not measured; Python `tracemalloc` is not total process memory.

## Proposed workload

- Unique Stim shots: 304,000 (64,000 model-selection + 240,000 evaluation).
- Selection candidate predictions: up to 512,000 rows (8 fixed PM configurations × 64,000 selection rows).
- Evaluation predictions: up to 1,200,000 rows (5 reported arms × 240,000 evaluation rows, before deduplication of identical configurations).
- BM evaluation rows: 240,000. At the two prior five-row observations, simple linear scaling gives roughly 17–41 seconds of decoder-reported/harness-equivalent BM inference, excluding process startup, decoder reconstruction, Stim sampling, disk I/O, and Python orchestration. This extrapolation is weak and must not be represented as measured run time.
- Approximate uncompressed evidence at 40 detector bytes/shot: 12.16 MB for detectors, 0.30 MB for one-byte observables, 0.51 MB for eight selection predictions, and 1.20 MB for five evaluation predictions, plus provenance and per-root metadata. Packed detectors would reduce detector storage to about 1.52 MB. A conservative planned disk reservation is 1 GB to allow temporary, checkpoint, and log files.

## Runtime and resource gate

The full Stim sampling, end-to-end runner, peak RSS, and checkpoint path have not been measured on this allocation. A planning envelope of **30 minutes wall time**, **2 GiB process RSS**, and **1 GiB free storage reserved for this run** is proposed as a hard stop, not a verified capacity claim. The observed small-fixture BM component is under one minute by linear arithmetic, but does not bound sampler cost. Before any execution authorization, a separately authorized non-evaluation end-to-end benchmark must exercise Stim generation, all selection decodes, model reconstruction, BM decode, paired scoring, and atomic output. If that benchmark projects above the wall/RSS/storage caps or cannot verify resumability, do not start the pilot.

No GPU is required by the documented CPU PyMatching/BM integration. No CUDA training or CNN work is proposed. Do not install packages as part of this protocol task. The dependency record should use the NS-2D lock: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.2.6, SciPy 1.18.1, BeliefMatching 0.2.0 pinned to commit `4458c278bbec273c8c1a26411dadccc49222f8ef`; verify the actual runtime before any later freeze because the prior integration report recorded a different NumPy version in its runtime summary.

## Uncertainty and stopping

If benchmark throughput is highly variable, use the conservative high-throughput-time bound plus checkpoint/reconstruction overhead; do not reduce the frozen proposal silently. Stop before evaluation sampling if all-condition DEM validation, alias-collision checks, resource monitoring, disk preallocation, or interruption recovery fails. Preserve any separately authorized pilot failure as evidence; do not auto-restart with duplicate seeds.
