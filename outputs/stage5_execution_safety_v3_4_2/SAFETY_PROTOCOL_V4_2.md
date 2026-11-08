# Stage 5 v3.4.2 process-ownership safety protocol

## Scope and preservation

This version repairs the v3.3 supervisor/child ownership handoff. It does not change the frozen Stage 5 scientific protocol, decoder, seed allocation, sample counts, Endpoint B, or secondary inference. The 53-hash v2 freeze and v3.3 safety history remain read-only. Stage 5 remains unauthorized; tests use only a new safety-only seed namespace and small benchmark fixtures.

## Ownership protocol

The supervisor first holds the OS-backed launcher lock. Before creating a worker, auditor, or finalizer it atomically records a unique child launch intent with the role, parent identity, token, and the shared absolute monotonic deadline. The token is passed in the child command line. The child must acquire its role-specific Windows/POSIX file lock and atomically claim that intent before it reads or writes run artifacts.

The supervisor retains the launcher lock until each child exits. If the supervisor is forcibly terminated, the durable intent remains. A subsequent launcher first probes all role locks and then checks the intent. A recorded child PID is verified against process creation time and token. If termination occurred in the `CreateProcess`/PID-recording window, the new launcher searches same-interpreter processes for the unique token, rather than depending on Windows parent-PID persistence. A live or ambiguous process blocks takeover. A stale intent is resolved only after the child is demonstrably gone and all role locks are available. Corrupt metadata and inaccessible candidate process information fail closed.

Each child starts a watchdog against the same absolute `time.monotonic()` deadline. The watchdog forcibly exits the process at expiry even if its supervisor has died or it is stuck inside a long operation. The normal supervisor also enforces the same deadline. The finalizer writes a verified manifest but never writes `status=completed`; only the still-live supervisor may do so after the finalizer exits, the manifest is reread, and the shared deadline remains.

## Restart and integrity behavior

Atomic NPZ archives retain SHA-256 commit sidecars. Resume verifies all existing sidecars before reconciling an in-flight calibration/evaluation stream. An interrupted, uncommitted stream is recorded and replayed with the same frozen seed only after explicit recovery. A committed stream is counted once. Ownership cleanup never repairs or rewrites experimental data.

## Frozen decision rules and evaluation boundary

The v2 Endpoint B threshold, separate zero-probability no-harm gate, four-condition Holm secondary family, finite-envelope inference rules, and 6,050-root / 27,225,000-shot allocation are preserved by hash. This safety revision itself does not authorize sampling. Its benchmark seeds are screened against recoverable historical metadata, prior safety benchmark seeds, and the frozen v2 reserved numeric namespace without opening Stage 5 seed rows.

## Required tests

Windows subprocess tests forcibly terminate the supervisor during auditor startup, active audit, finalizer startup, and active finalization. A separate launcher must reject each live child and may proceed only after the child watchdog exits and the role lock is released. Additional benchmark-only tests cover live contention, ordinary completion and independent rescoring, same-seed crash recovery, hashes, final status, and deadline expiry. Production sampling is not part of these tests.


This revision supersedes the failed v3.4.1 benchmark suite while preserving its source freeze and failed test report as historical evidence. Its new benchmark namespace is separate from all earlier safety revisions.
