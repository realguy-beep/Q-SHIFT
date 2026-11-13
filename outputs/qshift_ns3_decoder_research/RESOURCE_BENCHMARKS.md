# Deterministic fixed-fixture benchmark

## Setup and reproducibility

Reproduce from this directory with `python benchmark_fixed_fixtures.py`; output is JSON. The preserved successful output is `benchmark_results_ns3a.json`. The script constructs the Q-SHIFT d=3, five-round balanced Z-memory circuit at gate/measurement p=.003, bias ratio 10, burst p=.01 on pair (8,10), then deterministically converts it to an undecomposed approximate DEM for BP and a decomposed approximate DEM for PyMatching. It creates one zero syndrome plus four selected single-mechanism syndrome rows. No sampler or logical labels are used.

Machine: Windows 11 Home build 26300; Python 3.12.10 64-bit; Stim 1.16.0; NumPy 2.5.3; PyMatching 2.4.0; 16 logical CPUs; approximately 16 GiB RAM. Timings use `perf_counter`. PyMatching batch timing averages three repeats; BP timing is one measured batch because it is much slower. Construction timing is one run. Python `tracemalloc` peak is measured separately so it does not contaminate latency. It does not include native C++ allocations.

## Q-SHIFT fixed fixture results

| Quantity | Result |
|---|---:|
| Detector bits / observable bits | 40 / 1 |
| Undecomposed approximate DEM mechanisms parsed by BP | 448 |
| Decomposed approximate DEM error instructions given to PyMatching | 591 |
| Deterministic syndrome rows | 5 |
| BP iterations / converged rows | 50 / 5 |
| BP batch time | 0.520604 s |
| PyMatching ordinary batch time | 0.00000880 s |
| PyMatching correlation-enabled batch time | 0.00001027 s |
| Python allocation peak during BP batch | 884,704 bytes |
| ordinary vs correlation-enabled PyMatching prediction disagreements | 0 / 5 |
| BP vs ordinary PyMatching disagreements | 0 / 5 |
| BP vs correlation-enabled PyMatching disagreements | 0 / 5 |

The prediction match is limited to these hand-picked rows. BP has no independent truth label here, and its DEM differs from PyMatching's decomposed DEM. This is not an algorithm-only comparison and does not measure correctness or logical error rate.

## Synthetic graphlike scaling

Deterministic cycle DEMs, zero plus three selected mechanism syndromes, one BP batch timing, and PyMatching means over five batches:

| Detectors | Mechanisms | BP batch (s) | PyMatching ordinary batch (s) | BP converged |
|---:|---:|---:|---:|---:|
| 10 | 21 | 0.012350 | 0.00000726 | 4/4 |
| 20 | 41 | 0.022220 | 0.00000674 | 4/4 |
| 40 | 81 | 0.046710 | 0.00000652 | 4/4 |
| 80 | 161 | 0.111907 | 0.00001156 | 4/4 |

This is a small synthetic scaling check, not representative of all circuit DEMs. Timings are environment-specific and the BP 50-iteration setup is a research prototype, not optimized production code.

## Runtime interpretation

The Q-SHIFT BP timing corresponds to roughly 0.104 s per fixed row for this batch. A naive single-core extrapolation would be about 87 hours for 3.03 million rows, before batching, data generation, analysis, or I/O; because this uses five hand-selected syndromes and one BP timing, treat it only as an order-of-magnitude warning, not a credible runtime forecast. PyMatching is orders of magnitude faster on these fixtures. BP requires substantial optimization or a hybrid design before a large comparison is justified.

The initial benchmark attempt timed out before the harness was repaired. A later attempt exposed invalid detector annotation syntax in the synthetic DEM builder; this was fixed by omitting unnecessary detector annotations because every detector is targeted by an error instruction. The two older zero-byte interrupted outputs remain untouched. The invalid-syntax error is recorded in the session transcript. Two complete low-iteration outputs, `benchmark_results_ns3a_attempt2.partial` and `benchmark_results_ns3a_attempt3.partial`, preserve the observed nonconvergence before using the 50-iteration cap. `benchmark_results_ns3a.json` is the final successful output.
