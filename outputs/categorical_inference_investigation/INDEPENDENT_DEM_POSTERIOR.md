# Exact posterior under the approximate DEM's independent mechanisms

## Interpretation

Stim's DEM file specification defines an `error(p)` instruction as one error mechanism with probability `p`; DEM mechanisms are sampled independently. A `^` target suggests how a complicated mechanism may be decomposed into simpler graphlike mechanisms. For this posterior enumeration, each complete `error(...)` line remains one Bernoulli event, and all detector/logical targets in that line (across separators) contribute their total XOR parity. We do **not** turn separator components into separate independent fault events. This follows the documented event semantics. See the [Stim detector-error-model format](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md).

The toy DEM contains six events at probability 0.03, so all `2^6=64` event subsets were enumerated exactly. The independent-DEM mass sums to 0.9999999999999998. Separator-removal checks later confirm the same per-event probability and detector/logical masks.

## Joint and conditional posteriors

`P(L0=1 | s)` is the posterior probability of a logical flip given the detector syndrome. The two exact models use the same tie rule: if posterior masses are within `1e-15`, choose the smallest observable bit pattern (0).

| Syndrome `D1D0` | Categorical P(s,L0=0) | Categorical P(s,L0=1) | Categorical P(L0=1|s) | DEM P(s,L0=0) | DEM P(s,L0=1) | DEM P(L0=1|s) | Both exact MAP |
|---|---:|---:|---:|---:|---:|---:|---:|
| 00 | 0.82900000 | 0.00180000 | 0.00216659 | 0.83386810 | 0.00169362 | 0.00202692 | 0 |
| 01 | 0.02820000 | 0.02820000 | 0.50000000 | 0.02740638 | 0.02740638 | 0.50000000 | 0, tie |
| 10 | 0.02820000 | 0.02820000 | 0.50000000 | 0.02740638 | 0.02740638 | 0.50000000 | 0, tie |
| 11 | 0.00180000 | 0.05460000 | 0.96808511 | 0.00169362 | 0.05311914 | 0.96910172 | 1 |

The total-variation distance between the two joint `(syndrome, L0)` distributions is 0.00486810. Despite this distributional change, there are zero categorical-MAP versus DEM-MAP decision disagreements among the four syndromes. Both exact decoders have risk 0.0600 when evaluated under the original categorical channel. Exact DEM-MAP risk under the independent DEM itself is 0.0582; that cross-model number is not a paired performance comparison.

## Decoder comparison

| Decoder / posterior | Risk under original categorical channel | Risk under independent DEM channel | Decision at `11` |
|---|---:|---:|---:|
| Categorical exact MAP | 0.06000000 | 0.05820000 | 1 |
| Independent-DEM exact MAP | 0.06000000 | 0.05820000 | 1 |
| PyMatching, separator DEM, standard | 0.11280000 | 0.10962552 | 0 |
| PyMatching, separator DEM, correlations enabled | 0.11280000 | 0.10962552 | 0 |

The exact joint probabilities and predictions are saved in `INDEPENDENT_DEM_RESULTS.json`; graph evidence is in `SEPARATOR_ABLATION.json`.

