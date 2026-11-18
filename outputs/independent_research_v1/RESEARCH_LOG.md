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

## Checkpoint — distance-3 syndrome-round resource frontier (2026-11-18)

- Compared 3/5/7/9 extraction rounds at d3, p=.003, 10:1 bias, across both profiles and X/Z memory bases. The first preflight exposed a hard-coded 5-round detector-count assertion in the source helper and stopped before sampling. The scaled Stim builder was used after inspection; all four 5-round circuits were byte-identical to the source versions.
- The corrected preflight passed; 3.2M main circuit shots completed. Per-attempt LER rose monotonically with round count in every cell, while two-qubit channel opportunities rose 72→120→168→216. Source five-round configuration remains one point on this fixed-distance resource frontier; this does not imply fewer rounds improve equal-duration storage because duration shrinks with round count.
- Full preflight/results/protocol, code, and report references are saved under `outputs/independent_research_v1/round_count_frontier*`. Cumulative Q-SHIFT development shots now 35,791,400; no confirmatory data accessed.
- Next: examine circuit time and idle-noise semantics before defining any equal-duration comparison. If the source lacks an evidence-backed schedule/noise model, reject this comparison design and choose another question rather than inventing padding semantics.

## Checkpoint — bias-strength decoder robustness (2026-11-18)

- Source audit found no explicit idle-time noise model; equal-time round padding was not attempted.
- Preflight and 1.2M-shot development run compared matching models built at assumed X/Z bias ratios 2/5/10 on identical detections from actual ratios 2/5/10 and both bases. Preflight passed; geometry matched within actual ratio. Macro LER was .005522/.005216/.005022 for assumed 2/5/10. Assumed10 beat assumed5 by paired delta -.000194 (conditional 95% interval [-.000242,-.000146]) and the per-condition correctly specified reference by -.000273 ([-.000323,-.000222]).
- Interpretation is a misspecification-robustness signal specific to this approximate DEM plus correlation-enabled matching implementation. The ratio10 winner is selected on the same finite grid and is exploratory; an independent, frozen ratio10-vs-ratio5 validation is needed before any deployment recommendation. No confirmatory data accessed. Cumulative Q-SHIFT development samples: 36,992,600.
- Reproduction: `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_strength_robustness.py --preflight` followed by the same command without `--preflight`.

## Checkpoint — frozen bias-strength validation (2026-11-18)

- Fresh 100,000-shot/cell test at actual ratios 2/3.5/5/10 compared only the frozen assumed-ratio5 and ratio10 matchers on identical detector shots (16 cells). Preflight passed and the main run took 2.5s.
- Macro LER .0052244 vs .0050025; paired ratio10-minus-ratio5 contrast -.0002219, conditional MC interval [-.0002626,-.0001812]. Contrast was negative within each actual strength on the equal-weight average; at actual ratio2 only 2/4 profile/basis cells favored10, while all cells at ratios5 and10 favored10.
- This independently verifies the fixed-grid development signal and includes a new interpolation strength, with finite d3/stationary-channel scope. No confirmatory data accessed; cumulative Q-SHIFT development samples 38,594,200.
- Reproduce with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_strength_frozen_validation.py --preflight` then without `--preflight`.

## Checkpoint — distance-5 frozen bias-strength comparison (2026-11-18)

- Compared assumed-ratio5/10 matching on 16 fresh d5 conditions (actual ratios2/3.5/5/10, both profiles/bases), 100k shots/cell. The explicit custom ratio10 circuits matched the existing scaled builder; 216 detectors/one observable; preflight passed and projected 92s; main completed in 23s.
- Macro LER .0019131 for ratio5 and .0019331 for ratio10; paired ratio10-minus-ratio5 +.0000200 (conditional MC 95% interval [-.0000060,+.0000460]). No clear d5 difference; do not claim equivalence. The d3 ranking did not reproduce as a clear size-independent effect.
- No confirmatory data accessed; cumulative Q-SHIFT development samples 40,195,800. Full report and per-cell output are saved in the d5 validation files.
- Next: analyze graph/edge-weight shifts across assumed ratio and distance before considering more sampling.

## Checkpoint — deterministic matching-graph audit (2026-11-18)

- Audited eight ratio5-vs-ratio10 model pairs across d3/d5, both profiles, and both memory bases. Ratio10 source/scaled builder checks passed. No circuit shots generated.
- All pairs had exact same topology and logical-fault labels: 142 edges at d3 and 950 at d5. Mean absolute edge-weight delta .238/.249, median .131/.128, and median absolute edge-error-probability delta .000353/.000353 at d3/d5. Ratio10 raised 74.6%/70.3% of common weights.
- This rules out edge topology changes as the simple explanation; causal syndrome interaction remains open, and raw earlier shot records are unavailable. No fundamental inference from this deterministic audit.
- Reproduce with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_graph_mechanism.py`.

