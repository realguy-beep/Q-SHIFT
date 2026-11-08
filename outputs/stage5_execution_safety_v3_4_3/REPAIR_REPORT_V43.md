# Q-SHIFT Stage 5 recovery-safety repair v3.4.3

**Base:** `8c06750808582137f6a81e2170ad702a552594fb`
**Decision:** **NO-GO for authorizing actual Stage 5 recovery with this standalone repair package.** The bounded Windows persistence and archive-reconciliation primitives passed their fixtures, but the repair is not integrated into the Stage 5 worker/supervisor/auditor/finalizer. Stage 5 remains paused and no recovery or additional evaluation sampling occurred.

## Preserved evidence and current failed-run state

The post-failure inventory verified **265/265** original run/log/evidence files and the forensic manifest verified **56/56** entries. The final independent script repeated both checks. The v2 frozen hashes (**53/53**), v3.3 safety hashes (**13/13**), and v3.4.2 source/configuration hashes (**14/14**) also match. No historical protocol, decoder, seed, result, archive, checkpoint, log, or manifest was modified by v3.4.3.

The forensic records establish 123 complete decoder comparisons and one additional `evaluation_complete` checkpoint (root 123 at `p=0`). Across its 124 committed archive/sidecar pairs, the records establish 248,000 calibration rows and 310,000 evaluation rows (558,000 persisted rows), while `status.json` accounts for 555,500. The partial root has its saved 2,000 calibration and 2,500 evaluation rows, but lacks `p_hat` and predictions. It is not a complete decoder comparison. This repair did not run full-study inference or decode that actual root.

## Repair implementation

- `atomic_safety_v43.py:80–133` uses an OS file lock. `:167–202` retries only Windows replacement errors 5, 32, and 33 with six attempts, capped backoff, and the caller's monotonic deadline. `:205–256` fsyncs the exact pending temp, journals its SHA-256 and expected old target hash, then uses compare-and-swap. `:259–290` only replays the unique exact pending write if the old target and temp hashes match; missing/changed temp or newer target fails closed. `:293–391` commits NPZ data and sidecar separately and recovers only from a unique durable write intent.
- `recovery_v43.py:45–60` requires provenance before recovery mutations. `:89–163` validates filename, identity, frozen seed mapping, archive phase/schema, dimensions, binary values, `p_hat`, and independent predictions. `:166–230` reconstructs counts from hash-verified committed archives and refuses orphan temps or unapplied intents. `:233–277` assigns status counters from the ledger and writes via compare-and-swap. `:280–341` completes an `evaluation_complete` archive from saved detector arrays; there is no sampler argument, and its inputs do not include observables. `:344–452` validates every source manifest hash and copies only status, root arrays, and commit markers into a new destination with source provenance; it never writes to the source.
- `SAFETY_FREEZE_V43_2.json` is the final source/configuration freeze. The earlier in-task `SAFETY_FREEZE_V43.json` and `SAFETY_FREEZE_V43_1.json` remain intact; the hash chain explicitly records each supersession. They are benchmark-only records, not experimental protocol changes.

## Validation results

**Windows 11, Python 3.12.10:** 14/14 tests passed; all seven Python files compiled. The tests create only temporary synthetic NumPy fixtures with benchmark IDs screened against 12,100 reserved Stage 5 stream entries (zero collisions; no seed values emitted).

Key checks:

- A live subprocess lock blocked two status writers; after release, a writer using the current SHA succeeded. Compare-and-swap rejected an old expected hash and preserved the newer status.
- A simulated transient WinError 5 succeeded on retry. A real `CreateFileW` handle with no delete sharing caused persistent replacement denial; all retries failed closed, old bytes remained intact, and the exact pending payload was recovered after handle release.
- Real subprocesses exited at temp-fsync, intent-fsync, archive-replace-before-sidecar, and sidecar-replace boundaries. Unjournaled temp data could not be committed. Unique durable intents recovered safely; already committed archive/sidecar pairs were accepted. A crash after a new intent over an older valid checkpoint recovered only the newer journaled payload.
- Synthetic archive tests reconstructed counters idempotently, distinguished `evaluation_complete` from `complete`, rejected bad sidecars/predictions, duplicate/noncanonical roots, seed collisions, unknown phases, orphan temps, and missing durable checkpoints.
- A synthetic `evaluation_complete` checkpoint was estimated/decoded from its saved arrays, independently checked, committed, and retried idempotently. The result reported zero additional samples. A mutation attempt against an unmarked directory was rejected.
- A synthetic source directory was copied to a new path with manifest provenance; source hashes remained unchanged and ownership files were omitted.

One early test iteration exposed that a valid old archive commit could mask a newer durable completion intent. The recovery rule was corrected to prioritize exactly one pending compare-and-swap intent and fail closed on multiple pending intents. The full 14-test suite passed after the correction and was rerun by the independent audit.

## Independent audit

`independent_audit_v43.py` imports neither repair module. It independently verified the 53/13/14 historical freeze hashes, all 265 original inventory files, all 56 forensic-manifest entries, the fixture seed collision screen, and absence of a sampling API in the recovery module. It then reran the 14 Windows tests through a separate subprocess. Result: **PASS** (`INDEPENDENT_AUDIT_V43.json`).

This is a separate scripted audit in the same workspace, not a second human or agent review. No external reviewer was available. The production decoder callbacks were not invoked on the actual in-flight root.

## Requirement assessment

| Requirement | Status |
|---|---|
| Original 265 files and forensic evidence preserved | **PASS** |
| Bounded retry, backoff, exact payload, no overwrite of newer state | **PASS** |
| Idempotent archive-derived counter reconstruction | **PASS in synthetic fixtures** |
| `evaluation_complete` recovery without resampling | **PASS in synthetic fixture; actual root not touched** |
| Separate recovery directory with source hashes/provenance | **PASS in synthetic fixture** |
| Frozen scientific hashes and choices unchanged | **PASS (53 + 13 + 14 hashes)** |
| Required contention, access-denial, crash, duplicate, and recovery tests | **PASS (14/14)** |
| Independent scripted audit and Windows subprocess injections | **PASS with reviewer-scope limitation** |
| Integrated recovery runner and full recovery workflow | **NOT IMPLEMENTED / BLOCKER** |
| Actual Stage 5 recovery or sampling | **NOT EXECUTED** |

## Residual risks and next action

The precise historical holder behind WinError 5 remains unknown. Windows directory-entry durability under power loss is not proven because portable directory `fsync` is unavailable. Full-scale disk, memory, and deadline behavior is untested. Most importantly, the package does not replace or wrap the frozen worker, supervisor, independent saved-array auditor, aggregation, or finalizer. Recovery should not be authorized until that integration is implemented in another version, its deadline and failure handling are audited, and a separate reviewer checks the recovery procedure.

**Recommendation: NO-GO for Stage 5 recovery authorization now.** Keep the failed run immutable. No endpoint or partial-study statistics were computed. A future recovery requires a separately versioned integrated repair and fresh explicit authorization.

### Reproduction

See `REPRODUCE_V43.md`. Main command:

```powershell
python outputs/stage5_execution_safety_v3_4_3/independent_audit_v43.py
```

No command in this package launches Stage 5.
