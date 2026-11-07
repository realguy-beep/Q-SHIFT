# Stage 5 Pre-execution Readiness Decision

**Decision: NO-GO for sampling today; implementation ready for independent review.** No Stage 5 samples were generated and the sealed independent-test allocation was not opened, enumerated, or accessed.

## Completed checks

- Candidate Stage 5 freeze independently verified: 14 recorded hashes, 4,171 recoverable historical development seed values, 1,002 proposed Stage 5 seeds, zero recorded collisions, and 2,250,000 planned shots. The older candidate protocol/configuration/freeze were preserved unchanged.
- Stage 5 v2 runner, inert-by-default command guard, resumable phase-tagged root checkpoints, per-root predictions and arrays, and an independent saved-array audit were implemented. The audit reimplements the profile estimator and statistics and rebuilds the DEM/PyMatching decoders; it imports neither the runner nor runner statistics.
- Eleven focused unit tests passed. Source files compiled. Tests include estimator parity on hand-built arrays, independent matcher decoding of a deterministic fixture, independent statistics recomputation, seed uniqueness, no-sampling-by-default, durable partial checkpoint resume, corrupted-prediction rejection, and a check that the auditor does not import runner/reporting functions.
- No-shot preflight passed with Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, Python 3.12.10. The zero-noise circuit/DEM were 40 detectors/one observable, and deterministic all-zero detector fixtures decoded to zero. DEM/graph construction succeeded for all five planned probabilities and a representative interpolated profile probability. No Stim sampler was invoked.
- Peak process RSS during the final no-shot preflight was 83,869,696 bytes; elapsed structural preflight was 0.088 seconds. Six DEM/graph builds took 6.7–12.7 ms each; the detector-profile estimate on a fixed 2,000-row engineering fixture took 3.17 ms; decoding 256 zero rows averaged 0.074 ms. These are structural/engineering benchmarks, not Stage 5 sampling throughput.

At the slower historical throughput recorded for the earlier 175,500-shot Stage 4 run (about 2,975 shots/s), 2.25 million shots would project to about 756 seconds (12.6 minutes) before Stage 5 specific overhead; the much faster Stage 4C run gives a shorter projection, but is less conservative. This supports plausibility under 1,800 seconds, not a measured Stage 5 runtime guarantee. The raw stored arrays require about 95 MB uncompressed from their frozen dimensions; compressed archives should be smaller, excluding metadata and filesystem overhead.

## Statistical review and remaining conditions

The proposed allocation is arithmetically correct: 1,000,000 calibration + 1,250,000 paired evaluation = 2,250,000 shots, below the 2,500,000 cap. Recomputed historical root SDs yield aggregate SE 0.000064291. The candidate's approximately 87.5% figure is power for rejecting a zero effect at true Δ=−0.0002 under a normal approximation; the full conjunction gate additionally requires an observed Δ≤−0.0002, which has only 50% probability at its boundary, before the all-four-strata consistency condition.

The two-sided root sign-flip test is not a randomized-treatment test. Its finite-sample validity depends on independent root effects being sign-symmetric under the null. The previous seven-root-per-cell SDs do not give a stable variance guarantee. These limitations do not justify silently changing the frozen test; they require the project reviewer to accept the conditional interpretation and provisional power before sampling.

The runner's full end-to-end runtime cannot be verified without generating the prohibited Stage 5 samples. Earlier Stage 4 throughput suggests the 30-minute cap may be feasible, and current no-shot construction is inexpensive, but this is an extrapolation. Actual run must stop safely at 1,800 seconds or 2 GiB RSS.

## Exact unresolved authorization items

1. A separate reviewer must explicitly accept the sign-symmetry interpretation, the root-cluster bootstrap, the Holm family, and the approximate power assumptions (or prospectively authorize a separate versioned amendment before any samples).
2. The project owner must separately authorize Stage 5 sampling. Neither this readiness work nor an earlier candidate-plan freeze authorizes the 2.25-million-shot run.
3. Before execution, rerun `python -m outputs.stage5_preexecution_v1.freeze_stage5` and `python -m outputs.stage5_preexecution_v1.stage5_runner --preflight` from the repository root to confirm hashes and environment remain unchanged.

The runner requires both `--run` and `--authorize-stage5-sampling`; passing only one does not launch. This task intentionally did not invoke either flag.