## Checkpoint — paired decoder-decision seed replay (2026-11-18)

- Replayed prior d3/d5 seeds exactly and matched all 64 archived per-cell error counts. No new independent samples were generated.
- d3 model predictions differed on 1,105/1.6M shots; ratio10 fixed 730 errors and introduced 375 (66.1% correct among disagreements, Wilson 95% 63.2–68.8%). d5 disagreed on 452/1.6M; ratio10 fixed 210 and introduced 242 (46.5%, 41.9–51.1%). This decomposes observed net LER changes, but does not identify the syndrome features/mechanism.
- Cumulative unique development samples remain 40,195,800. Full cell and aggregate counts saved to `bias_strength_decision_replay_results.json`; reproduction uses `bias_strength_decision_replay.py`.

### Same-seed syndrome-weight strata (descriptive)

- Added predeclared detector-click bins to the existing exact-seed replay without changing seeds. At d3, 1,022/1,105 model disagreements had 3–8 clicks and ratio10 was right on 678/1,022; only 29 disagreements had 9+ clicks and ratio10 lost 18 vs fixed 11. At d5, 363/452 disagreements were 9+ and ratio10 won only 168 vs 195. This is consistent with a changed disagreement population, not a causal finding; d3/d5 detector counts differ and bins are unnormalized.
- No new unique Q-SHIFT samples; aggregate/condition/bin data all in `bias_strength_decision_replay_results.json`.

### Sample-specific two-output selector ceiling

- From the same archived-seed replay, an oracle selecting the correct output for every ratio5/ratio10 disagreement still leaves 7,629 d3 and 2,851 d5 both-wrong events. Relative to the better fixed decoder on each sample, the observed maximum error reduction is 4.69% at d3 and 6.86% at d5. This finite-sample ceiling is not a population bound, but it deprioritizes ratio-only selection as a route to orders-of-magnitude improvement.

## Checkpoint — two-qubit fault composition screen (2026-11-18)

- Instrumented each PAULI_CHANNEL_2 event into categorical E/ELSE outcomes with private flags, leaving 1Q/measurement channels unchanged. The four-cell 5k-per-arm preflight had max independent LER difference .85 SD; main 100k/cell took 16.8s.
- For actual ratio10 high-LER mismatched-basis cells, shared wrong outcomes carried mean 1.94 pair faults/shot at d3 and4.67 at d5 versus .35/2.14 among both-correct. XX/ZZ was enriched 5.7–5.8x/2.28x per shot; decoder ratio10 fixed/broke 91/67 events at d3 and37/41 at d5.
- Limitation: only two cells per distance and pair faults only; this is not a lower bound on correctable LER. Cumulative simulated Q-SHIFT samples 40,635,800. See the shared-failure artifacts and protocol.

## Checkpoint — sparse exact categorical inference across three layers (2026-11-18)

- Exact sparse signature aggregation solved the final two layers despite dense VE's 17.2B entry estimate: 12 categorical locations/10 detectors, 2,048 states, direct DP versus six-plus-six convolution max difference1.33e-15, 512 Stim composition checks, 4.85s.
- Extended the exact slice to 18 locations/12 detectors. Sparse DP and Walsh XOR convolution agreed over 8,192 states at1.22e-15; 512 forced-fault cases passed; runtime4.63s. The isolated fragment MAP risk is not full-circuit LER.
- An incorrect Walsh normalization was detected by sparse-DP comparison and fixed before final result. No stochastic circuit shots were generated. Sparse complexity scales exponentially with touched detector support; next do only a fourth-layer scope preflight.

### Four-layer sparse exact pass

