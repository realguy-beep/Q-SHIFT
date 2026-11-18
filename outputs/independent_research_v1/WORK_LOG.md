# Work log

## 2026-11-18 — resumed research

- Resumed the existing worktree and verified branch `codex/qshift-independent-research-v1`, checkpoint commit `507611c`, clean status, and installed Python 3.12.14.
- Installed Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.5, SciPy 1.18.1, and NetworkX 3.7 into the worktree-local ignored `.venv`. This environment is isolated from the original checkout and Claude's branch. No GPU was detected.
- Reviewed the existing planned correlation pilot and discovered its seed block `93000001...` collides with historical Q-SHIFT allocations. Then found the separate `outputs/correlation_pilot/` already contains a completed and independently audited 720,000-shot development pilot. Avoided rerunning it.
- Reviewed the existing correlation-mechanism audit. Its proposed next step requires a non-approximated DEM for categorical `PAULI_CHANNEL_2` channels.
- Ran a deterministic, no-sampling preflight on the six Phase 2B d=3 five-round circuits. All six non-approximated DEM conversions failed with Stim's documented requirement to set `approximate_disjoint_errors=True`. No historical files were modified.
- Searched local prior-work inventories for decoder portfolio, correlation-aware matching, categorical exact references, and operating-limit studies. Several candidate directions in the first-pass matrix already have prior Q-SHIFT work; no duplicate experiment was launched.
- Network source check: official Stim source on `raw.githubusercontent.com` reachable; arXiv API and DOI resolver blocked with tunnel 403. Research papers cannot currently be independently fetched from those domains.
- Current hypothesis: a useful fundamental follow-up is bounded exact inference directly over native categorical channels, because the planned DEM comparison is semantically blocked and existing exact enumeration only covers toys. This remains untested.
- Elapsed active research time since resumption: approximately 10 minutes at 14:39 UTC. Current experiment: none running.

## Next actions

1. Stop dense variable elimination for the two-layer Phase 2B factorization; move to a separate decoding or code-design family.
2. Revisit neural/hybrid, rare-event, or code-resource approaches for a distinct mechanism not already rejected by current development screens.
3. Continue primary literature review using accessible primary/repository sources. Mark inaccessible sources explicitly and avoid citation details that cannot be supported.
4. Maintain checkpoints on the isolated branch. No confirmatory/sealed evaluation is authorized.
- Retrieved source-tagged official documentation from Stim v1.16.0 and PyMatching v2.4.0. Stim explicitly requires approximate disjoint-error conversion for non-independent custom channels; PyMatching documents its correlation feature as a two-pass sparse-blossom procedure. Retrieved the official LDPC project README, which points BP+OSD users to Roffe et al. 2020 and notes BP+LSD as a newer alternative. Direct arXiv/DOI article endpoints remain unavailable.
- Added exact environment pins, reproduction steps, a runnable DEM-conversion preflight, literature/novelty review, candidate recommendations, interim Claude handoff, and `RESULTS.json`.

## Checkpoint at 2026-11-18 15:05 UTC

- Branch `codex/qshift-independent-research-v1`; prior committed checkpoint `fdf1337fe09735437bf8cd7e1d1bed9e3e9a293d` is being extended.
- Completed: broad local prior-work inventory, 12-candidate comparison, source-tag checks for Stim/PyMatching and LDPC, DEM conversion preflight, thresholded DEM sensitivity preflight, categorical sum-product toy prototype, exact toy comparisons, rare-event sample calculations, and paired-selector ceiling derivation.
- Verified findings: non-approximated DEM fails all six Phase 2B conditions; valid tested approximation thresholds give the same DEM per condition; Bethe categorical sum-product is exact on a one-location tree but misses exact MAP on one cyclic toy; three focused tests pass; no broken dependencies.
- Negative/inconclusive: no credible new decoder survives current toy/circuit gates; exact full-circuit posterior unavailable; Stage S source absent from published `main`; direct DOI/arXiv retrieval blocked.
- Active experiment: none. No jobs running. No stochastic Q-SHIFT shots generated.
- Resource use: 5 CPU cores available, 33 GiB RAM, no GPU. Research Python environment isolated in the worktree-local `.venv`.
- Current elapsed time since resumed: approximately 37 minutes. User's continuous directive remains active.
- Next action: continue searching distinct useful approaches from local source implementations and assess whether any remaining development experiment avoids duplication and passes exact small-instance checks. Do not access Claude's branch or launch confirmatory tests.

## MPS tensor-network feasibility checkpoint — 2026-11-18 15:15 UTC

- Branch `codex/qshift-independent-research-v1`; based on committed interim package `fdf1337fe09735437bf8cd7e1d1bed9e3e9a293d` (ancestor `507611c` verified).
- New candidate: qecsim planar untruncated MPS vs planar MWPM under paired IID depolarizing code-capacity noise. Installed qecsim 1.0b9 in the local ignored `.venv`; dependency pin recorded.
- 100-shot/distance preflight at d=3,5 verified every recovery returned to codespace. MPS was 0.864 ms/decode at d=3 and 60.9 ms/decode at d=5; projected 5,000 shots per distance exceeds five-minute runtime cap (~309 seconds MPS decoding only). Full screen not launched under the predeclared stop rule. Preflight outcomes are explicitly not performance evidence.
- No stochastic Q-SHIFT circuit samples, confirmatory data, or protected work were touched. Peak RSS 147,200 KiB. qecsim's optional `libpypm.so` was unavailable, so MWPM fell back to Python.
- Current files: `tensor_mps_screen.py`, `tensor_mps_preflight.json`; protocol/results updated. Next: continue to a different high-value family, or if MPS is revisited, design a separate bounded-bond protocol with fresh seeds and its own preflight.

