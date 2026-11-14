# Research log

## Checkpoint 1 — repository orientation (2026-11-14, Asia/Calcutta)

**Workspace:** detached worktree `the detached Q-SHIFT method-landscape research worktree`, exact review commit `f7f0fc167960e9499e40785a9b2262295bfecabc`. The requested V7 watchdog branch head is `033e98e873d503056b9e9b05a496c3b7cff06ccc`; the readiness-review branch head is the reviewed commit. No commits or pushes are authorized by this task.

**Read/inspected:** repository `AGENTS.md`, `README.md`, `RESEARCH_STATUS.md`, `EXPERIMENT_INDEX.md`; Phase 4A method/results/interpretation/validation; Phase 4B protocol/results/interpretation/evidence audit/template provenance; Phase 4C Stage 1 protocol and selection/results, Stage 2 frozen plan and recovered audit/results/limitations; NS-4A V2 readiness review and required corrections; V7 watchdog repair report. Inspected source paths only by targeted queries; no runner or tests were executed. Some large tool output was truncated, so selected readiness, implementation, and source files remain to be re-read directly.

**Preliminary evidence synthesis:**

- The repository itself states no demonstrated adaptive or neural advantage over strong fixed PyMatching.
- Phase 4A/4B are stationary static-calibration comparisons on a distance-3, five-round rotated Z-memory circuit, not online switching. Their primary measurement-heavy condition improved versus nominal fixed, but data-heavy/nominal did not show a corresponding broad gain. Phase 4B has a material fresh-template deviation despite its protocol specifying template reuse.
- Phase 4C is a closer pooled-fixed comparison. Its recovered Stage 2 equal-regime calibrated-minus-pooled effect is reported as +0.00001556 (not significant); calibration detector arrays and fitting traces are unavailable, limiting provenance.
- NS-4A V2 asks whether one selected BeliefMatching decoder changes paired logical outcomes versus a global selection from a finite PyMatching grid over six synthetic conditions. It does not test adaptive selection or identify a full factorial burst-by-composition interaction. Readiness remains corrections-required; no sampling authorization exists.
- The V7 watchdog repair is a separately scoped engineering change; the V2 readiness review reports its 600-second limit conflicts with the proposed 1,800-second protocol deadline and it is not integrated. V7's own report says it does not authorize the experiment.

**Tests/experiments:** none. **Stim sampling:** zero. **Decoder evaluation:** zero. **Training:** zero. **Protected Stage 5 access:** none. I did read the high-level project index, which summarizes archived development work; I did not open Stage 5 outcomes, manifests, seed inventories, raw artifacts, or checkpoints.

**Next:** reread the V2 protocol, config, runner/authorization and V7 gate source at the exact reviewed commits; inspect Phase 4C and NS-3B/BeliefMatching design evidence; then begin primary-source literature search with a citation-chain ledger. Check `RESEARCH_STOP.flag` before substantial tasks.

## Checkpoint 2 — adaptive decoding source review (2026-11-14, 00:55 UTC / 06:25 Asia/Calcutta)

**Work since checkpoint 1:** searched and opened primary-source arXiv HTML for DGR (arXiv:2311.16214v3), Adaptive Estimation of Drifting Noise in QEC (arXiv:2511.09491), Experimentally Informed Decoding from Syndrome Correlations (arXiv:2502.17722), and QAdapt (arXiv:2607.28422v2). Also located primary sources for Page CUSUM, ADWIN, and Bayesian Online Changepoint Detection. No tests, execution, sampling, new shots, decoder evaluation, training, seed work, or protected-data access.

**Interim synthesis:** DGR is closest to direct online matching adaptation, but uses prior MWPM matchings as pseudo-observations to update edge rates and correlations; this creates possible self-reinforcing estimation error and its paper reports that reliable frequency estimation may require very long histories (the text gives convergence illustrations around 10^6 trials for one p=0.001 setup). Its reported gains are simulation evidence under its own surface/honeycomb models, not evidence for Q-SHIFT's burst process. Bhardwaj et al. instead estimate time-varying Pauli noise from syndrome statistics with sliding-window/filtering analysis; transferability depends on their identifiability/noise assumptions and feature-to-parameter map. Remm et al. derive independent event probabilities from higher-order syndrome correlations, but uniqueness of event signatures and model closure are central conditions. QAdapt is a large learned residual predecoder with continual EWC updates, followed by matching; the paper's “online” refers to sequential training across noise tasks, while key compound-noise and hardware comparisons use frozen weights. This is not a detector-only causal change-trigger controller equivalent to Q-SHIFT.

**Design implication (not a finding of benefit):** the first tractable Q-SHIFT direction remains a detector-only causal change detector paired with a fixed, low-dimensional estimator and cached graph bank; evaluate against same-information static, trailing-window, EWMA, and periodic update rules. Treat matching-history reweighting (DGR-like) as a separate high-risk comparator because its pseudo-label feedback and data needs differ. Do not add adaptive neural training without a documented accuracy mechanism, information-parity plan, and compute justification.

**Remaining:** inspect the full methods/assumptions/results of the drift-estimation and syndrome-correlation papers; inspect Q-SHIFT controller repairs and strong-static headroom reports using targeted individual files; verify NS-3B compatibility limits and exact package manifests; extend primary-source scan to algorithmic matching/BP/OSD and temporal detectors; update the literature/method feasibility tables. No repository source changed.

**Targeted source inspection update:** `qshift_core_v1/controller.py` is a generic causal selector with confidence, hysteresis and dwell gates, but it is not a noise estimator nor a Q-SHIFT-specific change detector. The integrated NS-4A V2 runner remains a separate static model-selection experiment, not evidence of a production online controller. Therefore the current repository evidence does not yet contain a complete, deployable causal controller; a later candidate must specify the estimator and trigger independently, and must use previous-block detector data only.

### Checkpoint 3 — estimator and correlated-matching comparison (2026-11-14, Asia/Calcutta)
Focused review covered the full methods of the published drifting-rate paper, additional primary adaptive-weight and Bayesian-estimation papers, QAdapt's online-training details, and a recent correlated-matching preprint. The published syndrome-edge estimator in Bhardwaj et al. inverts detector moments under independent graph-edge mechanisms; Q-SHIFT's categorical joint event violates that assumption if naïvely treated as two independent edges. Bayesian TN+SMC/MCMC gives a principled generative alternative but depends on a known model and costly Monte Carlo likelihood/posterior estimation. Spitz et al. supplies an earlier algebraic adaptive-weight route and makes a drift-timescale/sample-volume caveat explicit. Huo & Li uses approximate correction/syndrome estimates plus GP extrapolation; its ideal-decoder evidence does not establish value against Q-SHIFT strong PyMatching.

A recent arXiv preprint on regularized correlated matching studies two-pass cross-subgraph reweighting, not PyMatching's correlation flag itself. Its failure claims must not be transferred to Q-SHIFT's PyMatching option without establishing algorithm identity. It motivates a deterministic minimum-weight fault-pattern audit for future correlated arms; that audit is not run here.

No tests, source execution, sampling, decoder inference, benchmarks, training, seed creation, protected data access, commit, or push occurred. Next: source review of Q-SHIFT estimator/model features and NS-3B dependency limitations; literature check of the actual official BeliefMatching paper and BP+OSD feasibility; refine recommendation and open issues.

**Correction to checkpoint 2 implementation wording (same date):** static inspection of `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py` confirms a source-faithful `DetectorProfileEstimator` exists. It maps each 40-bit detector shot into 45 bits (the 40 detectors plus the five specified co-firing indicators at `(8,10)`, `(16,18)`, `(24,26)`, `(32,34)`, `(36,38)`), fits template feature means at known development burst-probability knots, scales each coordinate by pooled template SD, linearly interpolates, and minimizes mean squared standardized feature error over a 1e-5 probability grid. Inference `estimate()` receives detector arrays only. The protocol-faithful final pooled version fits templates on separate labeled simulator settings, then consumes a detector-only calibration matrix. The related `headroom.py` classifier uses only smoothed detector marginals and is a separate lower-feature model. `qshift_core_v1/controller.py` is the generic causal selection hook (strictly prior block, confidence/hysteresis/dwell), but no implementation found yet connects this streaming selector to a predeclared rolling-window estimate/change statistic on a true chronological stream. Therefore “estimator exists” and “online adaptive controller exists” must stay distinct.

**Checkpoint 3 elapsed-work record:** The earliest UTC timestamp available after resuming this task was 2026-11-14 00:55:14 UTC (06:25:14 Asia/Calcutta); this source-review segment was recorded through 2026-11-14 01:02:37 UTC (07:02:37 Asia/Calcutta), a measured interval of 7 minutes 23 seconds. This is only the monitored segment, not a claim about earlier inactive time or total mission duration. Completed: primary-source literature audit batch; static check of the 45-feature estimator and causal selector; updated literature/method/hypothesis/open-question logs. Tests: none. Experiments/sampling: none. Remaining: assumption audit for drift/correlation estimators, upstream implementation checks, information-parity/timeline comparison, novelty review.

### Checkpoint 4 — decoder-family feasibility review
Read primary sources for BeliefMatching, BP+OSD, BP+LSD, tensor-network decoding, and union-find; distinguished each paper's target code/model from Q-SHIFT. No decoder executable was run and no accuracy test or benchmark occurred. Current reasoning: use PyMatching as the near-term comparator because Q-SHIFT is only 40 detectors/one observable and existing experiments indicate strong fixed performance; pursue another decoder only if a deterministic representation/correctness audit identifies lost hyperedge or correlation information that the selected interface can exploit. BP+OSD is a bounded exact-small-case backstop, not presumed practical/adaptive winner. Continue to extract primary citations, review the upstream BM interface claims from existing package evidence, and prepare final method ranking/novelty assessment after coverage checks.

**Static cost derivation (not a benchmark):** On the estimator's likely `[0,0.02]` template range (verify exact knots before final), `1e-5` step implies 2,001 candidate p values. The expected-feature matrix costs exactly 720,360 bytes for 2,001×45 float64 entries (~0.687 MiB), before array/Python overhead. Precomputing these means is an implementation optimization candidate. It does not imply 2,001 decoder graphs are needed; graph bank quantization is an unresolved method/cost decision.


**Arithmetic correction:** the stage4 feasibility config pins profile knots at `[0.002, 0.01, 0.018]`, not `[0,0.02]`. Therefore the actual existing profile fit spans 0.016 and contains 1,601 grid points at step 1e-5. The cached 45-feature float64 mean array would occupy 576,360 bytes (~0.550 MiB), plus 12,808 bytes for scores and object overhead. Current feasibility entries were corrected; no runtime claim.

### Checkpoint 4 — feature model, parameter grid and decoder scope (2026-11-14, 01:07:17 UTC / 06:37:17 Asia/Calcutta)

Targeted source inspection verified the actual 45-dimensional estimator and profile knots `[0.002, 0.01, 0.018]`. The p grid is 1,601 values at 1e-5; its 45-coordinate float64 mean array is 576,360 bytes (~0.550 MiB), excluding overhead. This is a static arithmetic bound, not a runtime benchmark. The grid estimates p and does not require a full 1,601-graph bank; graph construction/caching/horizon costs remain separate decisions. Clarified that the generic selector is not wired to the batch profile estimator in the inspected source.

Added a common information-set/time-axis table. Key issue: literature frequently treats within-memory syndrome rounds, but the proposed Q-SHIFT control stream may be completed five-round reset shots. These are different temporal models and cannot be silently concatenated. Added a cautious architecture hypothesis (frozen strong static fallback; cached coarse bank; detector-only estimator and trigger separated; prior-block only; uncertainty/OOD fallback; identical history/opportunities across baselines).

Validated primary sources for Wagner et al.'s identifiability theorem and discovered a DOI suffix typo in a preserved local memo; correct DOI is `10.22331/q-2022-09-19-809`. The generic theorem's support/detectability assumptions do not decide identifiability of Q-SHIFT's constrained categorical burst family. Confirmed DGR remains an arXiv preprint in author publication metadata; no implementation found. No code, tests, benchmarks, sampling, decoder inference, training, seed work, protected access, commit or push.

**Monitored elapsed interval since checkpoint 3:** 4 minutes 40 seconds (01:02:37–01:07:17 UTC). Earlier inactive time is not estimated.

**Pair coverage arithmetic:** `40 choose 2 = 780`; five explicit pair indicators correspond to 0.641% of possible detector-pair locations. This is an index count only, not a claim about information percentage. All 40 detector means plus those five pair-cofires encode five pair moments; no higher-order moments are directly represented. The 45-feature fit should be described as burst-family-specific.

**Temporal-model clarification from simulator source:** the current burst circuit inserts one independent `CORRELATED_ERROR(p) X8 X10` at each of five MR boundaries, with all five boundaries sharing the builder's scalar p. Thus five independent event opportunities are inside each shot. Across-shot drift is an outer stream of per-shot p values; within-shot rate drift is unsupported by the current circuit builder. Any future controller/pilot must freeze which transition is studied and ensure it can causally update only after a completed shot or, if physically intended, extend/redefine the circuit chronologically before protocol review.

### Checkpoint 5 — correlation calibration and BM pinned-source audit (2026-11-14, 01:12:19 UTC / 06:42:19 Asia/Calcutta)

Remm et al.'s published PRR paper was read more deeply: it estimates probabilities for independent error signatures via correlation moments and uses explicit truncation assumptions (e.g. no higher-support errors for lower-support closed forms). This can calibrate known model signatures but does not identify arbitrary correlated mechanisms or establish sufficiency of Q-SHIFT's 45 summaries. The map has 40 single means plus five selected pair cofires, covering five of 780 possible pairs and no explicit higher moments.

Read the exact pinned BeliefMatching `setup.py` and `belief_matching.py` source at commit `4458c278bbec273c8c1a26411dadccc49222f8ef`. Requirements are Stim, PyMatching>=2.0.1, LDPC, Sinter>=1.11, NumPy<=2.2.6 (no explicit Python/Bazel requirement in setup.py); local lock satisfies them. Apache-2.0 license. API accepts Stim circuit/DEM with decomposed errors. BP converged path returns BP-derived observable bits; nonconverged path derives edge probabilities from LLRs and constructs a fresh PyMatching graph with virtual boundary support per shot; `decode_batch` loops over shots, defaults 20 BP iterations/product-sum. This is a source-level compute risk and method distinction, not a newly run test.

Clarified actual simulator timeline: one scalar p is applied independently at five MR boundaries inside each five-round shot. Existing builder does not implement within-shot rate drift; across-shot p changes are a distinct outer chronology. Added a provisional ranking and narrowed publication-potential criteria; no final recommendation until coverage and audit complete.

**Monitored interval:** 5m02s since checkpoint 4 (01:07:17–01:12:19 UTC). No tests, samplers, detector shots, decoder inference, benchmarks, training, seeds, protected access, commits, or pushes.