- Extended preflight to the final four PAULI_CHANNEL_2 layers (24 locations). Support remained 12 detector bits. Sparse DP/Walsh joint masses agreed to2.78e-15 over 8,192 states, normalization passed, and 512 forced-fault tests matched. Runtime3.55s; no samples. Isolated MAP risk is not full-circuit LER.
- Continue only to a fifth-layer resource preflight next.

## Checkpoint — fifth-layer sparse preflight stop (2026-11-18)

- Forced-outcome mapping of the final five channel layers found 30 locations and 18 touched detectors. Upper bound 524,288 joint states; transition bound 251.66M exceeded the fixed 100M cap. Stopped before inference as planned; no samples generated.
- This limits the current sparse-DP protocol at four layers; it is not a lower bound on other representations. Artifact `categorical_five_layer_preflight.json` preserves signatures and resource estimates.

## Checkpoint — vectorized five-layer signature inference

- The five-layer Python dictionary route exceeded its declared transition budget, but a different NumPy vectorized XOR-kernel route with separate predeclared caps passed. DP/Walsh mass error3.55e-15 over524,288 states; 512 forced-fault checks passed; ~23MiB estimate and5.92s.
- This is exact five-layer fragment posterior evidence, not full-circuit decoding. No samples. The earlier stop is specific to the slow dictionary implementation. Next: preflight the six-layer support ceiling at the same 1M state cap.

## Checkpoint — exact six-layer coalesced kernel

- Exact per-location signature coalescing reduced 576 raw outcome branches to 296 distinct XOR signatures across 36 fault locations. Vectorized DP and Walsh-Hadamard convolution agreed to2.32e-16 across524,288 states; 512 forced combined errors matched Stim; runtime6.10s.
- Six-layer slice MAP risk .000866 is not full-circuit LER; no samples. The algebraic reduction preserves all probability mass. Next: fixed-cap seventh-layer support preflight.

## Checkpoint — seventh-layer state-cap stop

- Final seven layers map to 42 locations/20 touched detectors; joint signature bound 2,097,152 exceeds fixed1M states, and raw transition estimate is1.409B. No probability expansion or stochastic sampling ran.
- This bounds current coalesced dense-signature implementation at six final layers, not all exact methods. Artifact `categorical_seven_layer_preflight.json` preserves the signature map and cap result.


## Checkpoint — exact seven-layer parity-state inference (2026-11-18)

- Investigated the representation boundary after joint seven-layer signature inference exceeded 1M states. A new exact identity propagates syndrome mass and signed logical parity over 2^m states rather than 2^(m+1).
- Declared fresh fixed caps and validation before inference. Seven-layer tail ran over 1,048,576 syndrome states (42 locations, 20 detectors), with 788.5M updates and 1.804B Walsh ops in 14.51s. P/Z independent Walsh errors <8e-16; six-layer joint-reference max error <6e-16; all 512 forced Stim checks passed.
- Exact isolated-tail MAP risk 0.0010409337; not full-circuit LER. No stochastic shots. Result establishes a bounded exact representation, not a decoder gain.
- Next: move to a distinct research question; do not increase caps or infer whole-circuit behavior from this fragment.


## Checkpoint — pair-cluster categorical importance sampling (2026-11-18)

- Formed a fixed physically local cluster proposal after independent per-location cross-entropy failed. Pairing adjacent channel events within each native PAULI_CHANNEL_2 instruction gives 60 two-location clusters/condition, each with 256 joint outcomes.
- Synthetic channel instrumentation observed all categories and reproduced the expected data Pauli for every flag with zero mismatches. The actual circuit instrument had 15,987 instructions; the preregistered preflight projected 45.2s, and the full development screen took 60.3s.
- With six separate 100k training streams and independent three-arm 20k validations, the variance advancement gate passed 0/6. Cluster max absolute log weights were 17.84–23.67; biased-condition training failure ESS 113–129; mean weighted failure categories per cluster 20–37. All six estimates remained within 3 combined SE of both direct and global-tilt comparators.
- Negative finding is specific to this grouping/shrinkage/budget. Do not alter it based on validation or claim that all structured rare-event methods fail. Q-SHIFT samples +962,400; no confirmatory/sealed data.
- Next: select a different research family, rather than more proposal tuning on the same validation pool.


