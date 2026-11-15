# V1.1 saved-array analyzer fix (engineering only)

## Status

**The V1.1 study result is unchanged: INCONCLUSIVE / INCOMPLETE.** This package fixes the analyzer defect that stopped V1.1 finalization. It does not repair, re-finalize or rewrite the frozen V1.1 run, its freeze, or its post-run audit. Zero Stim sampler calls, zero decoder calls, no parameter tuning.

## Defect

The frozen runner `qshift_correlated_decoder_feasibility_v1_1/run_eval.py` writes `"A_global_qhat"` into `models_frozen.json`. The frozen analyzer `analyze_saved.py:181` reads `models["global_A_qhat"]`. As a result, `pilot_runs/attempt_001` failed with `KeyError: 'global_A_qhat'` after `paired_results.csv` had been written but before `analysis.json`. The frozen unit test missed the defect because its fixture used the analyzer's (wrong) key, not the runner's.

## Fix

`analyze_saved_fixed.py` is a copy of the frozen analyzer (SHA-256 `d6720b879cbef01f9c9a62ad103e930e5214129c615c4b0ade5e202320296239`, left untouched under `qshift_correlated_decoder_feasibility_v1_1/`). It has exactly three changes:

1. It reads `A_global_qhat`, the key the runner writes, via `MODELS_GLOBAL_QHAT_KEY`. The output field is renamed to match.
2. It loads and validates `models_frozen.json` and `calibration_diagnostics.json` before writing any file, so a metadata mismatch now raises `ValueError` with no partial outputs.
3. An optional `output_dir` / `--output-dir` lets the analysis be written outside a preserved run directory.

Scoring, bootstrap seeds/replicates, quantile method and the GO/NO-GO/INCONCLUSIVE rules are unchanged. The seed inventory is read from the frozen V1.1 package.

## Tests

From the repository root (Python 3.12.10):

```powershell
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_v1_1_analyzer_fix_v1/tests -v
```

There are 5 tests: the runner's key is accepted; the legacy misnamed key fails with no files written; `output_dir` leaves the run directory unwritten; a source contract check that the frozen runner writes the key this analyzer reads; and a check that the frozen analyzer's hash is unchanged. The frozen V1.1 tests (9) still pass unchanged.

## Read-only validation against saved attempt_001

`validation_attempt_001_copy/check_real.py` copies `attempt_001` to a scratch directory. Only in that copy, it sets `status.json` `state` back to `evaluation_complete_pending_independent_analysis`, the pre-analysis state the analyzer requires. It then runs the fixed analyzer with a separate output directory. Results (2026-11-15):

- The original `attempt_001` has identical SHA-256 for all 36 files before and after.
- The regenerated `paired_results.csv` is byte-identical to the frozen run's pre-failure CSV (SHA-256 `3b6f5435c9c52340d5b26d6671f927e91be100727502e0449a84b33ad28a827b`).
- The frozen analyzer on the same copy still raises `KeyError: 'global_A_qhat'`.
- The fixed analyzer reproduces the independent post-run audit: primary B−A `-0.003925`, 95% CI `[-0.004975, -0.002950]`; q=0 95th percentile `-0.00275`; errors A 821 / A2 756 / B 593 / C 594; `A_global_qhat` `0.0101667`.

`analysis_from_scratch_copy.json` records that output. Its `decision` field reads `GO_DEVELOPMENT_ONLY` because that is what the frozen rules compute on complete arrays. **It is not the V1.1 frozen finalization.** It was produced on a modified copy by a post-hoc analyzer, so the protocol's INCONCLUSIVE classification stands.

## Boundary

The fixed analyzer is intended for a future, separately frozen evaluation such as V1.2. It is not authorization to re-finalize V1.1. This package does not address the separate question of whether arm A (pooled fixed, q̂≈0.0102) is a strong enough comparator; at q=0 it underperforms A2 (1.060% vs 0.710%).
