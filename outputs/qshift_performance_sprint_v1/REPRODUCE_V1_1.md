# Reproduce and inspect the V1.1 development result

## Environment recorded for the run

- Python 3.12.10
- Stim 1.16.0
- PyMatching 2.4.0
- NumPy 2.5.3
- psutil 7.2.2

No packages were installed or changed for this pilot. The V1 and V1.1 source identities are recorded in `source_manifest.json`, `PRETEST_FREEZE.json`, and `RECOVERY_SOURCE_MANIFEST_V1_1.json`.

## Deterministic verification (no sampling)

From the repository root:

```powershell
python -m unittest outputs.qshift_performance_sprint_v1.tests.test_deterministic outputs.qshift_performance_sprint_v1.tests.test_recovery_v1_1 -v
python outputs/qshift_performance_sprint_v1/analyze_recovery_v1_1.py
python outputs/qshift_performance_sprint_v1/audit_recovery_v1_1.py
```

The analysis and audit commands read saved arrays only. They do not invoke Stim samplers. The auditor reconstructs detector-only calibration, four decoder predictions, per-root counts, and the primary bootstrap interval independently of the runner's aggregates.

## Sampling provenance

The bounded execution used the single recovery command:

```powershell
python -m outputs.qshift_performance_sprint_v1.run_recovery_v1_1 --execute-single-recovery
```

Do not run this command over the existing evidence. It is deliberately non-resumable and fails if `samples/recovery_v1_1/` exists. The exact local training/calibration archives from the preserved failed V1 attempt are required; they are ignored raw evidence and are not in Git. The run reuses these arrays, replays the already-returned but unarchived `eval:p0:r00` partition seed, then evaluates the remaining 49 frozen evaluation seeds. The lost initial transient sample cannot be byte-compared against the deterministic replay. Recreating the full experiment from a clean clone would require a separately prepared one-shot reconstruction workflow; this report does not authorize another execution.

Raw `.npz` archives remain under the local ignored `outputs/qshift_performance_sprint_v1/samples/` path. Their SHA-256 values are in `RUN_EVIDENCE_MANIFEST_V1_1.json` and `independent_audit_v1_1.json`. The committed root CSV and JSON reports are lightweight derived results, not a replacement for the raw arrays.

## Failed-attempt record

The original V1 command stopped at the first paired-evaluation registration because the profile matcher's metadata name did not match the registered key. That run's original `samples/status.json` and 51 persisted training/calibration artifacts are preserved. Its status counter says 32,000 verified rows even though durable archives contain 30,000; the independent inventory records this discrepancy. V1.1 does not rewrite those files.
