# Structured Decoder Integration and Development Results

## Scope

This report covers implementation and a small development-only run of Q-SHIFT's geometry-aware 3D CNN. It does not modify earlier runs, evaluate an untouched final test set, or establish that a neural decoder improves on PyMatching. The run trained four candidates on matched samples: direct MLP, PyMatching residual MLP, 8-channel structured CNN without class weighting, and the same CNN with class weighting.

## Training integration

The new `dashboard/structured_training.py` path streams Stim samples in batches and preserves the detector grid, measurement-round dimension, and occupancy mask. The worker derives reproducible train and validation streams separately and does not implement a test-sampling path. Candidate fits reuse identical train and validation samples so that comparisons are paired. It tracks the direct logical-observable target and the residual target (`observable XOR PyMatching prediction`) separately.

Checkpoint writes are atomic. Checkpoints include model, optimizer, scheduler, RNG, epoch/batch position, best-validation state, progress, and validation history. The best validation state is restored for saved model predictions. Wall-clock pause is checked at batch boundaries. Development validation artifacts are saved in batches instead of retaining the full data set in memory or GPU memory. The existing legacy worker remains available.

The dashboard now routes structured jobs separately and presents the 100K multi-regime allocation. A prospective 100K configuration was generated and seed-screened; its test allocation remains reserved and inaccessible to this worker.

## Small development run

Run: `python dashboard/structured_worker.py --config outputs/neural_decoder_diagnostic/structured_integration/development_config.json --run-dir outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000`

The run used 6,000 unique training shots and 3,000 unique validation shots: 2,000 and 1,000 per regime respectively. This is one development seed allocation, not an independent-root evaluation. The positive target prevalence was 349/6,000 (5.82%) for direct prediction and 35/6,000 (0.58%) for residual correction.

| Comparator / selected candidate | Validation errors / 3,000 | LER | Result |
|---|---:|---:|---|
| Identity (no logical correction) | 156 | 5.20% | Baseline only |
| Frozen PyMatching | 11 | 0.367% | Strongest observed baseline |
| Direct MLP, selected threshold 0.50 | 156 | 5.20% | All-negative collapse; recall 0% |
| Structured CNN, unweighted, selected threshold 0.50 | 156 | 5.20% | All-negative collapse; recall 0% |
| Structured CNN, weighted, selected threshold 0.75 | 156 | 5.20% | Threshold choice collapses to all-negative; recall 0% |
| Residual MLP, selected threshold 0.50 | 11 | 0.367% | Exact tie with PyMatching; zero prediction disagreements |

Regime-specific raw/paired validation counts for PyMatching were 5/1,000 (X-biased), 2/1,000 (balanced), and 4/1,000 (Z-biased). Direct MLP had 74, 54, and 28 errors respectively. CNN at threshold 0.50 predicted positives for 33 validation shots and made 183 logical errors overall (6.10% LER), with 3 true positives, 30 false positives, 153 false negatives, and 1.92% positive recall. The validation selector chose threshold 0.75 for the weighted CNN, where it predicted no positives. The model-selection rule minimized equal-regime validation LER over thresholds 0.25, 0.50, and 0.75; threshold and model selection were performed on this same development validation set.

At the selected threshold, direct and both CNN models had 152 candidate-only failures versus PyMatching and 7 PyMatching-only failures (net 145 more errors). The residual model had zero disagreements and copied the PyMatching decisions on all 3,000 validation shots. These are exploratory validation metrics after selection, not independent test estimates; no inferential claim is made from them.

Direct, unweighted CNN, and weighted CNN probability outputs showed inadequate discrimination. The unweighted CNN assigned all 3,000 validation predictions below the positive threshold. Weighted CNN scores concentrated around 0.4–0.6 and did not rank useful corrections reliably. Calibration metrics, confusion matrices, histograms, and threshold sensitivity are in `dev_run_6000/structured_development_results.json` and the diagnostic figure.

## GPU and resource measurements

The run used CUDA on an NVIDIA GeForce RTX 4050 Laptop GPU (`torch 2.14.1+cu126`, Python 3.12.10). Training performed actual CUDA forward, backward, and optimizer operations. It processed 81,000 total shot presentations (54,000 training presentations including the prevalence scan and 27,000 validation/evidence presentations) in 8.91 seconds: 9,095 presentations/second end-to-end for this small run. This is not a sustained throughput benchmark and includes repeated fits on the same unique samples. Host peak RSS was 1,295,151,104 bytes (~1.21 GiB); CUDA peak allocated memory was 20,564,480 bytes (~19.6 MiB), with 25,165,824 bytes reserved.

The prospective 100K setup allocates 70,000 train, 15,000 validation, and 15,000 reserved test shots. A rough linear extrapolation from this short run suggests about 2–6 minutes for development work of similar model/configuration complexity, but actual performance can vary substantially with candidate widths, batch sizing, simulation, and system load. A simple linear presentation-count projection is approximately 20 minutes / 3.4 hours / 34 hours for the 1M / 10M / 100M budgets; these are unvalidated estimates, not benchmark guarantees. No such larger job was started.

## Verification

- `python -m unittest discover -s dashboard/tests -v`: **36 tests passed**.
- `python -m compileall -q dashboard`: **passed**.
- `node --check dashboard/static/app.js`: **passed**.
- `python dashboard/verify_structured_resume.py`: **PASS**. Resumed and uninterrupted tiny CPU runs both reached 18 steps; best weights matched bit-for-bit; 9 validation evidence batches; no test samples; 27 distinct derived seeds. This verifies deterministic resume mechanics on a small CPU fixture, not overnight CUDA crash recovery.
- `python dashboard/audit_structured_development.py outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000`: **PASS**. Re-generated and checked 24 validation batches, independently re-decoded PyMatching predictions, recomputed 96 candidate/regime best-checkpoint prediction sets, and verified that no test samples were generated or accessed.
- `python dashboard/verify_run.py dashboard/run_data/runs/18ca68def80946838b26aaea7f59ff3e`: historical smoke run **PASS**, 1,000 test shots; the old CPU-era run remains distinct and unchanged.

## Interpretation

Integration, streaming, best-checkpoint restoration, reproducibility, and small-run GPU execution work. Learning does not: direct and unweighted structured models collapse to all-negative outputs, the weighted CNN fails to generalize useful positive predictions, and the residual network reproduces PyMatching exactly. The residual target is rare (0.58% in training), which explains why copying PyMatching is an easy validation optimum. These results do not justify scaling the current training setup overnight.

The independent audit proves saved validation evidence is reproducible from saved seeds and restored checkpoints. It does not provide independent calibration of the neural models or an untouched generalization test.
