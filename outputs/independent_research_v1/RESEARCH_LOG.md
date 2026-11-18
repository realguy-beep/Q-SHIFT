# Independent research expedition log

## Checkpoint 0 — 2026-11-18

- Repository: `realguy-beep/Q-SHIFT`, published `main` revision `7cbc2e791a854e40ed4e840393fc8b4368d95ac2`.
- Original checkout `/workspace/Q-SHIFT` was clean on entry, branch `work`. Remote `main` resolves to the same revision. Claude's `codex/qshift-adaptive-robust-v1` remote branch resolves to `3a34a6abdeff0d3bb44386708f50fb645d5df686`. No checkout or modification of that branch occurred.
- Isolated worktree `/workspace/qshift-independent-research-v1`, branch `codex/qshift-independent-research-v1`, created from published main at the revision above.
- Runtime: Python 3.12.14, 5 CPU cores, 33 GiB RAM, approximately 60 GiB free workspace disk. No `nvidia-smi` executable or GPU observed.
- Available globally: NumPy 2.3.5 and SciPy 1.17.0. Stim, PyMatching, PyTorch, LDPC, Sinter, and NetworkX are not installed in the isolated worktree runtime. No packages have been installed. This means Stim-based experiment execution needs an isolated environment setup step before experiments.
- Read `AGENTS.md`, `RESEARCH_STATUS.md`, `EXPERIMENT_INDEX.md`, Phase 5D/5E findings and audits, and unified headroom audit summaries. No frozen test material was opened and no historical experiment was rerun.
- Current primary assessment from the inspected evidence: adaptive switching has not established superiority. Phase 5E ML and utility policies match pooled-fixed totals on the four short schedules, while hindsight is label-informed. Phase 4C Stage 2 has near-zero equal-regime primary effect (+0.00001556, reported p=0.6666) and missing calibration arrays. Existing source independently warns against scaling the current approach.
- No experiment has yet been run. No change to the previous cloud configuration draft or publication was made.
- Elapsed research time for this checkpoint was less than one hour. This is an interim checkpoint, not completion of the requested expedition.

## Next actions

1. Audit Stage E, Stage S, Stage 5, headroom feasibility, adaptive-robust latest materials, and relevant decoder implementations from source without opening any sealed evaluation material.
2. Complete a reference-checked literature survey and candidate matrix before selecting experiments.
3. Formalize the relative-reduction target and zero-failure sample bounds with reproducible code.
4. Decide whether an isolated CPU-only prototype is feasible and predeclare its development-only protocol before sampling.
5. Keep all files and generated outputs beneath this research directory. Do not access confirmatory data or change protected historical files.
- Existing-work audit found `outputs/research_direction_selection/` and `outputs/correlation_pilot/`. The pilot completed the exact 720,000-shot correlation-mode comparison proposed by the selection note, and its practical-effect gate failed. The raw pilot bundles are absent from this checkout. No repeat or post-hoc selector training was attempted.
- Found `outputs/correlation_mechanism_audit/FOLLOWUP_PROTOCOL.md`; its next experiment requires a non-approximated categorical DEM. My 6/6 deterministic Stim conversions failed because `PAULI_CHANNEL_2` requires the approximate-disjoint option. This closes that pretest gate without opening evaluation data.
- Existing `outputs/categorical_decoder_feasibility/` already exhaustively validates an exact decoder on small categorical toys and reports 2^609 full circuit assignments. I tested a distinct loopy categorical sum-product/Bethe prototype on those exact toys. It passed basic validation but performed poorly on one-qubit toy (LER 0.057354 vs exact MAP 0.002646, decision agreement 2/4) and matched exact MAP on the other toy (0.060000, agreement 4/4). The topology-dependent result is a negative feasibility result; no distance-3 sampling was run.
- Added tests `test_categorical_bp.py`; 2 tests passed. They validate outputs and invalid-input handling, not decoding performance.
- External literature endpoints: `export.arxiv.org` and `doi.org` failed with tunnel 403. Official Stim DEM format documentation at raw GitHub was accessible. Existing local reviews supply a detailed bibliography but cannot substitute for independent retrieval of inaccessible primary papers.
- Active hypothesis: direct categorical inference may need stronger structured elimination or correctly scoped local marginals; naive global parity BP is insufficient. Further circuit-scale testing is deferred until the method passes exact topology controls.
- Following the exact-DEM blocker, ran a deterministic Stim threshold scan at 0.001, 0.0018, 0.003, and 1.0. The 0.001 threshold failed on all biased cells due to a 0.00178571 event; all successful thresholds yielded identical per-condition DEM and matching graph hashes. No alternate model family exists at the tested probabilities, so no stochastic sensitivity comparison was launched.
- Derived an oracle selector ceiling from the paired pilot summary: for the existing off/on prediction pair, maximum label-aware relative reduction is 763/3,532 = 21.6% on that sample, leaving 2,769 shared failures. Recorded it as a descriptive development-sample constraint, not a population bound.
- Revisited the Bayes-risk definition as the correct logical-class ML benchmark. Full-circuit gap from PyMatching is still unknown because no validated full categorical posterior is available.

