# Decoder bank v11: execution-safety remediation

Responds to `codex/qshift-v10-independent-review` (e9b89bbf1). Base: v10 at 9b95923f2. Branch: `claude/qshift-v11-execution-safety`.

Engineering only: no decoder, study, tuning, Stim sampling or sealed data. v1-v10 are unchanged. **This is Claude's own work. It is not an independent audit and not a GO.** FIXED below means "the reproduced failure now fails closed in Claude's tests".

Codex's C1 ruling, kept here for the record: **DB8 is void under its original protocol's section 8; the retained amended run is descriptive development evidence with numerical NO ADVANCE.** `ERRATA_DB8.md` in v10 is left as it was. CF2 stays NOT CONFIRMED.

## Closure matrix

| Blocker | Status | Code | Tests (`tests/test_v11.py` unless noted) |
|---|---|---|---|
| 1. Exclusive start, terminal recovery | FIXED | `lifecycle11.py`: `reserve`, `_claim`, `execute`. Unsaved one-time token, supervisor OS lock, pristine folder, exclusive `START.json` | `StartTests` (4 processes racing, 5 rounds; loser writes nothing; interrupted and torn startup; recovery then start); `test_seven` 2, 3; `IntegrationTests.test_concurrent_launches` |
| 2. Verified recovery and commits | FIXED, within the stated assumptions | `check_commit`, `inventory`, `_guarded`, `_check_fence`, `recover`, `_close_failed` | `RecoveryTests`, `FailureTests`; `test_seven` 1; `IntegrationTests.test_interrupted_supervisor` |
| 3a. Journal and lifecycle admission | FIXED | `load_success`, `_check_journal` | `AdmissionLifecycleTests` (each edit tried with valid hash chains and a matching CLOSE record); `test_seven` 5 |
| 3b. Controller metadata | PARTIAL | `policy.py` replays segments, change points, plausible sets, tracker, all bank arms, estimator rules, AD3 and action flags | `PolicyTests`; `test_seven` 4. The reproduced contradictions are rejected. Numbers whose inputs are not saved cannot be recomputed (limit 1) |
| 3c. Binding to verified bytes | FIXED in the helper | `study11.py`: `Study.verify`, `check_imports`, `launch`, `admit` | `IntegrationTests` (wrong head, runtime, freeze, inputs, unfrozen import, other revision) |
| 4. Seeds and archives | FIXED | `strict.py` | `StrictTests`; `test_seven` 6, 7; `IntegrationTests.test_bad_seed_inventories` |
| 5. Integrated path | PARTIAL | `synthetic_study.py` drives the real launch, recovery and analysis | `IntegrationTests`. No real study runner is wired in: that needs its own protocol and freeze (limit 2) |

## Requirement to mechanism

| Requirement | Mechanism |
|---|---|
| One lifecycle per reservation | `START.json` is created exclusively and never removed; any leftover file blocks a start |
| Worker quiescence | Each worker holds an OS lock from before its first action to after its last. Failed and recovered records are written only while holding every lock |
| Orphans and late commits | A worker exits when its supervisor dies, refuses to act or commit once the run is fenced, and blocks recovery while it lives |
| Sampling intent vs confirmed | `sampling_intent` before the first draw; `sampling_confirmed` after the last, with the hash of the seeds used; a commit needs both |
| No unsafe retry | One retry, only if the event file shows just `started` and no output exists |
| Evidence preserved | Nothing is moved, deleted or reused; `CLOSE.json` stores byte hashes |
| Analysis after a failed lifecycle | Analysis can only obtain records from `admit`, which requires the single `succeeded` terminal record and an exact file set |

## The seven reproduced v10 failures

Codex's unmodified script reproduced all seven on v10 in this environment. Ported to v11 (`tests/test_seven.py`):

| # | v10 failure | v11 |
|---|---|---|
| 1 | Empty episode folder called committed | classified `corrupt` |
| 2 | Recovered reservation starts | start refused, terminal record unchanged |
| 3 | Two starts on one reservation | exactly one claim in each of 20 races; loser writes nothing |
| 4 | Contradictory plausible set, estimate, segment, change points | rejected, together and one at a time |
| 5 | Failed journal admitted | rejected, even with a consistent chain and CLOSE record |
| 6 | Duplicate archive member | rejected |
| 7 | Seed alias by coercion | rejected |

The port is Claude's. Codex should write its own against the v11 interfaces.

## Test results

Python 3.12.10, numpy 2.5.3, scipy 1.18.1, stim 1.16.0, pymatching 2.4.0, ldpc 2.4.1, Windows. From the repository root:

```
py -3.12 -B outputs/qshift_decoder_bank_v10/tests/test_v10.py -v
py -3.12 -B outputs/qshift_decoder_bank_v11/tests/test_seven.py -v Seven
py -3.12 -B outputs/qshift_decoder_bank_v11/tests/test_v11.py -v
```

| Suite | Result |
|---|---|
| v10 tests, unchanged, saved archives included | 30 of 30 pass, 64 s |
| Seven adversarial regressions | 7 of 7 pass, 4 s |
| v11 tests | 48 of 48 pass, 565 s |

After the final run, two orphan pool workers were alive. Both were started during the v10 suite, whose killed-supervisor test leaks them: the v10 weakness Codex reported. No worker from the v11 suite was left.

Earlier runs, kept for the record:

- The first run was stopped by hand because it was slow. It showed idle pool workers outliving a killed supervisor. They could not act (the fence refuses them) but they now exit too.
- The second full run had 47 tests, with 4 subtest errors (a keyword clash in the test helper) and 2 subtest failures. The failures were mutations of `gfit` and `S1` that stayed consistent with every dependent field. The tests now mutate them into contradictions, and `test_known_limit_consistent_numbers_pass` pins the limit.

## Remaining assumptions and risks

1. **Not recomputable from records:** the estimator's numbers and its excluded-detector set, the g and fit values, the choice among AD3 library entries, and the absence of an AD3 match. They are checked for type, range and consistency. Changes that keep every dependent field consistent pass.
2. **No real runner yet.** `decoder_factory` and the preflight are passed in by the caller; the synthetic study uses a stand-in. A future study must wire the real ones into frozen code. Learned decoder keys cannot be built in advance.
3. **No signatures.** The trust root is the freeze commit the owner approved. Anyone able to rewrite the repository or the run folder consistently can forge a run.
4. **Workers must write only through `Episode`** and start no processes that outlive them. The lock proves nothing about other programs, and code that deliberately bypasses the interface is not contained.
5. **Local filesystem** with working OS locks and atomic rename. Network and cloud-synced folders are out of scope. Only Windows was tested; the POSIX lock branch was not.
6. **Power loss, disk failure and a torn `RUN.json` or `CLOSE.json`** need manual diagnosis. They block start and analysis.
7. **If workers cannot be proved dead after a failure,** no terminal record is written. The run stays unstartable and unanalysable until `recover` succeeds.
8. Admission expects the analysis checkout's HEAD to be the freeze commit, so analysis runs in a checkout of it.
9. `policy.py` covers the DB8 record format. A different controller needs its own policy module.
10. Seed uniqueness covers the study inventory and every file it lists as screened; it cannot see inventories that are not listed.

## Recommendation

Request an independent execution-readiness audit. Claude makes no GO claim.
