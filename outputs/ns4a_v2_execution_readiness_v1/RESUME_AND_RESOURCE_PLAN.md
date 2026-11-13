# Resumability and resource readiness plan

## Current state

The PR #7 lock-matched preflight is deterministic compatibility evidence, not an end-to-end workload benchmark. It constructed six DEM families and tested twelve decoder rows on a three-row synthetic detector fixture. It reports single-call construction/decode diagnostics; it did not measure Stim sampling throughput, 304,000-shot runtime, total-process RSS, checkpoint storage, restart time, or disk-write behavior. Full-workload resource readiness is **UNKNOWN**.

V2 proposes hard limits of 1,800 seconds wall time, 2 GiB peak RSS and 1 GiB free-disk reserve. These are proposed fail-stop limits, not observed capacities. Prior fixture timings cannot be linearly extrapolated into an execution guarantee.

## Required transactional runner behavior (not implemented)

1. Before sampling, validate frozen source/config hashes, all six exact circuit/DEM identities, all twelve candidate constructions, alias checks, seed uniqueness, the total shot cap, disk reserve, and absence of run/lock/recovery state.
2. Represent each root-condition partition as `planned → sampling → archive_verified → predictions_verified → committed`. Write a temporary archive, flush it, atomically replace into the run directory, hash it, and then atomically commit a journal marker that binds sample IDs, seed record, expected/actual rows and archive hash. The marker—not a mutable counter—is the unit of completion.
3. Check the 1,800-second monotonic deadline before and after sampling, scoring, output writes, final aggregation, audit and finalization. Fail closed if the deadline expires inside a non-interruptible Stim call: mark that call ambiguous/uncommitted and do not claim its rows. Never retry with a new seed.
4. Recover by verifying hashes and commit markers, reconstructing counts from committed archives, rejecting duplicate root IDs/sample keys, and resuming only missing, provably uncommitted partitions with the exact frozen seed. Preserve failed/partial artifacts in place; do not promote a partial archive to committed.
5. Enforce the 304,000 cap from committed sample IDs, with 64,000 selection and 240,000 evaluation separated by namespace and directory. Completion requires exact expected roots/shots, all arms' predictions, independent-audit pass, and valid analysis products. No automatic subsequent phase.
6. Use explicit lock/ownership semantics and tests for concurrent launch, termination during sampler and atomic write, corrupt and missing archive, duplicate root, stale/incomplete status, and resume from each commit stage. The runtime must never treat `generated` as `completed`.

These are acceptance requirements, not a claim that such a runner or recovery layer exists today. The reviewed PR #7 preflight runner is a deterministic compatibility tool and must not be repurposed as a scientific runner without a separate implementation review.

## Resource assessment

| Quantity | Evidence/status |
|---|---|
| Six DEM / twelve candidate deterministic fixture diagnostics | Observed in PR #7 lock-matched preflight; three synthetic rows only |
| Stim sampler throughput for these six models | UNKNOWN; no sampler benchmark authorized here |
| End-to-end 304,000-shot runtime | UNKNOWN; existing proposed 30-minute cap unvalidated |
| Peak process RSS including native Stim/PyMatching/BM allocations | UNKNOWN; not established by Python allocation tracking or fixture calls |
| Archive/checkpoint disk use and crash durability | UNKNOWN; no scientific persistence path exists in this package |
| Required 1-GiB free-disk reserve availability | Not measured in this task |
| Resumability / duplicate prevention | UNKNOWN; planned tests above have not been implemented |

Before owner authorization, run a separately approved benchmark using new non-evaluation benchmark seeds outside every experimental namespace. It must measure full generation, all twelve selection decodes, selected-model construction, paired BM/PM evaluation, aggregation, auditing, atomic I/O, RSS and restart cost. Report conservative elapsed-time/resource bounds under the exact proposed limits. This task did not run that benchmark or query resource capacity as a substitute.
