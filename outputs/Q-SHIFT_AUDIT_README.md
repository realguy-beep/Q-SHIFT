# Q-SHIFT v0.1 audit and reproducible benchmark

## What was inspected

The supplied project is `C:\Users\LENOVO\Downloads\Q-SHIFT_v0.1_starter`. Its original scripts, CSV, and pickle were not modified. The CSV has 150,000 rows and 11 columns. The existing pickle is about 1.97 MB; it was not loaded or treated as a validated decoder artifact.

The circuit in `src/qshift_step1_dataset.py` is Stim's `repetition_code:memory` with distance 3, three rounds, and `after_clifford_depolarization` set to 0.001, 0.003, or 0.006. It has eight detector outputs and one observable. `syndrome_0` through `syndrome_7` match those eight detectors for this exact circuit configuration. `logical_error` is the sampled observable flip (`L0`), not a generic count of all physical or logical faults. The observable is final data-qubit parity relative to the circuit's noiseless reference.

## Dataset and original evaluation caveats

The CSV has 61 unique eight-bit syndrome vectors across 150,000 rows. This is expected to be possible because an eight-bit detector space has only 256 patterns and the physical circuit has structured detector correlations, but the low distinct count means many rows repeat detector patterns. The script reuses a deterministic seed per noise level and records no per-shot ID or generation manifest, so the CSV alone cannot establish sample independence, detect duplicate shot records, or reconstruct exact generation history. Its label counts are 70/50,000, 240/50,000, and 490/50,000 by noise level.

The old Step 3 model uses a random row split, which mixes examples from the same noise regimes and potentially duplicates across train, validation, and test. It does not guarantee independence by simulation batch or generalization to an unseen noise regime. `noise_probability` and `noise_group` should not be inputs to a runtime decoder unless an independently available calibration signal is explicitly part of the deployment design.

Predicting `logical_error` from detectors and XORing that prediction with the observed logical flip is mathematically a residual-label metric, but the flip label is unavailable at runtime. Operationally a decoder maps the observed detector vector to an estimated observable correction; simulator evaluation computes `actual_observable XOR predicted_correction`. The raw observable rate is the before-correction baseline. Comparing an old model's result to a raw rate is meaningful only when both come from the same untouched shots; it does not establish that the model itself is a valid decoder.

## Fresh benchmark

`qshift_step4_benchmark.py` was added under the project `src` directory, without editing the original files. It builds the same three circuits, derives a detector error model from each circuit, and uses PyMatching 2.4.0. It measures 100,000 fresh shots per noise level and seed for matching. Optional ML evaluation uses a separately seeded sample, 60/20/20 stratified train/validation/test split, detector bits only, and selects the threshold minimizing validation residual error; it evaluates the selected threshold once on test. Confidence intervals are 95% Wilson intervals. Fixed seeds and environment package versions make this run repeatable; results are in `qshift_benchmark_results.json`.

| Noise setting | Raw observable rate | Matching residual | ML held-out residual |
|---:|---:|---:|---:|
| 0.001 | 0.133% (133/100,000) | 0.001% (1/100,000) | 0% (0/20,000) |
| 0.003 | 0.489% (489/100,000) | 0.006% (6/100,000) | 0.010% (2/20,000) |
| 0.006 | 0.963% (963/100,000) | 0.045% (45/100,000) | 0.020% (4/20,000) |

These are simulation results for one small repetition-code circuit. The ML results have fewer test shots than matching, so they are noisy and do not show a reliable advantage over matching. In particular, zero observed errors is not a zero true error rate; see the nonzero Wilson upper bounds in the JSON. This is not hardware integration and does not demonstrate adaptive decoder superiority.

## Running it

Install dependencies in the Python environment used for the run:

```powershell
python -m pip install stim pymatching numpy scikit-learn
```

From any working directory:

```powershell
python C:\Users\LENOVO\Downloads\Q-SHIFT_v0.1_starter\src\qshift_step4_benchmark.py --shots 100000 --ml --output C:\path\to\results.json
```

Omit `--ml` to run only the matching baseline. `--shots` controls matching shots and the total independent ML sample at each noise level (split 60/20/20).

## Limitations and next steps

This circuit only models the specified depolarizing channel after Clifford gates; it does not include a complete hardware noise model, leakage, drift, calibration uncertainty, or runtime latency. A defensible fixed-vs-adaptive comparison needs multiple independently generated simulation batches, a prespecified range of noise regimes, matching as the baseline, a calibrated telemetry policy available at decode time, identical held-out shots for paired comparisons, confidence intervals on paired differences, and a locked test set used once. Keep the observable correction separate from simulator-only labels. Record circuit text, package versions, seeds, and all split identifiers in a manifest for future datasets.