- Investigated tensor-network decoding with qecsim 1.0b9. Native planar MPS and MWPM returned valid codespace recoveries in a 100-shot/distance preflight. The exact untruncated d=5 MPS runtime projects beyond the 5-minute cap at the declared 5,000-shot count, so the full screen was stopped before sampling. Treat the small failure counts as timing-preflight artifacts only.

- New LDPC BP+LSD screen: all six distance-3 Phase 2B conditions accepted binary matrices built from the same approximate DEM used by the strong PyMatching comparator. On 5,000 original-circuit shots per condition, each tested LSD method produced 321 failures versus 138 for correlation-enabled PyMatching; all detector syndromes were reproduced. This is a bounded negative result, not a statement about other settings/distances.

- Tested fivefold-odds likelihood-ratio importance sampling for the fixed decoder under the approximate DEM surrogate. The weight estimator passed exhaustive three-event validation. Main and independent replicated screens showed lower estimated sampling error in 5–6/6 conditions (details in `rare_event_*.json`). This is a statistical-method result for the surrogate only; it does not reweight the original categorical circuit noise.

- Extended likelihood-ratio work to exact categorical `PAULI_CHANNEL_2` circuit sampling by instrumenting mutually exclusive outcomes and recording them in auxiliary flags. Synthetic checks and a fresh unmodified-circuit crosscheck validated the instrumentation and ratios. Direct and weighted LER estimates agree, but two 8-replicate blocks show the fixed global fivefold tilt is not a stable overall variance reduction (macro SD ratio 1.12, with condition ratios 0.52–1.64). This is a methodologically useful negative/qualified result; it does not support an LER improvement claim.

- Screened a forward-KL cross-entropy proposal formed from exact weighted failure-conditioned categorical marginals. On fresh validation trajectories it passed the predeclared efficiency gate in 0/6 conditions; variance was worse than or similar to global tilt, and some failure ESS values were very low. The likelihood ratios remained numerically consistent, so the negative result is proposal efficiency rather than an apparent bias.

- Analyzed same-resource X/Z memory orientation under known Pauli bias using 40k exact circuit samples per cell across two independent direct sets. Matching logical basis to the stable dominant axis yielded 5.2x (X bias) and 11.1x (Z bias) lower LER; balanced noise showed no difference. This is a code/circuit configuration result, not a decoder improvement or adaptive policy.

- Extended known-profile memory-basis alignment to d=5/9 rounds under the two biased regimes. Matched resource circuits (64 qubits/216 detectors) showed 36×–45× lower observed LER for the aligned basis, with six aligned failures per 50k cell. This supports the d3 direction but is low precision in absolute terms and is not a threshold estimate.

- Mapped the static known-bias memory-basis effect at 2:1 and 5:1 profiles using 50k exact source-circuit shots per cell. Alignment already reduced LER at 2:1 and the reduction grew at 5:1; this gives a bounded baseline for known-profile configuration, not an adaptive detector.

