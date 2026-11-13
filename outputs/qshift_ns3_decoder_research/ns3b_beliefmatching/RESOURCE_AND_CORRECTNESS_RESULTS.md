# NS-3B correctness and bounded resource results

## Deterministic correctness

Command:

```powershell
python -m unittest -v test_beliefmatching_adapter
```

Run under the dedicated Python 3.12.10 environment with pinned dependencies. Final suite: **14 tests passed in 1.353 s**. Coverage includes default-disabled construction, toy exact-MAP comparison for all four two-detector syndromes, two-observable output ordering/shape, detector and observable ordering/count checks, sampling-circuit/DEM dimension mismatch, input immutability, invalid output shape/type/binary values, construction failure reporting, model identity separation, repeatability and close behavior, five saved Q-SHIFT fixtures, NS-2C checked-adapter registration with experimental opt-in, upstream alias counterexample versus exact MAP and PyMatching, and a forced BP-nonconvergence fallback case.

Q-SHIFT fixture outcomes: 40 detectors, one observable, 591 decomposed approximate DEM error instructions. The five saved deterministic syndromes yielded zero BM-vs-ordinary-PyMatching disagreements and zero BM-vs-correlation-enabled-PyMatching disagreements. All five BP convergence flags were true at 20 iterations. These five patterns are not representative random samples and carry no logical labels; matching predictions are not a correctness oracle.

The toy exact-MAP test uses the exact same two-independent-mechanism Stim DEM as the oracle and BeliefMatching. Both agree for all four syndromes. This does not establish exactness for loopy Q-SHIFT.

## Resource measurements

Command:

```powershell
python benchmark_beliefmatching.py > benchmark_results_ns3b.json
```

Measurements are fixed-fixture wall-clock seconds from `perf_counter`. Construction includes the upstream model/LDPC graph initialization; warm construction is the mean of two fresh objects after imports. A fresh subprocess probe measures process start through Python imports, circuit/DEM creation, BM construction, and first zero-syndrome prediction. Warm single-row and five-row batch inference are separate. The five-row batch is sequential upstream `decode_batch`; means use 3 BM repeats and 4 PyMatching repeats. Nothing samples Stim.

| Q-SHIFT operation | Seconds |
|---|---:|
| BM first construction after imports | 0.020867 |
| BM warm fresh-construction mean (2) | 0.019332 |
| BM first single row after construction | 0.000154 |
| BM first 5-row batch after one-row warmup | 0.000409 |
| BM warm single-row mean (3) | 0.000048 |
| BM warm 5-row batch mean (3) | 0.000363 |
| PyMatching ordinary construction | 0.001232 |
| PyMatching ordinary first/warm 5-row batch | 0.000030 / 0.000007 |
| PyMatching correlation-enabled construction | 0.001634 |
| PyMatching correlation first/warm 5-row batch | 0.000024 / 0.000008 |
| Fresh subprocess from launch to first BM prediction | 1.755957 |
| Inner fresh-process timer from after import to first prediction | 0.015120 |

Dividing the warm 5-row means by five gives about 73 microseconds/row for BM, 1.4 microseconds/row for ordinary PyMatching, and 1.6 microseconds/row for correlation-enabled PyMatching, for this one fixed syndrome set. Batch-divided values are not independent single-shot measurements. BM is roughly 52x ordinary and 45x correlated PyMatching in this run, while remaining below a millisecond for five Q-SHIFT rows. Construction is about 12–16x PyMatching here.

Synthetic graphlike chains with 10, 40, and 80 detectors (20, 80, and 160 DEM instructions) took BM 0.000067, 0.000089, and 0.000131 seconds per four-row warm batch. Ordinary PyMatching took 0.000004, 0.000004, and 0.000005 seconds; correlation-enabled PyMatching about 0.000006 seconds at each size. All selected rows agreed. These tiny synthetic cases do not predict circuit workloads.

## Memory and limitations

`tracemalloc` Python allocation peak during the final Q-SHIFT BM batch was 1,498 bytes (synthetic cases are in the JSON). These are not total decoder memory: NumPy, SciPy, LDPC, and PyMatching native allocations are not captured, and process RSS was not isolated per decoder. No reliable peak-RAM claim is made.

The Q-SHIFT benchmark rows all converged, so its fallback path is not represented in that timing; a separate 1-iteration deterministic fixture forces nonconvergence and verifies that the adapter returns valid binary output through upstream's reweighted-matching fallback. Fallback runtime and error performance are not characterized.

One benchmark attempt after adding circuit/DEM dimension checks failed because the synthetic scaling cases used an empty Stim circuit with a nonempty DEM. The guard correctly rejected it; the redirected `benchmark_results_ns3b.partial` remains zero bytes. The synthetic fixtures were corrected to carry matching detector/observable dimensions, and the successful result is `benchmark_results_ns3b.json`. Earlier warm/cold snapshots and the alias-collision probe remain preserved under distinct filenames.

Upstream exposes no decoder `close()` method. The adapter's `close()` releases its reference and invokes an optional close method if present; actual native resource reclamation is left to Python/extension object cleanup and is not guaranteed synchronously.