## BP+LSD development screen checkpoint — 2026-11-18 15:18 UTC

- Same isolated branch/worktree. Implemented `bplsd_feasibility.py` using LDPC 2.4.1 and the six existing Phase 2B distance-3 circuits. The script maps each flattened approximate-DEM error instruction to one binary fault variable and records detector/logical parity.
- Protocol was written before the run: 100-shot-per-condition validity/runtime preflight followed by 5,000 samples per condition, fixed seed list 202611191–196, fixed decoder settings and correlation-enabled PyMatching comparator. Seed scan found no collisions in tracked research files.
- Preflight passed; corrected main run used 30,000 circuit samples total. All BP+LSD estimates reproduced their detector syndromes. Each LSD method (LSD_0/E/CS, min-sum 0.9, 200 iterations) recorded 321 errors, vs 138 for correlation-enabled PyMatching; each lost in all six conditions. No variant gained at the chosen setting.
- The first full-pass script lacked a syndrome-reproduction assertion. It was preserved as `bplsd_first_pass_unverified.json`; the fixed-seed run was repeated with the check, and all outputs were valid. Report only corrected `bplsd_results.json`.
- No sealed/confirmatory data or protected branch accessed. Total new stochastic Q-SHIFT development shots: 30,000. Next: independently review the transformed fault-variable model and continue to another research family; no tuning on these outcomes.

## Rare-event estimation checkpoint — 2026-11-18 15:34 UTC

- Validated Bernoulli likelihood-ratio weighting exhaustively on all 8 outcomes of a three-error toy. Normalization was exactly 1; weighted and exact LER were 0.34 within 5.6e-17.
- Preflight: 5,000 direct and fivefold-odds-tilted samples per arm in six approximate Phase 2B DEM conditions; relative SE gain gate passed 6/6.
- Main screen: new 20,000 samples per arm/condition, seeds 202611231–236 (direct), 202611241–246 (tilted). Estimated relative SE ratios were 0.437–0.509; failure-weight ESS 104–719; max |log weight| 14.0–17.2.
- Independent replication: 8 fresh 5,000-per-arm blocks, seeds 202611301–348 and 202611401–448. Between-replicate SD fell at least 25% in 5/6; balanced z-memory was the exception (ratio 1.12). All mean estimator differences were under 1.8 estimated SE.
- This supports importance sampling only for the approximate independent DEM surrogate and fixed correlation-enabled PyMatching. It does not estimate the source categorical circuit, validate 99.99% LER reduction, or access confirmatory data. Added ~780,000 DEM samples, 0 circuit samples.
- Continue by examining proposal robustness/alternative shifts or next research family; no use of the promising estimate for confirmatory claims.

## Exact categorical rare-event follow-up checkpoint — 2026-11-18 15:55 UTC

- Instrumented each source `PAULI_CHANNEL_2` pair as an exact mutually exclusive Stim E/ELSE branch and recorded each categorical outcome in private four-bit flags. Fivefold odds tilt multiplies each nonidentity Pauli-pair probability relative to identity and renormalizes; all other noise stays at the original distribution.
- Validity gates passed: synthetic channel frequencies and data Pauli actions; 60 one-hot checks of Stim's channel argument order across X/Z basis combinations; multiple channel pairs in one instruction remained independent; rec-based detector/observable fixture unchanged. All six source circuits retained the expected detector/logical dimensions.
- The 200-shot/condition preflight completed in ~1.2 s. Main screen sampled 20,000 direct and 20,000 tilted shots in each of six conditions. Separate 20k/condition samples from unmodified circuits matched the instrumented-direct LER (max absolute independent-binomial z=0.701).
- Independent exact-circuit stability check: two blocks of eight fresh replicates, each 5k per arm/condition. Across 16 replicates, mean direct and weighted estimates agree within 1.37 SE in every condition, but per-condition between-replicate SD ratios are 0.516, 0.789, 1.638, 0.783, 0.827, 1.078. Macro ratio is 1.12. Thus the weight estimator is validated, but this global 5x tilt is not a robust variance reduction and can increase variance in selected regimes. Do not claim general efficiency gain.
- Total new Phase 2B circuit samples for this branch now 1,352,400, all development-only and all in the isolated branch; no confirmatory data accessed. Additional 780,000 samples were from approximate DEM surrogate runs.
- Continue by identifying structured proposal distributions or return to code/noise co-design; no post-hoc tilt tuning on these samples.

## Cross-entropy proposal checkpoint — 2026-11-18 16:02 UTC

- Implemented the forward-KL independent product projection of the decoder-failure-conditioned per-location categorical marginals. Trained on 100,000 exact categorical circuit samples per condition under global 5x tilt, weighted back to the original channel law, with 50 baseline pseudocounts per location. Validation used fresh 20k direct, global-tilt, and cross-entropy arms per condition.
- Code smoke check passed on an independent quick sample with 120 channel locations and finite weights. Full validation completed in 18 seconds. The proposal failed its predeclared advancement gate in 0/6 conditions; no condition had >=25% SE reduction against both comparators. All estimates were within 3 combined SE, but lowest cross-entropy failure ESS was 9.0 and maximum weight was 77.3.
- Result: the independent conditional-marginal proposal does not capture enough failure trajectory structure at the tested shrinkage. No post-validation tuning was performed. Added 960,000 new source-circuit development shots; cumulative new Phase2B development shots 2,312,400. No confirmatory evidence accessed.
- Next: continue to code/circuit co-design or investigate alternative structured rare-event progress functions; avoid tuning the failed proposal on these results.

