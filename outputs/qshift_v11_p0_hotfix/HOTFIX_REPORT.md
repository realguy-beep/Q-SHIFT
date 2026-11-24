# v11 P0 safety hotfix

Responds to `codex/qshift-v11-independent-review` (abc1ae474). Base: v11 at 5052efacf. Branch: `claude/qshift-v11-p0-hotfix`. All new files are in this folder; every earlier file is unchanged.

**Claude's own work, not an independent audit.** No Stim sampling, experiment, sealed data or tuning. DB8 stays VOID under section 8 with descriptive numerical NO ADVANCE. CF2 stays NOT CONFIRMED.

## Closure matrix

| Finding | Reproduced on v11 | Change | Test that shows it | Unproven |
|---|---|---|---|---|
| **NEW-1a** recovery's lock authorises a delayed worker | Codex `test_gap_recovery_owner_passes_worker_fence` passes on v11 (gap present) | Worker authority is the original supervisor's OS process handle (parent of the worker) plus an unsaved session secret whose hash is in `START.json`. No worker decision reads the supervisor lock | `test_01`: a real child holding the true session, watchdog off, is refused at initialisation, guard and intent while a real recovery holds the lock. Codex's own probe, unmodified, now fails at its gap assertion | Code that reads private memory or bypasses the API |
| **NEW-1b** recovery does not exclude startup | Shown by Codex's interleaving | Persistent fence under `locks/gate`, which every worker start, intent and commit also takes. Slots are held for a pool process's whole life. Recovery certifies only while holding all of them | `test_02` (worker stopped inside initialisation), `test_02b` (12 kill times), `test_10` (paused commit, then idle orphan still blocks), `test_10b`, `test_09` | Every bootstrap instruction boundary; only the listed points were injected |
| **NEW-1c** I/O error read as a live owner | Codex `test_gap_io_error_appears_live` | `LockBusy` (Windows errors 33 and 997 only) is separate from `LockError`, which always propagates | `test_03`, `test_03b` (real read-only lock files), `test_03c`; Codex's probe, unmodified, now raises | Filesystems that misreport lock errors |
| **NEW-2a** `succeeded` without intent | Codex `test_gap_success_without_intent` | `check_run` (what analysis uses) and the study's `check_study` run on the exact bytes to be published, before `run_end` or `CLOSE.json` exists | `test_05` (including forged state and a fully forged commit), `test_06`, `test_07`, `test_07b`, `test_p0_study` | A consistently forged run; a bug shared by both uses of the same check |
| **NEW-2b** stages rely on caller order | Codex static | `Episode` is one-way and checks its event file; any other call breaks it permanently | `test_05` (`swallow_no_intent`), `test_06b` | Deliberate tampering with private state before an intent |
| **NEW-2c** terminal write | Torn record blocks but cannot be diagnosed as interrupted | Written whole to `CLOSING.*`, then renamed. Interrupted files are kept. A published success is never rewritten | `test_08` (killed at three points), `test_08b`, `test_08c`, `test_torn_failure_records_do_not_reopen` | Power loss |
| **NEW-6a** partial lock acquisition | Static | `_all_slots` releases everything on any exception | `test_04` (5 positions, 4 exceptions, tracebacks kept alive), `test_04b` | - |

NEW-3, NEW-4, NEW-5 and the deadline part of NEW-6 are **P1 and open**: see `STUDY_INTEGRATION_CHECKLIST.md`.

## Required tests

| # | Test in `tests/test_p0.py` |
|---|---|
| 1 Recovery paused with the lock, delayed worker | `test_01`, `test_01b` |
| 2 Recovery racing initialisation | `test_02`, `test_02b` |
| 3 Permission error in checks | `test_03`, `test_03b`, `test_03c` |
| 4 Partial multi-lock failure | `test_04`, `test_04b` |
| 5 Missing intent | `test_05` |
| 6 Missing or mismatched confirmation | `test_06`, `test_06b`; `test_p0_study` (`wrong_seed_meta`) |
| 7 Failed journal, valid hashes | `test_07`, `test_07b` |
| 8 Interrupted success record | `test_08`, `test_08b`, `test_08c` |
| 9 Concurrent recoveries | `test_09` (4 processes, 5 rounds) |
| 10 Late commit after a fence | `test_10`, `test_10b` |

Tests 1, 2, 8, 9 and 10 use real Windows processes and file barriers.

## Results

