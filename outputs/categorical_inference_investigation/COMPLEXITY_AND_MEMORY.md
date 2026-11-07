# Complexity and memory assessment

## Exhaustive fault enumeration

For the five-round circuit, there are 40 four-outcome one-qubit locations, 120 sixteen-outcome two-qubit locations, and 49 binary measurement-fault locations. The full categorical configuration count is

`4^40 * 16^120 * 2^49 = 2^609` (about `2.12e183`).

Direct configuration enumeration is infeasible. This count is exact from channel-location cardinalities; it is not an extrapolated shot count.

## Executed XOR-frontier inference

The executed structured algorithm sums independent categorical factors by XOR convolution, represented in the Walsh domain. For `k=D+O` output parity bits, it stores a dense `2^k` float64 joint array. Grouping local transforms by support reduced the number of frequency-domain factor applications to 26, 59, and 97 groups for rounds 1, 2, and 3. The measured exact-inference state counts were 512, 131,072, and 33,554,432; the three-round result finished in 89.09 seconds with 764 MB peak working set.

This measured solver uses a global parity frontier. Its induced width is `k` bits and its joint factor has `2^k` states. It does not use spatial/temporal locality to shrink the frontier.

## Direct parity graph width estimates

Two symbolic heuristics were evaluated on the raw factor-graph primal graph for rounds 1–3. They estimate dense elimination factors; no such large dense circuit factors were allocated.

| Rounds | Primal graph edges | Min-fill width / max log2 states | Min-degree width / max log2 states |
|---:|---:|---:|---:|
| 1 | 380 | 20 / 57 | 21 / 61 |
| 2 | 1,429 | 41 / 129 | 41 / 128 |
| 3 | 2,476 | 69 / 213 | 70 / 221 |

For the toy factor graphs, the actual dense variable-elimination runs completed under both heuristics (width 4; max intermediate factor states 256 for one-qubit and 2,048 for two-qubit). Circuit min-fill/min-degree values are symbolic width estimates, not completed inference. The structured XOR solver exploits parity algebra and therefore has a different state representation than materializing the direct high-arity parity factors.

## Resource stop

Rounds 4 and 5 were stopped before posterior allocation. At 32 detectors plus one observable, a dense table would require 64 GiB. At 40 detectors plus one observable, it requires 16 TiB. The solver's conservative working-set estimate is four times the dense output plus 64 MiB, far above the 2 GiB per-job cap. These are exact memory arithmetic, not measured allocations.

A locality-aware junction tree or tensor-network factorization may lower the width, but no such circuit-local exact solver was implemented or measured here. Therefore the results do not establish a feasible route to full five-round inference.