## Known-profile code/circuit co-design result — 2026-11-18 16:12 UTC

- Reused two independent exact circuit samples already generated for the categorical importance study and its raw Stim crosscheck: 40,000 total shots per memory-basis/noise cell. No additional circuit samples were launched.
- At matched resources (26 physical qubits, 40 detectors, 5 rounds, same gate/measurement p), X-memory under X-biased noise reduced failures 80.6% versus Z-memory (51 vs 263 / 40k; rate ratio .194, exact conditional 95% CI .141–.257). Z-memory under Z-biased noise reduced failures 91.0% versus X-memory (28 vs 312 / 40k; ratio .0897, CI .0614–.1323). Balanced noise had no evidence of a basis effect (187 vs 197; ratio 1.05, CI .858–1.280).
- This is known-profile orientation evidence at d=3 only. It is not novel code construction, decoder superiority, or an adaptive selection result; no data on drift or scale.
- Total generated Phase2B circuit samples remain 2,312,400; this analysis reuses saved aggregate result files.

## Distance-5 basis-alignment checkpoint — 2026-11-18 16:20 UTC

- Added a scalable circuit builder and verified byte-identical reproduction of the six d=3 source circuits. At d=5/9 rounds, X/Z memory used matched 64 physical qubits, 216 detectors, and 720 two-qubit channel pairs.
- Preflight projected the declared 50,000 shots/cell below the five-minute cap. Main run used 50,000 direct exact-circuit shots in each of four biased distance-5 conditions. Under X bias, aligned X-memory had 6 failures vs 217 for Z-memory (LER .00012 vs .00434, rate ratio .0276, conditional exact CI .0100–.0543). Under Z bias, aligned Z-memory had 6 vs 270 (ratio .0222, CI .00808–.0436).
- Same alignment direction persists from d=3 to d=5, but each aligned d5 cell has only six failures. This is not a threshold estimate or evidence at larger distances. Total new Phase2B development shots: 2,512,800. No confirmatory/sealed data accessed.

## Bias-strength crossover checkpoint — 2026-11-18 16:28 UTC

- Added a small, theory-motivated known-profile comparison at bias ratios 2 and 5, between previously sampled ratios 1 and 10. Same distance-3/5-round circuit and 0.003 gate/measurement rates; X and Z memory resource counts matched.
- 50,000 fresh exact-circuit shots per condition. At ratio 2, aligned/mismatched LER ratios were 0.736 (95% CI .613–.876) under X bias and 0.646 (.538–.768) under Z bias. At ratio 5, ratios were 0.325 (.257–.403) and 0.239 (.188–.298). Directional benefit is visible by 2:1 and grows in these sampled ratios. No exact crossover interpolation is justified.
- New circuit samples: 401,600 including preflight; cumulative Phase2B development shots 2,914,400. No confirmatory/sealed data accessed.

## Fixed-bond MPS follow-up checkpoint — 2026-11-18 15:42 UTC

- Continued from the untruncated-MPS runtime stop with a separate fixed-chi=16 qecsim protocol, fresh predeclared seeds, and 100-shot preflight. Worktree `/workspace/qshift-independent-research-v1`, branch `codex/qshift-independent-research-v1`; no other branch or evaluation data accessed.
- Completed 5,000 paired IID depolarizing code-capacity samples per distance at p=.05, d=3 and d=5. All MPS and MWPM recoveries passed codespace checks. Fixed chi16 MPS had 123/5,000 vs MWPM 206/5,000 failures at d3 (paired delta −.0166; McNemar p=3.49e−17), and 30 vs 92 at d5 (delta −.0124; p=9.33e−12).
- Runtime: 0.988 ms/MPS decode at d3 and 13.74 ms at d5; MWPM Python path 0.181 and 0.507 ms. Whole run 80.4 s, peak RSS 118,636 KiB. This is promising at the tested model, but not evidence on Q-SHIFT's noisy repeated-measurement circuit, not a threshold result, and not a real-time deployment candidate at d5 latency.
- Reports and `RESULTS.json` now include the bounded-bond run. Next question: identify whether a scientifically fair circuit-level MPS comparator can be built with the current dependencies/noise model; otherwise move on to a different research family rather than tuning chi.

## Distance-7 bias-alignment checkpoint — 2026-11-18 15:50 UTC