## Checkpoint — fixed-bond MPS screen — 2026-11-18

- Branch/worktree remain `codex/qshift-independent-research-v1` / `/workspace/qshift-independent-research-v1`. Current pending research files include `tensor_mps_truncated.py`, its preflight and full result JSON, and report updates. No publication or merge performed.
- Completed fixed chi=16 qecsim MPS vs qecsim MWPM on 5,000 paired ideal-syndrome IID depolarizing samples at p=.05 for d=3,5. MPS recorded 123 vs 206 logical failures at d3 and 30 vs 92 at d5; all recoveries valid. McNemar p values 3.49e−17 and 9.33e−12.
- Result supports a model-specific code-capacity advantage with significant latency cost (13.74 ms/sample at d5 vs 0.507 ms for Python MWPM). It is not Q-SHIFT circuit-level evidence, a threshold estimate, or a scaling law.
- Earlier candidate findings and limitations are retained. Next: establish circuit compatibility and a strong circuit-level baseline before further MPS work; if infeasible, prioritize another distinct candidate. Reproduce with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_truncated.py` from the worktree.

## Checkpoint — distance-7 basis alignment — 2026-11-18

- Current branch/worktree: `codex/qshift-independent-research-v1` / `/workspace/qshift-independent-research-v1`. New files `basis_alignment_distance7.py`, preflight and results JSON. No changes outside isolated research worktree, no publication.
- Extended known-profile X/Z memory orientation to d=7/13 rounds at p=.003, ratio 10, using exact categorical source circuits and the same approximate DEM/correlation-enabled PyMatching approach as earlier comparisons. Resources match: 118 qubits, 624 detectors, 2,184 two-qubit channel pairs.
- Fixed batch decode passed scalar agreement on all 100 preflight syndromes in each condition. Main 500k per cell completed in 34.6s. Aligned failures: X-under-X-bias 5 vs 1,009; Z-under-Z-bias 3 vs 1,227. Rate ratios .00496 and .00244, with exact conditional intervals [.00161,.01017] and [.000504,.00590]. Sparse aligned counts limit absolute-rate precision; no threshold/scaling model.
- Updated cumulative Q-SHIFT development circuit sample count to 4,914,800. No confirmatory/sealed evaluation accessed. Next: reassess if a useful unknown-bias protocol can beat the static known-profile bank using only detector data; do not use the outcome-aware basis here as an online policy.

## Checkpoint — detector-only bias policy — 2026-11-18

- Branch/worktree remain isolated at `codex/qshift-independent-research-v1` / `/workspace/qshift-independent-research-v1`; no published changes or protected data accessed.
- Trained a detector-only four-feature LDA on d3 ratio-10 X/Z source circuits. A frozen binary model generalized to ratio2/5/10 and d3/5/7. At 500 calibration shots, direction accuracy at ratio2 was 94.9%, 99.3%, and 99.35%, respectively; ratio5/10 were 100% on the tested windows. The separate balanced-vs-biased classifier struggled at moderate ratios, so do not conflate direction with magnitude detection.
- Direct d3 independent-stream policy screen at p=.003 used 500 detector calibration shots and 100 logical shots per memory basis per calibration window. Equal-profile policy LER at ratios2/5/10 was .00405/.00198/.001165 versus fixed-Z .004855/.00416/.00412, relative reductions 16.6/52.4/71.7%. Stratified window-bootstrap intervals for policy-minus-fixed Z were all below zero.
- A first pass inverted classifier score sign, was labeled invalid and preserved; corrected code asserts training-mean polarity and uses the same predeclared seeds. The same random streams were sampled again to fix the wiring defect; they are not counted as independent data.
- This was a promising synthetic adaptation result at that checkpoint, not hardware, drift, model-mismatch, or confirmatory evidence. The planned stable-direction total-rate-drift challenge was subsequently completed and is recorded below; later entries supersede this checkpoint's cumulative sample count and next-action note. qecsim ideal-syndrome runs are counted separately.

## Checkpoint — total-rate drift — 2026-11-18

- Frozen detector-only basis selector evaluated with p=.003 calibration and p=.006 gate/measurement error in independent logical runs; bias direction remained stable. A deterministic conversion check required DEM approximation threshold .004 (max local event probability .003571); .0018 failed before shots. The same .004 threshold was used for all arms.
- Equal-prior LER reductions versus static Z at ratios 2/5/10 were 12.2/50.6/71.0%, with 5,000-window-bootstrap intervals below zero. This is synthetic model robustness only, not drift in X/Z direction.
- Unique development circuit sample total 27,377,800 including preflights; repeated score-sign fix used identical seeds and is excluded from unique count. No confirmatory data accessed. Next: evaluate reconfiguration under actual X↔Z profile transitions and compare calibration interval/resource costs against a periodically recalibrated fixed basis.

## Checkpoint — calibration-cost frontier — 2026-11-18

- Re-scored existing direct-policy seed streams at calibration prefixes 25 and 100 in addition to the primary 500; no new random streams or model fitting. Results are exploratory and correlated because the windows are nested.
- At ratios 2/5/10, the 25/100/500-shot per 100-logical-shot LER reductions versus static Z were 5.1/11.6/16.6%, 27.8/49.6/52.4%, and 57.5/71.2/71.7%. Ratio2/25-shot interval includes zero. This suggests the calibration cost/benefit depends strongly on bias magnitude.
- No sample-count increase. Future evaluation should predeclare one calibration budget and an equal total-resource objective; do not choose a confirmatory budget from this rescore.

## Checkpoint — calibration amortization

- Computed a resource break-even for correct logical outputs per total circuit shot under an explicit assumption that 500 calibration shots are unusable and cost the same as logical memory shots. The minimum stationary horizon from observed d3 rates is roughly 618k/228k/169k logical shots per calibration at ratios 2/5/10.
- This differs from per-logical-shot LER, which improves in the direct experiments, and makes the operational objective explicit. It is an uncertain plug-in calculation, not empirical evidence of noise stability. No new samples generated.

## Checkpoint — same-observable decoder selection

- Frozen profile classifier selected between profile-conditioned correlation-enabled PyMatching graphs on one fixed Z-memory circuit and observable. Static pooled model used elementwise-averaged X/Z channel probabilities. Correct profile was selected in all 2,000 calibration windows.
- Test errors: 775 selected-bank vs 779 pooled in 200,000 source-circuit shots; 95% paired window-bootstrap interval includes zero. Fixed X graph also 779; fixed Z 806; oracle 775. Accurate model labels therefore added no statistically resolved decoder gain in this condition.
- This also narrows interpretation of basis-alignment findings: X/Z memory evaluate different logical observables; large reductions are task-specific and do not establish arbitrary-state memory improvement. New total unique development shots: 28,581,800. Next candidate: robust same-observable model selection at multiple profiles or stop decoder-bank line if no distinct mechanism; keep fixed resource/task objective.

## Checkpoint — XZZX local-H co-design

- Fixed checkerboard H transform of the CSS source circuit was tested at d=3,5, p=.003, bias ratio10, both X/Z bias. Correct H-CX-H conjugation and transformed resets/readout passed deterministic DEM checks. A first invalid CNOT rewrite was stopped before sampling and not counted.
- Added single-qubit H gates/noise to realize the compiled transform: H/noise targets rose 1.5x at d3 and 1.67x at d5; two-qubit pairs and core geometry stayed matched. On 500k samples/cell, transformed LER was worse in all four settings (ratios 1.33, 6.65, 1.49, 19.83 vs CSS). Negative result applies to this gate-level implementation/noise model, not to an optimized hardware-native schedule.
- Unique development samples total 32,589,800 including preflights. No confirmatory evaluation accessed. Next: only pursue XZZX with a concrete native-gate schedule that controls the one-qubit overhead; otherwise move to another unresolved family.

## Checkpoint — alternating-profile resource replay

- Reused only previously saved classifier-confusion and independent per-window logical-failure summaries; no new stochastic samples. Tested deterministic equal-duration X↔Z profile alternation at dwell periods 100, 1,000, 10,000, and 100,000 logical shots, 25/100/500 calibration shots, and four re-estimation intervals (144 schedules, d=3, ratios 2/5/10).
- With calibration shots charged as unusable circuit resources, no tested schedule beat the best static basis through 10k-shot dwell. At 100k dwell, the best plug-in throughput ratio to static was 0.999857, 1.001041, and 1.002052 at ratios 2, 5, and 10. This is a scenario projection with point estimates, not an empirical change-point detector or uncertainty-bounded result.
- No Q-SHIFT circuit-shot increase; cumulative unique development samples remain 32,589,800. No confirmatory data accessed. Next: examine exact native-categorical inference via width-bounded elimination and stop before scaling if width grows too quickly.

## Checkpoint — exact categorical variable elimination

- The corrected log-domain elimination engine retained each local error as a categorical variable. Exhaustive comparison covered every syndrome/logical target on a one-location tree and two cyclic/repetition toys; max joint/posterior discrepancy 2.8e-16, with exact MAP risk and decisions. Forced Stim Pauli outcomes independently reproduced the joint masses for both circuit-backed toys.
- Topology stress on sparse pairwise grids reached 11x11 (121 binary variables, 220 checks) at induced width 18 and 524,288 intermediate table entries under a hard 1,000,000-entry cap; one target took 0.38 s. Growth was sharp between 7x7, 9x9, and 11x11. This is not a Phase 2B factor graph, and only one target per grid was evaluated beyond 2x2.
- Floating-point tie and factor-axis ordering bugs were found by exact controls and fixed before final metrics. No Q-SHIFT stochastic or confirmatory samples generated.
- Next: derive exact event-to-detector/observable signatures for a bounded Phase 2B fragment and perform an induced-width-only preflight before any inference run.

## Checkpoint — native-categorical Phase 2B fragment

- A deterministic fragment of the source d=3 five-round Z-memory / X-biased ratio10 circuit now maps the first three pairs of the final PAULI_CHANNEL_2 layer into three 16-state categorical variables. All other stochastic locations were suppressed to identity.
- The initial map was invalid: Stim's detector sampler subtracts each forced circuit's own deterministic reference. This produced false zero effects. The corrected raw-measurement extraction shares the noiseless circuit's detector/observable reference, then passed 256 combined-fault XOR cases and exact enumeration of all 4,096 assignments. Variable elimination matched all 64 reachable syndrome/logical masses to 2.22e-16; width2 and max factor512.
- No stochastic circuit data were generated. This is an exact local slice only, not a decoder result. Next: width-only preflight on all six pair locations in the same final layer.

## Checkpoint — exact six-location Phase 2B layer

- The scope-only preflight for the whole final PAULI_CHANNEL_2 layer predicted induced width4/max factor131,072, under the fixed 1M cap.
- Exact XOR-convolution of all 16^6 probability assignments produced 1,024 reachable syndromes. Variable elimination agreed with the independent reference to max joint mass error1.11e-16 and posterior error2.47e-15; 512 forced combined Pauli circuits verified XOR signatures. All six native categorical events and source probabilities were retained.
- One isolated-layer MAP LER was 1.0572e-5, not a full-circuit error estimate because every other fault was suppressed. Runtime 95s; no stochastic Q-SHIFT data generated.
- Next: preflight two adjacent final-round channel layers (12 categorical locations) using factor scopes only.

## Checkpoint — two-layer dense-elimination stop

- Scope-only mapping of the last two adjacent channel instructions built 12 native 16-state locations over 10 touched detectors. Weighted min-fill predicted width9 and max table 17,179,869,184 entries.
- Seven alternate orderings (weighted min-product, min-fill, min-degree, natural/reverse, and two location/carry interleavings) were tied or worse; best remained 17.2B. The 1M-entry cap failed before inference or any dense allocation. This stops the current dense VE route at one isolated layer; it does not bound specialized tensor contractions.
- No stochastic circuit samples generated. Next: move to another family rather than continue order tuning.
