# Q-SHIFT v11 independent execution-readiness review

Audited `5052efacfef4e39bfd2c16ec8317a7ed90dbf4ac` on `claude/qshift-v11-execution-safety`, against review `e9b89bbf12117879cea1796931de2ca377c2899c`. Read the nine committed v11 files, the v10 validation and analysis contracts, and the directly invoked v9/controller/estimator dependencies. Executed only sampler-blocked synthetic fixtures and metadata replay against the committed DB8 development records. No training, tuning, experimental sampling or sealed contents were accessed.

## Decisions

| Decision | Verdict | Basis or condition |
|---|---|---|
| Seven original v10 failures | **GO** for the seven reproduced cases | Independent tests closed all seven. This does not extend to adjacent races or full scientific provenance. |
| Synthetic execution framework | **CONDITIONAL GO** | Disposable, local, sampler-blocked rehearsals. Treat successful terminal status as provisional until admission passes, and keep failed folders for diagnosis. |
| Real-runner integration | **HOLD** for a sampling-capable launch | A sampler-disabled integration can proceed. Fix lifecycle identity/fencing and bind a fixed launcher and worker entry point before enabling real draws. |
| New unsealed development experiment | **HOLD** | Resolve lifecycle blockers. Freeze the real design, admitted evidence, input binding, resource envelope, analysis and seed screen separately. |
| Confirmatory experiment | **HOLD** | Requires independent, prospective design, calibrated inference, demonstrable information parity and separate approval. |
| Sealed evaluation | **HOLD** | No access authorization or sealed-run readiness established. |

**Historical rulings stand.** DB8 is **VOID** under its original Section 8. The amended run remains descriptive development evidence with numerical **NO ADVANCE**. CF2 is **NOT CONFIRMED**. This audit does not recompute or change those decisions.

## Seven v10 reproductions

| Case | Fresh independent result | Scope |
|---|---|---|
| Empty episode | Classified corrupt | Verification of committed file set and hashes |
| Recovered reservation | Start refused, bytes unchanged | Terminal recovery never makes a reservation reusable |
| Concurrent starts | Four real Windows processes produced one claim; only one START file added | Same reservation, valid token. The separate reserve race can leave an unused sibling folder by design. |
| Controller contradictions | Independent mutations of segment start, length, plausible state and estimator rejected | New contradictions below remain admissible |
| Failed journal | Rejected after rebuilding the chain and closing inventory, with either terminal state | Same-byte verification and lifecycle checks |
| Duplicate ZIP name | Rejected | Duplicate name checked before NPY decode |
| Invalid seed aliases | Fraction, Boolean, string, missing value, infinity, negative, overflow and duplicate rejected | Exact keys and uniqueness hold within provided screen inventories |

## New findings

Line references are relative to `outputs/qshift_decoder_bank_v11/` unless otherwise specified. The matrix identifies executable probes and disposition.

