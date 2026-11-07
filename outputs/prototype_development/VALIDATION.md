# Prototype validation record

## Pre-sampling checks

- Rotated Z-memory circuit structure: distance 3, five rounds, 40 detectors, one observable.
- Noiseless Stim sample: all detector and observable bits were zero in the diagnostic sample.
- Nine DEMs: generated in the existing `decoder_bank.py` product order and accepted by PyMatching; each exposed 40 detector nodes.
- Noise settings and specialists: the three generation conditions match the established data-heavy, nominal, and measurement-heavy parameters; their grid indices are 6, 4, and 2. Nominal is index 4. The Stage 1 pooled fixed model is index 1.
- Seed allocation: 3 calibration + 600 evaluation-block + one diagnostic + one bootstrap seeds; all 605 distinct. A text-artifact scan screened 201 recoverable repository files outside this folder and found no exact collisions; see `SEED_SCREENING.json`. Unrecorded RNG use and omitted historical records cannot be ruled out.
- Evaluation separation: evaluation detectors, labels, and seeds are separate from calibration. Evaluation labels are not available to `AdaptivePolicy.select_for_next_block`.
- Causality: selection for block t occurs before sampling that block and receives only block t-1 detector data. The policy code does not receive generating-state metadata or logical labels.

## Execution and saved-evidence verification

`python -m unittest -v test_demo.py` passed six checks. `python run_demo.py` completed 50 independent schedule-replicate roots and 307,200 paired evaluation shots after a reporting-field exception was corrected. It also sampled 60,000 calibration shots (20,000 per regime). The failed first reporting attempt used the same deterministic RNG allocation and did not change the method; the successful rerun regenerated and overwrote only this new development package's arrays.

`python audit_saved.py` independently rebuilt all nine PyMatching models, decoded every saved test detector row, and confirmed exact equality with every saved nine-model prediction across all 50 roots. It also decoded the saved calibration arrays, reconstructed all nine residual-error rows, recomputed detector profiles and utility rates, and checked the selected calibration indices. It independently recomputed policy errors, paired discordances, and regime counts; all totals matched the runner's aggregates. The audit result is `PASS` for calibration/test prediction consistency and aggregate recomputation.

## Noise schedule interpretation

The generating regime is constant inside each five-round Stim circuit and changes only between 512-shot blocks. This is an explicit blockwise nonstationary experiment, not an accidental claim of within-circuit time variation. It isolates whether completed detector blocks can justify changing the decoder for a subsequent batch. A continuous-memory, round-resolved drift circuit has not been implemented.

## Limitations

The detector estimator assumes independent Bernoulli detector marginals and does not model correlations. Calibration utility rates are estimated on finite development samples. Runtime measurements are small-process benchmarks and are not hardware latency measurements. The 50 roots are spread over five hand-defined schedules; they do not support confirmatory inference for all possible drift patterns. The hidden-state diagnostic is privileged. No real quantum hardware is connected.
