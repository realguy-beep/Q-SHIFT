# V1.1 Post-run Audit and Finalization Failure Report

## Status

**Overall run status: INCOMPLETE. Frozen development decision: INCONCLUSIVE.**

The one authorized V1.1 evaluation sampled and committed all 30 allocated roots (60,000 new paired shots). The frozen runner then failed during independent saved-array analysis with `KeyError: 'global_A_qhat'`. The frozen writer persisted `A_global_qhat` in `models_frozen.json`; the analyzer requests `global_A_qhat`. The analyzer had already written the root-level `paired_results.csv`, but did not write `analysis.json`; the runner consequently did not write `run_manifest.json` and persisted `state=failed` at phase `independent_saved_array_analysis`.

The independent calculations below recover the prespecified descriptive and inferential summaries from the committed saved arrays. They do **not** repair the original status, create the missing frozen finalization files, or change the frozen run's failure state. The protocol explicitly treats incomplete evidence as **INCONCLUSIVE**, so the conditional result “GO if the run had finalized” is not the reported study decision.

## Preservation and audit method

- The original run directory is `outputs/qshift_correlated_decoder_feasibility_v1_1/pilot_runs/attempt_001/` and remains the authoritative failed-attempt evidence.
- No sampler, decoder, or runner was invoked for this audit. No archive or file under `attempt_001` was written or repaired.
- `audit_saved_run.py` is a separate read-only implementation. It imports neither `run_eval.py` nor `analyze_saved.py`; it independently verifies the 30 status/call/archive identities, seeds, sample IDs, byte counts, SHA-256 values, NPZ schema and array shapes/dtypes/binary values; recomputes per-root paired scores and the frozen bootstrap; and reconciles every field in the pre-failure CSV.
- Recomputed values matched all 540 fields in `paired_results.csv` (30 roots × 18 fields). All 30 archives matched their status call journal and archive registry. The audit result is stored separately under `postrun_audit_v1/recovered_outputs/`.
- The post-run audit used the frozen statistic seeds and methods exactly once in the independent reconstruction: 20,000 root-stratified paired bootstrap replicates for the primary interval and 20,000 zero-condition root bootstrap replicates; NumPy `quantile(method="linear")`.

## Allocation, integrity, and timing

| Measure | Verified result |
|---|---:|
| Evaluation roots | 30 / 30 |
| Evaluation calls | 30 / 30 |
| New paired evaluation shots | 60,000 / 60,000 |
| Reused V1 train/calibration shots | 3,000 / 15,000 |
| Cumulative unique development shots | 78,000 |
| Original status | `failed` |
| Original phase | `independent_saved_array_analysis` |
| Original `analysis.json` | absent |
| Original `run_manifest.json` | absent |
| Watchdog-observed lifetime | 86.312 s |
| Recorded sampling time | 0.041 s |
| Recorded A inference | 0.096 s |
| Recorded A2 inference | 0.120 s |
| Recorded shared B/C inference | 78.939 s |
| Recorded model construction | 0.724 s |
| Recorded archive writing | 0.702 s |
| Run peak memory | unavailable in failed final status; not inferred from preflight |

The 30 unique root/sample IDs and 30 unique evaluation seeds exactly match the frozen V1.1 seed inventory. Each archive contains 2,000 samples with `uint8` binary detector arrays of shape `[2000, 40]`, one-observable labels of shape `[2000, 1]`, and four binary prediction arrays (`A`, `A2`, `B`, `C`) of shape `[2000, 1]`. Model metadata and the execution identity state that model choice preceded evaluation and evaluation labels were not exposed to decoders. The saved-array audit verifies these records and arrays; it does not replay decoder inference.

## Recovered arm results

Rates are actual logical-error counts divided by the common paired evaluation shots. `C` is a privileged true-q reference and is not deployable.