- Added one predeclared third-distance point to challenge the known-profile code/circuit co-design finding. Source builder remained byte-identical at d=3. At d=7/13 rounds, X/Z memory resources matched within each profile (118 qubits, 624 detectors, 2,184 two-qubit channel pairs).
- Initial 100-shot scalar preflight projected over five minutes and stopped before main. A fixed batched PyMatching decode implementation then passed 100/100 scalar-output checks per condition, with projected sampling+decode 189.3 s for the preregistered 500,000 shots per cell. The main run completed in 34.6 s (hardware cache/runtime variation notwithstanding).
- At bias ratio 10, gate/measurement p=.003, X bias gave 5/500,000 aligned X-memory failures versus 1,009 mismatched (ratio .00496, conditional 95% CI [.00161,.01017]); Z bias gave 3 aligned failures versus 1,227 mismatched (ratio .00244, CI [.000504,.00590]). The p-value for the latter underflows to 0.0 in double precision; it is not literally zero. Sparse aligned failures make absolute LER and scaling estimates coarse.
- Cumulative new Phase2B development shots now 4,914,800; this excludes code-capacity MPS samples. No confirmatory data accessed. Reports, JSON, and reproduction docs updated.

## Detector-only bias inference and direct policy checkpoint — 2026-11-18

- Hypothesis: detector-event asymmetry from a fixed Z-memory calibration circuit can identify X/Z bias direction before a separate logical-memory run. Implemented a four-feature linear discriminant (coordinate family × temporal half) using detector samples only. Training: independent d=3 ratio-10 profiles, 100k shots/class. Frozen validation: 1,000 independent calibration windows/profile/distance at d=3,5,7, window budgets 25/100/500 shots.
- Binary direction accuracy at 500 calibration shots was 94.9/100/100% at d=3 for ratios 2/5/10; 99.3/100/100% at d=5; and 99.35/100/100% at d=7. A separate predeclared balanced/X/Z three-class classifier trained on d3 balanced and ratio10 profiles often labeled ratio2 profiles as balanced; this did not invalidate the binary direction test. It shows magnitude detection and direction estimation need separate models/evidence.
- An end-to-end fixed policy test used new independent calibration streams and separate paired X/Z logical-memory streams at d=3 (1,000 500-shot calibration windows/profile, 100 memory shots per basis/window). Under equal X/Z profile weights, policy LER was .00405 vs static-Z .004855 at ratio2 (16.6% lower; cluster-bootstrap 95% delta interval [−.001125,−.000490]); .00198 vs .00416 at ratio5 (52.4%; [−.00246,−.00190]); and .001165 vs .00412 at ratio10 (71.7%; [−.00323,−.00267]). Decoder was correlation-enabled PyMatching from the same approximate DEM threshold .0018.
- First implementation pass inverted classifier sign (positive class means Z), so it selected the opposite basis and is retained as invalid artifact. Added an explicit training-score polarity assertion, reran preflight and the fixed seeds; valid findings only use corrected run. The repeated run used the same deterministic seed streams and is not counted as independent shots.
- Cross-profile results remain synthetic, stable-model development evidence. Calibration overhead, drift, transfer to device data, and equal total shot/round budget remain open. No confirmatory data accessed. Next: design a held-out model-mismatch/drift test with a frozen estimator and a recalibrated-static baseline; include calibration cost.
- New unique Phase2B development circuit samples now total 23,159,800 (preflights included; exact-seed polarity rerun excluded from unique-sample count). qecsim code-capacity samples are counted separately. All docs/results updated in the next checkpoint commit.

## Total-rate drift checkpoint — 2026-11-18

- Challenged the frozen d3 ratio10 detector-only classifier after calibration at p=.003 and logical-run gate/measurement p=.006, holding X/Z bias direction fixed. Fresh calibration windows and separate logical test streams; equal profile weights; ratios 2/5/10.
- The .0018 DEM conversion threshold failed before shot generation on a categorical channel probability .00357. Deterministically selected .004 as the smallest fixed round threshold covering the p=.006 channels; every comparison arm used it. Preflight passed batch/scalar agreement and projected 2.3 s for the full sample.
- On 1,000 calibration windows/profile and 100 logical shots/basis/window, selector LER was .014785/.00776/.004325 at ratios2/5/10, versus static-Z .016845/.015715/.01493; reductions 12.2/50.6/71.0%, bootstrap intervals for policy-minus-static below zero. It matched oracle at ratios5/10 in this sample and was close at ratio2.
- This is one synthetic rate-shift condition with direction held fixed, not a change-point or hardware test. Calibration cost remains 500 shots for each 100-shot memory block. Unique Q-SHIFT development circuit sample total now 27,377,800 including preflights; qecsim code-capacity shots are separate.

## Calibration-cost frontier checkpoint — 2026-11-18

- Re-scored the fixed classifier on nested 25/100-shot prefixes of existing 500-shot calibration windows and reused the same direct logical outcome arrays. No new sample streams, no model refit, and no shot-count increase. This is explicitly exploratory.
- LER reductions versus static Z at calibration budgets 25/100/500 per 100 logical shots: 5.1/11.6/16.6% at ratio2 (25-shot interval includes zero), 27.8/49.6/52.4% at ratio5, and 57.5/71.2/71.7% at ratio10. Calibration load is .25/1/5 shots per logical shot, respectively. The result shows the weak-bias regime needs more calibration for reliable selection; nested estimates are correlated and not confirmatory.
- Current research branch before this checkpoint: `codex/qshift-independent-research-v1`, commit `4b91bba`. Continue with a model-mismatch/drift question; avoid tuning a budget on the inspected rescore.

## Calibration amortization analysis — 2026-11-18

- Derived a plug-in throughput break-even for the direct policy if calibration shots yield no logical output and cost the same as a memory shot: `N > C(1-p_static)/(p_static-p_policy)`.
- At C=500, observed d3 policy/static rates imply about 618k, 228k, and 169k logical shots per calibration at bias ratios 2, 5, and 10. This is a resource-objective calculation only; plug-in error rates are uncertain and long-term stationarity is untested. It does not change LER per logical shot.
- No new circuit samples. Current branch head before commit: `6ac1a17`.