## Checkpoint — native-XCX XZZX transform (2026-11-18)

- Followed up the prior H-overhead XZZX rejection by compiling the exact control-H/CX conjugation as Stim's native XCX and target-H conjugation as CZ. Fixed physical assumption: CX/XCX/CZ equal duration and source two-qubit noise.
- Preflight passed three tableau identities, noiseless determinism, DEM generation, unchanged p2 targets/probabilities, unchanged qubit/detector/round/interaction resources and added H targets=0. Projected 50.4s; main run took 11.8s.
- With 500k shots/cell, XZZX/CSS rate ratios for X-bias were 0.662 (d3) and 0.376 (d5); for Z-bias they were 3.86 and 11.24. Strong orientation-by-bias interaction, not a uniform code gain.
- No hardware claim because native-gate noise equivalence is assumed. Q-SHIFT samples +4,000,800 including preflight. Next: a single complementary checkerboard orientation test is the discriminating follow-up.


## Checkpoint — one complementary XZZX orientation (2026-11-18)

- After native-XCX results showed an X/Z bias interaction, tested exactly one complementary checkerboard, on Z-biased ratio10 d3/d5 only, with CSS and the original orientation as references. Predeclared fresh streams; no pattern sweep.
- 500k shots/arm/distance; preflight passed resource, noise, tableau, DEM, and noiseless-determinism checks. Complement improved over original by 13.7%/21.5% but remained 3.04x/6.16x worse than CSS.
- Decision: the tested checkerboard family is not a competitive universal code option under this model. Stop this family here. Native entangler equal-noise remains assumed.
- Q-SHIFT shot count +3,000,600.


## Checkpoint — local-map versus pooled matching under spatial hotspots (2026-11-18)

- Built east-/west-hot synthetic two-qubit maps with 1.5x/.5x local factors and exactly preserved mean p=.003. Local graph had the exact map; pooled graph used the mean model. Both decoded identical detector/observable shots.
- A no-shot DEM preflight first exposed the .0018 threshold issue; after predeclaring .003 uniformly across both decoders, preflight passed and the 200k/profile run completed.
- East-hot paired local-minus-pooled LER +.000035 (95% CI [-.000143,.000213]); west-hot -.000170 ([-.000336,-.000004]); equal-weight macro relative gain .93%, below 10%. No spatial selector follow-up under this model.
- Synthetic robustness evidence only; not hardware calibrated. +400,200 Q-SHIFT samples; no confirmatory/sealed data touched.


## Checkpoint — distance-9 basis alignment (2026-11-18)

- Conducted one fixed d9/17-round extension for X-biased ratio10, Z-memory task: aligned X-memory vs mismatched Z-memory, 500k shots each. Resource, noiseless determinism, DEM, and scalar/batch checks passed. Main runtime 47.9s.
- Observed 1 vs 408 failures; ratio .00245 with exact conditional 95% interval [.0000619,.01373]. This is compatible with both large and modest gains and does not establish 10,000-fold reduction or a scaling law. The fixed protocol prohibited extending after outcome inspection.
- Q-SHIFT samples +1,000,200; no confirmatory/sealed data accessed.


## Checkpoint — biased code-capacity MPS and independent replication (2026-11-18)

- Tested established qecsim chi=16 planar MPS under 10:1:1 X-biased code-capacity noise vs its bias-aware MWPM decoder. 5k paired samples at d3/d5; both recovery-valid.
- Fresh independent-seed repeat under same protocol. MPS direction favored at both distances in both roots; d5 intervals below zero in both, d3 interval crossed zero in replication. d5 MPS latency ~31x MWPM.
- Positive result is restricted to perfect-syndrome code capacity. No Q-SHIFT circuit shots, no confirmatory data. A spacetime tensor network is required for an information-fair circuit comparison.


## Checkpoint — averaged MPS mode ablation (2026-11-18)

- Tested qecsim's documented average row/column mode against fixed column mode at chi16 on a fresh 5k/d biased code-capacity stream. Preflight projection 179.5s, main 239.9s.
- Both modes gave exactly identical logical outputs on every sample at d3/d5; mode a doubled d5 latency. No ablation benefit. This does not address Q-SHIFT's missing spacetime support.


## Checkpoint — exact seven-layer tensor-train compressibility (2026-11-18)

