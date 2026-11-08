# Stage 5 n=1,210 allocation: statistical design validation

## Decision

**NO-GO for Stage 5 sampling readiness.** The primary Endpoint B procedure and allocation pass their prespecified finite-envelope size, coverage, and formal power gates. The required condition-level Welch/Holm family fails under right-skew and tied/asymmetric nulls. No Stage 5 runner or sampling inventory was prepared; the Stage 5 sampling command was not run.

This is design simulation only. The proposed 1,210-root allocation projects to **27,225,000** Stage 5 calibration/evaluation shots if separately authorized. This validation generated **zero** Stim/Stage 5 shots and did not access sealed test outcomes.

## Frozen primary design

The estimand is the equal-weight average of four nonzero-condition, root-level paired adaptive-minus-fixed LER differences. Practical boundary: −0.0002. Planning alternative: −0.0003. Root-level distributions use the historical provisional condition SDs (derived from seven roots) scaled by 1.5× or 2×. The calibrated studentized-mean method and Wilson-bound criteria were not changed. Eleven primary null scenarios were used for separate critical-value calibration and independent validation; 20 power cells cover five 1.5× and five 2× families at effects −0.0003 and −0.0004. The missing 2× zero-inflated power family was included.

Primary calibration criticals at n=1,210: one-sided **1.781621**; central lower **2.137194**; central upper **1.992383**. Each null and power cell has 100,000 replicates.

### Primary boundary-null size and coverage

Pass requirements per null scenario: Wilson 95% upper bound for type-I ≤5.2%; one-sided upper-bound coverage Wilson lower bound ≥94%; central interval coverage Wilson lower bound ≥94%.

| Null scenario | Type-I | Type-I Wilson upper | One-sided coverage Wilson lower | Central coverage Wilson lower | Gate |
| --- | --- | --- | --- | --- | --- |
| normal_q1_5 | 3.653% | 3.771% | 96.229% | 96.008% | PASS |
| normal_q2 | 3.852% | 3.973% | 96.027% | 95.964% | PASS |
| student_t5_q1_5 | 3.761% | 3.881% | 96.119% | 95.976% | PASS |
| student_t3_q2 | 3.784% | 3.904% | 96.096% | 95.962% | PASS |
| right_skew_lognormal_q1_5 | 4.863% | 4.998% | 95.002% | 95.815% | PASS |
| right_skew_lognormal_q2 | 4.908% | 5.044% | 94.956% | 95.876% | PASS |
| zero_inflated65_q1_5 | 3.682% | 3.801% | 96.199% | 95.923% | PASS |
| zero_inflated65_q2 | 3.769% | 3.889% | 96.111% | 95.852% | PASS |
| tied_asymmetric65_q1_5 | 4.106% | 4.231% | 95.769% | 95.977% | PASS |
| tied_asymmetric65_q2 | 4.175% | 4.301% | 95.699% | 95.936% | PASS |
| balanced_offsets_normal_q1_5 | 3.782% | 3.902% | 96.098% | 95.884% | PASS |

All 11 primary null cells passed. Worst type-I Wilson upper: **5.044%**. Lowest one-sided coverage lower bound: **94.956%**. Lowest central coverage lower bound: **95.815%**.

### Primary power

The formal gate from the prior protocol is the 95% Wilson lower bound ≥80% at −0.0003 in all five 1.5× scenarios. The prior protocol labels 2× cases as sensitivity, so this report does not relabel them as a new formal gate; all were nevertheless simulated. `zero_inflated65_q2` is explicitly present.

| Root-effect scenario | True effect | Power | 95% Wilson interval | Status |
| --- | --- | --- | --- | --- |
| normal_q1_5 | -0.0003 | 96.760% | 96.648%–96.868% | Formal |
| normal_q1_5 | -0.0004 | 100.000% | 99.996%–100.000% | Sensitivity |
| student_t5_q1_5 | -0.0003 | 96.694% | 96.581%–96.803% | Formal |
| student_t5_q1_5 | -0.0004 | 100.000% | 99.996%–100.000% | Sensitivity |
| right_skew_lognormal_q1_5 | -0.0003 | 94.859% | 94.720%–94.994% | Formal |
| right_skew_lognormal_q1_5 | -0.0004 | 99.994% | 99.987%–99.997% | Sensitivity |
| zero_inflated65_q1_5 | -0.0003 | 96.725% | 96.613%–96.834% | Formal |
| zero_inflated65_q1_5 | -0.0004 | 100.000% | 99.996%–100.000% | Sensitivity |
| tied_asymmetric65_q1_5 | -0.0003 | 96.082% | 95.960%–96.200% | Formal |
| tied_asymmetric65_q1_5 | -0.0004 | 100.000% | 99.996%–100.000% | Sensitivity |
| normal_q2 | -0.0003 | 82.059% | 81.820%–82.296% | Sensitivity |
| normal_q2 | -0.0004 | 99.989% | 99.980%–99.994% | Sensitivity |
| student_t3_q2 | -0.0003 | 82.850% | 82.615%–83.082% | Sensitivity |
| student_t3_q2 | -0.0004 | 99.869% | 99.845%–99.890% | Sensitivity |
| right_skew_lognormal_q2 | -0.0003 | 80.703% | 80.457%–80.946% | Sensitivity |
| right_skew_lognormal_q2 | -0.0004 | 99.896% | 99.874%–99.914% | Sensitivity |
| zero_inflated65_q2 | -0.0003 | 82.440% | 82.203%–82.675% | Sensitivity |
| zero_inflated65_q2 | -0.0004 | 99.991% | 99.983%–99.995% | Sensitivity |
| tied_asymmetric65_q2 | -0.0003 | 81.741% | 81.500%–81.979% | Sensitivity |
| tied_asymmetric65_q2 | -0.0004 | 99.971% | 99.958%–99.980% | Sensitivity |