## Same-observable decoder-selection checkpoint — 2026-11-18

- To separate code/task selection from decoder improvement, fixed the d=3 Z-memory circuit and logical observable, then compared correlation-enabled PyMatching graphs trained from X-profile, Z-profile, and pooled mean-channel DEMs. Frozen detector-only calibration selected X/Z graph; 1,000 500-shot calibration windows/profile; independent 100,000 logical shots/profile.
- Classifier chose the correct profile for all 2,000 windows. Selected bank had 775 errors vs 779 for pooled graph in 200,000 same-observable samples; paired window-bootstrap interval for LER difference [-9e-5,+5e-5] includes zero. Static X graph also had 779; static Z graph 806. Oracle graph had 775. This is a negative result for decoder selection in this one d3 ratio10 condition despite accurate labels.
- Important scope correction: prior basis-adaptation results switch X/Z memory circuits and thus the observable under test. They support a configurable known-basis memory task only, not an arbitrary logical-qubit memory or decoder-only gain. This distinction is now explicit in fundamental limits and handoff.
- Unique development circuit samples now total 28,581,800 including preflights; qecsim code-capacity samples remain separate. No confirmatory data accessed.

## XZZX code/circuit co-design checkpoint — 2026-11-18

- Implemented a fixed checkerboard local-H conjugation of the source rotated-memory circuit. A first gate rewrite incorrectly treated H-CX-H as a reversed CX and produced nondeterministic detectors; it stopped before any shots. The corrected exact conjugation compiles marked-control interactions as H-CX-H, models each added H with the source one-qubit Pauli channel, and passed noiseless deterministic detector and DEM checks.
- Core resources matched (qubits, detectors, rounds, two-qubit pairs), but one-qubit H/noise targets increased 40→100 at d3 and 216→576 at d5. Fixed 500k/cell run completed in 11.9s.
- XZZX-transformed LER was worse than CSS in all conditions: d3 X-bias .009594 vs .007216 (1.33x), d3 Z-bias .006532 vs .000982 (6.65x), d5 X-bias .006752 vs .004534 (1.49x), d5 Z-bias .003332 vs .000168 (19.8x). This rejects this local-H transpilation under its explicit noisy-H cost model; it does not reject native-compiled XZZX generally.
- Cumulative unique Q-SHIFT development circuit samples now 32,589,800 including preflights; failed deterministic gate preflight had no shots. No confirmatory data accessed.

## Alternating-profile resource replay — 2026-11-18

- Current branch before this checkpoint: `codex/qshift-independent-research-v1`, commit `a380d86`. This was a reanalysis of saved direct calibration and logical windows; no new circuit samples were generated.
- Replayed 144 combinations of ratio 2/5/10, detector-only calibration budgets 25/100/500, update periods 100/1,000/10,000/100,000 logical shots, and equal profile dwell periods in the same grid. Frozen classifier confusion rates and basis-specific logical failure rates were applied to deterministic alternating X/Z-bias profiles over 10M logical attempts.
- Charged every calibration shot as a circuit resource with no useful output and compared correct outputs per total circuit shot to the best static X/Z basis. No tested schedule beat static at dwell <=10k shots. At 100k dwell, best plug-in throughput ratios were 0.999857 (ratio2), 1.001041 (ratio5), and 1.002052 (ratio10). This is a temporal scenario projection, not an empirical change-point or device test; no uncertainty propagation was performed.
- Source and stable-policy reconstruction checks passed; 144 schedule rows saved in `temporal_basis_replay_results.json`. Cumulative unique Q-SHIFT circuit samples remain 32,589,800; no confirmatory data accessed.
- Next: map a bounded native-categorical circuit fragment into local factors; require forced-fault agreement and measure induced width before attempting inference.

## Exact categorical variable-elimination feasibility — 2026-11-18

- Current branch before this checkpoint: `codex/qshift-independent-research-v1`, commit `fe1f992`. Implemented exact log-domain dense factor elimination with greedy weighted min-fill, one mutually exclusive categorical variable/location, detector XOR constraints, and a prefix logical parity chain.
- Exhaustively compared all syndrome/logical masses, posteriors, MAP decisions, and risk on the single-location tree and one-/two-qubit repetition toys. Maximum error was 2.8e-16. Independently forced each local Pauli outcome through Stim on both circuit-backed toys; joint masses agreed.
- Synthetic pairwise grid stress at one consistent syndrome kept max table size 16/32/128/1,024/65,536/524,288 at 2x2/3x3/5x5/7x7/9x9/11x11, with induced width 3/4/6/9/15/18. The 2x2 result also matched exhaustive enumeration. At 11x11, one target took .38s and remained under the 1M-entry cap. This does not represent the Phase 2B categorical temporal graph.
- Exact controls caught two implementation defects before final reporting: floating-point MAP tie handling and unsorted variable order in prefix parity factors. Both were corrected; final independent checks pass. No Q-SHIFT stochastic samples generated.
- Next: map a bounded Phase 2B native categorical fragment to local factors and measure exact width, stopping before any dense intermediate exceeds 1M entries.

## Native-categorical Phase 2B fragment — 2026-11-18

