# DEM follow-up feasibility decision

## Outcome: **BLOCKED**

The proposed B conversion is unavailable for the frozen Phase 2B circuits and noise model. With Stim 1.16.0, all six calls using `decompose_errors=True, approximate_disjoint_errors=False` raise `ValueError` at a `PAULI_CHANNEL_2` operation. The exact exception and complete circuit stack trace for every condition are in `DEM_CONSTRUCTION_RESULTS.json`.

The error is expected from Stim's model semantics: a DEM contains independent error mechanisms, while these categorical Pauli channels have mutually exclusive alternatives. With the no-approximation flag, Stim refuses to replace those disjoint outcomes by independent mechanisms. The requested B model therefore does not exist under the specified circuit and conversion.

Conversion A succeeds in every condition, and PyMatching 2.4.0 constructs both correlation-disabled and correlation-enabled decoders from it. A's detector/observable coordinates and IDs match the circuits, and the two PyMatching modes have identical graph weights and topology. This verifies A's software usability, not exact representation of the native categorical channel.

Since B has no DEM, there are no B error records, probabilities, separators, or matching graphs to compare. It is therefore impossible to establish that A and B are valid comparable decoder models. The proposed 9-million-shot experiment must not start under this design. No shots were generated in this feasibility gate.

## Statistical gate

The six-stratum signs and weights in the proposed G contrast are correct. The root-level statistic must be constructed as `gₛ,r = (LER_on − LER_off)_A − (LER_on − LER_off)_B` within each condition/root on identical samples, then aggregated with coefficients (+1/2, −1/4, −1/4, −1/4, −1/4, +1/2).

The proposed sign-flip procedure is not an exact randomization test: the decoder arm is not randomly assigned, and a global zero G does not imply symmetric per-stratum root contrasts. A Welch–Satterthwaite root-cluster contrast with a paired, stratum-resampled studentized bootstrap is more defensible, subject to independent roots and adequate root counts.

The previous 60-root power calculation assumes equal family variances and zero covariance from data that contain only family A. Unknown covariance and B variance make that estimate provisional, not a power guarantee. If the technical blocker is resolved, re-estimate the variance of the paired family contrast using independent development/validation data before freezing test sample size.

## Integrity

The audit read the prior follow-up documents, the pilot configuration and frozen Phase 2B generator, then built circuits and DEMs without sampling. It did not alter Phase 2B, the completed correlation pilot, or the mechanism audit. The new output manifest hashes all audit files and relevant source/protocol artifacts.
