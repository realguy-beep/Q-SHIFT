# Q-SHIFT Performance Sprint V1 — Development Pilot Results

**Decision: NO-GO for this detector-profile adaptation.** In the frozen synthetic pilot, the profile-estimated and pooled-fixed PyMatching decoders produced identical predictions on every saved evaluation shot. The primary estimated reduction was zero, far below the predeclared 50% target. This is a development-only result, not a hardware result or confirmatory evaluation.

## Experimental identity and scope

- Isolated branch: `codex/qshift-performance-sprint-v1`
- Pre-sampling recovery implementation commit: `5e4af92b7730cf471d05fcd3af5baa75248539d3`
- Original V1 source-manifest SHA-256: `74ed5a099c9269bb58f38eb1b4c3884095e9680b0f433c4af81ae8400681c926`
- V1.1 recovery-source-manifest SHA-256: `dfe3ee7b4221fd68f92f8ff5d816629a3dd101fc2e599e54359f190e46c125a7`
- Circuit: Stim distance-3, five-round rotated Z-memory; balanced gate and measurement noise at 0.003; spatial burst pair (8, 10); burst probabilities 0, 0.004, 0.008, 0.012, 0.016.
- The decoder model is built from the frozen Stim DEM settings `decompose_errors=True` and `approximate_disjoint_errors=True`; PyMatching correlation support is enabled at construction and decode.
- The result is conditional on this synthetic circuit and this DEM conversion. It does not validate a physical processor or remove decomposition/approximation limitations.

## Compared decoders

| Arm | Information and role |
|---|---|
| Pooled-fixed PyMatching | One static matcher with a single pooled burst estimate from detector-only calibration. It uses all calibration batches. |
| Profile-estimated PyMatching | One matcher per evaluation root, with a detector-only estimate from that root's calibration batch. It shares the training partition and calibration allocation with the fixed arm. |
| True-p PyMatching | Privileged reference using the generating burst probability; not deployable and excluded from the primary decision. |
| No-burst PyMatching | Context baseline fixed at burst probability zero. |

Each of the four arms decoded the same evaluation detector rows. Observable labels entered scoring only after decoder calls. The true-p reference has information unavailable to deployable arms and is not a fair primary comparator.

## Allocation and execution record

The intended unique partition allocation was 5,000 training rows, 25,000 calibration rows, and 100,000 evaluation rows: 130,000 archived rows across 105 partition identities. There were 10 independent evaluation roots at each of five burst probabilities.

The first run stopped before decoding or saving the first evaluation root because the profile decoder's metadata name did not match the paired-evaluator registration key. Its historical `samples/status.json` incorrectly reports 32,000 verified rows; only 30,000 training/calibration rows were durably archived. The initial status hash remains `aae010949baa43dc1d9837ef73ce430d7bc4dac49ca5d5158ab12432285bc65e` and was not changed.

The separate V1.1 recovery fixed the name mismatch, reused the persisted training/calibration arrays, replayed the exact frozen `eval:p0:r00` seed, and executed the other 49 original evaluation seed partitions. No seed was substituted. Because the initial transient p=0/root-0 sample was not saved, byte-for-byte comparison against that lost in-memory array is impossible; the replay assumes deterministic Stim 1.16.0 behavior for the same circuit and seed.

| Measure | Observed |
|---|---:|
| Recovery calls / evaluation rows returned | 50 / 100,000 |
| Cumulative calls across failed attempt and recovery | 106 |
| Cumulative rows returned across both attempts | 132,000 |
| Distinct frozen partition identities | 105 |
| Persisted training + calibration + evaluation rows | 130,000 |
| Evaluation roots committed | 50/50 |
| Recovery wall time / cumulative wall including first attempt | 8.296 s / 9.718 s |
| Stim evaluation sampling time | 0.0547 s |
| Paired decode time | 0.9901 s |
| Profile matcher construction total | 1.2590 s |
| Peak process working set | 108,711,936 bytes (about 103.7 MiB) |
| Sample artifact tree size at completion | 540,080 bytes |

The 132,000 total counts sampler returns, including the transient first p=0/root-0 call and its replay. Only the one committed archive for that partition is part of the 130,000-row saved dataset. The run completed within the configured 600 s, 1 GiB peak-process-working-set, 128 MiB artifact, and 1 GiB minimum-free-disk limits. These are measured process-level checks, not a hard OS memory limit.

## Measured logical error results

Each condition below has 20,000 paired evaluation shots. Rates are errors divided by 20,000.

| Burst p | Pooled fixed errors (LER) | Profile estimated errors (LER) | True-p reference errors (LER) | No-burst errors (LER) | Profile vs fixed disagreements |
|---:|---:|---:|---:|---:|---:|
| 0 | 133 (0.00665) | 133 (0.00665) | 130 (0.00650) | 130 (0.00650) | 0 |
| 0.004 | 132 (0.00660) | 132 (0.00660) | 133 (0.00665) | 145 (0.00725) | 0 |
| 0.008 | 151 (0.00755) | 151 (0.00755) | 151 (0.00755) | 179 (0.00895) | 0 |
| 0.012 | 127 (0.00635) | 127 (0.00635) | 127 (0.00635) | 180 (0.00900) | 0 |
| 0.016 | 156 (0.00780) | 156 (0.00780) | 157 (0.00785) | 209 (0.01045) | 0 |

