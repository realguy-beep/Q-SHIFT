# V2 independent saved-array audit plan

**State:** implementation and fixture checks only; there are no V2 output arrays to audit. This is not an audit of V1 raw evidence and does not access Stage 5 outcomes.

## Independence boundary

`audit_saved_arrays_v2.py` must not import the V2 runner, its result/reporting functions, or its aggregate counters. It independently reads committed NPZ archives, validates identities and hashes, reimplements the small detector-profile feature/interpolation calculation, reconstructs the baseline selection from saved selection/validation arrays, rebuilds PyMatching models from frozen parameters, re-decodes saved detector samples, and recomputes paired counts and the primary root-bootstrap interval. The frozen Stim/PyMatching circuit/model-construction primitives are reused as the declared decoder specification; matching predictions are recomputed from arrays rather than accepted from runner summaries.

## Read-only checks on a completed V2 run

1. Verify the candidate freeze, config/`seed_inventory_v2_r2.json` hashes, source hashes, stream uniqueness, allocation totals, and no-sampling marker in the inventory.
2. Verify every archive's `.commit.json` SHA-256, archive metadata, partition/probability/root/seed/shot identity, file path, and required array set. Calibration and template archives must contain detectors only. Scoring/evaluation archives must preserve binary detector-observable alignment. Prediction archives must point to the exact source archive hash.
3. Recompute selection and validation candidate predictions on each saved paired detector matrix. Recompute all candidate root errors. Reapply the frozen safety-static selection/tie-break and validation accept-or-fallback rule; compare to the saved selection freeze.
4. Fit a reference profile from template detector arrays only. Re-estimate pooled p from concatenated final-calibration detector arrays and root-specific p from each root's own calibration array; compare to the committed calibration/final-selection freezes and stored evaluation `p_hat`.
5. Independently decode each final evaluation detector matrix with the five frozen arms in order: nominal, pooled, safety-static, adaptive, privileged true-p. Require exact prediction equality to saved predictions before calculating errors.
6. Recompute per-root, per-condition, and total paired logical errors, candidate-only/fixed-only discordances, equal-weight nonzero primary effect, and the condition-stratified root-cluster bootstrap interval. Compare all saved summaries. No p-value is produced under the V2 development plan.
7. Write audit outputs to a caller-specified directory outside the run directory; never repair or mutate run artifacts.

## Completion conditions

The audit rejects partial/corrupt archives, missing roots, unexpected streams, duplicate seeds, p-hat mismatches, prediction mismatches, unpaired arrays, or summary disagreement. A process exit status alone is insufficient. The audit reports incomplete if any expected archive or freeze is missing. It does not treat a candidate freeze as sampling authorization.

## Reproduction

After (and only after) a separately authorized V2 execution, run the auditor against the preserved run directory. During this review checkpoint, only tiny synthetic fixtures are used to test the archive and scoring checks; no Stim samples, V2 run archives, independent-test arrays, or Stage 5 outcomes are opened.
