# Scalability assessment

## Existing Phase 2B circuit size

The saved `outputs/phase2b_pauli_bias/CIRCUIT_VALIDATION.json` reports, for the distance-3, five-round rotated memory circuits, 40 one-qubit categorical channel targets, 120 two-qubit categorical channel locations, and 49 binary measurement-flip targets; there are 40 detectors and one logical observable. For one condition, a complete independent-location fault configuration therefore has

`4^40 * 16^120 * 2^49 = 2^609 = 2124551971267068394758352826209874509318372470908127692797776552801614239443408970956650009060917142675557317944986004061386317350610828957638079915066349407775325083341572876126912512`.

The integer above is the exact product of categorical outcome counts and is about `2.12e183` configurations (184 decimal digits). Direct enumeration is not feasible.

## Inference alternatives

**Exact enumeration** visits every complete fault assignment. With `N=product_i |O_i|` assignments and `L` fault locations, the current implementation takes `O(N*L)` mask-combination work and stores the populated syndrome/logical buckets. It is demonstrated only for the 64- and 256-configuration toys.

**Exact structured inference** could, in principle, sum categorical factors with parity constraints using variable elimination, a transfer-matrix/frontier method, or a tensor network. Its cost depends on induced treewidth and intermediate factor sizes, not just the number of circuit locations. No such implementation, treewidth measurement, or exact d=3 result is provided here. The 40-detector syndrome space alone has `2^40` states; a dense float64 table for every syndrome-observable pair would require 16 TiB. A sparse or structured exact algorithm might avoid dense storage, but that possibility is not evidence of feasibility.

**Approximate inference** could include sampling, truncation, belief propagation, or approximate tensor contraction. Those methods would need quantified approximation error and independent validation; none is implemented in this prototype. A DEM plus PyMatching remains an approximate representation for these categorical `PAULI_CHANNEL_2` channels under the tested Stim conversion settings.

## Bounded next step

If pursued, first extract one-hot detector/observable effects for each location on a small circuit fragment, construct the categorical factor graph, and measure variable-elimination width and memory on reduced round counts. Only then test whether exact structured summation can reach a full distance-3 circuit. Any posterior surrogate or approximate method must be labeled accordingly and compared against exact toy results before larger evaluation. No Phase 2B test samples should be reused for decoder selection.