Across the 80,000 nonzero-burst evaluation shots, pooled-fixed PyMatching had 566 logical errors (LER 0.007075), and profile-estimated PyMatching also had 566 (LER 0.007075). The profile arm had zero candidate-only errors and the fixed arm had zero fixed-only errors. At p=0, both deployable arms had 133/20,000 errors.

The privileged true-p arm had 568/80,000 errors across the nonzero conditions (LER 0.00710), descriptively close to fixed and not uniformly better. This is an oracle reference, not a deployable result or a separately powered comparison.

## Estimator diagnostic

The detector-only regression largely returned the grid-average burst probability instead of distinguishing conditions. The pooled estimate was 0.0080043. Across 50 calibration batches, mean bias was 0.0000043 and MAE was 0.0047649; the near-zero overall bias is misleading because the five grid values are symmetric around 0.008.

| True burst p (diagnostic only) | Mean estimated p | Bias | MAE |
|---:|---:|---:|---:|
| 0 | 0.0079502 | +0.0079502 | 0.0079502 |
| 0.004 | 0.0079638 | +0.0039638 | 0.0039638 |
| 0.008 | 0.0079902 | -0.0000098 | 0.0000280 |
| 0.012 | 0.0080359 | -0.0039641 | 0.0039641 |
| 0.016 | 0.0080815 | -0.0079185 | 0.0079185 |

Generating probabilities appear here only for post-fit calibration diagnostics and the explicitly privileged oracle arm. They were not passed to the deployable decoders.

## Prespecified primary and gates

The primary estimand was the equal-weight mean, over p=0.004, 0.008, 0.012, 0.016, of root-paired profile-minus-pooled-fixed LER differences. The result was `0.000000`; the 100,000-replicate root-stratified paired percentile 95% interval was `[0.000000, 0.000000]`. It is degenerate because the two saved prediction arrays agreed on every evaluated shot; it is not a general equivalence proof.

- Relative reduction: 0% (target: at least 50%).
- Favorable nonzero conditions: 0 of 4 (gate: at least 3).
- Fixed errors on nonzero conditions: 566 (minimum evidence gate: 100, met).
- Maximum per-condition harm: 0 (tolerance: 0.0005, met).
- p=0 difference: 0; one-sided 95% bootstrap upper bound 0 (no-harm tolerance: +0.0005, met).
- Frozen decision rule: **NO-GO**. The confidence interval does not show an improvement, the relative-reduction target is missed, and no nonzero condition favors the profile arm.

The small root count and zero-inflated/low-error setting limit broader conclusions. The result rules against claiming benefit for this tested detector-profile estimator/configuration; it does not rule out other adaptation methods or noise regimes.

## Independent audit

The independent saved-array audit returned `audit_status=PASS`: 50 roots, 100,000 evaluation rows, 200 arm/root prediction reconstructions, zero prediction mismatches, and maximum calibration-estimate reconstruction difference 0. It independently rebuilt PyMatching models from the saved configuration and detector-only calibration arrays and recalculated the primary interval and zero-burst bound. It made zero sampler calls and generated zero shots.

Raw `.npz` arrays remain local and ignored by Git. Their archive hashes and paths are recorded by the committed independent audit and run evidence manifest; repository users can inspect the report and lightweight per-root CSV, but must have the local archives to rerun the saved-array audit.

## Validation and deviations

- Deterministic V1 + V1.1 tests: 13 passed.
- `python -m compileall -q outputs/qshift_performance_sprint_v1`: passed.
- Initial V1 runtime failure: decoder-name mismatch before any prediction/scoring; preserved.
- Direct-script recovery launch failed at import (`qshift_core_v1` not on script-mode path), before runner initialization or sampling. The module invocation then passed and completed.
- Module-form analysis launch failed at import before analysis I/O. Running the same frozen analysis and audit files as direct scripts succeeded.
- One early deterministic test failed because its expected manifest entry count was stale; corrected before the recovery commit and sampling. Its prevalidation manifest is preserved as superseded evidence.
- No Stage 5 files, sealed evaluation outcomes, or hardware results were accessed.

## Artifacts

- `EXPERIMENT_PROTOCOL.md` — frozen prospective design.
- `RECOVERY_V1_1_OPERATIONAL_AMENDMENT.md` — explicit replay and failure disclosure.
- `root_results_v1_1.csv` — per-condition/per-root paired counts and rates.
- `analysis_v1_1.json` — prespecified analysis.
- `independent_audit_v1_1.json` — saved-array reconstruction audit.
- `RUN_EVIDENCE_MANIFEST_V1_1.json` — hashes for committed and local run evidence.
- `samples/recovery_v1_1/` — local ignored evaluation archives and commit markers.