### Historical Stage 4 feasibility evidence (report-only review; no data reanalysis)
The preserved `outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_FEASIBILITY_PILOT_FINDINGS.md` reports a 48,000-shot development feasibility pilot (six roots, three per unseen p stratum). It used fixed balanced gate/meas noise, profile knots `{0.002,0.010,0.018}`, unseen p values `{0.006,0.014}`, separate calibration data and paired detector/observable scoring. Reported detector-only estimates: p=0.006 had mean p-hat 0.00559, MAE 0.00050, bias -0.00041; p=0.014 had mean 0.01334, MAE 0.00086, bias -0.00066. The report records estimation-assisted errors 63/12,000 vs nominal 74/12,000 at p=.006, and 70/12,000 vs 102/12,000 at p=.014. It also records true-p reference errors 62 and 72; hindsight assumed p=.010 gave 58 at true p=.006 and p=.018 gave 69 at true p=.014. These make physical p recovery distinct from LER-optimal decoder parameter choice.

These are *historical small development observations*, not reanalysis, and root intervals had only df=2. All three calibration bootstrap intervals per stratum covered true p, but strata intervals overlapped; no dependable separation or superiority conclusion follows. Crucially, the controls fixed gate and measurement probabilities, so this does not establish robustness to measurement mismatch. The later strong-fixed-baseline report compared causal/per-root adaptation to pooled static and found a much smaller mean `-0.00002917` adaptive-minus-pooled effect over nonzero burst settings; that later report also had a disclosed calibration implementation deviation and a corrected reconstruction. Therefore evidence supports only that the selected 45-feature map contains useful information about the known burst parameter under its fixed model and that a p-conditioned matcher can change decisions vs nominal. It does not establish an advantage over strong static selection, joint nuisance identifiability, or hardware transfer.

The pilot's reported 9.19s CPU runtime is retained as that report's historical measurement only; this phase did not repeat it, and it is not a deployment or full-study runtime estimate.

### Checkpoint 6 — historical pilot/context audit (2026-11-14, 01:13:28 UTC / 06:43:28 Asia/Calcutta)

Read existing Stage 4 estimator design, feasibility review and pilot findings, plus its already aggregated burst-p mismatch table. This is report-only inspection; no raw detector arrays, seed manifests, or sealed material were opened. Confirmed the pilot stress was *burst probability interpolation* at fixed gate and measurement settings, not a measurement-model mismatch stress. Thus no historical evidence yet establishes robustness to measurement noise changing away from 0.003. Reported small pilot estimates were below truth by -0.00041 at p=.006 and -0.00066 at p=.014, only three roots per stratum; cannot resolve bias source. Estimated-model errors improved over nominal in that small sample but were not better than true-p model consistently and did not establish a strong-static advantage. Later strong-fixed report is more directly relevant and describes adaptive-minus-pooled-static average -0.00002917 with a disclosed run deviation/reconstruction.

The burst mismatch table shows the LER-minimizing assumed p differs from true p in these finite development arrays (p_assumed .010 at true .006; .018 at true .014). This reinforces that physical parameter estimation and decoder utility are distinct objectives. It is an offline hindsight sensitivity table, not a deployable policy and not an optimality claim.

**Measured interval since checkpoint 5:** 1m09s (01:12:19–01:13:28 UTC). No tests, experiments, new shots, benchmarks, decoder inference, training, seeds, protected access, or repository changes outside the new research folder.

**Provenance limitation:** detailed Phase 2B/2C deterministic identifiability/joint-estimator packages are not present in this exact checkpoint checkout. Earlier chat summary provides qualitative context but no full report/source hash; no branch fetch or protected search was attempted. Final report must mark specific prior numerical conditioning values as unverified here unless supplied through an authorized research package.

### Checkpoint 7 — static/adaptive information parity review (2026-11-14, 01:13:28–01:18:39 UTC)

Targeted report review of `outputs/strong_fixed_baselines_v1/BASELINE_FAIRNESS_MATRIX.md` and `FINAL_RESULTS_AND_INTERPRETATION.md`. The historical comparison used identical paired final-development detector and observable arrays for nominal fixed, pooled detector-calibrated static, safety-constrained static, per-root detector-profile adaptive, and privileged true-p arms. Their *model-selection information* differed by design: the safety-static candidate used a separate labeled development selection partition and validation partition; pooled static estimated one p from aggregate final-calibration detector rows; adaptive used per-root detector-only calibration; the privileged arm received hidden generating p. Thus equal evaluation observations do not imply equal training/calibration information. Privileged results remain diagnostic only.

The 3.66M-shot historical study had separate template, selection, validation, calibration, and final-development evaluation allocations. The report confirms the pooled arm had a material implementation deviation: the original pooled-profile fit used calibration batches tagged with generating p, contrary to the frozen detector-only pooled calibration procedure. A post-run reconstruction refit on independent profile templates and pooled calibration detectors; it preserved legacy outputs and rebuilt predictions. The documented 100,000-resample condition-stratified root-cluster interval for adaptive-minus-pooled static is descriptive and conditional on selected/calibrated models and development arrays, not a confirmatory test. The reported mean effect is -0.00002917 absolute LER across nonzero conditions, well below the stated 0.0002 benchmark. These are historical report values only; no data were reanalyzed.

Monitored interval since checkpoint 6: 5m11s (01:13:28–01:18:39 UTC). Completed: information-parity and label/calibration split audit. Tests, experiments, sampling, decoder inference, benchmarks, training, seed creation, protected access, commit and push: none. Remaining: literature coverage check, reconcile novelty/readiness claims with evidence, update unresolved questions and checkpoint. No final reports before STOP.

### Checkpoint 8 — latest adjacent model-mismatch literature (2026-11-14, 01:18:39–01:19:55 UTC)

Reviewed the primary text of Hoyt et al., arXiv:2609.29018, including its model-mismatch construction, sector-risk argument and graphlike DEM moment/parity fit. Added a literature entry and narrowed the provisional novelty statement. The paper treats `W` (minimum-cost/compatibility proxy) as distinct from MWPM logical gap `Δ` and uses them for postselection. It gives a principled reason to track detector-model incompatibility, but it does not establish that incompatibility identifies the latent rate or that switching decoder graphs improves unconditional LER. Its controlled mixture uses a whole-shot latent state shared across circuit locations, distinct from Q-SHIFT's scalar burst probability applied independently at five within-shot injection boundaries and outer across-shot drift. Therefore cite it as adjacent literature and a reason for careful mismatch analysis, not as a directly comparable adaptive-decoder result.

Monitored interval since checkpoint 7: 1m16s (01:18:39–01:19:55 UTC). Completed: focused latest-literature review, relevance/limitation characterization. Tests, sampling, new detector shots, decoder inference, training, seed creation, protected access, commit/push: none. Remaining: primary literature coverage check, synthesis and update checkpoint. Final report files remain deferred until explicit STOP.


### Checkpoint 9 — telemetry-conditioned adaptation comparison (2026-11-14)

Reviewed Stein et al. arXiv:2601.16123 primary text for input signals, supervised objective, evaluation split and deployment-cost claim. It uses hardware calibration telemetry (T1/T2, readout and gate metrics), GCN-generated FiLM conditioning, and per-qubit correction targets learned during training; it evaluates IBM repetition-code data including later recalibrated/unseen chains. This is materially different from detector-only estimation and graph switching. Added this distinction to the literature record to prevent broad “adaptive decoder under drift” novelty claims from overlooking telemetry-conditioned supervised adaptation.

The results are paper-reported; no implementation or datasets were accessed, and no Q-SHIFT tests or experiments were run. Remaining: audit category coverage and claim wording in working docs, refine final directions. Final named deliverables still wait for STOP.

Monitored interval since checkpoint 8: 47 seconds (01:19:55–01:20:42 UTC). Completed source review of calibration-conditioned FiLM adaptation and added its supervision/telemetry boundary. Tests and empirical Q-SHIFT work remain none.

### Checkpoint 10 — taxonomy and feasibility-matrix coverage correction (2026-11-14, 01:20:42–01:21:21 UTC)

Updated current-status language in the working method catalog and added explicit taxonomy rows for model-compatibility/postselection and calibration-conditioned supervised decoders. Updated the preliminary feasibility matrix so calibration-telemetry FiLM remains an adjacent, supervised paradigm and model-compatibility postselection is not conflated with unconditional error reduction or causal decoder switching. This is a static documentation reconciliation only. No tests or experiment code were run.

Monitored interval since checkpoint 9: 39 seconds. Remaining: cross-check the candidate ranking/draft for stale broad novelty claims and unresolved owner decisions; continue reporting actual elapsed segments only.


Monitored interval since checkpoint 10: 1m19s (01:21:21–01:22:40 UTC). Completed: checked candidate-ranking language and verified the calibration-conditioned FiLM work's final APS publication metadata; corrected the literature status. No tests, sampling, decoder inference, training, new seed work, protected-data access, commits or pushes.

### Scorecard note and monitoring segment
Added a preliminary weighted feasibility scorecard for eight serious method families plus the required strong static baseline. Weighted totals use the user's specified dimensions/weights and are readiness assessments, not performance claims. Unknown or unmeasured Q-SHIFT utility is explicitly described in the evidence-basis notes; adaptation remains a hypothesis. This is an internal working assessment that will be reviewed before final reports.

### Checkpoint 12 — V6/V7 resource and watchdog evidence audit (2026-11-14)

Inspected the targeted V6 memory-guard report, V7 watchdog-repair report, and integrated-runner report/protocol references. Historical reports say V6 fixed a 64-bit Windows ctypes peak-working-set measurement failure and V7 added bounded Job PID-list drain/termination behavior; V7's watchdog is capped at 600s, does not impose aggregate process-tree memory cap, is unintegrated, and never authorized a benchmark. Full decoder-workload performance remains unmeasured. Historical test results remain report claims, not current-session execution. No token or protected outcome was opened.

No sampling, test execution, decoder inference, training, production seed work, protected access, or changes outside this research directory occurred. Remaining: complete owner decision inventory, audit working-doc consistency and provenance, continue coverage research. Final report remains deferred until STOP.

Monitored interval since checkpoint 11: 3m02s (01:22:40–01:25:42 UTC). The interval includes stop-signal check, scorecard preparation, and targeted V6/V7 systems report review. Tests/experiments run now: none.

### Checkpoint 13 — broadened DEM-learning and label-aware adaptation coverage (2026-11-14, 01:25:42–01:30:42 UTC)

Added primary-source records for Walsh–Hadamard/sparse DEM estimation, graph/hypergraph moment calibration, CAHR topology discovery and variance cascade, data-driven correlated mechanism augmentation, variational TN logical-risk fitting, RL-inspired decoder-prior search, local-noise adaptation sensitivity, and PriorGuard update integrity. Added source-verification statuses, owner decision list, candidate hypotheses, and additional weighted feasibility rows. The score arithmetic was checked deterministically against the declared weights; no scientific data or method outputs were computed. Fixed a score typo: syndrome-only DEM-estimation weighted readiness total is 3.85/5.

Important synthesis change: a finite-dimensional, detector-only p-burst profile is a distinct class from (a) blind topology discovery, (b) model-augmentation with new mechanisms, and (c) logical-label-supervised direct-LER optimization. The latter methods may be stronger if the information/product objective expands, but their source-level advantages cannot be assigned to the current no-logical-label controller. Literature makes the contribution case narrower; generic “syndrome-based DEM calibration” and “adaptive prior tuning” are not novel.

Monitored interval: 5m00s from checkpoint 12 (01:25:42–01:30:42 UTC). Tests, Stim sampling, detector shots, decoder inference, benchmarks, training, new seed creation, protected Stage 5 access, commits, pushes and merges: none. Remaining: verify score/source-status consistency, expand missing decoder-family coverage (soft/erasure/leakage/ensembles/sequence models) with primary sources, maintain handoff/checkpoint. Final named reports remain deferred until STOP.

### Checkpoint 14 — soft information, leakage, ensemble and RG coverage (2026-11-14, 01:30:42–01:34:15 UTC)

Added focused primary-source records on analog/soft readout decoding, leakage-aware event-triggered adaptation, harmonized ensembles, and renormalization-group decoding. Updated the source-verification ledger and method catalog with their information requirements and Q-SHIFT applicability limits. No implementation source, scorecard numeric, or scientific conclusion changed. These findings make ensembling a possible static-comparator strengthening path; soft readout and leakage require inputs/noise mechanisms absent from the present detector-only contract; RG remains a plausible family without Q-SHIFT-specific evidence.

Monitored interval since checkpoint 13: 3m33s (01:30:42–01:34:15 UTC). The saved checkpoint's `last_checkpoint_local` field had a timezone conversion error: the 01:30:42 UTC timestamp is 07:00:42 Asia/Calcutta, not 07:30:42. This is corrected in `WORK_CHECKPOINT.json`. Stop-flag check was clear. Tests, sampling, decoder inference, benchmarks, training, seeds, protected access, commits and pushes: none. Remaining: cover sequence/transformer decoder literature, audit all weighted totals and source-status wording, refresh handoff/checkpoint. Final reports remain deferred until STOP.

### Checkpoint 15 — sequence models and scorecard consistency audit (2026-11-14, 01:34:15–01:36:05 UTC)

Reviewed Nature's AlphaQubit article and arXiv:2510.22724v1 on a Mamba/state-space decoder. Recorded the supervised logical-prediction objective, soft-IQ/model/data dependencies, and distinction from detector-only drift estimation. Publisher access for the Mamba journal page redirected to a blocked authorization endpoint; its source status is explicitly limited to the arXiv record. Recalculated all 15 feasibility-score totals from the stated weights; every displayed value matched within rounding. Corrected one stale introductory line claiming scores were not assigned. Updated the architecture draft and handoff.

Monitored interval since checkpoint 14: 1m50s (01:34:15–01:36:05 UTC). No tests, sampling, decoder inference, benchmarks, training, seed work, protected access, commits or pushes. Stop flag absent at completion. Remaining: source/status/citation-chain consistency audit, owner-decision refresh, state/diff integrity audit. Final named reports still wait for explicit STOP.

### Checkpoint 16 — code-availability and provenance qualification (2026-11-14, 01:36:05–01:38:10 UTC)

Inspected the public code-link page associated with the published drifting-noise estimation paper. The repository labels itself under construction; its page shows five commits and a notebook, with no visible pinned release/license. Recorded the code and reproducibility status as unverified without running notebook code. Refreshed the evidence distinction: the peer-reviewed method/paper findings are source-supported, the linked implementation is not yet a reproducible dependency. Stop flag absent, and Git status remains limited to the untracked research directory.

