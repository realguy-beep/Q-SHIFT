# Q-SHIFT neural-decoder audit and next diagnostic

## Audit of the completed CUDA smoke run

The saved run is `18ca68def80946838b26aaea7f59ff3e`. Its detector sampler produced 40 binary detector bits and one binary Stim logical-observable bit per shot. The direct MLP was trained on the observable bit using unweighted `BCEWithLogitsLoss`; inference applied `sigmoid(logit) >= 0.5`, equivalent to `logit >= 0`. The resulting predicted bit is a proposed logical parity correction, and residual error is correctly scored as `prediction XOR observable`. This is a decoder-scoring convention, not a physical gate applied to a qubit.

The target and XOR conventions are correct. The failure is **majority-class/threshold collapse**: the direct MLP predicted zero on every reconstructed training, saved validation, and saved test shot. Positive observable labels were not rare enough to make this an acceptable decoder: 491/8,000 train (6.14%), 61/1,000 validation (6.10%), and 53/1,000 test (5.30%). The model's highest test probability was about 0.295, so the 0.5 threshold never fired. Its test confusion matrix (true rows, predicted columns) was `[[947, 0], [53, 0]]`; test sensitivity was zero. Accuracy alone was misleading.

| Split | Observable positives | Direct positives | Direct errors | PyMatching errors | Residual correction targets | Residual predicted corrections | Residual final errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 491 / 8,000 | 0 | 491 | 40 | 40 / 8,000 | 0 | 40 |
| Validation | 61 / 1,000 | 0 | 61 | 4 | 4 / 1,000 | 0 | 4 |
| Test | 53 / 1,000 | 0 | 53 | 3 | 3 / 1,000 | 0 | 3 |

The direct MLP's test probability histogram in ten equal-width bins was `[3, 102, 895, 0, 0, 0, 0, 0, 0, 0]`; all probabilities were below 0.30. Test Brier score was 0.09768, log loss 0.36695, and 10-bin ECE 0.20723. Training loss fell from 0.6920 to 0.3800, but this did not produce a single positive prediction. The validation and test score summaries therefore confirm the classifier failure rather than support learning progress.

The residual MLP target is `PyMatching_prediction XOR observable`, and the final parity prediction is `PyMatching_prediction XOR predicted_residual`. That convention is correct. PyMatching failures were 40/8,000 (0.50%) in training, 4/1,000 in validation, and 3/1,000 in test. The residual network predicted zero correction bits everywhere; its test residual-target confusion was `[[997, 0], [3, 0]]`. Its 3 test errors exactly match PyMatching's 3 errors. Thus it learned the safe identity residual, not an improvement.

One training-selection limitation was also found: the worker records a scalar `best_validation_ler`, but checkpoints contain the latest model weights and the final model is evaluated; it does not snapshot or restore the weights from the best validation step. The recorded scalar is the minimum across direct and residual validation scores, not a model-selection record. The current smoke had one fixed training pass and no threshold calibration or early stopping. This does not invalidate the saved paired test counts, but it limits claims about the best neural checkpoint.

The complete sampler-to-label-to-score path was reconstructed from the frozen circuit and seed plan. Saved validation/test model outputs were independently regenerated from the checkpoint. The test data here are used only to audit the already completed run, never for selecting the new architecture. This run contains only the `balanced` generating regime; it provides no X-biased or Z-biased evaluation. Full split diagnostics are in `saved_smoke_audit/18ca68def80946838b26aaea7f59ff3e_neural_diagnostics.json` and `.md`.

## Structured neural decoder

Added `dashboard/structured_decoder.py`. It maps each detector using Stim's fixed `[x, y, round]` coordinates into a sparse `(round, y, x)` tensor, with an occupancy channel to distinguish absent check positions from zero syndrome bits. The current distance-3/five-round Z-memory circuit maps to six time slices and a 4×4 spatial grid, with 40 detector sites. A compact 3-D convolutional model preserves local spatial and temporal structure while producing one logical-flip logit. It consumes syndrome bits and fixed circuit geometry only; regime/noise labels are not inputs. The module is implemented and unit-tested, but it has not been trained or compared for performance.

## Prospective 100K-shot diagnostic protocol

The protocol is **not executed**. It allocates 70,000 training, 15,000 validation, and 15,000 final test shots (100,000 unique simulated shots total), each balanced across `x_biased`, `balanced`, and `z_biased` as recorded in the JSON files. The same paired detector/observable samples are used across PyMatching, direct MLP, structured CNN, and residual MLP. The model receives no regime ID or noise parameters. Architecture, checkpoint, loss choice, and threshold are selected using validation only; final test seeds remain unopened until this selection is frozen.

The proposed CNN grid is channels `{8,16}` and dropout `{0,0.05}`; thresholds `{0.25,0.5,0.75}` are validation-only. The test set is 5,000 shots per regime, adequate for a diagnostic of gross collapse and shift sensitivity, but underpowered for small logical-error improvements. Preserve paired counts, confusion matrices, calibration, and regime-stratified results. Use a fixed decoder on ties or when validation evidence does not resolve the comparison. The 397 allocated train/validation/test/model seeds were unique and disjoint from 2,076 recoverable historical seed values and recorded dashboard allocations.

## Resource estimate and limits

No training was launched for this protocol. At batch size 256, the CNN uses a small 3-D tensor (two channels × six rounds × 4 × 4 positions) and can be streamed; expected GPU memory is below 0.5 GB on the RTX 4050. The 70K-sample training set is about 2.9 MB as uint8 detectors and labels, or about 11.5 MB as float32 detector tensors before framework overhead. Six fits × two epochs cap the proposed development budget at about 840,000 training-example presentations; 100,000 is the number of unique generated shots. Expect tens of seconds including circuit setup, validation, and candidate fits; measure actual runtime before any future expansion. The previous smoke's peak allocated VRAM was about 18 MiB for the MLP, not a benchmark of the new CNN.
