# Phase 4A–4C baseline and provenance audit

## Phase 4A: detector-fit specialist versus nominal

Phase 4A uses rotated Z-memory, d=3, r=5, 40 detectors and one logical observable. Native DEPOLARIZE1/2 gate noise and basis-appropriate premeasurement noise are injected at Stim-generated locations. Its nine candidates use gate and measurement p in {.001,.003,.006}. Separate 50,000-shot/candidate templates yield Jeffreys-smoothed detector marginals. Per-regime calibration detector counts are scored by a summed composite Bernoulli log likelihood; calibration labels do not choose the calibrated model. Fixed is nominal (.003,.003); informed reference uses true rates. Each decoder receives the same test detector outcomes; residual is observable XOR predicted logical frame.

In measurement-heavy noise (.001,.006), 940/600,000 calibrated errors versus 1,118 nominal, 80 candidate-only and 258 fixed-only, p=5.600789e-23, 19/20 seed wins. Data-heavy is slightly worse and nominal ties. Independent Stage 0 audit explained three Markdown hash differences as documentation-only and passed scientific artifact checks. Static, condition-specific result only.

## Phase 4B: independent static replication, with deviation

Same d=3/r=5 Z-memory and grid, 20 fresh roots and 600,000 measurement-heavy test shots. Fixed made 1,165 errors and calibrated 1,008; discordances 99/256, exact McNemar p=3.730723e-17, 20/20 roots favored calibration. Saved test predictions independently re-decoded. Audit decision is PASS WITH DEVIATION: the actual runner created a fresh template bank while protocol text specified reuse. The result is a static calibrated-versus-nominal replication, not adaptive evidence. Recorded freeze chronology is not cryptographic proof.

## Phase 4C: stronger fixed comparison and missing calibration evidence

Stage 1 used calibration logical labels over 1.2 million development shots to select pooled fixed (.001,.003), minimax fixed (.006,.003), and condition-specific candidates. This is not the Phase 4A detector-marginal fit. Stage 2 used that frozen pooled model as baseline and the nine-point Phase 4A-style detector-marginal calibrated choice. On 1.8 million paired held-out shots, the equal-regime calibrated-minus-pooled difference was +0.00001556, 95% root-stratified CI [-0.00004889,+0.00007667], p=.66658. No gain over pooled fixed was detected.

The Stage 2 raw test predictions for all 60 roots were independently re-decoded. Calibration detector arrays and fitting score traces were not saved, so the choices cannot be independently refit. The RNG allocation was resolved by prospective amendments after the original Stage 2 plan; it is not an unqualified original preregistration.

## Causal interpretation

Phase 4A/B’s positive result is relative to a deliberately nominal fixed model. Stage 1 demonstrates that a stronger pooled fixed candidate can be selected from calibration outcomes. Stage 2 finds no calibration gain over that pooled baseline. This is consistent with baseline weakness and calibration selection variability as explanations for the earlier apparent headroom; it does not establish that these are the only causes. Calibration arrays missing in Stage 2 prevent a full reconstruction. Every within-phase decoder contrast described above is paired on common detector/observable shots; phases must not be pooled because they use different baselines/selection estimands.
