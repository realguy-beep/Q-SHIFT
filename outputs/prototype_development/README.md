# Q-SHIFT executable development prototype

This development-only package adds a matched-shot demonstration without editing the submitted research files or historic result folders.

## Run

From this directory, with Python plus Stim 1.16, PyMatching 2.4, NumPy, SciPy, and Matplotlib installed:

```powershell
python -m unittest -v test_demo.py
python run_demo.py
python audit_saved.py
python finalize_manifest.py
```

Open `QSHIFT_DEMO.html` in a browser for a genuine shot-by-shot replay. The viewer includes the detector bits, chosen model, predicted logical flip, sampled logical observable, and paired baseline outcomes. The displayed simulated condition is for evaluation interpretation; it is not passed to the adaptive policy.

## Design

Stim generates distance-3, five-round rotated Z-memory circuits. Each shot has 40 detectors and one logical observable. The nine existing PyMatching candidates are reused in their frozen grid order. Index 1 is the Stage 1 pooled fixed baseline; index 4 is nominal; indices 6, 4, and 2 are the condition-matched model settings for data-heavy, nominal, and measurement-heavy noise.

Separate calibration streams estimate three detector-marginal profiles and a 3-by-9 table of decoder residual rates. At runtime, only the immediately preceding completed block's detectors enter the regime estimator. The policy combines its posterior with the calibration utility table and uses a confidence threshold, two-block hysteresis, two-block dwell, a switch penalty, and paired calibration uncertainty. It begins and falls back to pooled decoder 1. Calibration labels are used to estimate decoder utilities; evaluation labels are only used for scoring.

The comparators are identity/no decode, pooled fixed, nominal fixed, adaptive, and a regime-informed diagnostic. Identity predicts no logical flip; it is a decoding baseline, not a physical circuit without error correction. The regime-informed diagnostic receives hidden generating-regime metadata for analysis and is not deployable.

## Noise timing and scope

Each Stim circuit is stationary across its five rounds. A schedule changes the circuit parameters between batches of independent memory experiments. This demonstrates block-level drift and causal selection for a later block. It does not simulate noise changing partway through one five-round circuit or continuous error correction on one persistent encoded state. A hardware-connected within-cycle controller remains future work.

## Evidence

- `config.json`: all noise, sample, policy, and seed settings.
- `DEVELOPMENT_RESULTS.json`: runner aggregates and per-root schedule records.
- `data/calibration_evidence.npz`: calibration detectors, observables, all nine predictions/errors, detector profiles, and utility estimates.
- `data/eval_*.npz`: paired detector/observable arrays, all nine predictions, adaptive predictions, true evaluation regime, block choices, estimates, and posteriors.
- `audit_saved.py`: separate recomputation from the saved NPZ arrays; it rebuilds all nine decoders and checks exact prediction equality.
- `AUDITED_RESULTS.json`, `PER_REPLICATE.csv`, `PER_REGIME.csv`, `DECODER_DISAGREEMENT_MATRIX.csv`, `DEVELOPMENT_FINDINGS.md`: independently recomputed output.
- `QSHIFT_DEVELOPMENT_RESULTS.png`, `QSHIFT_DEMO.html`: measured comparison and interactive real-shot viewer.
- `SEED_INVENTORY.json`, `SEED_SCREENING.json`, `MANIFEST.json`: reproducibility and integrity records.

The seed screening checked 201 recoverable text artifacts for exact collisions with this package's calibration, diagnostic, bootstrap, and 600 evaluation seeds. It cannot reveal unrecorded historical RNG use or state hidden in omitted binary-only artifacts.

All new results are exploratory development evidence. No adaptive advantage or hardware compatibility is claimed.