- Mapped the first three target pairs from the final `PAULI_CHANNEL_2` instruction (source d3, five-round Z-memory, X-biased ratio10). Each location keeps its 16 mutually exclusive outcomes and source probabilities. Other stochastic locations were identity for this fragment.
- Initial mapper used per-circuit `compile_detector_sampler` results and falsely reported zero effects because that API subtracts each deterministic circuit's own reference. Preserved the artifact as invalid; fixed mapping reads raw record bits and explicitly evaluates detector/observable rec parity relative to one shared noiseless source circuit.
- Corrected map touches six detectors. All 256 combined-fault verification cases matched XOR composition. Exhaustive 4,096 categorical assignments and VE agree on all 64 reachable syndromes/logical classes with max joint-mass error 2.22e-16. Width=2, max factor=512 entries, ~1.96 seconds. No stochastic shots generated.
- Current branch before this checkpoint: `codex/qshift-independent-research-v1`, commit `d4f24ef`. This is a deterministic three-location final-layer slice only, not a full-circuit decoder or LER result.
- Next: width-only preflight across two adjacent final-round channel layers (12 categorical locations); stop before inference if any factor exceeds one million entries.

## Exact six-location Phase 2B layer — 2026-11-18

- Separate scope-only preflight for all six pair locations in the final channel layer predicted 10 touched detectors, induced width4, and a largest dense intermediate of 131,072 entries; under the fixed one-million cap.
- Expanded only after that preflight. A sparse XOR-convolution reference aggregated the exact 16^6 source categorical probability mass. VE agreed on all 1,024 reachable syndromes; max joint mass error 1.11e-16, max posterior error 2.47e-15. 512 deterministic combined-fault cases matched XOR-composed Stim signatures. Full all-syndrome VE took 95.2 sec; width4/131,072 entries matched the preflight.
- Isolated-layer MAP LER was 1.0572e-5, but all other circuit faults were identity; do not compare it with the full Phase 2B LER. No stochastic circuit samples generated.
- Current branch before this checkpoint: `codex/qshift-independent-research-v1`, commit `11f5fce`.
- Next: structural width-only preflight on two adjacent final-round channel layers (12 locations), with same fixed cap.

## Two-layer exact-inference width stop — 2026-11-18

- The final two adjacent `PAULI_CHANNEL_2` instructions in the d3 five-round Z-memory/X-biased-10:1 circuit contribute 12 native 16-state variables and touch 10 detectors. A scope-only weighted min-fill preflight predicted width9 and a largest factor of 17,179,869,184 entries.
- Compared eight scope orderings: weighted min-fill, weighted min-product, unweighted min-fill, min-degree, natural, reverse, and two location/carry interleavings. None fit the fixed 1,000,000-entry cap. Best remained 17.2B entries; no inference table was allocated and no posterior was attempted.
- This demonstrates a sharp scaling break from the single-layer pass and stops this dense factorization at one layer. It is not a lower bound for tensor contraction or other exact representations. No stochastic shots generated.
- Current branch before this checkpoint: `codex/qshift-independent-research-v1`, commit `c0acddd`.
- Next: return to another research family; consider a resource-matched d3 round-count/code design screen or circuit-compatible tensor decoder audit rather than more dense VE ordering work.

## Distance-3 syndrome-round resource frontier — 2026-11-18

- Continued in the isolated branch `codex/qshift-independent-research-v1` from commit `37e0800`. Tested 3/5/7/9 extraction rounds at d3, p=.003, bias10, across both profiles and memory bases. The initial source-builder preflight stopped on a hard-coded 5-round detector-count assertion before samples; the documented scaled Stim builder fixed this, and its 5-round circuits matched all four source circuits byte-for-byte.
- Preflight passed and the 3.2M-shot main screen completed in 3.6s. Per-attempt LER increased monotonically with rounds in all four profile/basis cells. Pair-channel opportunities were 72/120/168/216 for rounds 3/5/7/9; each round count was resource-matched across cells. Cumulative unique Q-SHIFT development samples: 35,791,400 including the 1,600-shot preflight. No confirmatory data accessed.
- Interpretation is limited: fewer rounds shorten the memory duration, so the 3-round lower per-attempt LER is not an equal-time gain. Exact intervals, cell results, and reproduction command are recorded in the round-count artifacts and required reports.
- Next hypothesis: quantify the resource frontier under an explicitly matched elapsed-time model. First inspect whether source circuit timing/noise semantics support a defensible idle-padding control; do not append ad hoc idle noise or claim duration matching unless every added interval has a defined physical noise model. If the source cannot justify that model, move to a separate bounded research family.

## Bias-strength decoder robustness — 2026-11-18

