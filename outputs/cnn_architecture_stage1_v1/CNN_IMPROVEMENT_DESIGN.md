# Q-SHIFT CNN Improvement Design — Stage 1

## Selection

Two development-only architecture candidates are implemented. Both use real Stim detector coordinates and occupancy, preserve absolute positions by flattening rather than global pooling, accept the frozen PyMatching observable prediction, and predict the residual parity bit. They are alternatives for a later controlled experiment, not validated improvements.

### Candidate A — `ResidualPositionCNNV2`

This candidate keeps the successful position-preserving representation and adds one full 3-D convolutional residual block with an identity skip. A four-channel feature map and a 32-unit head keep its parameter and multiply-add budgets close to the old residual CNN. The explicit PyMatching bit is concatenated only at the compact decision head. The skip path is intended to make optimization of a deeper spatial/round feature representation less brittle. This training benefit remains a hypothesis.

### Candidate B — `FactorizedSpatialTemporalResidualCNN`

This candidate separates local spatial filtering `(1×3×3)` from temporal/round filtering `(3×1×1)` using two depthwise filters inside a residual block. It retains the full position-indexed feature map before the compact head; cross-channel mixing occurs in the stem and dense head. The design may model local space/time structure with fewer parameters; it does not assume the underlying noise is separable or physically independent.

## Capacity and cost check

Counts below are from the deterministic architecture preflight on the actual 40-detector geometry. All weights use float32 in this estimate; this is parameter storage only, not total process/GPU memory.

| Model | Parameters | Float32 parameter bytes | CPU forward median, batch 256 | CPU microseconds/shot |
|---|---:|---:|---:|---:|
| Existing `ResidualPositionCNN` | 13,429 | 53,716 | 4.796 ms | 18.733 |
| `ResidualPositionCNNV2` | 13,041 | 52,164 | 4.704 ms | 18.375 |
| `FactorizedSpatialTemporalResidualCNN` | 12,653 | 50,612 | 4.110 ms | 16.055 |

The preflight runs short CPU and CUDA microbenchmarks with one thread, warm-up forwards, and five timed trials per device (25 CPU forwards or 100 CUDA forwards per trial, batch 256; CUDA uses events). In the final saved run, CUDA medians were 3.651, 3.827, and 3.923 microseconds per shot respectively. The candidates are within 6% of the old CNN's parameter storage; the measured CUDA timings were about 5% and 7% slower, while CPU timings were comparable or faster. Timing varies across runs and batch size, so these are local microbenchmarks, not end-to-end decoder or simulator throughput. A future study should retain measured resource overhead and drop a candidate if any LER benefit does not justify its cost.

## Why other directions were not selected

- **More coordinate channels:** The prior coordinate-channel CNN had 1.689% LER versus 1.267% for the flattened CNN on the same earlier diagnostic; both were worse than PyMatching. Absolute positions are already retained by the flattened head, so another coordinate encoding is not the highest-value first test.
- **Larger pooled CNN:** A 16-channel pooled control improved over the original pooled model but still lagged the position-preserving model in the earlier pilot and PyMatching in the later study. Global pooling discards where a feature occurred.
- **Direct label classifier:** Direct MLP/CNN runs had substantial positive-class imbalance and poor logical error rates. The more promising direction is to model the rare residual correction relative to PyMatching.
- **Unbounded/deeper network or neural training at scale:** Neither data nor results justify increasing compute or complexity yet.

## Data and output convention

Training target: `residual = observable XOR frozen_PyMatching_prediction`. At inference, a thresholded residual bit is combined as `final_prediction = frozen_PyMatching_prediction XOR residual`. The neural modules do not consume observable labels, noise-regime labels, burst flags, or future data. Only the residual models receive the baseline prediction. A direct position CNN remains a separately scored comparator.

The new models are isolated in `cnn_architectures.py`; no dashboard worker or historical experiment code is changed. They are not yet registered as production dashboard models.
