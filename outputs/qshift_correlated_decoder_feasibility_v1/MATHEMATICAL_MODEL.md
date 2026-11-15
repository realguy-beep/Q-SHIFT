# Candidate correlated-noise model

## Physical motivation and scope

The single candidate is a synthetic control-sequencer/crosstalk fault: one common cause flips three data qubits together at an `MR` round boundary. This represents a shared pulse or controller disturbance affecting multiple scheduled data operations. It is a **synthetic proxy**, not a hardware-calibrated noise model and not a claim about real quantum hardware.

The fixed data-qubit trio is `(8, 12, 15)`. We selected it from a small deterministic geometry check because its exact Stim response has three detector targets and no observable flip. No stochastic outcomes or logical-error metrics were used to select it. Three other deterministic placements were checked during feasibility only: `(8,10,12)` produced a graphlike two-detector signature; `(1,10,19)` was a zero-syndrome logical signature and was rejected; `(1,3,12)` also produced only two-detector signatures. These checks were not a noise-model performance search.

## Circuit-level definition

Start from the existing Phase 3A / Phase 2B distance-3, five-round rotated Z-memory Stim circuit:

- balanced within-gate Pauli composition;
- gate-fault probability 0.003;
- measurement-flip probability 0.003;
- detector order `D0..D39`, observable `L0`.

Immediately after each of the five `MR` boundaries, append one Stim `CORRELATED_ERROR(q) X8 X12 X15`. Each round's common-cause event is an independent Bernoulli draw with probability `q`. The five event mechanisms are spatially correlated within a round and independent between rounds. There is no cross-round latent persistence in this candidate.

For event indicator `b_r in {0,1}` in round `r`, its detector contribution is `b_r s_r`, with exact signatures derived from a noiseless Stim DEM:

| Round factor | Detector support | Observable parity |
|---:|---|---:|
| 1 | D5, D7, D10 | 0 |
| 2 | D13, D15, D18 | 0 |
| 3 | D21, D23, D26 | 0 |
| 4 | D29, D31, D34 | 0 |
| 5 | D37, D38, D39 | 0 |

The total candidate-burst syndrome is the XOR of the active round signatures. The exact, undecomposed DEM contains a three-detector term for each round. This is not a graphlike single-edge error. On the noisy circuit, Stim can produce a graphlike decomposition with `^` separators; those separators retain component correlation information, and the PyMatching baseline uses correlation-aware construction and decoding. The baseline's decomposition remains an approximation of the original circuit DEM, not an exact circuit-to-decoder equivalence claim.

## Decoder representations

**A — pooled fixed PyMatching.** One q is inferred from all detector-only calibration batches. PyMatching is constructed from the full candidate circuit DEM using `decompose_errors=True`, `approximate_disjoint_errors=True`, and `enable_correlations=True` both at construction and decoding.

**A2 — calibrated-profile PyMatching.** Same decoder and same per-root q estimate used by B, providing a control for scalar parameter adaptation without changing decoder representation.

**B — five-factor burst enumeration plus background matching.** Enumerate all `2^5=32` latent burst subsets. For each subset, XOR its exact three-detector event signatures out of the observed syndrome, decode the residual with a correlation-aware PyMatching model of the same base circuit without the candidate bursts, and score the subset by background matching edge weight plus independent burst-event log-odds. Select the minimum-scoring hypothesis with a deterministic tie rule. The event is retained as one multi-detector factor. This is a tractable finite-factor hybrid, **not exact maximum-likelihood decoding for the entire circuit**.

**C — privileged true-q B.** Same five-factor decoder as B with the generating q supplied. It is an oracle reference only and cannot establish deployable performance.

A, A2 and B receive the same detector-only calibration arrays and generating-noise description. A pools all calibration detector rows across the three prespecified conditions and uses one global q estimate/model for all evaluation; A2 and B use the same root-matched calibration batch and q estimate. A therefore has the larger pooled calibration sample for its globally fixed model, while A2/B are information-matched. The B inference path costs up to 32 residual matching calls per detector row; runtime is measured and this extra cost is not hidden.

## Validity boundaries

The model assumes independent burst indicators across rounds and the exact fixed qubit trio. Its probability calibration, gate/measurement Pauli model and Stim DEM conversion are synthetic. Decoder prediction disagreement is a feasibility measure, not evidence of fewer logical errors. Logical labels are available only to the paired scorer after every decoder has returned predictions for an evaluation batch.
