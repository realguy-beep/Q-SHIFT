# NS-4A V6 stopped-benchmark recovery protocol

## Scope

V6 is a separately versioned execution-readiness benchmark attempt. It does not change the six conditions, six seeds, 6,000-shot maximum, six-call maximum, decoder configurations, or any scientific protocol. The Stage 5 boundary remains closed.

## Preserved V5 failure

The V5 attempt is preserved at `outputs/ns4a_v2_final_readiness_v5/benchmark_runs/3eb8d077109e8d2a`. The observed launcher error was `Windows process peak-working-set measurement failed.` It stopped during the initial resource check after about 3.1 seconds, before the sampling loop. The attempt had zero sampler calls, zero shots, and an empty output directory. The V5 local owner-authorization file is retained untracked and is identified only by its recorded SHA-256. The machine-readable record is `STOPPED_ATTEMPT_RECORD_V6.json`.

## New-attempt rules

- V6 never resumes or writes into the V5 attempt directory.
- V6 checks that the old V5 output root contains exactly the recorded attempt directory and that it remains empty.
- V6 verifies the old V5 authorization file's recorded hash as preserved incident evidence; it does not parse that file as permission and cannot accept it for V6.
- V6 writes to a new root, `outputs/ns4a_v2_final_readiness_v6/benchmark_runs/`, with an ID derived from the final V6 commit, V6 manifest, unchanged protocol and inventory, and recovery-record hash.
- V6 fails closed if that output root already exists. No implicit retry or resume is implemented.
- V6 requires a new owner authorization with schema `qshift-ns4a-v2-benchmark-recovery-authorization-v6`, created only after the final V6 commit and manifest are published.
- The authorization expires within 24 hours and binds the exact V6 Git HEAD, source-manifest hash, protocol hash, seed-inventory hash, and recovery-record hash.

## Preserved hard limits

The original limits remain unchanged: 6,000 total detector shots, six Stim sampler calls, 600 seconds wall time, 1 GiB peak working set, 1 GiB minimum free disk, and 128 MiB generated artifacts. Failure to measure peak working set is a hard stop. V6 reports the OS high-water `PeakWorkingSetSize`; it does not substitute current RSS, virtual memory, or available system RAM.

## Before any future execution

An owner must separately review the published V6 source and provide a new exact V6 authorization. That authorization is not included in this package. The V6 branch/PR and deterministic preflight do not authorize sampling.
