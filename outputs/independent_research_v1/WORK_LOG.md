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
