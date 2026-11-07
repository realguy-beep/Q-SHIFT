# Stage 2 Implementation Freeze V3 — Pre-sampling Supersession

This record supersedes the V2 implementation freeze before Stage 2 sampling. It changes no scientific condition, sample allocation, seed, model, optimizer, calibration rule, threshold, endpoint, or statistical criterion.

## Why V2 was stopped

FREEZE_IMPLEMENTATION_V2.json was created prospectively with zero samples and zero training. The first post-freeze environment preflight then called the runner's resource gate and found that the runner expected minimum_free_disk_gib, while the frozen configuration uses minimum_free_disk_gib_before_sampling. The frozen configuration itself is unchanged. This was an implementation-key mismatch, not a scientific-protocol change. The command failed before any Stim sampler was constructed. At that point run_v1/ did not exist, the preflight found no active experiment process, and no Stage 2 sample or training had started.

The old V2 freeze, V2 freeze builder, V2 readiness record, and original freeze remain preserved. V2 is a historical blocked pre-sampling record. Its source hashes are retained in that file and are not rewritten to match later code.

## V3 changes and checks

The runner now reads the exact frozen disk-limit key. Its environment check, per-partition resource gate, and 256-shot dry-run gate use the same configuration field. The V3 runner and independent auditor also expect the V3 freeze identifier. The V3 freeze hashes the original frozen sources, the V2 blocked record, this supersession record, the V3 readiness report, runner, auditor, freeze builder, and tests.

The superseded chain contains six snapshots: the four draft hashes listed by the committed original FREEZE.json, that original freeze, and the blocked V2 implementation freeze. V3 remains a pre-sampling freeze with shots_generated=0, training_started=false, and no independent-test allocation/access.

## Resumption/sampling rule

No Stage 2 execution can begin unless V3 hash verification passes. Only then may the permitted first 256 rows of the already allocated dev-root-00 nominal training stream be sampled for the bounded diagnostic. The stream continues to its frozen 10,000-shot allocation and those first rows are reused byte-for-byte. A failed dry-run estimate stops the experiment without changing the shot budget.
