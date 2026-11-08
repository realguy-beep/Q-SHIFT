# Q-SHIFT v2 Pilot 2 protocol

Protocol ID: `qshift-v2-pilot2-v1`; status: frozen before Pilot 2 sampling. Branch: `qshift-v2-dev`, based on Pilot 1 commit `14985e3`.

## Question and hypotheses

Estimate whether detector-only causal event-triggered adaptation reduces unconditional logical error rate (LER) compared with (i) a development-selected burst-aware static decoder and (ii) EWMA profile adaptation. No superiority is presumed. Ordinary matching and explicit correlation-aware matching are parallel, separately analyzed conditions. The `oracle_true_p` arm is privileged and descriptive only.

Primary estimands: the equally weighted mean across the eight prespecified evaluation scenarios of (event GLR minus comparator) per-shot logical-error risk, for each primary comparator and decoding mode. Negative favors event GLR. Primary comparators are the static arm selected independently for that decoding mode and EWMA (alpha=.08). Pairing is by identical syndrome and observable shot. Co-primary success requires the upper endpoint of the two-sided 95% stream-cluster bootstrap interval to be below zero for both comparisons in at least one mode. This intersection rule avoids claiming a win from one selectively chosen comparator. No multiplicity adjustment is needed for this conjunctive decision rule. All other comparisons are secondary and descriptive.

## Sampling allocation and precision

Evaluation: 8 scenarios × 20 independent roots × (200 warm-up + 1,300 scored) = 240,000 unique shots. Scored length is 26 chronological 50-shot blocks. Scenarios: stationary burst p=0, .008, .016; step-up .002→.018; step-down .018→.002; smooth sinusoidal .01±.008; a .016 short transient on .002 background lasting 100 scored shots; measurement-noise mismatch at burst p=.008 with generated measurement-flip p=.006 while all decoder/profile models assume .003.

Separate data: 5,000 profile-template shots (1,000 each at p=0,.005,.01,.015,.02); 5,500 static-selection shots (500 each at 11 candidates p=0,.002,...,.020); 36,000 stationary GLR-calibration shots (12 roots × (200 warm-up + 800 scored) at each p=0,.008,.016); 12,000 change-detection tuning shots (6 roots × (200 warm-up + 300 scored) for step-up, step-down, smooth and transient schedules). Total planned unique shots: **298,500**, below the 300,000 ceiling. All sample seeds are enumerated and audited for overlap before sampling.

Using the Stage 4 development reference 478/87,500 = 0.546% as a rough rate, expect about 1,136 errors per policy and decoder mode over 208,000 evaluation-scored shots, with both decoder modes replaying those same unique streams. Scenario-specific counts vary with noise. Under an independent-shot approximation, the standard error of one arm's pooled LER at p=.00546 and n=208,000 is 0.0162 percentage points. Paired stream clustering can widen this materially. At each scenario (n=26,000 per arm/mode), the same approximation is 0.0456 percentage points. Therefore the design can inform moderate effects, but will remain imprecise for small differences; the independent stream (20 per scenario) is the uncertainty unit.

## Controller tuning and false alarms

A fixed tuning budget of 24 prespecified configurations is enumerated in the config and candidate CSV/log. Candidates vary GLR threshold, history length, minimum dwell, hysteresis, profile-estimation window, and pair-summary construction. The 36,000 stationary calibration shots alone determine eligibility. A candidate is eligible only if its empirical alarm rate is at most 1.0 alarm per 1,000 scored stationary shots pooled and separately at each of p=0,.008,.016. Among eligible candidates, select the lowest mean detection delay on the step-up, step-down and transient tuning streams (18 roots); the smooth-drift tuning streams are retained for responsiveness diagnostics but have no single change-point delay; ties break on fewer alarms then lexicographic config ID. If no candidate qualifies, select from all 24 candidates the one with the lowest worst per-p stationary alarm rate and mark the false-alarm target missed. Tuning records all candidates, including failures. Evaluation data are not used for controller selection.

A false alarm is an accepted GLR alarm during a constant-p segment, counted once per accepted event; exposure is stationary scored shots / 1,000. A graph switch is a change in the cached p-grid index actually used for the next decoded block; initial graph choice is not a switch. Detection delay is the number of scored shots from a scripted change point to the first subsequent block using a graph index closer to the new regime's nearest p-grid point than the pre-change index. If no such switch occurs before the next change/end, delay is right-censored and reported as such. Minimum dwell is in completed 50-shot blocks. Alarm diagnostics also record raw threshold crossings separately from accepted switches.