| Burst probability q | A: pooled fixed PM | A2: per-root PM | B: calibrated five-factor + background PM | C: privileged true-q reference |
|---:|---:|---:|---:|---:|
| 0.00 | 212/20,000 = 1.060% | 142/20,000 = 0.710% | 141/20,000 = 0.705% | 142/20,000 = 0.710% |
| 0.01 | 266/20,000 = 1.330% | 265/20,000 = 1.325% | 218/20,000 = 1.090% | 218/20,000 = 1.090% |
| 0.02 | 343/20,000 = 1.715% | 349/20,000 = 1.745% | 234/20,000 = 1.170% | 234/20,000 = 1.170% |
| All q, pooled | 821/60,000 = 1.368% | 756/60,000 = 1.260% | 593/60,000 = 0.988% | 594/60,000 = 0.990% |

Equal-weight nonzero-condition LERs are A `1.5225%`, A2 `1.5350%`, B `1.1300%`, and C `1.1300%`. The descriptive relative reduction for B versus A is `25.78%` (absolute difference `-0.3925` percentage points). This is an exploratory estimate from this single synthetic mechanism and this small development allocation.

## Prespecified paired results

Primary estimand: equal-weight mean across q=0.01 and q=0.02 of root-paired `LER(B) - LER(A)`.

- Estimate: **-0.003925** (−0.3925 percentage points).
- Root-stratified paired percentile-bootstrap 95% interval: **[-0.004975, -0.002950]**.
- q=0.01 difference: `-0.002400`; root-bootstrap 95% interval `[-0.004150, -0.000950]`.
- q=0.02 difference: `-0.005450`; root-bootstrap 95% interval `[-0.006700, -0.004250]`.
- q=0 zero-burst `B-A` estimate: `-0.003550`; one-sided safety upper percentile (95th): **-0.002750**, below the frozen `+0.0005` harm tolerance.
- Pooled nonzero A errors: **609**, exceeding the frozen minimum of 100.
- B had a lower point LER than A in both nonzero conditions.

Paired prediction disagreements, summed over all 60,000 rows: A/B `500`; A2/B `413`. Against A, B made `136` errors where A was correct and avoided `364` A errors where B was correct. These are paired descriptive counts, not independent observations.

The frozen criteria would otherwise satisfy the V1.1 development GO conditions if finalization were complete. However the original run failed and did not produce the required frozen `analysis.json` and `run_manifest.json`; therefore the correct reported result is **INCONCLUSIVE / INCOMPLETE**, not GO. No confirmatory superiority claim is supported.

## Calibration summary

The committed pre-evaluation detector-only diagnostics report:

| q | Mean q-hat | Bias | MAE |
|---:|---:|---:|---:|
| 0.00 | 0.0000152 | +0.0000152 | 0.0000152 |
| 0.01 | 0.0103788 | +0.0003788 | 0.0017727 |
| 0.02 | 0.0190455 | -0.0009545 | 0.0009545 |

These values passed the frozen calibration gate before evaluation. The estimator is detector-only; the values above are reported from the persisted pre-evaluation calibration record, not re-fit using evaluation labels.

## Failure and corrective boundary

Cause is established from source and persisted failure: the finalizer at `outputs/qshift_correlated_decoder_feasibility_v1_1/analyze_saved.py:181` requests `global_A_qhat`, while the model-metadata writer at `outputs/qshift_correlated_decoder_feasibility_v1_1/run_eval.py:349-360` stores `A_global_qhat`. It is a deterministic interface defect in post-run analysis, not an archive-integrity or sampling-counter discrepancy. This audit does not modify the frozen analyzer or historical `attempt_001` files. A code fix, repaired finalization, rerun, or new evaluation requires separate authorization; no automatic recovery is proposed.

## Validation and reproduction

From `outputs/qshift_correlated_decoder_feasibility_v1_1/postrun_audit_v1/`:

```powershell
py -3.12 -m unittest discover -s . -p 'test_*.py' -v
py -3.12 audit_saved_run.py `
  --run-dir ..\pilot_runs\attempt_001 `
  --output-dir .\recovered_outputs_reproduction_01 `
  --package-dir ..
```

The completed audit used the same command with `--output-dir .\recovered_outputs`. The command is read-only with respect to the original run and refuses to place output inside it. A reproduction should use a fresh, empty output directory and must not overwrite the recorded `recovered_outputs/` result. Exact source, input, and output hashes are recorded in `audit_bundle_manifest.json`.

No additional sampling, Stim sampler calls, Stage 5 access, sealed outcome access, model selection, or parameter tuning occurred during post-run audit.