- The circuit source models post-Clifford gate channels and measurement flips, but defines no separate idle-duration/error process. Therefore no equal-time padding study was fabricated from this model; the time-normalized round-count question remains unresolved.
- New hypothesis: precise bias-strength estimation may be unnecessary if the correlation-enabled matching decoder is insensitive to moderate prior-ratio mismatch. A paired screen compared assumed ratios 2/5/10 on identical detections from actual X/Z-biased ratios 2/5/10 at d3, five rounds, p=.003, both bases (12 cells). A 100-shot/cell preflight passed and projected 16.7 seconds; main used 100,000/cell (1.2M samples) and completed in 2.8 seconds.
- Equal-weight macro LERs at assumed ratios 2/5/10 were .005522/.005216/.005022. Assumed10 was lower than assumed5 by .000194 (paired conditional 95% interval [-.000242,-.000146]) and lower than the correctly specified-model reference by .000273 ([-.000323,-.000222]). This surprising result challenges the matched-model-is-best assumption for this approximate DEM plus matching decoder; it does not generalize beyond the tested grid. Same-screen ratio ranking is selection-optimistic; no decoder was promoted.
- Cumulative Q-SHIFT development shots: 36,992,600 including the 1,200-shot preflight. No confirmatory data accessed. Code, fixed protocol, paired results, preflight and required report updates are in this checkpoint.
- Next: independent validation of a frozen ratio10-vs-ratio5 comparison on fresh development seeds, with ratio2/5/10 held as actual conditions and an additional intermediate actual strength such as ratio3.5, if the p=.003 approximate DEM builder remains valid. Freeze contrast direction and keep the same equal-weight condition objective; do not tune on current streams.

## Frozen ratio-10 versus ratio-5 validation — 2026-11-18

- Executed the predeclared fresh-seed validation with assumed models fixed to ratios5 and10 and actual ratios2/3.5/5/10 across both profiles and bases (16 conditions). Preflight passed and projected 11.8s; 100,000 samples/cell completed in 2.5s.
- Macro LER was .0052244 for ratio5 and .0050025 for ratio10. The frozen paired ratio10-minus-ratio5 contrast was -.0002219 (conditional MC 95% interval [-.0002626,-.0001812]). The average stayed negative for each actual ratio; two ratio2 cells favored ratio5, while every cell at actual ratios5 and10 favored ratio10. This supports a narrow fixed-grid robustness effect and confirms the prior ranking on fresh streams; it is not a universal or hardware claim.
- Cumulative Q-SHIFT development samples: 38,594,200, including 1,600 preflight shots. No confirmatory data accessed. Exact per-cell results, preflight, protocol, and reproduction command have been added to the required outputs.
- Next: test whether the frozen prior-ratio effect persists at a second code distance under a clearly bounded resource cap, or investigate why a stronger assumed bias can outperform the correctly specified model under correlated matching. Do not fit a threshold from two distances or retune ratios on the current samples.

## Distance-5 frozen bias-strength validation — 2026-11-18

- Tested the same frozen ratio10-vs-ratio5 matchers at d5/9 rounds under actual ratios2/3.5/5/10, both profiles and bases (16 cells, 100,000 direct shots/cell). The ratio10 builder was byte-identical to the existing scaled d5 circuit for all four profile/basis cases; the 100-shot preflight passed and projected 92s. The run completed in 23s.
- Macro LER was .0019331 (assumed10) versus .0019131 (assumed5). Paired ratio10-minus-ratio5 macro delta +.0000200, conditional MC 95% interval [-.0000060,+.0000460], including zero. Contrasts were near zero across actual strengths; actual ratio5 slightly favored assumed5, while ratio10 slightly favored assumed10. The d3 ratio10 advantage therefore did not replicate as a clear d5 effect. This is inconclusive, not evidence of equivalence.
- Cumulative Q-SHIFT development samples: 40,195,800, including 1,600 preflight shots. No confirmatory data accessed. Artifacts/protocols and handoff/report updates are recorded.
- Next: inspect how the matching graph/edge weights change across assumed ratios at d3 vs d5 to explain the apparent interaction before running another large sweep. Use deterministic graph diagnostics and exact same-syndrome redecoding of saved results where possible; do not tune or fit thresholds from these two distances.

## Deterministic matching-graph mechanism audit — 2026-11-18

- Rebuilt eight pairs of correlation-enabled matching models (d3/d5 × X/Z profile × X/Z basis) under assumed ratios5 and10. All source/scaled builder checks passed. No stochastic samples were generated.
- Every pair had identical edge topology and logical-fault labels (142 edges at d3, 950 at d5). Mean absolute edge-weight perturbations were .238 (d3) and .249 (d5); medians .131 and .128; median absolute error-probability perturbation .000353 at both. The higher-ratio graph increased about 74.6% of common d3 weights and 70.3% at d5.
- Therefore edge addition/removal does not explain the d3/d5 performance difference, and gross reweighting magnitudes are similar. This audit is descriptive and does not identify the syndrome/decision mechanism. Raw sample syndromes were not saved with the earlier aggregate artifacts, limiting offline paired error-pattern analysis.
- Next: avoid further claims about why the finite-distance effect differs. If pursuing it, define a fresh targeted decoder-decision analysis where the same sample streams are retained and disagreement syndromes can be stratified; otherwise move to a separate research family.

## Paired decoder-decision seed replay — 2026-11-18

- Replayed the exact 32 saved d3/d5 seeds (100,000 shots/cell); all 64 archived per-cell decoder error counts matched exactly. This is a reanalysis/reproduction and adds no unique stochastic samples.
- At d3, ratio5/10 predictions disagreed on 1,105 of 1.6M samples (.0691%). Ratio10 fixed 730 ratio5 failures and introduced 375; accuracy among changed predictions was 66.1% (Wilson 95% 63.2%–68.8%). At d5, disagreement was 452/1.6M (.0283%); ratio10 fixed 210 and introduced 242, with 46.5% conditional accuracy (41.9%–51.1%). This decomposes the net d3/d5 contrast but not the syndrome mechanism.
- Cumulative unique Q-SHIFT development samples remain 40,195,800; no confirmatory data accessed. Exact replay verification and aggregates are saved; the raw syndromes are not retained in the report artifact.
- Next: avoid overfitting this finite set of disagreement cases. Move to an orthogonal research family or, if pursuing the mechanism, design fresh retained-syndrome data with predeclared stratification and an independent validation split.

