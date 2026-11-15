# V1.1 post-run validation note

The pre-execution V1.1 regression suite was run successfully before sampling: 13 tests passed. That suite intentionally requires `samples/recovery_v1_1/` to be absent and checks the original run-start state. After a successful run, rerunning the same preflight suite produced two expected state-guard failures because the recovery directory now exists. It did not alter files or sample data. The original failed-attempt inputs and status hash remained intact.

For completed evidence, use:

```powershell
python -m unittest outputs.qshift_performance_sprint_v1.tests.test_deterministic outputs.qshift_performance_sprint_v1.tests.test_results_v1_1 -v
```

This result-state suite verifies frozen input integrity, 50 committed roots, 100,000 evaluation rows, cumulative replay accounting, the independent saved-array audit, and all 50 archive hashes. It performs no sampling. The deterministic base suite remains valid after execution; the recovery preflight suite should be run only before the one-shot recovery.

The post-run invocation of `analyze_recovery_v1_1.py` as a module also failed before any analysis I/O because its sibling import expects script-directory execution. The documented direct-script invocation succeeded. No source was changed after the pre-run source freeze.