Monitored interval since checkpoint 15: 2m05s. No tests, experiments, sampling, inference, training, seed work, protected access, commits or pushes. Remaining: audit remaining bibliography identifiers/status; reconcile owner questions and final research ranking; refresh provenance/hash checkpoint. Final reports remain deferred until explicit STOP.

### Checkpoint 17 — core bibliography metadata spot-check (2026-11-14, 01:38:10–01:39:05 UTC)

Reopened publisher/primary-source records to check the exact identifiers and status of the published drifting-estimation, syndrome-correlation calibration and Bayesian syndrome-inference papers. Confirmed journal volume/article identifiers, dates and DOIs against the working ledger. Confirmed the Remm paper's distance-3 scope and its multiple syndrome-element mechanisms; its leakage material remains a different physical model from Q-SHIFT's declared burst. No Q-SHIFT implementation or source results changed.

Monitored interval since checkpoint 16: 55 seconds. No tests, sampling, decoder inference, benchmarks, training, seeds, protected access, commit or push. Remaining: reconcile bibliography limitations, owner decisions and state manifests; keep final reports deferred until explicit STOP.

### Checkpoint 18 — local source identity snapshot (2026-11-14, 01:39:05–01:40:09 UTC)

Recorded SHA-256 hashes for the reviewed detector profile estimator, generic causal selector, Q-SHIFT circuit simulator, relevant configurations/manifests, and the historical Stage 4 feasibility pilot result record. These are identity hashes only; no outcomes were newly opened, generated, recalculated or evaluated. A deterministic format check confirmed the working checkpoint JSON parses and all seven hashes are 64 hexadecimal characters. This small validation was not a test suite or experiment.

Monitored interval since checkpoint 17: 1m04s. No sampling, stochastic simulation, decoder evaluation, training, seeds, protected Stage 5 access, commit or push. Stop flag state was clear before the batch; remain attentive to STOP/flag. Remaining: reconcile citation status and owner decisions; inspect final working diff and refresh checkpoint.

### Checkpoint 19 — systems-level transient risk response (2026-11-14, 01:40:09–01:41:09 UTC)

Reviewed ReloQate arXiv v2 full text for its DFR-to-LER risk mapping, time-window uncertainty, transient/slow drift models, and patch-remapping actuator. Added it as adjacent systems literature and clarified the distinction among deterioration monitoring, physical-cause estimation, decoder selection and hardware remapping. The relevance is a better framing of purpose, not direct evidence for Q-SHIFT graph switching. No code or data was run or retrieved.

Monitored interval since checkpoint 18: 1m00s. No tests, sampling, decoder inference, benchmarks, training, seeds, protected access, commit or push. Remaining: final source/status reconciliation, unresolved decisions and exact workspace audit. Final reports remain deferred until STOP.

### Checkpoint 20 — reconciled prior-art statuses and open questions (2026-11-14, 01:41:09–01:42:32 UTC)

Rewrote the drift-estimation primary-source entry to consolidate later publisher/full-text verification and remove an obsolete “equation audit pending” statement. Reconciled the early unresolved-question list with current checkout-backed answers while preserving the original questions beneath it. The status table explicitly leaves noise identifiability, exact BM/NS-4A compatibility, development-only power, and publication scope unresolved. No conclusions claim causal decoder benefit.

Monitored interval since checkpoint 19: 1m23s. Stop flag clear at the start of this batch. No tests, sampling, decoder inference, training, seeds, protected access, commit or push. Remaining: final integrity/privacy/source manifest audit, owner decisions and checkpoint refresh. Final named reports still wait for STOP.

### Checkpoint 21 — bounded integrity and credential-pattern scan (2026-11-14, 01:42:32–01:43:18 UTC)

Recomputed and matched all seven locally documented SHA-256 values; parsed the working checkpoint JSON; confirmed the working folder contains ten files, all in the designated research directory; scanned the new working notes for common GitHub/cloud-token patterns, with no matches. Git status remains detached HEAD plus only the designated untracked output folder. Stop flags are absent. The scan is a limited pattern check, not a comprehensive secret detector.

Monitored interval since checkpoint 20: 46 seconds. No tests, experiments, sampling, inference, training, seed generation, protected-data access, commits or pushes. Remaining: source-manifest finalization, owner-decision/prioritization audit, keep monitoring for STOP.

### Checkpoint 22 — bibliography and status-language reconciliation (2026-11-14, 01:43:18–01:45:22 UTC)

Updated the Remm entry to cite its verified 2026 PRResearch publication and completed selected assumption review, removing a stale “derivations pending” statement while retaining the limit that no full proof or code was replicated. Updated QAdapt's 650,332-parameter statement to attribute it to the v2 paper and marked code/weight audit as not performed. Corrected the unresolved-register status timestamp and method-catalog progress line. No scientific claims about Q-SHIFT performance changed.

Monitored interval since checkpoint 21: 2m04s. No tests, sampling, decoder inference, benchmarks, training, seeds, protected access, commit or push. Remaining: final owner-decision prioritization and workspace checkpoint/diff review; final report files still deferred until STOP.

### Checkpoint 23 — owner-decision order (2026-11-14, 01:45:22–01:46:01 UTC)

Added a prespecified decision order to the unresolved register: time axis/information access, target objective, baseline/tuning budget, noise scope/external validity, then horizon/delay/switch/resource limits. This avoids making methodological choices before the estimand is selected. No analysis or methods were authorized by this documentation update.

Monitored interval since checkpoint 22: 39 seconds. No tests, sampling, decoder inference, training, seeds, protected access, commits or pushes. Stop flag status not rechecked within this short edit; check before the next batch. Final deliverables remain deferred pending STOP.

### Checkpoint 24 — separate risk monitoring from causal adaptation (2026-11-14, 01:46:01–01:46:54 UTC)

Added a falsifiable hypothesis that a coarse detector-fire/residual alarm could serve as a conservative fail-safe fallback signal without identifying a physical cause or proving that graph switching helps. This is motivated by the systems-level DFR-to-risk and remapping literature but is not established for Q-SHIFT. Stop flags were checked and absent. No experiments/tests or outcomes were generated or opened.

Monitored interval since checkpoint 23: 53 seconds. No sampling, decoder inference, training, seeds, protected access, commit or push. Remaining: final scope/audit and preserve working checkpoint; report set stays deferred until STOP.

### Checkpoint 25 — NVIDIA syndrome-to-weight learning and predecoder (2026-11-14, 01:46:54–01:51:19 UTC)

Reviewed the full arXiv:2604.12841v1 methods for its supervised 3D CNN predecoder and distinct CNN/MLP noise learner, including 25-parameter output, 18 edge/43 hyperedge formulas, two-round bulk syndrome input, inference aggregation, model assumptions and reported training scales. Inspected official NVIDIA Ising-Decoding README, config, inference requirements and Apache-2.0 license at snapshot `12bbeb13c5cfc1a064171ac91b07aea61f2eaae8`; obtained the full `main` SHA through read-only `git ls-remote`. Recorded model-checkpoint access/license separation and did not clone, install, download, train or benchmark.

Research implication: this is essential adjacent prior art that narrows generic “detector-only decoder weight estimation” novelty. It is not a direct Q-SHIFT baseline: it assumes a standard rotated surface-code 25-parameter model, uses a large training/data/GPU budget, and is not a causal burst-probability switcher. Added a non-scored row and falsifiable future-comparison hypothesis.

Monitored interval since checkpoint 24: 4m25s. Stop flag was checked and absent before the batch. No tests, Q-SHIFT experiments, Stim sampling, detector shots, decoder inference, training, seed work or protected access occurred. No commits/pushes. Remaining: final source/status/privacy review, keep final reports deferred until STOP.

### Checkpoint 26 — source-cited batch-estimator characterization and handoff reconciliation (2026-11-14, 01:51:19–01:54:45 UTC)

Reopened the cited NVIDIA/Chamberland paper at arXiv v1 and checked §V.1 and Table 12. Tightened the literature statement: it consumes two consecutive bulk rounds but aggregates logits over `N_test >> 1` syndrome pairs; its recipe is 250 parameter vectors × 4,096 shots (1,024,000 samples/epoch), distances 21/31, 32 GPUs across 8 nodes, ~1.26M parameters. This supports classifying it as batch-statistics noise estimation, not demonstrated per-round causal detection. Added the direct citation and source audit note. Reconciled the opening status in CODEX_HANDOFF.md with checkpoint 25, preserving later continuation history.

Monitored interval since checkpoint 25: 3m26s. Stop flag absent at the beginning and end of the batch. No tests, sampling, decoder inference, benchmarks, training, seed work, protected access, commit or push. Remaining: continue final source/status/privacy review; final report deliverables stay deferred until explicit STOP.

### Checkpoint 27 — update open decision register for supervised detector-only prior art (2026-11-14, 01:54:45–01:56:08 UTC)

Updated the working unresolved-status table through checkpoint 26 and recorded Chamberland et al. alongside the syndrome-driven adaptation/calibration literature. Clarified a methodological distinction: a learned syndrome-to-noise/weight estimator can be detector-only at deployment yet still rely on extensive supervised simulator/parameter training. Added an owner decision to declare offline training information and budget separately from deployment information, logical-label access and telemetry.

Monitored interval since checkpoint 26: 1m23s. Stop flag checked and absent. No tests, sampling, decoder inference, benchmarks, training, seed work, protected access, commit or push. Remaining: final scoped source/status/privacy review; final reports remain deferred until STOP.

### Checkpoint 28 — final-scope identity and integrity recheck (2026-11-14, 01:56:08–01:57:46 UTC)

Reconciled `WORK_CHECKPOINT.json`'s sequence number with the research log (the file still said 25 after checkpoints 26–27); it now identifies checkpoint 28. Revalidated all seven local SHA-256 source/config/result entries against files, parsed checkpoint JSON, confirmed exactly ten working files in the designated output folder and no other changed paths in the detached worktree, and ran a limited common credential-format scan with no matches. Both stop-flag locations checked were absent. This is not a comprehensive secret scanner and no protected file contents were searched.

Monitored interval since checkpoint 27: 1m38s. No tests, experiments, sampling, inference, training, seed generation, protected access, commits or pushes. Remaining: keep final deliverables deferred until explicit STOP; continue only useful bounded citation/source review.

### Checkpoint 29 — refine drift-estimator applicability to the actual burst mechanism (2026-11-14, 01:57:46–01:59:13 UTC)

Reopened the peer-reviewed PRX Quantum drift-estimation article and targeted the existing Q-SHIFT circuit-builder source. Corrected an overly broad incompatibility statement: the injected two-qubit X burst is Bernoulli and independent across five round boundaries, so a route through graph-event moment inversion may exist if each event maps to a distinct graphlike edge and nuisance mechanisms meet the assumptions. Kept applicability unresolved because gate Pauli alternatives, approximate disjoint-error DEM conversion, overlapping baseline contributions and nuisance separation need an algebraic mapping. No decoder/sampling activity.

Monitored interval since checkpoint 28: 1m27s. No tests, sampling, inference, benchmarks, training, seeds or protected access. Stop flags remain absent; no commits or pushes. Remaining: continue source/citation audit only; final reports deferred until STOP.

### Checkpoint 30 — add effective-edge identifiability boundary (2026-11-14, 01:59:13–02:00:26 UTC)

Added a conditional deterministic identity for independent Bernoulli events sharing the same detector support: their observed parity rate is `p_eff = (1 - product_k(1 - 2 p_k))/2`. This clarifies that syndrome moments may identify an effective edge rate without uniquely identifying its physical contributors. Explicitly limited the identity to independent events; mutually exclusive channel alternatives and whole-circuit/approximate-DEM validity remain unproven. Added this as a falsifiable boundary in the candidate-hypothesis notes. Stop flags checked absent; worktree remains detached at the pinned commit with only the research folder untracked.

Monitored interval since checkpoint 29: 1m13s. No tests, experiments, Stim sampling, decoder inference, training, seeds, protected access, commits or pushes. Remaining: final reports still await STOP; continue only bounded useful review.

### Checkpoint 31 — add prior-art history-scale evidence with transfer limits (2026-11-14, 02:00:26–02:02:06 UTC)

Reviewed the published drift-estimation paper's reported 50,000-cycle simulation and approximately 2,000-cycle estimation windows (the paper notes its time index may also represent shots). Added this as a reported example-specific data/history scale, explicitly not as a Q-SHIFT window recommendation: Q-SHIFT records five-round detector vectors per independent shot and its covariance/finite-history estimator accuracy has not been measured. No sample or simulation generated.

Monitored interval since checkpoint 30: 1m40s. No tests, sampling, inference, training, seeds or protected access. No commits or pushes; stop flags remain absent. Final reports remain deferred until explicit STOP.

### Checkpoint 32 — reconcile burst/event terminology across working drafts (2026-11-14, 02:02:06–02:04:23 UTC)

Corrected draft language that conflated the full circuit's categorical gate-noise alternatives with the injected burst. The Q-SHIFT X8/X10 event is a Bernoulli `CORRELATED_ERROR` placed independently at five round boundaries; the baseline includes categorical channels. The drift-estimation paper is now described as potentially relevant through graph moments, but only after exact/DEM support mapping and nuisance separation. The model remains unresolved; no scientific outcome claim changed.

Monitored interval since checkpoint 31: 2m17s. Stop flag absent. No tests, sampling, decoder inference, training, seed work, protected access, commits or pushes. Final named deliverables remain deferred until STOP.

### Checkpoint 33 — deterministic approximate-DEM support collision audit (2026-11-14, 02:04:23–02:08:10 UTC)

Created and ran `deterministic_dem_support_audit.py` on the pinned circuit-builder source using Stim 1.16.0. This performs circuit construction and approximate DEM conversion only; it does not call a sampler or decoder. At the documented d=3/five-round balanced configuration with gate/meas p=0.003 and burst p=0.01, the baseline DEM has 586 mechanisms and the burst-inclusive DEM 591 (40 detectors, one observable each). Each burst support `(D8,D10)`, `(D16,D18)`, `(D24,D26)`, `(D32,D34)`, `(D36,D38)` has no exact-support baseline mechanism and one burst-inclusive mechanism at p=0.01. This reduces one DEM-level aliasing concern, but does not prove exact circuit-level identifiability or finite-history performance. Recorded source SHA-256 in SOURCE_VERIFICATION.md.

Monitored interval since checkpoint 32: 3m47s. No sampling, detector shots, decoder predictions, logical outcomes, training, seeds, protected access, commit or push. Stop flag absent. Remaining: final reports deferred until STOP; continue with bounded source audit.

### Checkpoint 34 — deterministic DEM-level feature means and local parameter sensitivity (2026-11-14, 02:08:10–02:14:40 UTC)

