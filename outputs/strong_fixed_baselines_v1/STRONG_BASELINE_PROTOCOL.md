# Q-SHIFT Strong Fixed-Baseline Comparison — Protocol v1

**Status:** prospective development/feasibility study; not a confirmatory test.  
**Branch/base:** `codex/research-strong-baselines-v1` from `ae5ad5bc9ff90db15a1a77b64bf68e9a2b1b4971`.  
**Historical evidence:** Stage 5 and all previous studies remain unchanged.  
**Independent test:** sealed material is not part of this protocol and will not be opened.

`PRETEST_FREEZE.json` through `PRETEST_FREEZE_V5.json` are retained as historical pre-sampling source snapshots. The first 3,500-shot non-study benchmark is in `BENCHMARK_RESULTS.json`. Two later comprehensive benchmark attempts each sampled 3,500 non-study shots but failed in projection bookkeeping; their errors and retired seed ranges are preserved in `BENCHMARK_FAILURE_V2.md` and `BENCHMARK_FAILURE_V3.md`. The current inventory records shot counts and validates the exact 3,660,000-shot allocation. The successful benchmark-v4 run used five separate seeds and is summarized in `BENCHMARK_RESULTS_V4.json` and `BENCHMARK_RESOURCE_PROJECTION.md`. `PRETEST_FREEZE_V6.json` is the controlling pre-sampling freeze and supersedes V5, including direct inventory validation in the runner and resume-safe progress accounting. No study seed, hypothesis, model-selection rule, or allocation changed; no study shots had been generated when V6 was frozen.

## Question

Does detector-profile adaptation reduce logical-observable error relative to a strong fixed decoder that is tuned on independent development data and screened for zero-burst harm, or does the Stage 5 gain mainly reflect comparison with a burst-blind nominal matcher?

## Frozen circuit and noise family

Reuse the already audited generator without edits: rotated surface-code Z memory, distance 3, five rounds, 40 detectors, one observable; gate and measurement probabilities 0.003; balanced base Pauli noise; and `CORRELATED_ERROR(p) X8 X10` after each of five `MR` boundaries. The five injection events are independent across rounds. Tested p values are 0, 0.004, 0.008, 0.012, 0.016. This is the same narrow synthetic model as Stage 5, not a physical crosstalk model. Stim DEM conversion remains `decompose_errors=True, approximate_disjoint_errors=True`; all matching decoders enable correlated decoding.

## Decoder arms

1. **Nominal fixed:** matcher constructed at p=0.
2. **Pooled detector-calibrated static:** one p estimate from all final calibration detector batches pooled together, without condition labels, observables, or event flags passed to the estimator. It is one matcher for every evaluation condition.
3. **Safety-constrained optimized static:** select one p from `{0,.002,.004,.006,.008,.010,.012,.014,.016}` using only the independent selection-development partition. Among candidates whose observed p=0 mean excess LER over nominal is at most +0.0002, select the candidate with lowest equal-weight nonzero-condition LER; break ties toward lower p. On an independent validation partition, retain that one candidate only if its one-sided root-bootstrap 95% upper bound for p=0 excess LER is ≤+0.0002; otherwise freeze p=0 as the fallback. No candidate is reselected on validation data.
4. **Detector-profile adaptive:** fit profiles at p={0,.01,.02} on independent template shots. For each final root, estimate p from that root's separate 2,000-shot calibration detector batch only and rebuild PyMatching at that p.
5. **Privileged true-p reference:** matcher constructed at the generating p; nondeployable diagnostic, not an optimality guarantee.

The final calibration pool contains the same 2,000 detector-only shots per root used by the adaptive arm: 1,200,000 rows in total (120 roots × five conditions × 2,000). Pooling versus per-root use is the policy difference; total calibration-shot count is equal. The optimized static arm also uses labeled *development* outcomes to select its fixed p, and that extra selection budget is reported separately.

## Partitions and allocation