- Audited whether the exact P/Z posterior can fit a low-rank MPS in the frozen temporal detector order. SVD across every binary cut completed in 6.44s with no sampling.
- Maximum TT rank 91 at 1e-10 relative error; rank 30 at 1e-6. Fixed exact-fidelity rank-64 gate failed. Do not implement the predeclared exact-fidelity prototype or adjust tolerances post hoc.
- This is not a bound for other orderings or a full circuit. Next, switch families/approaches.


## Statistical feasibility note — d9 relative target (2026-11-18)

- No new sampling. From 408/500k mismatched d9 errors, computed the 1e-4 relative target and exact IID candidate sample counts. At the point baseline, target LER=8.16e-8: 36.7M zero-failure shots or 58.1M shots allowing one failure to bound the rate. Conservative baseline lower endpoint needs 40.6M / 64.2M. These omit multiple conditions and clustered roots.
- This explains why the 500k aligned sample cannot establish the aspirational ratio; result artifact `d9_relative_target_sample_budget.json`.


### All-location fault composition screen

## All-location fault composition under ratio-sensitive decoding

The preflight passed synthetic flags for all 15 two-qubit Paulis, all three one-qubit Paulis, and explicit X/Z error events (zero data/flag mismatches). Both d3 conditions had 120 two-qubit pairs and 40 one-qubit locations; explicit measurement targets were 49 for Z-memory/X-biased and 49 total for X-memory/Z-biased. Source and instrumented samples had unchanged 40-detector/one-observable layout, and failure-rate differences were below 1.1 combined standard errors. The 200,000-shot main screen took 3.94 seconds.

At 100,000 shots/condition, ratio-5/ratio-10 models failed on 753/752 Z-memory X-biased shots (61 prediction disagreements) and 769/766 X-memory Z-biased shots (95 disagreements). The both-wrong groups contained 722 and 720 shots; ratio-10-fixes-ratio-5 groups contained 31 and 49, while ratio-10-breaks-ratio-5 contained 30 and 46. In both conditions, mean tracked two-qubit faults were about 0.349 per both-correct shot and 1.87 per both-wrong shot. In the biased Pauli outcome counts, XX was most frequent in the X-biased Z-memory both-wrong group (794 events), while ZZ was most frequent in the Z-biased X-memory both-wrong group (800). One-qubit and explicit measurement-fault counts also differed across outcome groups; see the JSON for full counts.

The decoder-disagreement groups are small, particularly the 30–49-shot fix/break groups. These are conditional fault associations from one fixed development stream, not causal attribution, evidence that one fault channel caused decoding errors, or a hardware noise claim. The new instrumentation extends the earlier two-qubit-only report; it does not change the prior conclusion that raw fault burden alone cannot explain decoder behavior. No sealed or confirmatory data were accessed.


## Secondary analysis: basis-alignment distance trend — 2026-11-18

The independent fixed-profile records show declining aligned/mismatched point ratios from d3 through d9, but aligned counts fall to 1/500k at d9. A descriptive Poisson fit suggests stronger aligned suppression; uncertainty is sparse and distance co-varies with round count. The 1e-4 relative target remains 24.5-fold below the d9 point ratio. No additional sampling. Next inspect the fair baseline used by native-XCX XZZX code comparisons.


## XZZX comparator correction — 2026-11-18

The XZZX generator explicitly builds both CSS and XZZX as Z-memory. Reused X-aligned CSS streams show lower LER at matched counted resources: native XZZX ratios 3.57 at d3, 13.48 at d5. This downgrades XZZX from a practical X-bias recommendation while preserving the conditional finding that it improves on mismatched CSS Z-memory. No samples generated.


## XZZX by memory-basis factorial — 2026-11-18

A fresh d5 2x2 screen found that native XZZX lowered LER versus mismatched CSS-Z (XZZX-Z/CSS-Z .363) but was worse than CSS-X in either XZZX memory basis (XZZX-X/CSS-X 7.65). The CSS X/Z ratio was .0427. Equal counted resources were verified; result remains conditional on identical CX/XCX/CZ physical errors and durations.


