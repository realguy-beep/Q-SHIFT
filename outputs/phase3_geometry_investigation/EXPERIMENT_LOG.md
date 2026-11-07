# Phase 3A pilot experiment log

## Prior phases reviewed

Before implementation, reviewed Phase 1 `REPORT.md` and `PHASE1_AUDIT.md`, plus Phase 2 `REPORT.md`, `config.json`, `EXPERIMENT_LOG.md`, and `run_specialist_study.py`. Phase 1 found strong regime recognition but no guarded adaptive improvement. Phase 2 found X-, Z-, and depolarizing-specialist PyMatching made identical corrections to fixed matching on all sampled repetition-code cases; its validation oracle selected fixed in every case. Those results are preserved in their own directories.

## Geometry and circuit checks

- Used Stim `surface_code:rotated_memory_z`, distance 3, 3 rounds: 9 data qubits, 8 stabilizer ancillas (4 X-type and 4 Z-type), 17 active physical qubits, Stim qubit-index range 0–25 (`num_qubits=26`), 24 detectors, and one `L0` logical-Z observable.
- Stim starts the encoded memory in logical `|0_L>` and repeatedly measures stabilizers before terminal logical-Z measurement. `L0` is the sampled logical-observable flip relative to the ideal circuit; it is an evaluation target, never a decoder input.
- The ideal circuit was sampled for 256 shots: every detector and `L0` bit was zero. Noisy circuits compiled, produced detector/observable arrays of shapes `(256, 24)` and `(256, 1)`, generated DEMs, built PyMatching decoders, and returned one prediction per shot.
- All conditions had identical post-Clifford channel-opportunity counts: 18 channel instructions and 168 participating-qubit opportunities. The model graph had 24 detectors and 75 matching edges. Exact hashes and DEM sizes are in the v3 JSON.

## Noise convention

The generated circuit uses the same ideal gates, rounds, measurement schedule, and detector/observable annotations. Stim's `DEPOLARIZE1/2(p)` locations are transformed to independent `PAULI_CHANNEL_1(pX,pY,pZ)` channels on every participating qubit after the same Clifford operation. `p=0.01` is the total nonidentity probability per participant at each such location. The compositions are X-biased `(0.8, 0.1, 0.1)`, Z-biased `(0.1, 0.1, 0.8)`, depolarizing `(1/3, 1/3, 1/3)`, and held-out mixed X/Z `(0.5, 0, 0.5)`, multiplied by p to obtain channel probabilities. Measurement flips are disabled (`p_measure=0`); there are no measurement-fault opportunities. There are 168 single-qubit participant-fault opportunities per shot in every condition, including data and stabilizer-ancilla participants. This is a controlled circuit-level composition comparison, not a data-qubit-only channel.

Stim DEM export uses `decompose_errors=True, approximate_disjoint_errors=True`; this is an approximation for converting the local Pauli-channel model to matching graph errors. Fixed nominal is depolarizing p=.01. Specialists use their stated composition at the same p. The noise-informed oracle uses the true known test condition's model and is not deployable. No model receives sampled L0 labels.

## Runs preserved

- **v1 failed development run:** outputs are retained, but excluded. The first implementation passed composition fractions (which sum to one) directly as channel probabilities instead of multiplying them by p=.01. This caused excessive noise and residual rates near 50%. The bug was found by inspecting the pilot results and corrected before interpreting results.
- **v2 corrected pilot:** three seeds × 12,000 shots × four conditions, with correct unconditional channel probabilities. Preserved as a checkpoint.
- **v3 checkpoint:** same corrected bounded sampling, plus ideal-circuit zero checks, explicit opportunity metadata, paired confidence intervals, and exact paired tests.
- **v4 reported pilot:** same shot budget, plus an assertion that all four noisy circuits have identical gate/target/annotation structure when channel arguments are ignored. The common structure hash is saved in the result JSON. The v4 run is the one reported; no additional shot budget was used.

## v3 decision

X specialist had 12 prediction disagreements out of 36,000 shots on X-biased noise; residual errors were 2,520 vs fixed's 2,528 (paired count difference −8), with per-seed differences −2, −4, −2. The other differences were 0–6 shots per 36,000 and did not replicate as clear advantages. An unadjusted exact McNemar p=.0386 for X-specialist/X-biased is exploratory; 12 discordant decisions and multiple decoder-condition comparisons make it insufficient evidence. No adaptive selector, classifier, or large run was built.