Added and ran `dem_feature_expectations.py`, which computes the source-defined 45 detector/pair-cofire means exactly under each approximate DEM's independent-error-instruction representation at burst knots 0.002, 0.010 and 0.018. A separate direct 2-/4-state XOR convolution agreed with the parity-characteristic formulas within `7.15e-16`. At p_burst=0.010 and p_meas=0.003, the raw unstandardized local Jacobian has rank 2, singular values 13.47154 and 3.27925, condition ratio 4.10812 and column cosine 0.44104. Finite-difference step changes down to 1e-5 caused maximum derivative changes ≤1e-11 for burst and ≤8.3e-7 for measurement. These indicate one-point local mean identifiability under the approximate DEM only; no global, finite-sample, exact-circuit or decoder-performance claim follows. The result JSON and source hashes are saved.

Monitored interval since checkpoint 33: 6m30s. No sampling, detector shots, logical labels/outcomes, decoder predictions, training, seed work or protected access. No commits or pushes. Final reports still await STOP.

### Checkpoint 35 — fail-fast reproducibility checks for deterministic analyses (2026-11-14, 02:14:40–02:17:05 UTC)

Strengthened both saved deterministic analysis scripts with fail-fast checks for the five expected DEM supports, mechanism totals, 45-feature vector shape/range, and agreement of parity formulas with direct XOR recursion within 1e-12. Re-ran both scripts: all structural checks passed, direct-convolution discrepancy remained `7.15e-16`, and sensitivity values remained unchanged. Updated source hashes. These are deterministic model-construction/calculation checks, not stochastic tests or decoder evaluations.

Monitored interval since checkpoint 34: 2m25s. Stop flag absent; worktree remains pinned with only the research output directory untracked. No sampling, decoder predictions, training, seeds, protected access, commit or push.

### Checkpoint 36 — single-shot feature covariance and oracle weighting sensitivity (2026-11-14, 02:17:05–02:20:06 UTC)

Extended the approximate-DEM calculation to the exact single-shot covariance of all 45 features using deterministic 2-/4-detector XOR-state recursion. The matrix is symmetric/positive definite at `(p_burst,p_meas)=(0.010,0.003)`, with eigenvalue range `0.0029250–0.0782344` and condition `26.7467`; binary variance identities are checked. Under an ideal iid-shot regular moment-estimator calculation with the true covariance known, oracle full-covariance GMM yields SD per sqrt(N) `(0.04708,0.01528)`, versus diagonal-variance weighting `(0.05085,0.01662)`—about 7.42%/8.05% lower SD. This is not finite-sample accuracy and does not show covariance estimation/regularization is worthwhile. Source/results hashes updated.

Monitored interval since checkpoint 35: 3m01s. No sampling, decoder inference, logical outcomes, training, seeds or protected access. No commits or pushes. Stop flag absent; final deliverables remain deferred until STOP.

### Checkpoint 37 — update QAdapt to its latest v2 evidence (2026-11-14, 02:20:06–02:22:59 UTC)

Checked the arXiv version history and v2 full text for QAdapt; v2 was revised on 10 Nov 2026, with a revised title and expanded metrics. Updated the literature and feasibility entries to distinguish its supervised correction-target neural predecoder plus residual PyMatching from the proposed known-mechanism detector-only graph switch. Recorded paired d=9 results, frozen transfer results, and the limitation that each configuration has one realized training seed (shot intervals are conditional on trained weights). No code, weights or outcomes were accessed or run. Stop flag absent.

Monitored interval since checkpoint 36: 2m53s. No sampling, decoder inference, training, seed work, protected access, commits or pushes. Final reports remain deferred until STOP.

### Checkpoint 38 — revalidate DGR sample-demand and feedback assumptions (2026-11-14, 02:22:59–02:24:43 UTC)

Reopened DGR arXiv v3 full text at its cited method/evaluation sections. Confirmed that its alignment estimator uses frequencies of prior MWPM-selected edges and is explicitly bounded by the current decoder's matching accuracy; the paper gives one example with mean-squared error convergence near 10^6 trials at p=0.001, d=5. Correlation tracking also uses matching-edge co-occurrences and approximates pairwise correlations. This supports its classification as a feedback-based adaptive baseline with potentially large history requirements, not a direct physical burst-parameter estimator. No code was run; no outcomes generated.

Monitored interval since checkpoint 37: 1m44s. Stop flag absent. No sampling, inference, training, seeds, protected access, commits or pushes. Final deliverables remain deferred until STOP.

## Checkpoint 39 — scoped integrity and privacy review (2026-11-14 07:58:19 +05:30)

Revalidated the two deterministic source hashes and the DEM result JSON hash against the source ledger; JSON parses with 45 feature entries and a 45×45 covariance matrix. A scoped pattern scan found the local absolute worktree path in the handoff and initial log; replaced both with a neutral worktree description. The bounded scan found no credential-token or private-key patterns. No scientific inputs/results changed. The task remains in progress; final reports are still deferred until explicit STOP. No sampling, detector shots, decoder evaluation, training, protected Stage 5 access, seed work, commit or push.


## Checkpoint 40 — deterministic parameter-grid identifiability screen (2026-11-14 08:02:27 +05:30)

Built an 81-point burst/measurement approximate-DEM population grid and seven local finite-difference Jacobian probes. All probes had rank 2; raw condition ratios 4.053–4.165 and nominal-variance standardized ratios 3.196–3.286. No exact grid collision appeared, but nearest adjacent population profiles were close (standardized RMS distance 0.006091). Reran the analysis and obtained byte-identical JSON. This is not an exact-circuit or finite-history result and does not establish global injectivity. Source/result hashes are in SOURCE_VERIFICATION.md. No sampling, decoder evaluation, training, protected Stage 5 access, or seed work occurred.


## Checkpoint 41 — exact DEM conversion boundary (2026-11-14 08:03:14 +05:30)

Deterministically attempted nonapproximated, undecomposed Stim DEM conversion on the existing baseline and burst circuits. Both were rejected at PAULI_CHANNEL_2 unless approximate_disjoint_errors is enabled. This confirms that prior population calculations are exact only for the converted approximate DEM; an explicit categorical expectation derivation is still outstanding. No sampling, decoding, or logical outcomes.



## Checkpoint 42 — exact categorical circuit feature map (2026-11-14 08:17:49 India Standard Time)

Added deterministic single-fault support propagation through the existing Clifford circuit and exact categorical expectation algebra for all 45 detector-only features. At nominal conditions 214 noise sites / 1,974 alternatives were mapped; parity identities agreed with direct XOR recursion to 3.84e-15. On an 81-point burst/measurement grid, independent recursion agreed within 6.53e-15, all seven Jacobian probes were rank 2, no grid collision appeared, and the approximate DEM mean discrepancy peaked at 3.30e-5. Initial character code failed because it omitted even-parity nonidentity alternatives; that failure was caught before saving a result and corrected. No stochastic sampling, detector shots, decoding, logical outcomes, training, or protected access.


## Checkpoint 43 — fault-map support guard and reproduction (2026-11-14 08:20:34 India Standard Time)

The exact fault mapper now asserts the five circuit-level burst supports equal the five declared detector-pair coordinates. Re-ran the 81-point exact-vs-approximate comparison with that guard and direct-XOR validation active; numerical profiles and JSON hash remained identical. No stochastic calls or decoder outputs.


## Checkpoint 44 — gate-noise nuisance direction (2026-11-14 08:22:17 India Standard Time)

A deterministic three-parameter local Jacobian for exact categorical-circuit means has rank 3 with variance-standardized condition ratio 10.439. Gate and measurement directions have cosine 0.825; 82.6% of gate derivative norm lies in the burst/measurement span. Approximate-DEM result is similar. This flags scalar gate-rate misspecification as a plausible confound, but does not quantify sampled estimator bias or gate-channel composition drift. No sampling or decoder calls.


## Checkpoint 45 — individual feature nuisance sensitivity (2026-11-14 08:23:24 India Standard Time)

Added reproducible rankings of exact-circuit feature-mean derivatives for burst, measurement and scalar gate p. Burst signal is concentrated on D8/D16/D24/D32/D36 and the five selected pair features; measurement signal is strongest on D37/D38/D39/D36; gate-p derivatives are largest on a different set of bulk detectors. This indicates distinguishable coordinate information while the aggregate gate/measurement derivative directions remain correlated. Derivatives are local per-unit-p changes, not accuracy claims.


## Checkpoint 46 — population burst-only mismatch screen (2026-11-14 08:26:15 India Standard Time)

A source-shaped one-parameter population-profile analogue used exact categorical means, the three existing burst knots, linear interpolation and 1,601-point selection grid. With true measurement p at exploratory 0.001/0.005 while templates fix it at .003, burst estimates shifted about −.0019/+ .0019; nominal measurement p recovered the tested burst points. The exact circuit and approximate DEM results nearly coincide. This is not the sampled estimator and uses exact nominal standard-deviation weights, not calibration-fitted scales. Initial helper-unpacking error was corrected before success; final result repeated byte-identically.


## Checkpoint 47 — nuisance-adjusted asymptotic moment precision (2026-11-14 08:27:35 India Standard Time)

Analytical iid-shot sandwich/GMM covariance using exact known single-shot covariance shows that adding scalar gate p as an estimated nuisance increases the measurement SD coefficient per sqrt(N) by about 47% under diagonal standardized fitting (0.01662 to 0.02444); burst coefficient is nearly unchanged (~0.0509). Full covariance weighting yields a similar relative change. This is asymptotic and oracle-weighted, not a finite-history result.


## Checkpoint 48 — exact payload rerun (2026-11-14 08:29:07 India Standard Time)

Reran the deterministic nominal exact-circuit analysis. Canonical hash over exact means, independent XOR means, approximate-DEM means and fault-map metadata was unchanged; direct-XOR discrepancy remained 3.844e-15. Full JSON includes wall-time metadata and can have a different full-file SHA across executions.


## Checkpoint 49 — exact covariance identities (2026-11-14 08:30:49 India Standard Time)

The 45-feature exact-circuit covariance now validates symmetry (error 0), binary-feature variance identities (max error 6.939e-18), and positive definiteness (eigenvalues [0.0029276503017423, 0.07829724614538348]). The full grid reran with these guards active.


## Checkpoint 50 — scalar gate-rate population mismatch (2026-11-14 08:33:31 India Standard Time)

Extended the idealized burst-only profile screen with true gate p 0.002/0.003/0.004 while templates remain fixed at .003. The ±.001 gate mismatch shifts fitted burst p about −.0020 to +.0023 and leaves residual MSE about .00135–.00141. Exact circuit and approximate DEM maps agree closely. This is a model sensitivity, not a sampled estimator/decoder result.


## Checkpoint 51 — residual-guard hypothesis refinement (2026-11-14 08:34:16 India Standard Time)

Added a falsifiable hypothesis that a detector-only adequacy residual may support fallback under nuisance mismatch but cannot identify the cause. The ±.001 p deviations and roughly .002 burst-fit bias remain exploratory population-model evidence only; false-alarm calibration and decoder-risk utility are unresolved.


## Checkpoint 51 — method-priority reconciliation (2026-11-14 08:34:41 India Standard Time)

Updated the feasibility ranking after exact categorical feature and mismatch calculations: the structural mean-feature screen is materially advanced, while guard calibration, finite-history performance, off-grid uniqueness and any decoder-risk benefit remain open. The next deterministic priority is model-family residual/fallback behavior, not more decoder complexity.


## Checkpoint 52 — privacy and cache cleanup (2026-11-14 08:36:42 India Standard Time)

Sanitized the structured checkpoint's absolute worktree field and removed six generated bytecode caches containing local paths. A recursive byte scan found no local absolute checkout or attachment paths among the 23 research output files. Source and result files were preserved.


## Time-tracking note — checkpoint 52

This resumed work segment began at 2026-11-14 07:56:56 +05:30 (02:26:56 UTC) and reached the checkpoint at 08:36:42 +05:30 (03:06:42 UTC), a wall-clock elapsed 00:39:46. A monotonic start value and the original mission start timestamp are not available in the saved checkpoint, so total mission duration cannot be reported reliably. The privacy-review phase ran 08:34:55–08:36:42 (+05:30), 00:01:47 wall time. Tool calls used bounded waits and resumable sessions; no waiting was added to consume a time budget.


## Checkpoint 53 — package integrity review (2026-11-14 08:38:28 India Standard Time)

All 23 JSON and research files parse/read successfully. No absolute local paths, credentials, private-key patterns, or bytecode caches remain. A generic email regex produced two false positives on NumPy matrix-multiplication `@` operators in the nuisance script; manual inspection confirmed no email address. Pinned HEAD remains `f7f0fc167960e9499e40785a9b2262295bfecabc`; only the intended output directory is untracked; no stop flag is present.


## Checkpoint 54 — handoff and unresolved-question reconciliation (2026-11-14 08:39:15 India Standard Time)

Updated the continuation handoff to checkpoint 53 and clarified remaining gaps: off-grid/global uniqueness, gate-channel composition mismatch, finite-history guard behavior, and causal decoder utility. The unresolved-question summary now includes the scalar gate-mismatch population bias.


## Checkpoint 55 — mismatch result repeatability (2026-11-14 08:40:18 India Standard Time)

Reran the expanded 30-row measurement/gate population mismatch analysis; the JSON hash was byte-identical and the output remained nominal bias 0, measurement bias max 0.00197, gate bias max 0.00228. Bytecode creation was disabled.


## Checkpoint 56 — mismatch summary-filter correction (2026-11-14 08:40:47 India Standard Time)

Preserved an analysis bookkeeping error: when the gate-mismatch arm was first added, the reported “nominal max bias” filtered only on measurement p and accidentally included the gate-mismatch rows, yielding 0.00228. Corrected the condition to require both measurement p=.003 and gate p=.003, and split measurement-mismatch vs gate-mismatch summaries. Correct values are nominal 0, measurement max 0.00197, gate max 0.00228. The saved JSON was regenerated and independently rerun byte-identically; no scientific inputs changed.


## Checkpoint 57 — exact single-fault support uniqueness (2026-11-14 08:42:03 India Standard Time)

A deterministic audit compared all 1,974 nonzero categorical alternatives with the five injected burst signatures. Each burst support occurs once from its own E event; no baseline gate/readout single-fault alternative has any of those exact supports. Multi-fault aliases and global statistical identifiability remain open. Bytecode generation was disabled.


## Time-tracking update — checkpoint 57 (2026-11-14 08:42:25 India Standard Time)

Resumed segment wall-clock elapsed is 00:45:07 from 07:56:56 to 08:42:03 +05:30. The exact support-audit phase ran 08:40:47–08:42:03 +05:30 (00:01:16). Monotonic elapsed remains unavailable; mission-wide initial start remains unknown.


## Checkpoint 58 — static package parse validation (2026-11-14 08:42:57 India Standard Time)