A post-hoc equal-weight X/Z memory-task average in the d5 factorial favors XZZX by 33.9% (rate ratio .661, interval .615–.710), while CSS-X is the strongest basis-specific cell. This might be useful only for a workload needing both separate memory tests; it is not arbitrary-state performance and requires prospective weighting before replication.


## Independent replication of basis-mix tradeoff — 2026-11-18

Fresh d5 streams replicated the equal-weight separate X/Z task average in favor of XZZX (.662 rate ratio), while CSS-X remained much stronger for known X-memory tasks. This supports a conditional code-selection tradeoff, not an arbitrary logical-qubit or hardware claim. A third distance should be pursued only if the balanced-basis workload is a real research target and can be protocolized without fitting to d5.


The XZZX/CSS equal-weight separate-memory tradeoff is distance-sensitive in new independent screens: CSS led at d3, XZZX led at d5/d7, with the ratio falling to .279 at d7. XZZX consistently lost to aligned CSS-X for the known X-memory task. This is not an arbitrary-state or threshold claim. Continue to d9 as a bounded falsification/scaling challenge.


The d9 challenge extends the balanced separate-memory XZZX/CSS benefit to a rate ratio .107, dominated by Z-memory suppression. CSS-X remains lower than XZZX-X. This is 89%, not 99.99%, and does not measure arbitrary logical states or account for actual native-gate calibration. A d11 preflight is the next falsification step if it remains within the declared runtime cap.


The d11 balanced X/Z task result continues the XZZX/CSS trend but with a broad interval and only 3 XZZX-Z versus 67 CSS-Z failures; both X-basis cells are zero-failure. The point rate ratio .0448 is far from 1e-4. Since runtime was 282s, stop this fixed-size sweep and move to another research family rather than adding a marginal d13 run.


A d11 exact rare-event budget shows the current balanced-memory XZZX point is ~448x above the 1e-4 relative target. Even if a future candidate hit the target, an optimistic one-sided IID 95% bound requires ~447M zero-failure shots. Do not scale sampling without a rate-lowering hypothesis.


The d13 balanced-memory factorial cannot fit the fixed runtime cap: preflight projects 455s. Preserve this as a scalability constraint and stop the sweep at d11 unless a new, independently justified computational method is designed.


The 2:1 d7 robustness point adds a mild-bias endpoint. Equal-weight separate-memory XZZX/CSS ratios at bias 2/5/10 are .853/.608/.279; at 2:1 the CI barely excludes 1 and XZZX-X is worse. The pattern is bias-dependent, not universal. Do not turn these three selected strengths into a fitted crossover without a defined physical workload.


The 5:1 d7 screen supports some robustness below 10:1, with equal-mix XZZX/CSS=.608. At 2:1 the gain is only .853, and XZZX-X is worse than CSS-X at every tested bias. Do not claim XZZX as a uniform biased-noise replacement.

## Checkpoint — d13 packed-path stop and Fusion Blossom feasibility (2026-11-18)

- Verified requested checkpoint `507611c` exists; resumed branch remains `codex/qshift-independent-research-v1`. Latest pre-checkpoint head was `0778d5f`.
- Bit-packed d13 preflight: 200,000 unique samples, exact Stim sampler/decoder output agreement, 358.13s projected main vs 300s cap; stopped without main data.
- Fusion Blossom 0.2.13 custom graph interface: 1,000 fresh d3 samples, zero output mismatches vs ordinary PyMatching MWPM, but serial Python throughput only 6.5–15.3% of PyMatching on these cases. It is not a justified route to the d13 runtime goal.
- New cumulative unique Q-SHIFT development samples: 66,781,000. No confirmatory/sealed data accessed. Exact artifact commands are in `REPRODUCE.md`; no external push or publish.
- Active next question: can a graph-informed detector-bit ordering lower the exact seven-layer P/Z tensor-train ranks below the failed natural-order rank-64 gate? This uses the already validated exact posterior and creates no new stochastic samples. Stop if the fixed ordering heuristic is not clearly specified before rank analysis.

## Checkpoint — exact-tail min-fill ordering challenge (2026-11-18)

