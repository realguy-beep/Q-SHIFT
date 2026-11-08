# Reproduce v3.4.3 safety checks

Run these commands from the repository root in the existing Python 3.12 environment:

```powershell
python -c "import pathlib,py_compile; paths=sorted(pathlib.Path('outputs/stage5_execution_safety_v3_4_3').glob('*.py')); [py_compile.compile(str(p),doraise=True) for p in paths]; print('compiled',len(paths),'python files')"
python outputs/stage5_execution_safety_v3_4_3/run_tests_v43.py
python outputs/stage5_execution_safety_v3_4_3/prepare_freeze_v43.py
python outputs/stage5_execution_safety_v3_4_3/independent_audit_v43.py
```

The freeze command is a one-time operation at base commit `8c06750808582137f6a81e2170ad702a552594fb`. It refuses a different HEAD and verifies historical hash inventories and original forensic files before writing the new freeze. After the repair is committed, verify the existing freeze with the independent auditor; do not regenerate it at the new commit.

The unit suite creates and removes `TemporaryDirectory` fixtures. It uses NumPy-only synthetic detector matrices and Windows subprocesses; it does not instantiate Stim, invoke `compile_detector_sampler`, call Stage 5 runner code, or access logical evaluation outcomes. The auditor repeats the suite independently and compares the 53, 13, and 14 frozen hash inventories plus the 265-file and 56-entry forensic manifests.

The recovery functions intentionally are not wired into `stage5_sampling_runner_v2.py` or `safety_runner_v4.py`. No command in this reproduction guide resumes Stage 5. Do not point a fixture test or recovery API at the historical Stage 5 run. A future recovery remains subject to a new explicit authorization and an integrated runner review.
