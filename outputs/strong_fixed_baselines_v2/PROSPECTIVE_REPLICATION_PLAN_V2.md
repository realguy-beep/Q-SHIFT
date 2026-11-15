# Prospective replication plan V2 — review candidate, not authorized to sample

**Status:** frozen candidate for supervisor review only. The seed inventory and pre-sampling hash freeze are prepared separately; `sampling_authorized` remains false. No V2 samples have been generated. A separate owner authorization is required before any sampling.

## Primary question and estimand

The primary comparison is **detector-profile adaptive Q-SHIFT minus strong detector-calibrated pooled-fixed PyMatching**, not adaptive minus the safety-static selector. For each nonzero generating burst probability, calculate the paired adaptive-minus-pooled logical-error-rate (LER) difference within each independent root. The primary estimand is the equal-weight mean of those condition-specific root means across `p = 0.004, 0.008, 0.012, 0.016`.

Report the effect in absolute LER points, relative reduction as a descriptive secondary scale, and the predeclared `0.0002` absolute practical-effect benchmark. This is a development study: the 100,000-resample root-stratified percentile bootstrap 95% interval is descriptive; no confirmatory p-value or superiority claim is planned. Report the number of condition estimates whose point effect is favorable, without treating that count as an independent significance test.

## No-burst safety and safety-static comparator

Retain the existing zero-burst no-harm rule for selecting the safety-constrained fixed comparator. On selection roots, eligible candidates must have mean `p=0` excess LER versus nominal fixed no greater than `+0.0002`; among eligible candidates, select the lowest equal-weight nonzero-condition LER, with lower-`p` tie-break. Validation may accept that single selected candidate only when the one-sided 95% root-bootstrap upper bound for `p=0` excess LER is no greater than `+0.0002`; otherwise fall back to nominal `p=0`, with no reselection. Report final-evaluation `p=0` effects for every deployable arm, but do not use evaluation results to change an arm or assert that adaptive has passed the selector's validation gate.

The safety-constrained static model remains a comparison arm, not the primary fixed reference. Its extra labeled selection/validation budget and its fallback behavior must remain visible in all summaries.

## Fixed design and paired evaluation

- Stim rotated surface-code Z memory, distance 3, five rounds, 40 detectors, one observable; gate/measurement probability `0.003`; synthetic spatial burst pair `(8,10)` inserted at the five circuit boundaries; burst probabilities `0, .004, .008, .012, .016`.
- Existing DEM conversion and PyMatching correlation setting remain as configured. No changes to circuit or noise model are proposed here.
- Five arms, in frozen prediction order: nominal fixed (`p=0`), pooled detector-only static, safety-constrained static, per-root detector-profile adaptive, and privileged true-`p` reference. The last is diagnostic and nondeployable.
- All five arms decode the same saved detector matrix for a root and are scored against the same saved observable vector. Calibration detector arrays are disjoint from every scoring/evaluation array. Adaptive estimation does not receive condition labels, observables, event flags, or future-root samples.
- Existing allocation: 60,000 template shots; 450,000 selection; 450,000 validation; 1,200,000 final calibration detector shots; 1,500,000 paired evaluation shots; 3,660,000 total unique allocated shots. Retain 20 selection roots, 20 validation roots, and 120 final-development evaluation roots per condition.

## Calibration and resource/information fairness

All detector-only deployable arms share the same 60,000 independent template shots. Pooled static and per-root adaptive each draw 1,200,000 final calibration detector shots. Pooled static concatenates all rows to fit one probability/model; adaptive estimates from each root's separate 2,000-shot calibration batch and can build a root-specific model. Equal total shot count therefore does **not** mean equal information aggregation, estimator variance, number of model rebuilds, or compute cost. Record estimation and decoder-construction timings for both.

The safety-static selector receives a further 450,000 selection plus 450,000 validation shots with observables (900,000 additional labeled shots). That is a stronger offline selection resource than detector-only pooled/adaptive calibration, not an equal-budget runtime comparator. Keep it as a deliberately safety-constrained static arm and disclose this imbalance.

## Partitions, seeds, and selection lock

Template, selection calibration/scoring, validation calibration/scoring, final detector calibration, final evaluation, and bootstrap RNG streams are disjoint in the inventory. The inventory is built from a fixed sequential namespace after collision screening against the exact historical seed-metadata allowlist and additional tracked seed-inventory/seed-manifest files. Only metadata are read; no shot archives or evaluation outcomes are opened. The audit records source paths, hashes, collision counts, and coverage limitations. Undocumented or unrecorded historical RNG use cannot be ruled out. `seed_inventory_v2_r2.json` is the candidate inventory bound by the freeze; the earlier no-sample `seed_inventory_v2.json` is preserved but is not used as historical RNG evidence.

The selection rule, candidate grid, estimator, calibration partitions, endpoint, bootstrap, and no-harm thresholds are fixed in this document/config before any V2 sampling. V1 outcome data and Stage 5 outcomes are prohibited as tuning inputs. Final-evaluation labels may be read only after all model selections/freezes have been written, for paired scoring.

## Statistical assumptions and limitations

The bootstrap resamples independent roots within each nonzero condition and computes the equal-weight four-condition effect. Shots within a root are not treated as independent inferential clusters. The interval is a percentile interval, not a confirmatory test; with five fixed noise conditions, inference is conditional on these tested conditions and does not generalize to arbitrary correlated noise. There is no multiplicity-adjusted hypothesis family because no confirmatory p-values are planned. The privileged reference is reported separately and never included in a deployable policy claim.

## Readiness boundary

V2 source, config, tests, statistical plan, independent audit implementation, and seed inventory are hashed in a candidate pre-sampling freeze with authorization explicitly false. The run entrypoint checks authorization before loading seeds or calling Stim. The freeze demonstrates prospective specification, not permission to sample. Do not alter the authorization field or run the candidate without a new explicit owner decision and supervisor review.
