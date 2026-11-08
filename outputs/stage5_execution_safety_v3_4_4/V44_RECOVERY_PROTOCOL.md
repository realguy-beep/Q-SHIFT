# Stage 5 filesystem and recovery-safety revision v3.4.4

## Scope

This revision integrates the v3.4.3 Windows persistence and archive-ledger primitives into a recovery-copy workflow. It does not change Stage 5's frozen scientific design: the five noise conditions, 1,210 roots per condition, 2,000 calibration shots and 2,500 evaluation shots per root, original seed inventory, detector-profile estimator, three decoder arms, Endpoint B, zero-noise no-harm gate, or secondary analyses remain as frozen.

The failed source remains `outputs/stage5_secondary_inference_repair_v1/run` at `worker_failed`. This package is not authorized to use that directory as a write target. All recovery mutations are restricted to the single separately created path `outputs/stage5_secondary_inference_repair_v1/run_recovery_v3_4_4`, with a `RECOVERY_PROVENANCE.json` linking it to the original 265-file inventory.

## Recovery-copy source protection

Before copying, the service hashes all 265 paths from `PRE_INVESTIGATION_SHA256.json`. It then holds nonblocking kernel locks on the existing launcher, worker, auditor, finalizer, and intent lock files without writing their contents. It requires the source status to remain `worker_failed`, checks that no token-owned process is live, and copies only `status.json`, root archives, and their commit sidecars. Every copied source hash must match the original inventory. Existing owner and lock records remain only in the source run and are recorded as omitted in recovery provenance.

If a source lock is missing, held, malformed, or ownership cannot be established, copy preparation fails closed. It never removes stale locks from the source.

## Recovery state machine

1. Verify the Stage 5 53-file freeze and the inherited 13-file v3.3 and 14-file v3.4.2 safety inventories; verify the new v3.4.4 source freeze.
2. Require a recovery directory with matching source inventory provenance. Verify every initially copied file and explain any later changed file through a unique chain of applied compare-and-swap write intents.
3. Under a recovery-copy OS lock, replay only exact durable write intents. Reconcile a checkpoint sidecar only when its archive replacement has one unique hash-verified archive intent.
4. Validate archive filename, condition/root identity, phase schema, shapes, binary values, both frozen seed IDs, and prediction re-decodes. Rebuild shot/root counters from valid archive arrays; never add deltas to old `status.json` numbers.
5. For `evaluation_complete`, calculate the frozen detector-profile estimate from saved calibration detectors, decode only saved evaluation detectors, independently reproduce the predictions, and atomically commit the complete checkpoint. Observable labels are not passed to the estimator or decoder. No Stim sampler is constructed by this recovery function.
6. Persist a recovery journal and reconstructed counters in the copy. Repeated execution is idempotent. An in-flight stream without a durable archive remains unresolved and is rejected; the system does not guess whether a sampler call completed.
7. Only the separate recovery runner can continue the frozen runner after an explicit `--authorize-stage5-recovery` flag, and only on the named recovery copy. It uses the original frozen seed map, skips verified committed roots, and carries the remaining frozen 7,200-second wall-clock budget into the owned worker/auditor/finalizer path.
8. Final completion still requires all 6,050 unique roots, 27,225,000 unique rows, independently re-decoded predictions, a complete archive manifest, matching reconstructed counters, and a finalizer manifest. Stage 5 statistics remain outside the recovery step and may be run only under a separate authorization.

## Windows persistence rules

`atomic_safety_v44.py` preserves exact payload bytes in a fsynced pending file and a write-ahead intent. It retries only Windows replace errors 5, 32, and 33 with bounded backoff and the caller's monotonic deadline. Before every replacement it checks the old target hash. A changed/newer target, missing pending bytes, corrupt journal, ambiguous intent, nontransient error, or exhausted retry fails closed. NPZ and sidecar writes are separately journaled; archive integrity is never inferred from shape alone.

## Commands (future operator use only)

From repository root, the read-only preflight is:

```powershell
python outputs/stage5_execution_safety_v3_4_4/recovery_runner_v44.py --preflight
```

Creating the separate copy is a distinct write operation:

```powershell
python outputs/stage5_execution_safety_v3_4_4/recovery_runner_v44.py --prepare-recovery-copy
```

Full continuation is deliberately gated separately:

```powershell
python outputs/stage5_execution_safety_v3_4_4/recovery_runner_v44.py --recovery-copy outputs/stage5_secondary_inference_repair_v1/run_recovery_v3_4_4 --authorize-stage5-recovery
```

**None of these recovery/copy/continuation commands was run in this task.** Only `--preflight` and disposable-fixture tests may be reported as executed. This protocol is an implementation record and does not grant recovery authorization.

## Residual limits

No production recovery copy was created and no actual Stage 5 archive was decoded or modified by v3.4.4. The root-123 recovery transition was exercised only with deterministic synthetic arrays. Full-scale throughput, disk headroom, crash behavior across power loss, directory-entry durability on Windows, and antivirus/ACL behavior on the user's machine remain unverified. The legacy v3.4.2 test that requires the original run directory to be absent cannot pass in this repository because that directory is required historical evidence; the independent v3.4.3 integrity audit checks the directory and its hashes instead.