| Partition | Roots/condition | Calibration shots/root | Scoring shots/root | Purpose |
|---|---:|---:|---:|---|
| Profile templates | 20,000 shots at each of p=0, .01, .02 | — | — | Fit detector-only feature profiles |
| Selection development | 20 | 2,000 | 2,500 | Choose one static p using the frozen rule |
| Model validation | 20 | 2,000 | 2,500 | Validate the selected p=0 safety rule; no reselection |
| Held-out development evaluation | 120 | 2,000 | 2,500 | Paired feasibility evaluation of all five arms |

Allocation: 60,000 template + 900,000 selection/validation + 2,700,000 held-out development shots = **3,660,000 unique study shots**. A separate 3,500-shot pipeline benchmark is screened and listed outside this allocation; it is not pooled with study results. The held-out development evaluation has 1,500,000 paired scoring shots and 1,200,000 calibration shots. It is not a final confirmatory test and will not be reused for later tuning or confirmation.

## Separation and leakage controls

- The profile estimator API receives detector matrices only.
- Static p selection can use logical observables only in selection-development data; validation labels can only trigger the prespecified fallback to p=0.
- The pooled final calibration estimator receives a concatenated detector array, not condition labels or observables.
- A `FINAL_EVAL_SELECTION_FREEZE.json` must record the selected static p, pooled-calibration p estimate, exact decoder arm order, DEM conversion and correlation settings, experiment-configuration hash, and evaluation seed inventory before any held-out evaluation observable is generated.
- All arms decode byte-identical detector rows and are scored against the same observable array. Logical residual is `prediction XOR observable`.
- The privileged true-p arm is labeled nondeployable.
- Test archives, if any are mentioned elsewhere in the repository, are not opened or used.

## Analysis and decision language

Primary descriptive contrast: equal-weight mean over p>0 of root-paired `adaptive LER − safety-constrained-static LER`. Also report adaptive minus pooled detector-calibrated static and adaptive minus nominal fixed. For each condition, report counts, LERs, discordances and root-level differences. Use 100,000 stratified root-bootstrap resamples with a frozen analysis seed; report percentile 95% intervals. For p=0, report one-sided 95% root-bootstrap upper bounds for adaptive and safety-static excess LER versus nominal, with +0.0002 as the practical harm benchmark. Report the absolute −0.0002 benefit benchmark separately; this development pilot does not treat it as a confirmatory threshold.

No confirmatory p-values or “statistical superiority” claims will be made from this pilot. Bootstrap intervals describe this finite development sample and are not a replacement for a separately validated confirmatory procedure. If the interval for adaptive versus safe-static includes zero, or the effect is smaller than 0.0002 in magnitude, report the result as inconclusive or statistically distinguishable but practically small, respectively. A later independent study requires its own frozen protocol and power validation.

## Reproducibility and stopping

The seed inventory is generated from a new 18,000,000,001 namespace and screened against the exact 25-source historical metadata allowlist named by the Stage 5 seed audit. The historical audit files are not present in this fresh clone; the previous workspace's report and manifest remain locally available and their hashes are recorded in `seed_inventory.json`. The allowlisted source bytes were verified in that prior checkout; this clone's line-ending-normalized copies are not accepted as byte-identical substitutes. One listed file, `outputs/stage5_final_decision_v1/ALLOCATION_ESTIMATES.json`, is absent from the clone but was available and hash-verified in the prior checkout. All 11,464 recoverable historical integer values were screened; all new streams are unique and collision-free. A separate 3,500-shot benchmark is tagged `included_in_allocation: false` and cannot be pooled into study outcomes. Source/config/inventory/protocol/analysis hashes are frozen before the benchmark or study runner. Each sample partition is committed by an atomic NPZ plus a hash marker; ambiguous orphan files fail closed. The runner uses an exclusive create-only lock and refuses a present lock rather than guessing whether it is stale. Maximum resource limits: 2 hours wall time, 2 GiB process RSS, and 5 GiB required free disk reserve. Stop on any hash mismatch, seed collision, malformed checkpoint, DEM mismatch, nonfinite estimate, or exceeded limit.
