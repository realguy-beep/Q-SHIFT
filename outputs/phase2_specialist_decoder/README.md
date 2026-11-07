# Q-SHIFT Phase 2 — Specialist PyMatching Investigation

This directory is separate from Phase 1. No Phase 1 files are modified.

## Scope

Build four composition-specific Stim DEM/PyMatching models (X-dominant, Z-dominant, depolarizing, measurement-only), evaluate every model on the same held-out shots for all six Phase 1 conditions, and decide whether any specialists deserve an adaptive selector. Phase 1 found 94.4% regime recognition but no guarded adaptation advantage; that finding is the baseline and is not assumed to change.

The circuit remains Stim `repetition_code:memory`, distance 3, 3 rounds, 5 qubits, 8 detectors, one `L0` observable. Data fault probability is 0.01 per participating qubit after each CX; measurement flip probability is 0.01 per Z-basis measurement when enabled. Channel compositions and location counts match [Phase 1](../noise_composition_phase/PHASE1_AUDIT.md).

## Model construction

Each specialist gets independent calibration shots. The composition family is known for its calibration source, while total local fault probability is estimated from detector-pattern likelihood over a prespecified p grid using independent Stim reference simulations. Observable labels are not read by the fit. The specialist DEM is then built at the selected probability using `detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)` and `pymatching.Matching.from_detector_error_model`. This is a simulator-calibrated model, not a hardware-calibrated model; its p grid and finite-sample uncertainty are documented.

The fixed baseline is the depolarizing specialist at the same `p_data`. The oracle model per condition is selected by its held-out validation residual rate, with condition knowledge; validation and test shots are independent. All test decoders receive the same detector samples. `L0` labels are used only for validation scoring and final residual computation.

## Run

```powershell
python run_specialist_study.py --seeds 10 --calibration 30000 --validation 10000 --test 30000 --output results\specialist_results.json
```

The run writes one compressed raw NPZ bundle per seed and a SHA-256 manifest. The bounded default run uses 10 seeds. The report states whether Experiment D (detector-based specialist selection) passed the pre-registered usefulness gate. If no specialist shows a credible advantage, no selector is built.

## Artifacts

- `config.json`: model compositions, splits, and gate.
- `run_specialist_study.py`: reproducible model construction and paired analysis.
- `results/`: frozen full result and plots.
- `raw/`: calibration, validation, test detector arrays and labels for audit; labels/condition IDs are not model inputs.
- `REPORT.md`: Phase 2 conclusions, comparisons, statistics, failed branches, and next steps.