AST-parsed all eight Python source files and parsed all eight JSON files successfully with Python bytecode generation disabled. This is syntax/serialization validation, not a stochastic or decoder test. Worktree remains pinned and only the designated output directory is untracked.


## Checkpoint 59 — continuation state consolidation (2026-11-14 08:44:45 India Standard Time)

Consolidated checkpoints 39–58 into the structured completion list and next-priority register. The worktree remains detached at the pinned review commit with only the intended output directory untracked. Final reports remain deferred until STOP/flag. Static validation phase ran 08:42:57–08:44:33 (+05:30), 00:01:36 wall time.


## Checkpoint 60 — population mismatch weighting sensitivity (2026-11-14 08:46:54 India Standard Time)

Extended the 90-row exact/DEM population fit to exact nominal SD, equal-weight pooled template SD, and unit weights. Nominal and pooled weights yielded identical max measurement/gate burst biases (0.00197/0.00228); unit weighting increased them to 0.00326/0.00402. Repeated result hash matched. Historical estimator fitted scales are unavailable, so this remains a sensitivity analysis.


## Time-tracking update — checkpoint 60 (2026-11-14 08:47:05 India Standard Time)

Resumed segment elapsed 00:49:58 (07:56:56–08:46:54 +05:30). The weighting-sensitivity phase ran 08:44:45–08:46:54, 00:02:09 wall time. Mission-wide initial start and monotonic elapsed remain unknown.


## Checkpoint 61 — bias-ratio inactive-parameter finding (2026-11-14 08:50:37 India Standard Time)

The exact source shows `bias_ratio` is ignored by the balanced regime; it only reweights X or Z in the corresponding biased regimes. Thus the local four-parameter map has an inactive bias-ratio column and rank 3. The first run emitted NaN/Infinity from dividing by a zero derivative norm; its nonstandard JSON is retained with a FAILED label, while corrected strict JSON stores null for undefined values. No change to biased regime was made.


## Checkpoint 62 — nuisance audit time tracking (2026-11-14 08:50:52 India Standard Time)

Resumed segment wall elapsed 00:53:41 from 07:56:56 to 08:50:37 +05:30. Bias-ratio source audit and correction ran 08:47:05–08:50:37 (00:03:32). Mission-wide start and monotonic elapsed remain unknown.


## Checkpoint 63 — strict output audit after nuisance update (2026-11-14 08:51:45 India Standard Time)

Nine Python sources AST-parse and nine JSON outputs parse. Recursive byte scan of 28 files found no machine paths, credentials/private keys, or bytecode. Two email-regex matches were reviewed and are false positives on NumPy matrix-multiplication `@` operators. Pinned HEAD unchanged; only research output untracked; no stop flag.
### Checkpoint 64 — calibration scale weighting clarification (2026-11-14)

Inspected only the exact calibration construction and config excerpts in the Stage 4 runner: three estimator knots, two batches per knot, each generated with 2,000 detector rows. `DetectorProfileEstimator.fit` concatenates all feature rows and uses population variance (`np.var`, default `ddof=0`) across them. Therefore the equal-knot mixture SD in the deterministic burst-only mismatch audit has the same population-limit weighting as the source estimator. It still differs from the finite-sample scale vector estimated from the actual calibration batches. No historical scale result vectors, raw samples, evaluation outcomes, or protected material were opened. Updated the audit description, architecture note, and source verification note. Re-ran the deterministic 90-row population calculation; the numerical summaries are unchanged: measurement mismatch maximum absolute burst bias 0.00197 and scalar gate mismatch maximum 0.00228 under both nominal marginal SD and source-weight-aligned population pooled SD; unweighted sensitivity maxima remain 0.00326 and 0.00402. No sampling, decoder inference, or outcome scoring occurred.

### Checkpoint 65 — correlated-readout identifiability boundary (2026-11-14)

Added `CORRELATED_READOUT_IDENTIFIABILITY_NOTE.md` with an exact detector-observation algebra argument: an independent nuisance event with the same detector mask as a burst is observationally aliased for detector-only data, with net parity probability `q = p_b + p_r - 2 p_b p_r`. This is explicitly a hypothetical observation-space stress, not a claim that the current circuit implements correlated readout. The pinned circuit model remains unchanged. This establishes why a pair-cofire residual is evidence of joint detector activity, not proof of physical burst cause; decoder correlation settings cannot resolve that inference limit. No sampling, Stim circuit changes, decoder calls, or protected-data access.

### Checkpoint 67 — adaptive decoding prior-art citation chain (2026-11-14)

Rechecked the publisher record and public manuscript for Bhardwaj et al., “Adaptive Estimation of Drifting Noise in Quantum Error Correction,” *PRX Quantum* 7, 033024 (2026), DOI 10.1103/z1hc-nqw5. Publisher states syndrome-only sliding-window estimation, analytical window/filter behavior, overlapping windows for single-pass multi-frequency drift, and simulated improvements against static noise models; its linked implementation is still under construction/unpinned/unlicensed in the inspected public state. Also reviewed Toshio et al., “Decoder Switching: Breaking the Speed-Accuracy Tradeoff in Real-Time Quantum Error Correction,” arXiv:2510.25222 (2025/2026 manuscript): soft-output weak/strong switching is an established adjacent idea, with thresholds selected from reliability-conditioned logical-error behavior; it is not physical-noise cause estimation. This narrows novelty claims: generic switching or generic syndrome-only drift estimation is not novel; a Q-SHIFT contribution would need a clearly distinct identifiable mechanism and fair equal-information baselines. Updated the literature database only. No tests, sampling, training, decoder evaluation, or protected data access. `RESEARCH_STOP.flag` absent at this checkpoint.

### Checkpoint 70 — published edge-moment inversion mapped to Q-SHIFT (2026-11-14)

Applied Bhardwaj et al.'s published independent-edge covariance inversion to the five detector pairs associated with the five Bernoulli X8/X10 burst sites. Across the exact 9×9 burst/measurement population grid, all 405 pair estimates were in domain and recovered the common true model p with mean absolute error `4.18e-17` and max `1.65e-16`. The approximate-DEM version likewise had maximum error `3.47e-16` (reported separately). An additional 45 exact-circuit profiles over gate p `.002,.003,.004` and burst p `.002,.010,.018` at measurement p `.003` had max error `5.38e-17`. Underlying moment means passed independent direct XOR parity validation with max discrepancy `6.53e-15`. The code and result are `published_edge_moment_inversion_audit.py` and `PUBLISHED_EDGE_MOMENT_INVERSION_AUDIT.json`; source/result SHA-256 values are in `SOURCE_VERIFICATION.md`. This is a deterministic population identity, not evidence on finite-history bias/variance, change alarms, latency, or decoder performance. It strengthens the priority of comparing a simple published edge-moment estimate against the existing 45-feature profile in any separately authorized development feasibility work. No Stim sampling, decoder calls, training, protected data, or outcomes.

### Checkpoint 71 — edge-estimator asymptotic sensitivity (2026-11-14)

Computed an iid, first-order delta-method variance for the five published pair-edge estimates using exact categorical-circuit feature covariance at nominal `(p_b=.010,p_m=.003,p_g=.003)`. Analytic gradient central-difference discrepancy was `3.04e-10`. The equal mean of five edges has asymptotic SD coefficient `0.04714435/sqrt(N)`; the separate existing joint 45-feature profile's burst coordinate is `0.05085282/sqrt(N)`. This is only a model-conditional asymptotic comparison with true covariance known; the methods estimate different parameter sets, and finite-history bias, interval coverage, overlapping-window effects, drift delay and alarm behavior remain unknown. Updated method catalog, scored readiness matrix and architecture draft; the matrix assigns 4.10/5 readiness with validation and reproducibility explicitly low, not as a performance forecast. No samples/shots, decoder outputs, training or protected data.

### Checkpoint 73 — edge-estimator low-rate sensitivity (2026-11-14)

Extended the exact-covariance iid delta-method calculation over `(p_b=.002,.010,.018) × (p_m=.001,.003,.005)` while holding the declared balanced gate model fixed. At p_b=.002 and p_m=.003, the equal-five-edge mean has asymptotic SD coefficient `.02370/sqrt(N)`; its normal-scale separation from zero reaches three standard errors at about 1,264 independent shots. This is a rough asymptotic scale check only—not formal power, finite-N coverage, a practical window choice, or change-detection delay. The coefficient rises to `.04714/sqrt(N)` at p_b=.010 and `.06210/sqrt(N)` at p_b=.018. No simulated histories were generated. Updated source hashes and explanatory limits.

### Checkpoint 74 — edge inversion boundary behavior (2026-11-14)

Derived the analytic Hessian of the published edge-moment inversion and validated it against finite differences (max gradient discrepancy `3.04e-10`; Hessian discrepancy `2.40e-10`). Using exact categorical single-shot covariance and an iid second-order delta method, at low `p_b=.002,p_m=.003`, the equal-five-edge estimate has SD coefficient `.02370/sqrt(N)` and second-order raw bias coefficient `-0.001877/N`. An unbounded-normal approximation yields a negative raw estimate probability of 11.6% for 200 shots and 0.38% for 1,000; if clamped at zero, approximate added bias is `9.53e-5` at N=200. These are asymptotic illustrations, not exact finite-sample probabilities or coverage, but they make future boundary handling/minimum history decisions material. Added this as an unresolved owner choice. No histories or samples generated.

### Checkpoint 75 — edge-moment gate-composition robustness (2026-11-14)

Extended the deterministic published-edge inversion audit to two existing alternative gate-noise compositions in `noise_model.py`: `x_biased` and `z_biased` at bias ratio 10, with burst p `.002,.010,.018`, fixed measurement p `.003`, and gate p `.003`. All 30 edge estimates recover p with max error `1.284e-16`; exact categorical means for those profiles also match direct XOR recursion to `4.462e-15`. This is explicitly an alternative-model sensitivity, not a silent change to the balanced primary circuit. The result strengthens exact-model structural attribution against those independent Pauli composition changes, while the matched-detector-mask nuisance alias still limits general physical cause claims. Updated the literature and architecture notes/source hashes. No sampling or decoder evaluation.

### Checkpoint 77 — structural reason for edge-moment recovery (2026-11-14)

Added a complete exact single-fault support audit for the balanced Q-SHIFT circuit. Across 1,974 mapped nonzero categorical alternatives, none outside the five declared burst events toggles both detectors in any target pair. Also, no nonburst physical channel site has distinct mutually exclusive alternatives that can separately toggle both detectors of a target pair (site-group co-occurrence count zero for all five). Under independent physical sites, this means only the burst event contributes shared parity to each pair covariance; independent one-side faults cancel in the covariance inversion. This explains the floating-point recovery across the deterministic parameter/gate grids. It remains a conclusion conditional on the declared circuit and no external correlated readout; the matched-mask alias remains. Script/result: `burst_pair_joint_support_audit.py`, `BURST_PAIR_JOINT_SUPPORT_AUDIT.json`; source hashes recorded. No stochastic samples, decoder calls, or outcomes.

### Checkpoint 79 — shot-window mixture and time-axis transfer (2026-11-14)

Reviewed Bhardwaj et al.'s primary-source sliding-window derivation. Their index is syndrome-extraction cycle in an ongoing memory; Q-SHIFT's present detector stream is independently reset five-round shots, with burst rate constant within each shot and drift modeled between shots. Added `DRIFT_WINDOW_TIME_AXIS_AUDIT.md` and a deterministic exact-categorical population mixture calculation. Across 15 mixtures of two burst-rate regimes (`.002/.018`, `.002/.010`, `.010/.018`) and five old-regime fractions, pooled 45-feature means followed by the five pair-edge inversions recovered the arithmetic window-mean rate: 75/75 estimates, maximum bias `6.94e-17`, maximum edge spread `5.55e-17`. This supports a trailing-window mean-rate interpretation only under the fixed background and shotwise drift assumptions. The empirical relative-window difference across `W` and `W+1` nested shot windows reduces to the newest single-shot vector, so practical finite-history utility is unsupported. Script/result: `shot_window_mixture_audit.py`, `SHOT_WINDOW_MIXTURE_AUDIT.json`. No sampling or logical/decoder evaluation.

### Checkpoint 80 — heterogeneous-window asymptotic covariance (2026-11-14)

Propagated exact single-shot categorical feature covariance through the pooled edge estimator for independent shots with fixed low/high-rate fractions. Under `.002/.018` burst regimes, 25%, 50%, and 75% low-rate mixtures have conditional delta-method SD coefficients `.0550777`, `.0470111`, and `.0372302` over `sqrt(W)`. Stationary models at the same mean rates have `.0551630`, `.0471444`, and `.0373563`; pooled and stationary feature means differ by at most `8.33e-17`. These close asymptotic scales do not imply finite-window accuracy, probability-domain validity, confidence coverage, or useful adaptation. Source/result: `shot_window_delta_method.py`, `SHOT_WINDOW_DELTA_METHOD.json`. No sampling was performed.

### Checkpoint 81 — exact one-edge finite-count distribution (2026-11-14)

Exhaustively summed, without random draws, the four-cell multinomial distribution for the exact categorical `(D8,D10)` pair at burst p `.002/.010/.018` and windows 25/50/100/200. Independent arithmetic checks confirm unit probability mass, correct sample marginal expectations (maximum error `4.0e-15`), and the binomial zero-cofire identity. At W=200 the raw moment inverse is negative with probability `.5898/.1281/.02749`; corresponding no-cofire probabilities are `.6069/.1316/.02821`. Invalid-real-domain mass is negligible in this finite grid, but negative physically inadmissible estimates are common for sparse burst events. This is only one pair, so it does not quantify the joint five-edge average. It shows that asymptotic normal approximations are not dependable for the single-edge low-count regime, and finite-history boundary handling needs explicit specification. Source/result: `exact_edge_multinomial_audit.py`, `EXACT_EDGE_MULTINOMIAL_AUDIT.json`. No detector histories or samples were generated.

### Checkpoint 82 — bounded one-pair likelihood candidate (2026-11-14)

Evaluated a detector-only four-cell multinomial MLE using the exact categorical pair law and exhaustive finite-count enumeration. The p interval is `[0,.5]`; endpoint distributions are determined by positive-p exact profiles, Bernoulli affine response, and the both-bit complement, with an independent `.018` affine check at `1.11e-16`. At W=200, MLE bias/RMSE are `+.000380/.003470`, `+.0000825/.007327`, and `+.0000177/.009779` for p `.002/.010/.018`. Lower boundary mass matches the no-cofire probabilities. Single-edge RMSE reductions versus raw inversion are modest and do not establish a five-edge composite or controller advantage. The candidate's use of exact gate/readout pair distributions is a stronger information/model assumption than the raw moment formula; pair dependence must be handled for aggregation. Reproducer/result: `exact_edge_likelihood_audit.py`, `EXACT_EDGE_LIKELIHOOD_AUDIT.json`. No samples or outcomes were generated.