The formal 1.5× power gate passed in all five cells. The lowest power Wilson lower bound was **94.720%** for `right_skew_lognormal_q1_5`. At 2×, all five −0.0003 sensitivity lower bounds also exceeded 80%; the lowest was **80.457%** for `right_skew_lognormal_q2`. These are operating characteristics under the simulated root-effect families, not forecasts guaranteed for real Stage 5 roots.

### p=0 no-harm endpoint

| p=0 null scenario | Type-I | Wilson upper | Upper-bound coverage Wilson lower | Gate |
| --- | --- | --- | --- | --- |
| normal_q1_5 | 4.364% | 4.492% | 95.508% | PASS |
| normal_q2 | 4.330% | 4.458% | 95.542% | PASS |
| zero_inflated65_q2 | 4.849% | 4.984% | 95.016% | PASS |
| tied_asymmetric65_q2 | 4.925% | 5.061% | 94.939% | PASS |

The separate p=0 calibration critical was **1.705489**. All four null size/coverage cells passed. All eight p=0 safety-pass simulations (four distributions × true effects 0 and +0.0001; 100,000 each) had 100,000/100,000 passes, with Wilson lower bound 99.996%.

## Required secondary Holm family — failure

The Stage 5 candidate’s saved implementation uses one-sided Student-t/Welch-reference p-values for four condition-level differences and Holm adjustment at .05. This exact procedure was evaluated at 200,000 complete-null family replicates per scenario. Each family contains four independent condition-root vectors with the frozen unequal SDs. The ten scenarios cover the five root-effect families at 1.5× and 2×. Marginal p-values were also checked at each Holm step threshold with simultaneous one-sided Wilson bounds across 160 marginal checks.

| Complete-null family | Holm rejections | FWER | Simultaneous Wilson upper | Required upper ≤5.2% | Gate |
| --- | --- | --- | --- | --- | --- |
| normal_q1_5 | 9,783/200,000 | 4.891% | 5.017% | 5.200% | PASS |
| normal_q2 | 10,001/200,000 | 5.000% | 5.128% | 5.200% | PASS |
| student_t5_q1_5 | 9,788/200,000 | 4.894% | 5.020% | 5.200% | PASS |
| student_t3_q2 | 9,564/200,000 | 4.782% | 4.906% | 5.200% | PASS |
| right_skew_lognormal_q1_5 | 18,763/200,000 | 9.381% | 9.551% | 5.200% | FAIL |
| right_skew_lognormal_q2 | 18,670/200,000 | 9.335% | 9.504% | 5.200% | FAIL |
| zero_inflated65_q1_5 | 9,723/200,000 | 4.861% | 4.987% | 5.200% | PASS |
| zero_inflated65_q2 | 9,723/200,000 | 4.861% | 4.987% | 5.200% | PASS |
| tied_asymmetric65_q1_5 | 13,672/200,000 | 6.836% | 6.983% | 5.200% | FAIL |
| tied_asymmetric65_q2 | 13,859/200,000 | 6.929% | 7.077% | 5.200% | FAIL |

Right-skew lognormal FWER was **9.3815%** at 1.5× (18,763/200,000; simultaneous Wilson upper 9.551%) and **9.3350%** at 2× (18,670/200,000; upper 9.504%). Tied/asymmetric FWER was **6.8360%** at 1.5× and **6.9295%** at 2×. Therefore the Holm family fails its 5.2% operating bound. At the .05 marginal threshold, the right-skew 1.5× example had 13,985/200,000 rejections (6.9925%; simultaneous upper **7.1901%**, allowed upper 5.2%).

Independent replay reproduced all 160 marginal rejection counts and all 10 familywise counts exactly. The audit’s Holm gates are false. This is a method failure under the prespecified skewed/tied finite envelope, not a serialization artifact. Earlier serialization and audit-schema failures and their repaired versions are retained alongside the successful evidence.

## Independent audit and resource record

- Primary design simulation: 58 cells × 100,000 replicates; 612.57 seconds; final process RSS 102,903,808 bytes (this is a completion-time RSS reading, not a sampled peak).
- Primary independent audit: full seeded replay of 11 critical-value calibration cells, 11 primary null cells, 20 power cells, and 16 p=0 cells; exact counts and cutoffs matched; 568.48 seconds.
- Secondary Holm simulation: 10 families × 200,000; 245.24 seconds.
- Secondary independent audit: 160 marginal checks and 10 familywise cells replayed with exact counts; 247.17 seconds.
- Design-only primary seed inventory: 65 unique streams, zero collisions against 11,370 distinct large integers found in the explicit nonsealed metadata allowlist.
- Secondary inventory: 10 unique streams, zero collisions against 11,436 distinct large integers, including the parent design streams/results.
- Historical Stage 5 v2, Stage 4C, Stage 5 design v2, and the prior final decision memo hashes were verified and preserved by the freezes/audits.

## Limits

These simulations assess only the stated finite envelope. The SD values come from seven roots and remain uncertain; operating-characteristic validation cannot fix that. The root-effects are synthetic summary differences, not Stim-generated shots. Passing primary power does not establish a real decoder benefit. The secondary-test failure blocks the complete Stage 5 statistical package under the current protocol. No acceptance threshold or effect was changed, and the allocation was not increased.