- Reconstructed the hash-verified exact 20-detector P/Z posterior and applied the predeclared deterministic min-fill detector order; no stochastic samples were generated.
- The min-fill ordering reached maximum relative-Frobenius ranks 151 (P) and 150 (Z) at 1e-10, worse than natural order's rank 91. It fails the fixed rank-64 gate; no MPS prototype or alternative ordering was selected post hoc.
- Runtime 6.35s. Finding is specific to this graph and seven-layer tail. Next: switch away from ordering optimization and investigate a distinct robustness/adaptation candidate using existing methods and data, with a new prospective protocol.

## Checkpoint — sequential profile calibration and stable-dwell challenge (2026-11-18)

- Completed frozen SPRT training/validation, independent validation replication, matched fixed-budget likelihood checks, and direct d3 LER evaluation. The detector-only rule reduces selection errors at about the same calibration cost as 25 fixed shots in this two-profile simulator.
- Direct LER improvement is substantial versus static Z for equal separate memory tasks, but per-100-attempt calibration costs erase throughput. A 100k stable-profile reuse bootstrap projects a modest positive throughput gain; 10k direct grouped replay is inconclusive.
- X/Z gate family readout/fault composition differs; no hardware transfer or arbitrary-state claim.
- Current branch checkpoint is recorded after files are committed below. Next open question: stress the frozen detector-only policy with a withheld noise-composition shift or profile change, where Gaussian SPRT assumptions may fail. Use a new preregistered mismatch/false-switch protocol and do not infer robustness from the stable-profile projection.

## Checkpoint — sequential calibration misspecification challenge (2026-11-18)

- Frozen nominal Gaussian SPRT failed a targeted measurement-noise composition shift; fresh equal-variance SPRT did not recover <=5% profile error. This rejects the current sequential likelihood model as robust to the tested shift.
- Fixed 100-shot LDA was better in the shifted Z-profile sample, but its exact upper interval still exceeds the 5% target. No logical LER claim from the shifted stream.
- Current committed checkpoint before this challenge: `2b7c9f6` on `codex/qshift-independent-research-v1`; uncommitted robustness artifacts will be saved in the next checkpoint.
- Next: investigate actual piecewise profile changes with a frozen change-detection rule, using no oracle labels and explicit false-switch/detection-delay metrics. Do not reuse stable-profile utility as evidence of drift robustness.

## Checkpoint — CUSUM change-detection failure (2026-11-18)

- At branch checkpoint `05ca401`, started a detector-only change-point challenge. The CUSUM found all simulated switches quickly but false-switched frequently under stable controls. This failure is now committed with exact seeds and protocols.
- This rules out the nominal Gaussian likelihood CUSUM at its fixed threshold. No evidence supports mid-run profile adaptation from this prototype.
- Next open direction: evaluate minimum-fault-weight logical failure mechanisms / error-floor structure from the current Stim circuits and decoders, using deterministic development-only analysis, or return to a distinct decoding family if the existing tools cannot make this measurable.

## Error-floor feasibility checkpoint (2026-11-18)

- The first exact circuit-pattern lower bound validated physically, but was many orders below observed LER. It does not prove or disprove 10,000-fold potential. The single-path approach is not useful without counting an enormous family of degenerate logical mechanisms.
- Current branch before this deterministic analysis: `0af694c`; no samples or tree modifications to protected work.
- Next productive option: inspect whether the existing exact categorical and MPS tools support tractable error-family multiplicity estimates on a bounded circuit fragment; if not, move to a different candidate and record the gap rather than expanding distance blindly.


## Checkpoint — temporally heterogeneous gate-rate map (2026-11-18)

- Branch: `codex/qshift-independent-research-v1`; prior verified checkpoint `c889c92`. New versioned experiment directory: `outputs/independent_research_v2/`.
- Hypothesis tested: if a known per-round two-qubit rate map helps beyond its stationary average, round-aware decoding could merit later causal calibration.
- Exact profile matching gave modest, statistically supported gains on two reversed profiles: 2.84% equal-weight macro LER reduction for 200k paired shots/profile, at 1.02–1.04x decode time. It failed the fixed 10% advancement gate and supplies no online adaptation evidence.
- Main/preflight samples: 400,000/400; cumulative unique development samples: 83,223,400. No sealed/confirmatory data.
- Current active direction: identify a materially different, evidence-backed decoder or code-design mechanism; do not expand the tested temporal rate factors.
- Resume command: `cd /workspace/qshift-independent-research-v1 && MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/temporal_rate_hotspot.py`.