## Fairness and chronology

All policies and both decoding modes replay the same generated detector and observable arrays per stream. Every prediction is aligned shot-for-shot and scored as prediction XOR observable. Calibration/warm-up rows are excluded from LER. At a block start, all policies choose and use a decoder based only on detector rows strictly before that block; after prediction, the block's detectors may update the policy for the next block. The event test uses detector-pair summaries only. No online policy receives observables, logical labels, scripted scenario, or true p. Exact true p is passed only to the explicitly privileged oracle. The same graph cache/grid, data and timing boundaries are available to deployable policies.

Construction uses Stim DEM with `decompose_errors=True`, `approximate_disjoint_errors=True`; PyMatching `enable_correlations` is explicitly set at graph construction and `decode_batch` for every policy/mode. Profile, static-selection and tuning data are disjoint from evaluation roots. Static p is selected by minimum total development logical errors on its separate labeled set, with lower-p tie-break. No evaluation outcome is used for selection.

## Decoder bank, policies and timing

P-grid is 0,.002,...,.020. Policies: fixed p=0; static development-selected; one-time batch profile estimated from the 200 warm-up rows; trailing 200 detector rows; EWMA profile alpha=.08 over prior detectors; periodic refit each 200 scored shots; calibrated event-triggered GLR; privileged true-p block-mean oracle. The oracle is nondeployable and not a lower bound. Both decoding modes use identical banks where possible; static selection is mode-specific using the same selection observations. The oracle uses lazy exact-mean graphs, common to all policies in that mode.

Record graph-bank construction time and peak process RSS separately; per-stream and per-policy batch decode time; profile estimator time; change-statistic time; cached graph-index selection/switch time; calibration/training costs; and total replay time. Shared one-time model/profile costs are reported separately from adaptation overhead and per-shot decoding. Process RSS is a process-level high-water proxy, not reliably attributable to an individual C++ matcher; report that limitation. Python-level per-policy timing is attributable, with timer calls around each component.

## Statistical method and decision rules

For each stream, calculate the mean paired shot loss difference (event minus comparator). Primary estimate averages stream means equally within each scenario, then averages the eight scenario estimates equally. A 95% percentile interval uses 20,000 stratified cluster-bootstrap draws, resampling 20 independent stream IDs with replacement within each scenario and retaining paired method differences within each sampled stream. Recompute the statistic from saved stream summaries in an independent audit implementation. This is a development interval, not a confirmatory p-value.

GO toward protocol review for a full study only if the primary criterion above is met, or if event vs EWMA satisfies both: (a) the upper 95% clustered interval for event-minus-EWMA LER is below +0.10 percentage points (noninferiority margin fixed here); and (b) event reduces both total end-to-end CPU and graph switches by at least 20% relative to EWMA. A switch reduction alone is insufficient. Otherwise recommend the better-performing baseline or discontinue this event controller. No criteria will be changed after unblinding evaluation results.

Stop if any integrity check fails, if actual unique generated shots would exceed 300,000, if a required seed collision is detected, if the runner reveals leakage/misalignment, or if execution exceeds 8 CPU-hours or 8 GiB RSS. No full 11.736M-shot study or Stage 5 sampling is authorized.

## Independent audit

A separate audit program (not imported by the runner) will check the frozen config and hashes, development-seed disjointness against the listed historical Q-SHIFT development inventories, causal timestamps/update boundary, paired sample counts and outcome alignment, calibration exclusion, correlation flags, metrics/denominators, cluster bootstrap recomputation, timing fields and shot budget. It will read only Pilot 2 artifacts and explicitly listed nonsealed Stage 4 development inventories; it will not open Stage 5 files or Stage 5 seeds/outcomes.

## Reproduction

From repository root, after the seed plan is generated and audited:

1. `python -m outputs.qshift_v2_pilot2_v1.prepare_pilot2 --freeze`
2. `python -m outputs.qshift_v2_pilot2_v1.test_pilot2`
3. `python -m outputs.qshift_v2_pilot2_v1.run_pilot2`
4. `python -m outputs.qshift_v2_pilot2_v1.independent_audit`
5. `python -m outputs.qshift_v2_pilot2_v1.write_reports`

The exact environment, configuration, generated seed inventory, candidate records, result hashes and command outputs will be saved with the run. No evaluation sampling begins until configuration/seed inventory are frozen and tests pass.