### Checkpoint 83 — five-pair composite-score covariance (2026-11-14)

Built the exact joint distribution of the ten detectors in the five disjoint burst pairs and calculated dependence-aware Godambe variance for a sum of marginal multinomial scores. Pair marginals match the 45-feature exact means within `3.22e-15`. The exact joint score variance is 1.964%, 0.488%, 0.283% above a false independent-pair-score calculation at p `.002/.010/.018`. This quantifies a modest static-model asymptotic dependence correction; it does not prove finite-history utility or an advantage over the existing profile. Script/result: `composite_edge_likelihood_sensitivity.py`, `COMPOSITE_EDGE_LIKELIHOOD_SENSITIVITY.json`. No samples, decoder output, or logical labels.

Addendum: across all five pairs, exact one-shot no-cofire probability is `.98782/.95072/.91476` at burst p `.002/.010/.018`, yielding `0.08625/4.08e-5/1.82e-8` for a 200-shot IID window. This shows pooling all five pairs reduces the chance of no observed pair cofire relative to a single pair. It is not a probability of composite-MLE boundary hit.

### Checkpoint 86 — causal estimator step response (2026-11-14)

Added deterministic causal response formulas for between-shot drift. For a trailing width-W history after a p step p0→p1, the population estimate after n post-change observations is p0+(n/W)(p1-p0) for n≤W, reaching p1 only after W observations. For EWMA, m_n=p1+(p0-p1)(1-λ)^n. The first post-change shot necessarily uses the old estimate if prediction precedes its detector observation. These formulas make estimator lag explicit but do not select a window/smoothing constant or establish logical benefit; decoder-optimal p may differ from physical p.

### Checkpoint 88 — measurement drift across shot windows (2026-11-14)

Mixed exact categorical and approximate-DEM per-shot population feature means across `.001/.005` measurement-rate settings, separately, with stationary or paired burst-rate changes. At fixed burst p `.002/.010/.018`, an equal measurement mixture biases the pooled edge estimate by `+2.50e-5/+2.46e-5/+2.42e-5`. Correlated low/low to high/high and low/high to high/low burst/readout mixes give `-5.27e-5` and `+1.018e-4`; the corrected equal-weight nine-condition mixture over all 3×3 combinations at mean p_burst `.010` gives `+1.64e-5`. Exact-circuit and DEM edge-estimate biases differ by at most `4.51e-17` for valid scenarios. A subsequent static-manifold audit found nearest static templates at arithmetic mean parameters with standardized RMS residuals below `3.9e-4`, a very small descriptive population discrepancy.

**Preserved error and correction:** the first balanced-mixture row mistakenly used nine components at weight `1/6` (sum 1.5), making that row invalid. Preserved its output as `SHOT_WINDOW_NUISANCE_MIXTURE_AUDIT_FAILED_INVALID_WEIGHTS.json`; excluded it from inference. Corrected both mixture scripts to use `1/9` and fail if weights do not sum to one, then reran them. No stochastic work occurred.

### Checkpoint 91 — per-shot burst-step information (2026-11-14)

Computed exact KL/TV distances between the joint ten-detector distributions of five burst pairs for `.002→.010`, `.010→.018`, and `.002→.018` across measurement p `.001/.003/.005`, keeping categorical circuit and approximate DEM separate. At measurement p `.003`, exact-circuit KLs are `.03480/.01197/.10228` nats per independent shot. Minimizing over the coarse, independently varying old/new measurement grid yields `.03367/.01172/.09909`; DEM minima differ by <`2e-5`. This indicates pair-subset information remains under those tested nuisance rates, but it is not an alarm threshold, delay, or false-alarm guarantee. Script/result: `burst_step_information_audit.py`, `BURST_STEP_INFORMATION_AUDIT.json`.


### Checkpoint 92 — symmetric simple-hypothesis separation (2026-11-14)

Added a deterministic Chernoff-information audit over the same exact `2^10` laws for five burst-pair detectors, keeping categorical-circuit and approximate-DEM distributions separate. At equal measurement p `.003`, exact-circuit Chernoff information is `.0068443`, `.0027306`, and `.0185203` nats/shot for `.002→.010`, `.010→.018`, and `.002→.018`. The minimum over independently varying old/new measurement rates from `{.001,.003,.005}` is `.0066488`, `.0026774`, and `.0180411`. Approximate-DEM values differ only slightly. The `.010→.018` step therefore has materially weaker symmetric simple-hypothesis separation than the larger step, even though its directional KL remains positive. These are asymptotic IID error exponents for fully specified simple laws, not an online false-alarm rate, detection delay, unknown-nuisance guarantee, or decoder-utility result.

Validation: all laws normalized (maximum error `9.11e-15`); Chernoff values nonnegative and below both directional KLs; `s=1/2` coefficient agrees with Hellinger affinity within `2.23e-16`; bounded golden-section result agrees with an independent 10,001-point grid within `9.81e-11`. No outcomes or histories generated.

### Checkpoint 93 — adjacent real-time decoding literature

