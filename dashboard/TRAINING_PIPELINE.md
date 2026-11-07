# Training and decoder-evaluation pipeline

## Circuit and sampling

The dashboard imports the frozen Phase 2B `noise_model.py` and `decoder_bank.py`; it does not recreate those circuits in dashboard code. The smoke used the rotated distance-3 Z-memory circuit with five rounds, 40 detectors and one logical observable. Its balanced generator used categorical one-qubit Pauli probability 0.003 total (X/Y/Z each 0.001), categorical two-qubit Pauli-pair probability 0.003 total (15 nonidentity Pauli pairs each 0.0002), and measurement flip probability 0.003. Stim samples the actual categorical `PAULI_CHANNEL_1`/`PAULI_CHANNEL_2` circuit. It does not sample from an approximate DEM.

The fixed reference is the archived Phase 2B calibration-selected PyMatching bank model: global decoder index 2 for Z memory, index 0 for X memory. Its DEM uses `decompose_errors=True` and `approximate_disjoint_errors=True`; correlation-enabled PyMatching decoding is requested. The run records circuit, DEM, Phase 2B source and decoder-selection hashes. This baseline is a strong prior fixed model, not a model refit using the current run's held-out labels.

## Inputs, labels and model targets

Each Stim detector row is a 40-element binary vector. The target is Stim's one logical-observable flip bit. The direct MLP is `40 → 128 → 64 → 1`; it maps detector bits to a logical correction prediction. The optional residual MLP takes detector bits plus the frozen PyMatching prediction (`41 → 128 → 64 → 1`) and predicts an XOR correction to that prediction. Both use a sigmoid threshold of 0.5 at inference, binary cross-entropy with logits for training, and AdamW. No noise-regime ID, configured probability, observable label or validation/test label is supplied as an inference feature. The noise settings select the simulator distribution only.

Training is a single streaming pass over mini-batches; the default smoke has 8,000 unique training rows, batch size 256 and 32 gradient steps. The residual target during training is the supervised parity `logical_observable XOR fixed_prediction`. That is a training label, not an inference input. A newly initialized residual model can learn the safe no-op (predict no additional correction), which is why its exact tie with matching on the smoke batch is not evidence of added utility.

## Split order and checkpoints

The default seed root is 1,800,000,001. Training batch seeds are 1,800,000,001–1,800,000,032; validation seeds 1,850,000,001–1,850,000,004; test seeds 1,860,000,001–1,860,000,004; and model RNG seed 1,870,000,001. The archived historical scan contained 2,076 recoverable seed values; this run screened without a collision. Unknown or unrecorded historical seeds cannot be ruled out.

Validation data are generated before optimization and used only for progress reporting. Test samples are generated after the final gradient step and are evaluated once. Validation and test detector/observable arrays and predictions are stored in compressed NPZ files; training batches are streamed and are not retained. Checkpoints atomically store model and optimizer states, scaler state, step counters, loss history, best observed validation LER, and Python/NumPy/PyTorch RNG state. Pause, stop and checkpoint requests are polled at batch boundaries. The unit tests cover these controls and checkpoint resume routing; this smoke did not intentionally interrupt and resume an active run.

## Scoring

For each decoder, residual logical error is `prediction XOR observable`. Identity/no-decode is represented by an all-zero correction prediction; it is a scoring reference, not a claim that a physical machine ran without a QEC circuit. The fixed model, direct MLP and residual model are scored on identical test detector samples and labels. The result includes errors, LER, Wilson 95% shot interval and paired shot-level candidate-only/fixed-only failures, disagreement count and exact McNemar p-value. Those intervals/tests describe a single smoke batch and do not account for independent-root variability. They are not confirmatory statistics.

No adaptive controller or structured neural architecture is implemented here. Neural inference is static for a configured simulator distribution. Changing noise across separate runs is possible through configuration, but within-run nonstationary decoding is not part of this dashboard.
