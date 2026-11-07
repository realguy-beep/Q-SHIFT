# Baseline Fairness Analysis — Correlated-Noise Pilot

## Common evaluation contract

Every comparator must receive the **same detector array** and return a prediction for the same single logical observable. Logical residual error is `prediction XOR observable_label`. Paired evaluation archives must bind each prediction array to the exact detector/observable sample hash. Model fitting, calibration, and threshold selection use separate development partitions; final-development labels are read only for the frozen score. No candidate may receive a hidden burst-occurrence flag, generating-regime label, observable label, or future sample at inference time.

## Planned comparators

| Arm | Decoder construction | Noise information | Purpose and interpretation |
|---|---|---|---|
| Frozen historical PyMatching | Reuse the frozen Phase 2B Z-memory decoder built from the no-burst nominal DEM | No `p_burst`, burst-location, or event-model update | Practical fixed baseline; its model is deliberately blind to the added common-cause event |
| Burst-informed PyMatching | Build from the same circuit plus the declared `CORRELATED_ERROR` burst, with the true synthetic event probability and location; use the same Stim DEM conversion options and `enable_correlations=True` | Receives correct simulation parameters at decoder construction | Informed/model-matched reference, not deployable adaptation. The no-burst vs burst-inclusive DEM comparison measures the value of adding the event mechanism to matching weights/edges |
| Detector-only residual CNN | Train the existing position-preserving residual CNN on training detector arrays and `observable XOR frozen-PyMatching` targets; apply only a threshold frozen on its threshold-selection partition | Learns from detector/label examples during development; at inference receives detector bits only | Candidate learned correction under matched information at scoring; no hidden burst state or true parameter is exposed at inference |

The burst-informed matcher is intentionally privileged relative to a detector-only CNN: it knows the generating burst probability and location. Any advantage must be described as an informed reference. A neural win over the frozen baseline is still not evidence of an adaptive hardware decoder. The two matching arms and the neural candidate decode identical final samples within each condition.

## DEM and graph representation

The Phase 2B generator uses categorical `PAULI_CHANNEL_2` instructions. Stim fails DEM conversion with `approximate_disjoint_errors=False` and explicitly requires `approximate_disjoint_errors=True`; all matching arms therefore use the same frozen settings: `decompose_errors=True, approximate_disjoint_errors=True`. This decomposes/approximates categorical two-qubit mechanisms for graph matching. It is a known modeling limitation and must be reported, not hidden by changing the source channel.

For the selected pair (data qubits 8 and 10), the spatial burst has two-detector graphlike records. Across five rounds the burst-only DEM adds five records: `D8 D10`, `D16 D18`, `D24 D26`, `D32 D34`, and `D36 D38`. The full no-burst and burst-inclusive DEMs both have 40 detectors and one observable; the preflight reported 586 versus 591 error mechanisms and 444 separator-bearing records in the burst-inclusive DEM. The burst event itself remains a single joint mechanism; it is not split into independent single-qubit bursts.

PyMatching 2.4.0 constructed both `enable_correlations=False` and `enable_correlations=True` matchers from the **identical** burst-inclusive DEM (40 detectors, one fault ID). They had identical 147-edge graph counts. On the 256-shot deterministic sample they produced identical predictions (zero disagreements), as expected for this selected graphlike event. The burst-inclusive model differed from the historical no-burst model on 3/256 samples; its smoke LER was 1/256 versus 2/256. These counts only validate plumbing and are not a performance estimate.

## Hypergraph/decomposition boundary

A no-shot structural scan of all 36 data-qubit pairs found graphlike DEM conversion for 27 and a graphlike decomposition failure for 9. An example failure is Stim's message: `Failed to decompose errors into graphlike components with at most two symptoms` (reported component varies by pair, e.g. `D5, D7, D10, L0`). Such mechanisms are effectively hyperedges for this graph-matching interface. The preflight does not discard or rewrite them; the planned feasibility study is limited to the predeclared graph-compatible pair. A future study of a failed pair would require a decoder that supports its full hypergraph/correlated likelihood or a separately justified approximation applied identically to all arms.

## Correlation-aware flag versus reweighting

For the selected two-detector burst edge, enabling PyMatching's correlation-aware option did not change the 256 smoke predictions because the mechanism already maps to a single graph edge. The defensible second baseline is therefore described as **burst-informed / appropriately reweighted PyMatching**: the added edge and probability are supplied by the circuit DEM. Do not claim that the `enable_correlations` switch itself helped. Phase 3B may retain an on/off matching ablation to confirm this behavior on its full paired evaluation, but it is secondary and must not be presented as an independent decoder if predictions remain identical.

## Reproducibility and controls

- Reuse the same Stim detector/observable arrays for every policy per condition/root.
- Recompute all LER and discordances from saved arrays, not only runner counters.
- Hash circuit text, DEM text, model configuration, selection records, and prediction archives.
- Record exact DEM conversion options and Stim/PyMatching versions.
- Preserve the predeclared detector ordering and logical observable ID 0 across arms.
- Report the paired candidate-only and fixed-only failures; a marginal LER difference alone is insufficient.
- Keep calibration, threshold selection, and final-development seed streams disjoint.
- Never use final-development labels to select weights, candidate decoder, or threshold.
