# Reproduce v3.4.4 validation

Run from the repository root in the existing Python 3.12 environment. These commands do not resume Stage 5.

```powershell
python -c "import pathlib,py_compile; ps=list(pathlib.Path('outputs/stage5_execution_safety_v3_4_4').glob('*.py')); [py_compile.compile(str(p),doraise=True) for p in ps]; print('compiled',len(ps),'Python files')"
python -m unittest outputs.stage5_execution_safety_v3_4_4.test_recovery_service_v44 -v
python outputs/stage5_execution_safety_v3_4_4/run_ownership_regressions_v44.py
python outputs/stage5_execution_safety_v3_4_4/recovery_runner_v44.py --preflight
python outputs/stage5_execution_safety_v3_4_4/independent_audit_v44.py
```

Expected bounded results on the recorded Windows environment: 8 Python files compile; 6/6 recovery-service tests pass; 8/8 applicable process tests pass; preflight reports `PASS_NO_SAMPLING_PREFLIGHT`; the independent audit reports `PASS_WITH_DEVIATION` due to the legacy raw-result hash mismatch documented in the audit report.

The legacy v3.4.2 `run_tests_v4.py` command is intentionally not part of reproduction: its frozen test suite contains an assertion that the historical failed-run directory must not exist. The read-only audit validates its 14 frozen source hashes and uses the eight process tests applicable when the failed run is retained.

No command in this reproduction guide creates a recovery copy, decodes the actual incomplete root, launches the frozen sampling worker, accesses sealed outcomes, or computes full-study statistics. `--prepare-recovery-copy` and `--authorize-stage5-recovery` are future operator actions and were not executed.