- **P0 — Recovery can look like the original supervisor.** The fence treats a held supervisor lock as proof of liveness. Recovery holds the same lock before it publishes its fence. With recovery paused in that interval, a delayed Windows child entered the real worker guard and committed synthetic bytes after the original start lock had been released. This controlled interleaving uses a standalone child at the guard. The default parent's watchdog narrows that interval, and this test does not estimate its frequency or prove a default-pool orphan occurred. A separate injected PermissionError also appeared as a live owner. Bind the worker fence to the actual supervisor identity/handle, separate acquisition errors from contention, and make recovery exclude worker startup before testing quiescence. Join or explicitly account for idle and initializing children. See `lifecycle11.py:95–134,240–244,282–326,470–515`.
- **P0 — A terminal success may be unadmittable.** A job omitted sampling intent, confirmed synthetic seeds, and committed. The launcher persisted `succeeded`; admission correctly rejected it. Run the complete lifecycle and study validation before publishing success. Also make stage transitions one-way at their API boundary, so retry safety does not depend on the caller remembering to write intent first. See `lifecycle11.py:254–279,448–458,519–555`.
- **P1 — Callback, import and runtime binding stops short of executing the verified implementation.** Commit/parent/clean tracked files and declared working bytes are checked. Training/seed input bytes are checked when read via `frozen_json`, and analysis starts with admission. An independent post-verification probe demonstrated that an unbound preflight and supplied pool are accepted. External module origins are ignored, and imported code is authenticated by rereading its current source path. Worker checks run at commit, after computation. A transient file swap, stale bytecode, package shadow, late import or subprocess path difference can slip through or trigger rejection only after draws. These are avoidable accidental-integrity risks. Use a fixed launcher/worker and canonical preflight from a fresh controlled interpreter, admitted origins, immutable source and hash-on-use inputs before the first draw. Version labels alone do not authenticate package files. There is no need for signatures for a trusted owner and local filesystem. See `study11.py:39–101,116–169` and `lifecycle11.py:312–320`.
- **P1 — Inconsistent estimator records still pass.** The independent policy probe changed an already-flagged non-recall estimate and its AD3 copy to `p_hat=.25` and `b_hat=100`, outside the implemented fit range. The record remained admissible. Static review also found no rejection of the impossible S1=true/S2=false case for some known-class records, conflation of fit exclusion count and residual set, and insufficient validation of the final-block lookahead score. Verify implemented fit bounds and structural/finite-value invariants against the actual fit outputs. See `policy.py:59–76,104–130`, `../qshift_adaptive_robust_v1/estimate3.py:71–113`, `estimate4.py:26–50`, `he1b.py:26–27` and `../qshift_decoder_bank_v10/validate.py:106–109`.
- **P1 — Raw decisions and paired scoring are underdetermined.** The policy correctly replays changes, segment boundaries, plausible sets with quantization tolerance, tracker and bank decisions, fallback, legal AD3 recall membership and action flags conditional on supplied fields. It cannot reconstruct the actual approved windows, g/fit values, excluded detector sets, AD3 best match or lack of match, nor pred-to-label pairing across different decoder keys. A self-consistent change can alter lookahead, fallback, harm attribution and therefore a study's advance decision. AD3 match quality is directly material only for endpoints that use AD3. Adopt the smallest evidence tier for the claims actually frozen. See `policy.py:96–183`, `../qshift_decoder_bank_v9/db8_run.py:121–155,171–186` and `../qshift_decoder_bank_v10/analyze10.py:14–43`.
- **P1/P2 — Failure handling and resource bounds.** Unexpected errors while acquiring multiple slots can keep already-held locks alive in a retained traceback (`lifecycle11.py:120–134`, static finding). Release every acquired lock on exceptions and ensure OS errors are diagnosed. The current timeout is per completion stall, not an end-to-end deadline. Freeze whole-run resource limits before real execution. Preserve non-admissible torn terminal records byte-for-byte, with manual diagnosis under the local-filesystem assumptions. Cross-machine adversarial integrity and crash durability under actual power loss are outside the demonstrated scope.

## Evidence and limitations

Fresh results: **63 distinct checks passed and zero test assertions failed**. This includes seven shipped regressions, 37 shipped focused tests, 16 independent probes and three scoped integration cases. Of the 16 independent probes, six passed by reproducing a defect. The scoped 64-episode integration used committed DB8 development metadata, synthetic error bits and synthetic collision-screen metadata. It completed two identical analyses and rejected the wrong revision and runtime. Eight other shipped integration tests and original collision-screen inputs were outside this rerun. See TEST_RESULTS.json for commands, durations and unverified cases.

Independent tests exercised real Windows contention, simultaneous recovery, worker death during staging and a torn terminal marker. Shipped tests also exercised launcher termination with workers active, fencing after recovery, kills around the rename, interrupted startup and late final-check errors. Coverage is by explicit injection point. Windows spawn/bootstrap races, all possible process-death instruction boundaries, filesystem/OS failure and machine power loss were not exhaustively tested. The recovery impersonation probe pins the vulnerable logic rather than relying on a rare schedule.

Initial sparse worktree setup ran status before initializing its index. It displayed historical filenames beyond the audit scope. The unexpected deletions described an empty new index. It did not alter the checked branch or show protected contents. Initialized the isolated index from the pinned commit and switched to scoped status and file reads. Sparse setup had three import failures before the needed source dependencies were materialized. These were setup failures before any relevant test body. No software was installed or changed. See the machine-readable record for commands and counts. No experiment hypotheses, decoder performance claims or scientific evidence were changed.

- ☑ Pinned source and environment verified.
- ☑ Seven original cases independently reproduced.
- ☑ Lifecycle, record and source-binding limits assessed.
- ☑ Integration gate and minimum evidence specified.
