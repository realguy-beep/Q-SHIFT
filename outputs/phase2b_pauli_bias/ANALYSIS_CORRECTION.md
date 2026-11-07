# Phase 2B Analysis Implementation Correction

The first post-sampling execution of the frozen analyzer failed during aggregate count accumulation. Exact command:

```powershell
python analyze_phase2b.py
```

Traceback location and error:

```text
analyze_phase2b.py, line 191, in main
    model_errors += err.sum(axis=1)
numpy._core._exceptions._UFuncOutputCastingError:
Cannot cast ufunc 'add' output from dtype('float64') to dtype('int64') with casting rule 'same_kind'
```

The saved per-shot residual array is binary `uint8`; NumPy 2.5 returns `uint64` from its sum. Adding that vector to an `int64` accumulator promoted the operation to `float64`, which NumPy refused to cast back under `same_kind`. The frozen `analyze_phase2b.py` remains unchanged. A separate `analyze_phase2b_verified.py` copy casts the exact nonnegative integer sums to `int64` before accumulation.

The first run of that corrected copy then exposed a second report-wiring mismatch: the analyzer asked for `STATISTICAL_PLAN.json["primary_test"]`, but the frozen schema stores the procedure under `"primary_signflip"`. The corrected copy now reads the recorded `primary_signflip` object. The test definition, number of draws, seed, statistic, and add-one p-value are unchanged.

These are reporting implementation corrections only. The saved detector arrays, observables, predictions, calibration selection, seed allocation, estimand, bootstrap, sign-flip test, and multiple-comparison rules were not changed. The corrected analyzer re-decodes every saved test prediction from its detector array and checks all frozen pretest hashes before computing outcomes. The corrections and corrected-script hash are included in the final evidence manifest.
