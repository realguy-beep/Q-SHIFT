# Q-SHIFT Phase 3B — Pre-Registered Protocol

**Protocol status:** frozen before Phase 3B final test-data generation. The SHA-256 digest of this exact file is recorded in `CONFIG.json`, `RESULTS.json`, and `SHA256_MANIFEST.json`.

## Research question and primary hypothesis

Does the Phase 3A X-specialist PyMatching decoder reduce residual logical-observable error compared with fixed nominal PyMatching for the distance-3 rotated surface-code Z-memory circuit under X-biased noise?

The primary endpoint is the paired per-seed difference in residual logical-observable error rate:

`X-specialist rate − fixed nominal rate`.

Negative values favor X-specialist decoding. The two-sided primary significance level is 0.05. Evidence for a reproducible improvement requires both (a) a two-sided exact sign test across non-tied independent seed differences with p < 0.05 and (b) the 95% percentile bootstrap interval for the mean seed-level difference to lie below zero. Shot-level tests are supporting analyses and cannot override seed-level results. Effect size will be reported in absolute percentage points and relative to fixed's error rate; statistical significance will not be equated with practical value.

## Frozen primary circuit and decoders

Use Stim `surface_code:rotated_memory_z`, distance 3, 3 rounds, 9 data qubits, 8 stabilizer ancillas, 24 detectors, and one `L0` observable. The generated circuit is flattened and its `DEPOLARIZE1/2(0.01)` instructions are replaced using the corrected Phase 3A rule: each participating qubit receives an independent `PAULI_CHANNEL_1(pX,pY,pZ)`, with unconditional probabilities equal to total p=0.01 times the conditional composition fractions. For the primary condition `(X,Y,Z)=(0.8,0.1,0.1)`, probabilities are `(0.008,0.001,0.001)`. Measurement flips remain disabled. Thus the local noise total and opportunities are equal, but the model is not a correlated two-qubit gate-noise model and includes channel opportunities on ancilla participants.

Fixed nominal is the PyMatching decoder from the depolarizing circuit's DEM at p=.01. X specialist is the PyMatching decoder from the X-biased circuit DEM at p=.01. DEM conversion retains `decompose_errors=True` and `approximate_disjoint_errors=True`. Decoder predictions use only detector samples; `L0` is read only for residual scoring. Residual error is `sampled L0 XOR predicted L0 correction`.

## Independent test data and seed plan

Use 20 independent replicate roots, starting at 31604001 and increasing by 10,000. For replicate index i=0…19, root=`31604001+10000*i`. For condition index c in the frozen order X-biased, Z-biased, depolarizing, held-out mixed X/Z, the Stim sample seed is `root + 101 + 100*c`. This produces 80 unique condition seeds, none used in Phase 3A (31503001–31503003 and their offsets) or the development timing check (31999001). Each root is the independent seed-level unit; the four condition samples within a root are not counted as additional independent replicates.

Generate 30,000 paired test shots per replicate and condition. The primary comparison therefore uses 20 independent seeds and 600,000 paired X-biased shots. The three other conditions are secondary, exploratory cross-evaluations on 600,000 shots each. For every dataset, exactly the same detector array is passed to each decoder being compared. Test samples are generated once and are not used to tune, select, or calibrate models.

## Shot-count and compute rationale

Phase 3A had 12 prediction disagreements in 36,000 X-biased shots (rate 0.000333) and an eight-error net reduction (rate 0.000222). If those pilot rates recur, 30,000 shots per seed yields about 10 informative disagreements per seed and approximately 200 over 20 seeds; the estimate is exploratory and may not recur. A separate non-test timing check on seed 31999001 decoded a 30,000-shot batch with both primary decoders in about 0.029 seconds combined. The planned data volume is 2.4 million shots across four conditions. The shot count and seed count are fixed before final outcomes are read; there is no outcome-based stopping.

## Primary and secondary statistical analysis

For each seed, record fixed and X-specialist residual counts/rates, prediction disagreements, X-only wrong shots, fixed-only wrong shots, and their difference. Report mean and median seed-level rate difference, a 95% percentile bootstrap interval from 100,000 resamples of the 20 seeds (bootstrap RNG seed 22604001), and the exact two-sided sign-test p-value over non-tied seeds. Also report pooled exact two-sided McNemar for the paired shots, clearly labeled as shot-level rather than seed-level evidence.

Secondary conditions are Z-biased, depolarizing, and held-out mixed X/Z. The frozen secondary comparison family has 15 candidate-condition contrasts: X, Z, depolarizing specialists and the condition-informed oracle each versus fixed on the three secondary conditions, plus the three non-primary specialist contrasts (Z, depolarizing, oracle) on X-biased. Apply Holm correction across all 15 exact sign-test p-values and separately across the corresponding 15 pooled McNemar p-values. Secondary outcomes cannot replace or modify the primary hypothesis.

## Integrity and deviations

Before testing, verify the ideal circuit yields zero detectors and zero `L0`, noisy condition circuit structures have one common structure hash when only channel arguments are ignored, and decoder outputs have one correction bit per shot. Save compressed raw detector and observable arrays and SHA-256 hashes. Verify aggregate counts equal per-seed sums. Preserve all outputs. If a demonstrable bug is found after test generation, mark the run invalid, document it, and restart with a new frozen protocol and fresh seeds; do not repair silently.
