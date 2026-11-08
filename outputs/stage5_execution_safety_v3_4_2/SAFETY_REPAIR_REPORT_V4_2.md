# Q-SHIFT Stage 5 Process-Ownership Safety Repair — v3.4.2

**Result: PASS on Windows (`win32`). Stage 5 sampling remains unauthorized and was not run.** No sealed outcomes or Stage 5 seed rows were opened.

## Requirement-by-requirement result

| Requirement | Result | Evidence |
|---|---|---|
| Ownership covers worker, auditor, finalizer, and process creation through ownership acquisition | PASS | Durable intent/token; suspended child is assigned to a Windows Job Object before resume; each child acquires its role lock and claims intent before artifact access. See `ownership_runtime_v4.py` lines 202–305, 408–477, 483–521 and `safety_runner_v4.py` lines 128–176, 211–270. |
| Second launcher cannot enter while an artifact-capable child remains | PASS | Kill-on-job-close contains children after supervisor death. Six actual subprocess failure injections passed. Separate active worker and finalizer lock probes returned 12 while owned and 0 after release. |
| No handoff gap, unsafe stale takeover, or concurrent finalization | PASS | A suspended unassigned child was found and terminated before takeover. Role locks and serialized launcher/finalizer ownership reject contenders. Finalizer writes a verified nonterminal manifest; only the supervisor commits `completed` after child exit. |
| Auditor/finalizer deadline enforcement | PASS | Children use absolute monotonic watchdogs; a real watchdog fixture exited 124 at its deadline. Windows Job Object teardown is the immediate cleanup path after supervisor loss. |
| Historical freeze and scientific protocol preserved | PASS | Verified all 53 Stage 5 v2 hashes, 13 v3.3 hashes, and 14 source hashes in each superseded v3.4/v3.4.1 freeze. Current v3.4.2 freeze contains 14 source/config hashes. Allocation, decoder, Endpoint B, and inference rules are unchanged. |
| Benchmark-only evidence and sealed-test boundary | PASS | 9/9 tests and independent audit PASS. Normal: 2 roots / 1,536 unique calibration+evaluation shots / 2 checkpoints. Recovery: 1 root / 256 committed unique shots. A deliberately uncommitted 128-shot calibration call was replayed with its same benchmark seed and not double-counted. Stage 5 shots: **0**; run directory absent. |

### Windows supervisor termination injections

| Role / phase | Supervisor killed | Child alive before probe | First launcher result | Child alive after probe | Launcher accepted after release |
|---|---|---:|---:|---:|---:|
| worker / startup | killed | False | 0 | False | True |
| worker / active | killed | False | 0 | False | True |
| auditor / startup | killed | False | 0 | False | True |
| auditor / active | killed | False | 0 | False | True |
| finalizer / startup | killed | False | 0 | False | True |
| finalizer / active | killed | False | 0 | False | True |

In each case the Job Object had terminated the child before takeover. Separate live-owner probes verify rejection while a worker/finalizer child owns its role lock.

## Failed revision and repairs

The v3.4.1 attempt is preserved with its FAIL report. It exposed a 266-character Windows temporary sidecar filename exceeding classic `MAX_PATH`, a `KeyError: create_time` because `psutil.process_iter` did not request that attribute, and a watchdog fixture invocation missing required `--run-dir`. v3.4.2 uses short random temp names, requests creation time, and supplies the fixture argument. A long-path write test passes. Review also caught and repaired a missing `job` argument in `_audit_and_finalize`; normal benchmark completion exercised auditor and finalizer under the Job Object. A post-test process sweep also found one `CREATE_SUSPENDED` unassigned v3.4.1 test fixture left behind by the failed test before its cleanup assertions ran; its command line and creation time were checked, that exact fixture was terminated, and absence was verified. The cleanup record is `V341_TEST_FIXTURE_CLEANUP.json`.

## Commands and results