### Coarse syndrome-weight diagnostic (same replay, no new samples)

- On d3, ratio10 changed decisions were concentrated in syndrome weights3–8 (1,022/1,105), where 678/1,022 favored ratio10; weight9+ changes were sparse (29) and favored ratio5 (18 vs11). At d5, 363/452 changes were weight9+ and ratio10 was correct on 168/363. These are raw counts across 40 versus216 detectors and cannot be compared as normalized distance coordinates.
- This gives a descriptive lead that ratio10's changed-decision mix varies by distance, but it does not identify fault geometry or causality. The full bin table is saved in the replay artifact; all archived error counts still reproduce.

### Two-output selector ceiling (same replay)

- The sample-specific oracle that selects the correct ratio5 or ratio10 answer on each disagreement still fails on all both-wrong cases. Against the best fixed model observed, this oracle could reduce failures by at most 4.69% at d3 and 6.86% at d5. This is a development-sample ceiling, not a population bound; it shows that selecting between these two decoders alone cannot approach the 99.99% relative reduction objective.

## Two-qubit fault composition in shared failures — 2026-11-18

- Preflight instrumented 5,000 independent original and 5,000 instrumented samples in four high-LER cells (actual ratio10, both bias directions with mismatched memory basis, d3/d5). The instrumented/direct LER standardized differences were within .86 SD; 120 pair locations at d3 and 720 at d5. Projected main runtime 49.6s, below cap.
- Main used 100,000 instrumented source-equivalent shots/cell and tracked every categorical PAULI_CHANNEL_2 outcome; one-qubit and measurement channels were left intact but untracked. Shared-both-wrong shots had mean 1.94 pair faults at d3 and 4.67 at d5, versus .35/2.14 among both-correct. XX/ZZ, the pair type aligned to the imposed profile, was enriched about 5.7–5.8× at d3 and 2.28× at d5. Ratio10 fixed/broke 91/67 d3 outcomes and 37/41 d5 outcomes in these four cells.
- Descriptive only: two cells/distance, fault subset omits one-qubit/measurement tags, and high pair-fault counts do not prove the errors are intrinsically uncorrectable. Main run 16.8s. Cumulative Q-SHIFT simulated shots now 40,635,800 including 40k preflight and 400k main; no confirmatory data accessed.
- Next: avoid promoting an error-floor claim from this screen. The remaining useful path is a decoder that addresses shared multi-fault failures; an implementation would need to preserve the full categorical channel model and beat correlation-enabled matching under matched information/resources.

## Exact sparse inference for two and three channel layers — 2026-11-18

- Revisited the dense two-layer failure with exact probability aggregation over XOR detector/logical signatures. For the final 12 locations/10 touched detectors, direct sparse DP and independent 6+6 half-map convolution matched all 2,048 joint states to 1.33e-15; 512 forced combined faults matched Stim. 4.42M sparse operations, 4.85s. Isolated-layer MAP risk 9.94e-5 only.
- Extended to 18 locations in the last three layers/12 touched detectors. Sparse DP (1.22M transitions) and independent Walsh-Hadamard convolution (2.02M operations) matched all 8,192 states/4,096 syndromes to 1.22e-15; 512 forced-fault checks passed; 4.63s. Isolated-fragment MAP risk 2.23e-4, not full-circuit LER.
- A first Walsh normalization divided by N^(L-1), causing .95 error; the independent sparse DP caught it before final reporting. Correct inverse uses one factor N. No stochastic samples generated.
- This is an alternate exact representation to dense VE, with exponential dependence on touched signature bits; full 40-detector circuits remain infeasible by this direct state-space method. Continue with a predeclared fourth-layer resource preflight if output support remains bounded.

### Fourth-layer sparse exact continuation — 2026-11-18

- The preflight passed for 24 categorical locations; all four final channel layers still touch only 12 detectors (8,192 joint states). Exact sparse DP and Walsh convolution agreed over all 4,096 syndromes to 2.78e-15; 512 forced combined-fault checks passed; normalization .9999999999999988; 3.55s.
- Isolated four-layer MAP risk .000431, not a full-circuit LER. Sparse DP used 1.62M transitions and Walsh 2.66M operations. No stochastic samples generated.
- Local support stayed at 12 detector bits across this temporal slice; this does not imply support remains bounded for longer/full circuits. Next: preflight a fifth layer against existing state/operation caps.

## Fifth-layer sparse categorical preflight stop — 2026-11-18

- Mapped the final five six-pair channel layers (30 locations) through forced-outcome Stim signatures. Compact detector support rose from 12 at four layers to 18; joint state upper bound 524,288; sparse-DP transition bound 251,658,240.
- The fixed protocol cap was 1,000,000 states/100,000,000 transitions, so the run stopped before mass expansion. No inference table/mass distribution and no stochastic samples generated. Do not raise the cap post hoc; this is the current bounded sparse-DP boundary, not a lower bound for other exact representations.
- Next: return to broader candidates or investigate a new representation under a separately predeclared resource design; do not keep extending layer count under changing caps.
