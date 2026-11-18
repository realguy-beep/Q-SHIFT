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

1. Complete the local source inventory, including BP+OSD, tensor-network, neural, and Stage S specifics, avoiding sealed files.
2. Finish the candidate matrix using documented previous-work evidence to distinguish genuinely open paths from repeats.
3. Check whether a bounded native categorical factor graph can be formed from a small Phase 2B circuit fragment, then validate it exhaustively before considering an algorithm prototype.
4. Continue primary literature review using accessible primary/repository sources. Mark inaccessible sources explicitly and avoid citation details that cannot be supported.
5. Maintain checkpoints on the isolated branch. No final confirmation study is authorized.
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