```powershell
python -m compileall -q outputs/stage5_execution_safety_v3_4_2
python outputs/stage5_execution_safety_v3_4_2/prepare_safety_freeze_v4.py
python outputs/stage5_execution_safety_v3_4_2/safety_runner_v4.py --preflight
python outputs/stage5_execution_safety_v3_4_2/run_tests_v4.py
python outputs/stage5_execution_safety_v3_4_2/independent_audit_v4.py
```

**Tests:** 9 passed, 0 failed, 0 errors in 21.11s. Independent audit recomputed archive hashes, paired predictions, counts, recovery journal, ownership events, historical hashes, and zero-shot boundary. Finalizer contention probe returned exit 12 while live and exit 0 after release.

## Source/configuration SHA-256 inventory

| File | SHA-256 |
|---|---|
| `ownership_runtime_v4.py` | `3e03c1cf3b8043364b74790f8554f8084c45518cfbc2381469b53c6792691199` |
| `safety_runner_v4.py` | `1e04b1b11b7891b4d99adc84c8deff8b7f763b287b934aecde0ecce8a31bd70c` |
| `worker_v4.py` | `676c06cd26c0b9eb66216dbb573d48b2e2ab698161b48bec9bb2fd2aec3bb4cd` |
| `audit_saved_run_v4.py` | `03c19293d5202765b4365a5708a90800b311b02e0994051474599c9c8462209e` |
| `finalize_v4.py` | `999ef79ca30c8127a72956dd24fc0e8b78520d65989b0d9ff336e93cb7d55c2f` |
| `test_process_child_v4.py` | `e794c9913bba149a7fa3d113db956f9347d1beb0fb8893f3cf8ef0383f6a2750` |
| `test_safety_v4.py` | `09a89041f9c46dad0e21b4346375b8f11448b77d5e0eb159e86bbea2ed6cf1bb` |
| `run_tests_v4.py` | `94c679047fb1d98002ae25f2d1a4ae559bd211811c8a60b4ae1606e845134c50` |
| `prepare_safety_freeze_v4.py` | `383fe6fa5d9084f1c1c4451805c12fb1972f7c1302ed8f4338187e75481ccf11` |
| `independent_audit_v4.py` | `5d39eb81e6b67cba4f32156cb2282244eac95f8a39dc87b6c9ec46537e2ce44d` |
| `benchmark_config.json` | `4be0c9b1b2f5ff54dcef3fb3c3d755c48fc8a164aac3738e32e975f20c4f4ed4` |
| `fault_config.json` | `c72d39d6c6dc1c5d1ebeb43e9c70e60ddb1a3c073fca9f4e45589e3c5a0c9a7e` |
| `active_sampler_config.json` | `55b3c783325f81a02553877da81a8602e4afa919d4094a9043bb3bc98e84c759` |
| `SAFETY_PROTOCOL_V4_2.md` | `a6afefc2a454ca8c9f18f0299d86106604e3102e1360a4b01c8a6f45525572db` |

The complete machine-readable inventory is `SAFETY_FREEZE_V4.json`; evidence hashes are in `SAFETY_EVIDENCE_MANIFEST_V4_2.json`. The eight fresh benchmark seeds 89,000,000,001–89,000,000,008 are unique and disjoint from recoverable historical values and the reserved Stage 5 range. The 1,000,000-shot active-sampler fixture was **not executed**.

## Limitations and decision

- Full 27,225,000-shot execution was not run; this validates lifecycle mechanics, not full-scale resource behavior.
- Windows Job Object assignment and real subprocess termination passed on this machine. Failures in Job Object assignment or process inspection fail closed.
- File data is flushed and files are replaced atomically; Windows directory-entry durability across sudden power loss is not guaranteed because directory `fsync` is unavailable here.
- The watchdog check is short, not a full two-hour run.

**Safety decision: PASS / GO for safety readiness to be considered in a separate authorization decision. This does not authorize Stage 5 sampling; sampling remains unauthorized at zero shots.**