Environment: Windows-11-10.0.26300, Python 3.12.10, numpy 2.5.3, scipy 1.18.1, stim 1.16.0, pymatching 2.4.0, ldpc 2.4.1 (matches the pinned versions).

| Suite | Target | Result |
|---|---|---|
| `test_p0.py` | hotfix | 26 of 26 pass, 58 s |
| `test_p0_study.py` (overlay) | hotfix | 3 of 3 pass, 147 s |
| Seven adversarial regressions, unmodified | hotfix (overlay) | 7 of 7 pass |
| v11 suite, unmodified | hotfix (overlay) | 43 of 48 pass; 5 incompatible, below |
| Codex v11 probes, unmodified | hotfix (overlay) | 13 of 16 pass. The 3 that now fail are exactly the P0 gap probes (NEW-1a, NEW-1c, NEW-2a); the 3 P1 gap probes still reproduce |
| Codex v11 probes, unmodified | v11 | 16 of 16 pass (all 6 gaps reproduce) |
| Seven adversarial regressions | v11 | 7 of 7 pass |
| v10 suite | v10 | 30 of 30 pass, saved archives included |
| v11 suite | v11 | 48 of 48 pass, 505 s |

```
py -3.12 -B outputs/qshift_v11_p0_hotfix/tests/test_p0.py -v
py -3.12 -B outputs/qshift_v11_p0_hotfix/tests/overlay.py <new folder> <Codex ADVERSARIAL_REPRODUCTIONS.py>
```

then, inside the new folder, the commands listed in `overlay.py`. The overlay copies test files byte for byte and aliases v11's lifecycle, study and analysis modules to the hotfix.

### v11 tests that contradict the corrected contract (kept, not edited)

| v11 test | It expects | Hotfix |
|---|---|---|
| `test_finished_runs_with_bad_content_are_not_analysed` (3 subtests) | a launch with invalid content succeeds, and only analysis rejects it | the launch ends failed (P0-B); covered by `test_p0_study` |
| `test_commit_needs_confirmation_and_never_replaces` | an episode is usable after a premature commit | an out-of-order call breaks it; covered by `test_06b` |
| `test_fence_stops_late_worker` | `Fenced` after setting a private flag | refused earlier, as an invalid stage; covered by `test_01`, `test_10`, `test_10b` |
| `test_recover_waits_for_live_worker` | a blocked recovery writes nothing | the fence is written first, so a live orphan cannot commit; covered by `test_10` |
| `test_unquiesced_failure_is_not_closed` | no `RECOVER.json` after a blocked recovery | same reason; no terminal record is written in either version |

### Earlier runs

The first `test_p0` run hung and was stopped by hand: a test process kept a pipe open. The second had 25 of 26 passing. Test 10 expected recovery to succeed while an idle orphan, with its watchdog switched off by the test, was alive. Recovery was right to refuse; the test now asserts that. The initialiser also printed a harmless thread error when called outside a pool; it now refuses cleanly.

Orphan processes left on the machine came from the v10 suite (known v10 weakness) and from those two earlier test runs. None came from the final hotfix run.

## Known limitations

1. Checks and hashes are not signatures. A consistent forgery by someone with write access is out of scope.
2. Jobs must use `Episode` and leave no processes behind. Code that uses private functions is not contained, though a forged commit without events was rejected.
3. One host, a local disk, working OS locks and atomic rename. No power-loss or cross-host claim. The POSIX branch is untested.
4. A parent process must be the direct supervisor. Other pool types are refused.
5. If workers cannot be proved gone, or a lock cannot be examined, the run stays fenced without a terminal record until recovery succeeds. A torn `RUN.json` or a foreign `CLOSE.json` needs manual diagnosis.
6. An exception after `CLOSE.json` is renamed (for example Ctrl+C) leaves a valid published success, although `execute` raises.
7. A blocked recovery now leaves a permanent fence. The run can then only end recovered.
8. The same check admits at publication and at analysis, so agreement between them is not independent evidence.

## Engineering readiness verdict

**The reproduced P0 cases fail closed in Claude's tests. Readiness is limited to a bounded, sampler-blocked rehearsal, and only after Codex verifies this commit independently.** This is not an experimental GO and authorises no sampling.

Recommended rehearsal, if Codex agrees: one disposable local synthetic run of at most 64 episodes and 4 workers, all Stim samplers blocked, a fixed wall-clock limit set from outside, one injected supervisor kill and one invalid episode, with every folder kept.

Outstanding before any study freeze: every item in `STUDY_INTEGRATION_CHECKLIST.md`.
