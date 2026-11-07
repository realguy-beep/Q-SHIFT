# Independent audit repair record

The pre-simulation freeze contains `independent_audit.py` at SHA-256 recorded in `DESIGN_VALIDATION_FREEZE.json`. That original file was not edited. Its first post-run invocation stopped before writing an audit result because `family[10:]` returned an empty suffix for `student_t5`. A separately copied `independent_audit_repair_v1.py` corrected this to an explicit `removeprefix("student_t")`. The first repair invocation then exposed a second reference-generator issue: `math.sqrt` was given vector input; the repair copy was corrected to use NumPy's elementwise square root. Neither failure changed simulation inputs, seeds, results, or the frozen source.

The repaired audit completed successfully. It independently checked the original pre-run freeze's nine source/config hashes plus preserved Stage 5 v2 and Stage 4C freeze hashes; recomputed type-I rates, Wilson intervals, one-sided coverage complements, central coverage, power intervals, calibration-envelope maxima, and p=0 summaries; and ran six separately written distribution-generator checks with 250,000 draws per condition. All finite-envelope size and coverage checks passed. It did not independently rerun all 100,000-replicate Monte Carlo cells; it verified saved aggregate counts and used independent generator moment checks. This remains a limitation.

Exact failed commands:

```powershell
python outputs/stage5_design_validation_v2/independent_audit.py
python outputs/stage5_design_validation_v2/independent_audit_repair_v1.py
```

The first failed with `ValueError: invalid literal for int() with base 10: ''` at the Student-t family parser. The second failed with `TypeError: only 0-dimensional arrays can be converted to Python scalars` at the reference generator's conditional standard deviation. The corrected audit command was:

```powershell
python outputs/stage5_design_validation_v2/independent_audit_repair_v1.py
```

It exited 0 and saved `INDEPENDENT_AUDIT_RESULTS_V1.json` with inference calibration PASS and power-gate FAIL at all three allocations.