A focused primary-source search found Sriram, Stahl, Kubica and Li, “Kinetics of sliding-window quantum error correction,” arXiv:2608.10081 (submitted 10 Aug 2026; https://arxiv.org/abs/2608.10081). The reviewed source studies finite-window syndrome processing with buffer/look-ahead and irreversible commit for ongoing real-time decoding, and an effective reaction-diffusion account of its residual defects. This is distinct from sliding-window noise estimation: Q-SHIFT currently selects a cached decoder between independent completed shots, not while committing corrections during a syndrome stream. The paper is therefore adjacent deployment literature, not direct evidence for the estimator or controller. Journal status and a reproducible code pin were not verified; no code was run and its numerical experiments were not reproduced.

The search did not change the provisional Q-SHIFT method ranking. It sharpens a future scope decision: specify whether deployment targets per-shot model updates or in-circuit, bounded-latency decoding, since these imply different causal timelines, memory constraints, and estimands.

### Checkpoint 94 — quickest-change asymptotic information scale

Reviewed Lorden (1971) and Moustakides (1986) primary statistical sources. Under known IID pre/post laws, classical quickest-change lower-bound theory scales worst-case delay as `log(gamma)/D(P1||P0)` for large mean-time-to-false-alarm gamma; Moustakides proves CUSUM optimality in the known-law IID Lorden setting. Applying this only as an asymptotic sensitivity calculation to the exact categorical ten-detector KL at illustrative gamma=1000 gives scales of ~199, ~577 and ~68 shots for `.002→.010`, `.010→.018` and `.002→.018`. Coarse independent old/new measurement nuisance-grid sensitivity raises these to ~205, ~590 and ~70. These are not finite-history predictions or CUSUM operating characteristics; composite nuisance, coarse-grid coverage, finite gamma, causal graph update cost and logical utility remain unresolved.

The exact/DEM calculation preserves representation distinction. No alarm was thresholded and no histories were generated.

### Checkpoint 95 — new hardware-control and real-time-decoder prior art

Reviewed the peer-reviewed 2026 Nature report by Sivak et al. on reinforcement-learning control during QEC. Its detector-event surrogate adapts more than 1,000 physical controls on Willow and reports hardware improvements against injected drift. The paper explicitly separates this from complementary decoder-prior steering, for which it relies on LER estimation and notes real-time scaling difficulty. This narrows novelty of the broad claim “use detection events to adapt QEC,” while leaving a different Q-SHIFT question: can a known-support, detector-only burst estimator safely choose cached decoder graphs when physical controls are unavailable? Custom code is proprietary; no data or code was downloaded or executed.

Also corrected publication status for Lee, Hur & Park’s Mamba decoder: peer-reviewed early-access *npj Quantum Information* article published 28 Oct 2026, DOI `10.1038/s41534-026-01403-y`; prior arXiv entry is retained as historical source provenance. It is supervised decoder/latency research with extensive synthetic pretraining and a hardware-data fine-tuning split, not a detector-only drift estimator. The Pancotti et al. TN variational method is separately confirmed to use logical labels in its loss and sampled labeled batches for training/tracking; it remains outside the current no-label controller information set.

Disposition: retain known-event exact detector-only edge inversion as a promising structural research candidate, but reduce novelty claims around generic detector-event adaptation. Physical-control RL is the stronger demonstrated hardware direction only where system controls and hardware feedback exist. Mamba is an adjacent decoder-latency alternative, not a substitute estimator.

### Checkpoint 96 — detector reward and decoder action are causally different

Static inspection of `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py` confirms the detector-profile estimator, circuit/graph construction for a supplied assumed burst p, and decoding of already supplied detector arrays are separate functions. The generic `qshift_core_v1/controller.py` selects proposals/fallback but does not change the circuit generator. Therefore, under the present downstream-only decoder-choice action, detector/observable generation is invariant to which cached decoder graph is later applied. This is the factorization `P(D,O | theta,a_decoder)=P(D,O | theta)`. The detector-rate objective in Sivak et al. can drive hardware controls because those actions alter the physical process; it cannot directly score decoder graph utility in this simulator. A graph switch needs a model-based mapping or a separate labeled decoder-utility assessment. This conclusion is conditional on the inspected simulator/interface; real closed-loop feed-forward would require a different model.

### Checkpoint 97 — dense old/new measurement nuisance grid

Expanded the independent measurement-nuisance search from the prior 3x3 coarse grid to a deterministic 101x101 grid over old/new measurement p in `[.001,.005]`, spacing `4e-5`, separately for the exact categorical circuit and approximate DEM. The minimum forward KL for `.002→.010` is `.0336590` (old/new measurement `.005/.00492`), for `.010→.018` `.0117140` (`.005/.00492`), and for `.002→.018` `.0990910` (`.005/.005`) in the exact circuit. DEM minima are `.0336665/.0117154/.0991106`. The first two minima are lower than the coarse grid by only `8.27e-6` and `3.94e-6`; the large-step minimum is unchanged at saved precision. This reinforces that the tested nuisance interval does not erase pair-subset information under these fully specified laws, while remaining only a finite grid result.

Validation: all distributions normalized with max error `1.80e-14`; all grid KL minima nonnegative; each selected minimum was recomputed directly. The illustrative `log(1000)/D` scale for the `.010→.018` exact-circuit step changes from coarse-grid ~589.50 to dense-grid ~589.70 shots. Neither is a continuous-nuisance robust bound, CUSUM delay, finite-history alarm guarantee, or decoder benefit. No samples or histories were generated.

### Checkpoint 98 — full joint likelihood versus 15 pair moments

Computed local Fisher information from the full exact `2^10` outcome law of the five burst-pair detectors, then compared it with optimal-covariance GMM information from the same ten detector bits plus five pair-cofire means. Burst p and measurement p are both unknown; burst information is profiled using the 2×2 Fisher Schur complement. Exact categorical-circuit and approximate-DEM results are separate.

At nominal measurement p `.003`, the exact-circuit full-joint vs 15-moment asymptotic burst SD coefficients per `sqrt(N)` are `.02207` vs `.02366` at p `.002` (6.73% reduction for full law), `.04663` vs `.04712` at p `.010` (1.05%), and `.06170` vs `.06208` at p `.018` (0.60%). Thus most selected-subset moment information is retained at medium/high burst p; the low-p difference is more noticeable. The comparison is not against the full existing 45-feature estimator, and a full-likelihood finite-window estimator could suffer severe sparse-state effects. It does not justify changing the estimator without a separately authorized finite-history study.

Validation: max law normalization error `7.33e-15`; maximum derivative-mass residual `2.03e-9`; full Fisher matrices positive definite; profile 15-moment GMM information never exceeds full-joint information; halving finite-difference steps changes profiled information by at most `3.27e-10` relative. These are local, static, model-correct asymptotic information bounds, not finite-sample RMSE, coverage, or decoder benefit.

### Checkpoint 99 — expected occupancy for the full ten-bit likelihood

For a stationary IID shot stream and the exact ten-detector laws, expected occupied cells are calculated as `sum_s[1-(1-q_s)^W]` and expected singleton cells as `sum_s W q_s(1-q_s)^(W-1)`, without drawing outcomes. At W=200, exact categorical expected occupied cells are only ~19.8, 23.3 and 25.2 across p `.002/.010/.018`, with ~9.8–12.0 expected singleton cells; 1,023/1,024 cells have expected counts below five. The approximate DEM gives nearly the same values. The outcome entropy effective support is ~3.1–4.4 despite 1,024 formally positive states.

This warns that a full-likelihood fit has sparse cell counts at short histories. It is still a low-dimensional parametric likelihood, not a 1,024-parameter multinomial; expected occupancy alone does not determine bias, RMSE, boundary behavior or whether exact likelihood outperforms the 15 moments. Under drift, a pooled IID occupancy calculation also requires a mixture model. No detector histories were generated.

### Checkpoint 100 — composite quickest-detection theory applicability
Reviewed primary sources for finite-window composite quickest-change detection with unknown post-change GLM parameters, unknown densities, and structured nonstationary post-change laws. Added `COMPOSITE_QCD_LITERATURE_NOTE.md` and a concise literature-database entry. The main refinement is methodological: a model-based finite-window likelihood/GLR is plausible because the Q-SHIFT per-shot categorical law is finite and low-dimensional, but published false-alarm and delay statements depend on assumptions (valid predictable densities/common support; known in-control reference in some methods; estimation regularity/curvature; controlled optimization error; stationary or structured nonstationary post-change behavior) that must be mapped before they can support this design. Generic KDE/NGLR is not currently favored because the outcome alphabet is large relative to short-window occupancy and a physical low-dimensional law exists. This is a literature assessment only; no new likelihood computation, alarm, history, sample, or experiment was run.

### Checkpoint 101 — bounded pair-cofire e-process feasibility screen
Using the exact categorical-circuit parity-character implementation and the approximate DEM separately, audited the population mean of `X=(1/5) sum_j D[a_j]D[b_j]`, where X is in [0,1]. At fixed null burst p=.002, the maximum over 101 measurement-p points in [.001,.005] was .0026946910 (exact circuit; grid maximum at pm=.005); for alternatives burst p in [.010,.018] (endpoint evaluation exact in burst p at each fixed pm by affine dependence), the minimum over the same measurement grid was .0099707443 (at pb=.010, pm=.001), giving a finite-grid gap .0072760532. Approximate DEM results were .0026936574, .0099703842, and .0072767268. This supports feasibility of testing a one-sided bounded-mean alarm if a uniform conditional null mean bound can be proved, but does not certify the continuum measurement-p maximum, any false-alarm operating characteristic, delay, causal attribution, estimator accuracy, or decoder benefit. A first attempt to extend the null burst range to include pb=0 failed because the circuit builder omits zero-probability burst sites and reweighting correctly rejected the altered site count; this failure and the reduced fixed-p null scope are preserved in the source/result note. No sampling, sequence generation, or alarm evaluation occurred.

### Checkpoint 102 — place bounded e-detector in the architecture
Added a narrow alarm-only candidate to the architecture draft and hypothesis ledger. The e-detector construction (Shin, Ramdas & Rinaldo 2024) can handle composite pre-change classes, including non-IID behavior, when each baseline increment satisfies a conditional expectation bound. This makes it an alternative to fitting an estimated pre-change likelihood for **alarms**, not a complete burst estimator/controller. The current pair-cofire statistic is promising on the finite pm grid but still lacks a continuum null envelope; never describe it as a validated or calibrated Q-SHIFT detector.

### Checkpoint 103 — correct false-switch risk target
Recorded an owner decision in the unresolved-question register: select ARL, fixed-horizon false-alarm probability, or expected false graph-switch count as the operational objective. The e-detector literature's ARL guarantee cannot be relabeled as fixed-horizon controller-switch risk, particularly if the process resets after each alarm. No thresholds or controller policies were chosen.

### Checkpoint 104 — expected log-increment population screen
Calculated expected log growth of the bounded-mean baseline increment using the exact ten-detector categorical law and approximate DEM separately. The six possible X levels were aggregated from the 1,024-state law; a deterministic 10,000-point lambda grid was searched. With each finite measurement-grid null maximum plus `1e-10` used as provisional m, exact-circuit E[log L] at p_b=.010 ranges .028721–.030276 nats/shot and at p_b=.018 .089886–.090705; DEM values are .028733–.030286 and .089914–.090730. Lambda grid optima are approximately .036–.037 and .073. These are expected increment rates only, not delay/ARL/false-switch metrics. They depend on the unproved continuum null envelope. No paths or data were generated.

### Checkpoint 105 — exact-circuit continuous mean certificate
Static circuit inspection found that `measurement_p` is passed as Stim's `before_measure_flip_probability`, producing independent `X_ERROR` sites; all other site parameters are fixed in this audit. The mean of the five pair-cofire bits is represented exactly as a degree-8 polynomial in `u=1-2p_m`. Exact rational Bernstein coefficients certify that its derivative with respect to u is negative across the full `[.99,.998]` interval at burst p `.002`, `.010`, and `.018`, hence mean increases in measurement p. Each disjoint pair is affected by one matching burst site and its simultaneous two-bit flip has even parity in the pair moment, so each pair-cofire mean is affine in common burst p. Bernstein coefficients also certify positive mean gaps `g(.010,p_m)-g(.002,p_m)` and `g(.018,p_m)-g(.010,p_m)` across measurement p. Therefore the exact categorical null maximum is `0.00269469102575917` at `.002/.005`, and the alternative rectangle minimum is `0.00997074427026786` at `.010/.001`; gap `0.00727605324450869`. Cross-validation against the existing feature-expectation routine is below `1e-16`. The DEM remains grid-only. This supports a conditional-mean e-detector under the tightly stated exact-model null, but does not validate a deployed alarm, ARL in the presence of model error, finite-horizon switching risk, or decoder utility.

Implementation history: an initial certificate attempt incorrectly unpacked the mapped site schema; a second corrected mapping unpack still passed a two-field tuple to a three-field loop. Both deterministic errors were corrected. The third version passed and now derives raw instruction indices and mapped supports separately. The earlier `p_b=0` template-site mismatch remains separately preserved.

### Checkpoint 106 correction to checkpoint 105
Checkpoint 105 described the exact-circuit null as fixed at p_b=.002. The exact pair-cofire mean is affine in the common burst probability: each disjoint pair is affected by exactly one corresponding independent burst site, and that event flips both detector bits, giving even parity in the pair term. The exact Bernstein certificate already proves g(.010,p_m)-g(.002,p_m)>0 throughout the full measurement interval, so the affine slope is positive. Therefore the null mean is monotone on p_b in [0,.002] and its continuous supremum remains at .002; the p_b=0 distribution is covered as the analytic limit, without trying to reweight a circuit with its omitted zero-probability instruction. The certified alternative minimum and gap are unchanged. Gate noise remains fixed and the approximate DEM remains grid-only.

### Checkpoint 107 — information retained by cofire count
Computed exact categorical-circuit and approximate-DEM simple-IID KL before and after compressing the ten selected detector bits to the six-level count of five pair-cofires. Across three burst steps and `pm=.001,.003,.005`, retention ranges 90.33%–99.26%. At `pm=.003`, exact-circuit retained fractions are 93.62%, 98.43%, and 94.48% for `.002→.010`, `.010→.018`, and `.002→.018`. The audit checks normalization and the data-processing inequality. This is information in the full count law, not e-increment or alarm performance; a richer category-wise e-process would need separate null-valid construction. No sequences were generated.

### Checkpoint 108 — e-detector operating-risk construction
Targeted review of the source definitions confirms: a baseline increment satisfying the conditional expectation bound yields per-start e-processes by products; e-SR sums the start-time processes and has ARL at least `1/alpha` at threshold `1/alpha`. The paper also describes summable start weights that control the probability of any false alarm, at a delay cost tied to the start-time weight. This sharpens the open owner choice between ARL, finite-ever/horizon false alarm, and repeated false-switch control. Added the mathematical construction and boundaries to the feasibility note; no e-process recursion, threshold, or detector stream was evaluated.

### Checkpoint 109 — dense independent measurement-nuisance KL audit
Ran deterministic 101x101 old/new measurement-p grids for all three burst transitions, comparing the full ten-bit law and six-level cofire count separately under the exact categorical circuit and approximate DEM. The initial ratio of separately minimized KL values could compare different nuisance pairs; it is now explicitly labeled as such. Added same-pair information ratios. Worst grid count/full ratios are 55.97%, 34.68%, and 76.35% for `.002->.010`, `.010->.018`, and `.002->.018`; exact circuit and DEM agree closely. These are discrete-grid information comparisons, not continuous or sequential guarantees. Normalization max error `1.80e-14`, data-processing violation `0`. No histories or decoder outcomes were generated.

### Checkpoint 110 — continuous category envelope and e-factor
Derived six exact categorical-circuit cofire-count probability polynomials (degrees 5 in 1-2p_b and 16 in 1-2p_m), then bounded each category on the continuous null rectangle with rational tensor Bernstein coefficients on 4x4 cells. The exact upper bounds sum to 1.011376721546938. Independent direct-XOR category laws match at five points within 7.44e-15. A fixed proposal q divided by each certified category upper bound is a one-step e-factor under the declared conditional model. Two proposal grids give minimum alternative expected log increments .0180323 and .0149429 nats/shot; the simpler fixed-lambda mean factor gives .0287210 on the same parameter grid. The category method is valid analytically but currently less attractive. No path, detector, alarm, decoder action, or logical outcome was evaluated.

Implementation note: an initial exact Bernstein 12x12 attempt was safely interrupted before output due high Fraction compute cost. An initial schema error in the optimized derivation was corrected; the 4x4 exact-rational version completed, with each exact category polynomial matching the independently built direct-XOR law at five probes. Finite-grid log-growth minima remain diagnostics, not continuous alternative guarantees.

### Checkpoint 111 — alternative-drift certificate compute limit
The category-wise e-factor has a continuous exact-model null-validity envelope, but its minimum expected-log growth is currently established only on a 101-point measurement grid for each of three burst alternatives. An optional rational atanh-log plus expected-log Bernstein enclosure was attempted twice and interrupted before completion after CPU-active exact-rational work (observed process CPU reached about 244 seconds on the second attempt). It produced no result. The source now gates this optional path behind `--certify-alt-growth`; the default reproducible run was rerun and again passed its direct-XOR checks. The continuous alternative-drift claim remains unproven.


### Checkpoint 112 — architecture and unresolved-question reconciliation
Recorded that the exact category-wise e-factor partially resolves only the narrow continuous-null-envelope question. The conditional expectation bound is certified for the exact circuit and declared rectangle; continuous alternative growth, approximate-DEM coverage, alarm operating objectives and downstream decoder utility remain open. The scalar mean factor remains simpler and has higher expected log growth on the tested alternative grid.

### Checkpoint 113 — exact-envelope transfer to approximate DEM
Applied the exact-circuit six-category upper bounds to deterministic DEM laws on 5 null burst settings x 101 measurement settings and 3 alternative burst settings x 101 measurement settings. No category envelope was exceeded on this grid. Null expected-e maxima were .98915 and .98935; alternative log-growth ranges nearly matched exact-law results; normalization error max 9.10e-15. This is finite-grid approximation evidence only and does not transfer the continuous exact-circuit guarantee to DEM or physical model error.

### Checkpoint 114 — proposal optimization and failed formulations
Two SLSQP maximin formulations failed numerically (all-constraint and cutting-plane forms). A smooth soft-min SLSQP formulation converged in 25 iterations; after exact rational rounding, the fixed q has minimum expected-log growth .0180357 nats/shot on the 303-row tuning grid and the same minimum on a 1001-point measurement sensitivity grid at the three burst levels. This is essentially unchanged from the reference q (.0180323), below the fixed-λ scalar mean (.0287210); log(N)/beta smoothing gap is .0022855. It does not certify exact minimax or continuous alternative drift. Failed attempts were recorded, with no results from them. No streams or decoders were evaluated.

### Checkpoint 115 — bidirectional bounded-mean regime triggers
Using the exact continuous mean rectangle certificate, derived a downward trigger on `Y=1-X` with high-burst null pb in [.010,.018] and low-burst alternative pb in [0,.002]. It has the same mean separation gap .0072760532 and, at fixed lambda=.003, a uniform log-increment lower bound 1.3047994e-5 nats/shot. The upward trigger bound remains 1.3304032e-5 at lambda=1e-5. These support a stateful two-regime monitor with a (.002,.010) indifference band, not a generic two-sided detector. Combining/resetting processes requires owner-defined risk allocation; no stream or graph switch was evaluated.


### Checkpoint 116 — directional e-factor state-machine limitation
Recorded the owner decision for the burst-probability indifference band and for the regime state following a switch. A false switch can invalidate the assumed null for the opposing process; alpha spending and state recovery must be designed before any controller study.

### Checkpoint 117 — continuous scalar e-factor growth certificate
Bounded each of the six cofire-count category probabilities over the up/down alternative rectangles with exact rational 4x4 tensor Bernstein bounds; bounded each rational log factor using an explicit-tail atanh series; summed worst-case endpoint products. At lambda=.005, the uniform expected-log lower bounds are .0107107321 nats/shot upward and .0000367389 downward. This certifies scalar-factor alternative drift continuously under the exact categorical circuit and measurement interval, while the optional category-q/U continuous-growth attempt remains incomplete. No paths, alarms, or decoder actions were evaluated.

### Checkpoint 118 — exact gate-mismatch counterexample grid
A deterministic fault-map reweighting audit evaluated 27 exact categorical circuit points. With gate p=.004, the low-burst null cofire mean exceeds its fixed-.003 continuous bound by up to .00031178; with gate p=.002, the high-regime mean falls below its fixed-.003 floor by up to .00006767. This establishes loss of the fixed-gate e-factor validity claim at those tested settings. It does not continuously characterize gate tolerance or identify physical cause from detector-only data. No histories or decoder outcomes were used.

### Checkpoint 119 — three-parameter exact-circuit mean identifiability
`three_parameter_detector_identifiability.py` deterministically maps exact categorical-circuit 45-feature means over burst, measurement, and gate probabilities. At nominal `(.010,.003,.003)`, a central-difference Jacobian with step-halving checks has covariance-whitened, scale-adjusted singular values `(0.297712,0.169915,0.107253)` and numerical rank three at relative cutoff `1e-8`. Relative derivative changes across the three tested steps are at most `4.67e-7`. Measurement and gate derivative columns have scaled cosine `0.84164`. On the finite `5 x 5 x 3` profile grid, closest distinct means are separated by `0.01205` marginal-variance-standardized feature RMS; closest pair changing both burst and gate is `0.02564`. This is local structural/population-mean evidence, not global identifiability or finite-history accuracy. It does not resolve the fixed-gate e-process failure under gate mismatch. No DEM analysis, histories, sampling, or decoder results were produced.

### Checkpoint 120 — approximate-DEM three-parameter comparison
`three_parameter_dem_identifiability.py` repeats the burst/measurement/gate mean-feature calculation using Stim DEMs generated with `decompose_errors=True` and `approximate_disjoint_errors=True`. Treating the resulting error mechanisms as independent, it derives the full 45-feature mean/covariance by parity-character inclusion-exclusion and calculates a local covariance-whitened Jacobian plus a `5 x 5 x 3` profile grid. The nominal DEM has 591 mechanisms and numerical rank three; scaled singular values `(0.297662,0.169928,0.107131)` closely track exact-circuit values. Independent XOR-state recursion over all 1,020 distinct detector subsets used in the nominal covariance gives max absolute mean error `7.15e-16` and covariance error `6.59e-16`. This validates DEM arithmetic, not equivalence to the categorical circuit or finite-history accuracy. No histories or decodes were evaluated.

### Checkpoint 121 — approximate-DEM gate-noise mismatch counterexamples
`dem_gate_noise_mismatch_audit.py` evaluated 54 deterministic DEM model points across three burst settings per regime, three measurement settings, and gate p `.002/.003/.004`. Against finite-grid envelopes at gate p `.003`, the low-burst grid maximum at gate `.004` exceeds by `.0003106202`; the high-burst grid minimum at gate `.002` falls short by `.0000673725`. This reproduces the direction and scale of the exact-circuit fixed-gate e-factor counterexamples in the approximate DEM. It remains a finite-grid audit, not a continuous robust guarantee; no histories or decodes were used.

### Checkpoint 122 — continuous robust burst/measurement/gate scalar e-factor envelope
`exact_three_parameter_efactor_envelope.py` constructs the ideal rational exact-categorical pair-cofire mean polynomial under the balanced source allocation (1Q alternatives `p_g/3`, 2Q alternatives `p_g/15`, measurement `p_m`, burst `p_b`) and proves continuous ranges using tensor Bernstein coefficients of degrees `(1,8,25)`. Over `p_g=[.002,.004]`, `p_m=[.001,.005]`, the low-burst null `[0,.002]` has `E[X] <= .003006472621297416`; the high-burst alternative `[.010,.018]` has `E[X] >= .009903071523335840`. Gap lower bound `.006896598902038424`. Complementary `1-X` has the same directional gap. Eight deterministic exact feature expectation probes agree with the polynomial within `1.02e-16`; source probability probes across endpoints/quarter/midpoints differ from the rational intended allocation by at most `8.68e-19`.

By concavity, the bounded-statistic e-factor with conservative null mean denominator has strictly positive uniform expected-log lower bounds for tested lambdas in both directions; at `.005`, the bounds are `.004718375080752108` nats/shot upward and `.00003478894429311721` downward. This is analytic population evidence for the ideal model and declared gate rectangle, not an implemented process, delay/false-alarm performance, repeated-switch policy, or decoder benefit. The old fixed-`.003` factor still fails under gate mismatch outside its original null bounds.

Optimizing only the conservative endpoint-chord lower bound gives exact-form lambdas `.0069173958633` upward and `.6964100871` downward, with certified lower bounds `.004932537879491168` and `.003336614487056263` nats/shot. The downward optimizer is large and not selected for implementation; it highlights an unresolved numerical/resource tradeoff, not a delay optimum.

Checkpoint-122 implementation record: pre-result attempts exposed a validation-fixture tuple-unpack error, a support-map tuple-shape error, and Python's integer-to-string digit limit when serializing exact rational logarithm endpoints. Each was corrected before the final output. The final output stores exact integer ratios for Bernstein mean bounds and compact hashes/bit lengths plus decimal approximations for very large rational logarithm intervals; positivity checks are performed on the exact `Fraction` values.

### Checkpoint 123 — feasibility ranking and novelty reconciliation
Updated the append-only feasibility and hypothesis ledgers after the continuous gate-robust certificate. The scalar cofire e-factor is now the best-specified deterministic alarm-statistic candidate over the declared three-parameter rectangles, while causal graph switching remains unproven and below strong static/trailing/EWMA controls pending equal-information utility evidence. The 45-feature exact-circuit and approximate-DEM local rank-three results refine—but do not erase—the prior two-parameter and 15-moment analyses. The low-rate boundary issue remains: edge inversion can produce inadmissible finite-count estimates, so no profile or edge estimator is promoted to controller-ready. Novelty remains narrow because detector-only drift estimation and adaptive decoding are established neighboring literatures. No empirical outcomes, alarms, histories, or decoder comparisons were generated.

### Checkpoint 124 — approximate-DEM transfer falsification grid
`dem_three_parameter_envelope_transfer.py` evaluated 250 DEM templates (5 values each of burst, measurement and gate probability in the low and high regions), using Stim decomposition and approximate disjoint-error conversion. The DEM low-null grid maximum `.0030042775703872982` remained below the exact-circuit null upper `.003006472621297416`. One DEM high-alternative point `(p_b,p_m,p_g)=(.010,.001,.002)` had mean X `.009903011675058504`, below the exact-circuit lower envelope `.009903071523335840` by `5.9848e-8`. Although the DEM grid itself retains a positive observed gap `.006898734104671206`, the exact-circuit e-factor constants do not transfer as a guaranteed DEM arm. The initial assertion demanding zero violations failed and is preserved by this log; the corrected check verifies and records the single counterexample. No stochastic observations were made.

Scope clarification: this transfer failure does not invalidate the circuit-level e-factor when observed detector vectors follow the exact categorical circuit; downstream decoder graph construction from an approximate DEM does not change that data-generating law. The failed transfer is relevant only if the DEM is itself treated as the source distribution or as an automatic replacement for the circuit law.

### Checkpoint 125 — e-factor role on the independent-shot time axis
Append-only updates to the drift-window, architecture and unresolved notes clarify that the e-factor is a post-shot regime alarm, not an estimate of burst p and not a decoder selection rule. On the current independent-shot axis, `X_t` is observed after shot t and any graph change begins at shot t+1. Relative-window inversion continues to collapse to one newest shot vector; trailing-window/EWMA/periodic comparators must receive the same prior detector history and cache budget. No computation, histories or decoder outcomes were added.

### Checkpoint 126 — directional e-processes do not yet define a safe switching state machine
The up and down e-factors are valid under different null rectangles. A possibly false transition from low to high leaves the next high-null process running under a low distribution, outside its validity premise. Thus reset-count alpha spending alone does not justify repeated bidirectional graph switches. The current result supports a one-sided alarm under a known sustained null, not autonomous switching; state recovery, abstention/hold behavior and the false-switch target remain owner/protocol decisions. No stochastic or sequential simulation was run.

### Checkpoint 127 — three-parameter exact-circuit local-rank grid
Ran the deterministic `5 x 5 x 3` exact categorical-circuit local Jacobian grid for the 45 detector features over burst, measurement, and gate probabilities. All 75 nodes have numerical rank 3 at relative cutoff `1e-8`; condition ratio using the fixed nominal single-shot covariance for whitening ranges `2.76834197–2.78366374`. Maximum central-difference step-halving change is `4.69768405e-7`. Scoped AST and result-schema assertions passed. This expands local rank evidence over the finite grid only; it does not establish continuum/global injectivity, finite-history recovery, or practical estimation. No sampling, histories, or decodes were used.

### Checkpoint 128 — bounded-increment finite-time alarm quantiles
Converted the exact-circuit continuous one-sided e-factor growth/log-range certificates into a deterministic Azuma-Hoeffding crossing bound. For fixed one-sided alpha .05/.01 and miss target delta .10/.05, sufficient alternative crossing quantiles are 69,239/89,719/69,885/90,366 shots upward and 150,462/195,217/151,419/196,176 downward. These are conservative distribution-free upper bounds under per-shot conditional alternative-law and bounded-increment assumptions; the much smaller mean-drift quotients (608/934 and 898/1,381) are not delay guarantees. Ville's bound applies only to one fixed one-sided process under its certified null, not repeated bidirectional switching. A first smoke assertion used a nonexistent JSON key and failed before output; after correcting the key, the run and n/n-1 boundary checks passed. AST, JSON, and arithmetic assertions passed; no streams, sampling, or decoder calls occurred.

### Checkpoint 129 — continuous log-second-moment attempt stopped at compute bound
Prototyped `efactor_log_second_moment_envelopes.py` to derive the exact joint law of the five cofire indicators by rational parity-character inclusion/exclusion, aggregate it into six count categories, and bound the alternative log-increment second moment for a Freedman delay calculation. The deterministic category-law polynomial normalized identically, and an independent direct XOR-state recursion over 1,024 detector syndromes agreed at three fixed parameter probes within the script tolerance. The first run failed before output because the validation harness unpacked a four-field alternative as three fields; no result file was written. After fixing that harness error, the corrected continuous Bernstein stage remained CPU-active for about three minutes, reached approximately 440 MiB working set/133.5 seconds observed process CPU, and was safely interrupted without writing output. Therefore no Freedman variance or delay number is claimed. The source is retained as an incomplete research attempt; continuous variance tightening remains unresolved. No sampling, histories, alarms, or decodes were produced.

### Checkpoint 130 — continuous Freedman quantiles from certified mean ranges
Used the continuous expected-log lower bound, Jensen upper bound from the exact continuous alternative mean envelope, and Bhatia-Davis variance bound over the log-increment support. Freedman's inequality gives sufficient counts `(alpha,delta)=(.05,.10),(.05,.05),(.01,.10),(.01,.05)` of `10,433; 13,232; 11,032; 13,839` upward and `3,787; 4,511; 4,503; 5,246` downward. Integer-bound checks confirm the Freedman RHS is at most delta at n and above delta at n-1. This is a continuous exact-categorical distribution-free bound for one fixed direction under sustained conditional alternative laws; it is not an expected/observed delay and has no repeated-switch guarantee. AST/JSON and formula checks passed; no streams or decodes were generated. The expensive category-polynomial variance attempt remains preserved as a failed/interrupted artifact, not as evidence.

### Checkpoint 131 — one-change mixture e-process and constant-memory recurrence
Constructed an anytime mixture over all candidate abrupt change starts with exact telescoping weights `w_s=1/[s(s+1)]`. The mixture remains a supermartingale under the fixed corresponding null and has a constant-memory update `A_t=L_t*(A_(t-1)+1/[t(t+1)])`, `E_t=A_t+1/(t+1)`. Exact deterministic recurrence tests match direct component summation for three factor sequences and verify the prior identity through 10,000 terms. The Freedman post-change sufficient counts at alpha=.05/delta=.10 are up/down `10,693/4,099` at start 1, `15,248/9,422` at start 1,000, and `19,611/14,556` at start 1,000,000. This covers an unknown single change time only; one direction is selected in advance from a trusted initial regime. No resets, reversal, two-direction null validity, graph selection, or decoder utility are claimed. No detector streams or outcomes were created.

### Checkpoint 132 — bounded-horizon prior alternative
Computed a uniform change-start prior on prespecified horizon H with a constant-memory recursion and an anytime no-change supermartingale. For alpha=.05/delta=.10, continuous Freedman sufficient bounds for starts anywhere up to H are upward/downward `12,921/6,715` at H=1,000; `13,711/7,633` at H=10,000; `14,486/8,535` at H=100,000; and `15,247/9,422` at H=1,000,000. The prior guarantees no alternative component for starts after H, so horizon is an owner decision. No streams or decoder results were used.

### Checkpoint 133 — fixed-point lower-bound recurrence
Built an exact-integer Q=2^96 sketch for the one-change mixture. All six rational factor values and mixture weights are rounded downward; integer comparison of the lower mixture to the alarm threshold can only delay or suppress crossing. Exhaustive deterministic checks covered 1,296 length-four abstract category-factor sequences per direction and 5,184 prefixes per direction; every fixed-point lower value was below the exact mixture and every lower-bound alpha=.05 crossing implied exact crossing. Direct component expansion matched the exact recurrence over all prefixes. Maximum relative factor shortfalls were <3.1e-29. This establishes arithmetic safety for the Python arbitrary-integer sketch only, not embedded fixed-width or decoder integration. No detector histories or outcomes were used.

### Checkpoint 134 — continuous e-growth signs and delay in the intermediate burst band
Partitioned p_b in [.002,.010] into four rectangles while retaining p_m [.001,.005] and p_g [.002,.004]. Exact three-parameter Bernstein means plus the same chord/Jensen inequalities certify upward log growth only on [.006,.008] and [.008,.010], and downward-complement growth only on [.002,.004]; other band signs remain unclassified. For alpha=.05/delta=.10, one-change mixture Freedman sufficient counts at starts 1/1,000/1,000,000 are upward 1,468,676/1,562,294/1,658,130 on [.006,.008], upward 22,510/31,248/39,642 on [.008,.010], and downward 34,070/53,503/71,985 on [.002,.004]. These concern sustained plateaus, not trajectories traversing bands. A detector alarm in this region remains separate from graph selection. AST/JSON and threshold-boundary checks passed; no streams were evaluated.

### Checkpoint 135 — linear drift plus endpoint dwell
Applied band-specific conditional mean and variance certificates to midpoint-indexed linear p_b ramps with a one-change mixture component beginning at the first uniformly positive band. At alpha=.05/delta=.10, from global start shot 1, 10k/100k/1M-shot upward ramps need 15,548/8,442/0 additional high-regime dwell shots; downward ramps need 10,854/9,005/0 low-regime dwell. Starting at shot 100,001 gives dwell 17,420/9,034/0 upward and 12,771/9,566/0 downward. The bound uses only time spent in certified positive bands plus any endpoint dwell and therefore covers the specified path and predictable nuisance variation inside the certified rectangles. Two initial schema-key errors were corrected before a result was written. No stream or decoder was evaluated.

Checkpoint 130 implementation note: the first Freedman-source run referenced the wrong JSON key for the downward arm and stopped before producing output; after reading the actual schema and correcting the key, the certified values and output were generated and independently checked.

Checkpoint 134 implementation note: the first attempt to serialize exact rational expected-log bounds exceeded Python's integer-to-string digit limit. The script was corrected to use the existing compact rational hash/bit-length/decimal representation; no scientific result was changed.

Checkpoint 135 validation note: two early ramp-screen runs stopped on mismatched field names when reading the already saved variance-bound schema; a separate independent check then stopped because its validation snippet omitted the `Decimal` import. After correcting the schema mapping and importing `Decimal`, the ramp output was independently recomputed for all 12 ramp/offset cases. These failures wrote no replacement result and are preserved here for provenance.

### Checkpoint 136 — global alpha allocation requires independent episode reset
Derived an exact summable episode allocation `alpha_j=.05/[j(j+1)]`; the first 1,000 allocations sum to `.05*(1000/1001)`, with total `.05`. Under independently verified baseline/null conditions at every external reset, a union bound controls any false switch across episodes without independence. At candidate start s=1,000 and delta=.10, sufficient counts for episodes j=1,2,10,100 are 15,474/15,832/16,767/18,192 upward and 9,687/10,105/11,200/12,877 downward. This does not support alarm-triggered autonomous reversal or baseline reset. No paths or decodes were evaluated.

Checkpoint 136 validation note: the first independent JSON assertion mistakenly expected the telescoping partial sum as `250/5005`; the exact value is `50/1001`. Corrected the assertion; the 24 minimal-n bounds and source AST/JSON checks then passed. This was a validator expectation typo, not a change to the alpha allocation or results.

### Checkpoint 137 — Q=2^96 start-weight representation cutoff
Calculated the largest s with nonzero fixed-point prior floor as `281,474,976,710,655`; at the next s the candidate weight rounds to zero. Pointwise lower rounding remains false-alarm conservative but no longer provides change-time coverage beyond that start. The extra log threshold at s=10^6 is only `5.21e-18` nats and at 10^12 is `2.05e-6`, under the Python arbitrary-integer Q=2^96 arithmetic prototype. Do not label the quantized infinite-prior implementation exact or unlimited-horizon. No sampling or decoder outcomes.

### Checkpoint 138 — fixed effect-size lambda mixture
Constructed four six-decimal-down-rounded lambdas per direction, each tuned to a continuous certified burst subregion, with uniform prior 1/4 and the existing unknown-change-time prior. The nested convex mixture is a valid one-direction e-process under the same null. At start s=1,000, alpha=.05/delta=.10, sufficient counts across up regions [.004,.006]/[.006,.008]/[.008,.010]/[.010,.018] are 289,572/46,517/20,974/15,700. Down regions [.006,.008]/[.004,.006]/[.002,.004]/[0,.002] are 391,256/61,091/21,669/9,951. This expands continuous sign certification versus a single endpoint-tuned lambda, with O(4) state cost; no decoder action or performance result. No streams were generated.
### Final STOP handoff — 2026-11-14
The user issued STOP. No additional literature searches, calculations, tests, feasibility runs, sampling, or experiments were started. Seven final synthesis reports were created from saved evidence. The saved weighted matrix contains 18 scored candidate rows. An exact unique-paper count is unavailable because the working literature ledger is not de-duplicated. Final audit disclosed the checkpoint-133 alpha-threshold predicate defect: its explicit threshold-crossing count is unsupported pending correction/rerun. The pre-fix artifact remains preserved. No correction run or lambda-bank fixed-point audit was performed. Conclusions requiring those checks remain unresolved.
