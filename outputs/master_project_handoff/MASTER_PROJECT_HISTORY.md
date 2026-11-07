# Q-SHIFT Master Project History

## Project identity

Q-SHIFT is a software simulation and research project about whether noise information can improve quantum error-correction decoder selection. Its present research question is: **Can noise-composition information improve decoder choice, and can a system recognize unfamiliar mixtures rather than force them into known categories?** Adaptive decoding is an established research direction; Q-SHIFT does not claim to have invented it.

The project has not demonstrated adaptive decoding superiority, connected to a real processor, accessed hardware telemetry, controlled qubits, or shown physical recovery of every data qubit. A Stim decoder prediction is an estimate of an observable correction. Simulator evaluation computes `sampled logical observable XOR predicted correction`.

## Evidence labels used here

1. **Raw/code verified:** the file contents or underlying raw table were inspected and independently calculated.
2. **Structured result verified:** source/config/result files were inspected and arithmetic, seed counts, aggregates, or hashes were checked; decoder outputs were not regenerated from every saved detector row.
3. **Cross-checked:** report claims agree with structured results and/or manifests, but raw shot-level reconstruction was not done.
4. **Prior report only:** a previous ChatGPT/Codex conversation states the result, but the underlying result file or source is absent or does not support independent verification.
5. **Proposal:** future work only; no data exist.

## 1. Starter kit and original dataset

The initial ZIP at `C:\Users\LENOVO\Downloads\Q-SHIFT_v0.1_starter.zip` contains an early script that generates 2,000 shots at each of p=.001, .003, and .006 (6,000 rows). The expanded folder `C:\Users\LENOVO\Downloads\Q-SHIFT_v0.1_starter` has a later Step 1 script with 50,000 shots per setting and a 150,000-row CSV. The ZIP's Step 1 source and the expanded folder's Step 1 source have different SHA-256 hashes; the ZIP is an earlier version, not an exact backup of the expanded project.

The current starter circuit is Stim `repetition_code:memory`, distance 3, three rounds, eight detectors, and one observable. Its only noise channel is Stim's `after_clifford_depolarization`. The CSV has columns `syndrome_0..syndrome_7`, `noise_probability`, `logical_error`, and `noise_group`. Direct inspection found 150,000 rows, no nulls, 50,000 rows per p, logical flips 70/240/490, 61 unique detector vectors, 117 unique complete rows, and 149,883 repeated complete rows. The eight-bit detector feature space has only 256 possible patterns. The CSV contains no shot ID or generation manifest, and the saved deterministic seed is implicit in source only. Repeated rows make row-random train/test splits unsuitable evidence of independent shot generalization.

The current Step 3 script uses detector columns only, stratifies rows, and selects an XOR-residual threshold on a validation split before one test evaluation. Its present 150k split is 105,000 train, 22,500 validation, 22,500 test; an earlier conversation result instead reported 112,500 train and 37,500 test with no validation. That conversation's classification report (balanced accuracy .9862; confusion matrix `[[37020,280],[4,196]]`) and its residual worsening (0.5333% to 0.7573%) have no matching local result artifact and cannot be reconciled to the current Step 3 source. Preserve them as conversation-reported negative evidence, not a verified run. The central lesson remains: classification metrics do not establish a useful decoder correction.

The local 1.97 MB `qshift_fixed_decoder.pkl` exists and its hash/size were recorded, but it was deliberately not loaded because pickle loading can execute code and the artifact is not independently validated. **Evidence:** CSV and source directly inspected (1); earlier RF outputs only from conversation (4); pickle existence only (2).

## 2. Fresh PyMatching benchmark and early single-seed lookup work

`qshift_step4_benchmark.py` added fresh Stim samples, a circuit-derived PyMatching decoder, Wilson intervals, and an optional detector-only random forest with separate train/validation/test splits. The saved benchmark used 100,000 matching shots per p and an independent 60k/20k/20k ML split. Matching residuals were 1/100k, 6/100k, and 45/100k at p=.001/.003/.006. ML residuals were 0/20k, 2/20k, and 4/20k. The smaller ML tests and rare errors do not establish ML superiority.

The first per-regime lookup run (`qshift_prototype_results.json`, seed 20261106) used 2m training, 200k validation, and 1m test shots per p. It recorded lookup vs matching errors of 13 vs 11, 87 vs 96, and 292 vs 373. The lookup helped at two settings and lost at one; it was a single seeded experiment.

A separate pooled three-regime lookup run (`qshift_mixed_regime_results.json`, seed 20261107) used 6m training, 900k validation, and 2m paired test shots per p. It recorded lookup vs matching errors 15 vs 21 at .001, 161 vs 178 at .003, and 598 vs 710 at .006. This looked favorable in that one run. The source uses validation to select a threshold and does not pass the test p as a feature. It was not an adaptive decoder and was not independent-seed evidence.

Follow-up one-seed runs were inconsistent. `qshift_decoder_experiments_results.json` recorded lookup/matched DEM counts 23/9 at .001, 94/109 at .003, and 311/371 at .006; a repeated p=.003 model and matching baselines had 10, 109, and 371 errors. `qshift_train_more_results.json` reported RF/matching counts 2/3, 33/19, and 81/72 over 200k shared test shots: one fewer at the lowest p, worse at the other two. These runs do not replicate the apparent pooled-lookup signal.

**Evidence:** source and JSON inspected (2); reports cross-checked (3); no shot-level raw arrays were found for these legacy JSON runs.

## 3. Ten-seed lookup/adaptation study and exploratory branches

`qshift_research.py` and `qshift_research_results.json` represent the larger early study: 10 seed families, 100k training and 30k validation shots per trained regime per seed, and 100k test shots per condition per seed (1m per condition). Detector inputs were used by the learned methods; nominal matching used p=.003; a condition-informed matching oracle and nearest-regime lookup were labeled as informed/oracle references. Conditions were .001, .002, .003, .0045, .006, and .008, with .0045 intermediate and .008 outside the training range.

Mixed lookup minus fixed matching aggregate error differences were +1, +8, +4, +23, +39, and +78 errors per million. Paired McNemar p-values were 1.000, .268, .744, .107, .0338, and .00142. The last two are shot-level exploratory values; the six-condition correction and seed-level analysis matter. Re-analysis of the ten per-seed JSON records gives two-sided Wilcoxon p-values .1.000, .125, .852, .117, .334, and .078. Paired t 95% intervals on seed error-count differences include zero at all six settings. Thus no generalizable mixed-lookup improvement was demonstrated. The noise-specific PyMatching oracle tied nominal on all sampled shots. Adaptive-validation-choice errors were 12, 62, 101, 251, 418, and 700 versus fixed's 6, 39, 97, 208, 374, and 663.

`qshift_time_varying_results.json` is a single six-segment, 600,000-shot stream (seed 20261222) with a 1,000-shot detector window. Fixed and adaptive both recorded 120 residual errors; nearest-regime lookup recorded 155. Regime estimation accuracy against the nearest trained p was 77.5%. This is one sequence and cannot establish adaptive performance.

The single-seed design sweep tested code distances/rounds and depolarizing, bit-flip, phase-flip, and measurement-flip channels. At p=.003 it reported lookup/matching counts: d3/r3 depolarizing 9/7; d5/r5 48/2; d3/r5 42/19; bit-flip 43/34; phase-flip 0/0; measurement 18/3. The phase-flip Z-memory case had no raw observable errors and is an uninformative negative control, not evidence of success. The 24-detector d5 case showed sparse pattern encoding worked but lookup accuracy did not scale. These are explicitly exploratory single-seed checks.

Smoke outputs in `qshift_research_smoke.json` and `qshift_scalability_smoke.json` use only 1,000 test shots per condition and are not research estimates.

## 4. Noise-composition Phase 1

Phase 1 retained the distance-3 repetition-memory ideal circuit (5 qubits, 8 detectors, one observable) and inserted X-biased, Z-biased, depolarizing, and measurement-flip channels; it also held out mixed X/Z and data-plus-measurement. Data and measurement p were each .01 per local operation, so the combined condition intentionally had more fault opportunities. The data channel was independent single-qubit Pauli noise on participating qubits, not a correlated two-qubit gate model.

The final guarded result `composition_results_v4_guarded.json` used ten fresh roots beginning 20271215, 30k training and 10k validation shots per trained regime, and 20k test shots per condition/seed (200k per condition). It split validation for threshold and decoder policy selection. Static pooled lookup had more errors than matching in five of six conditions; it had one fewer on Z-only without meaningful evidence. Noise-informed matching tied nominal on all samples. The held-out data-plus-measurement lookup was worse (605 vs 550 errors, paired adjusted p about .000234 per the report/result).

The causal stream had 12 blocks × 4,000 shots × 10 seeds = 480,000 shots. Fixed, guarded adaptive, and oracle matching each had 622 errors. The guarded policy made zero switches; 94.4% is regime-label recognition, not adaptive decoding. An earlier rate-only selector switched 29 times and recorded 589 errors versus fixed 558 on its separate stream, with 58 adaptive-only and 27 fixed-only failures (reported p≈.00102). Held-out mixtures mapped to nearest trained classes; this did not identify novelty.

**Unresolved source discrepancy:** the Phase 1 `REPORT.md` lists per-regime lookup counts 562, 46, 323, 100, 209, 612 across the six aggregate conditions, while `results/composition_results_v4_guarded.json` lists 565, 44, 374, 89, 185, 634. Raw files were not replayed here. Master machine-readable results follow the JSON, while both source values are preserved in the master report. This does not change the guarded stream result or its zero decoder switches.

Earlier `composition_results.json`, v2, and v3 are preserved as distinct development outputs; the final report relies on guarded v4. Smoke v4/v5 result sets are small and excluded. Raw checksums in the v4 and guarded-v4 manifests were verified (11 and 10 files respectively), but the raw arrays were not re-decoded in this documentation pass. **Finding:** detector regime recognition did not yield validated decoder improvement.

## 5. Specialist PyMatching Phase 2

Phase 2 calibrated X-, Z-, depolarizing-, and measurement-only DEM/PyMatching models at nominal p=.01. Per seed it generated 30k calibration shots per family, 10k validation shots per six conditions, and 30k paired test shots per six conditions; 10 seeds gave 300k shots/condition. Calibration probability was fit from detector-pattern likelihood on a fixed p grid, without labels. Fixed nominal was depolarizing p=.01; oracle matching knew the simulated condition. DEM conversion used Stim `approximate_disjoint_errors=True`.

Across X, Z, and depolarizing specialists the corrections exactly matched fixed matching on every tested sample. Measurement-only specialist changed few predictions and worsened several conditions. The validation-selected oracle chose fixed for all 60 seed-condition choices. No specialist passed the 24-comparison usefulness gate, so no detector-only selector was implemented.

The source discrepancy about totals is resolved by the structured JSON: fixed has 2,402 errors/1.8m; condition-specific `oracle_noise_specific` has 2,401/1.8m because it has 92 vs fixed's 93 measurement-only errors and ties elsewhere. The **validation-selected oracle strategy** chose fixed everywhere and therefore has 2,402 errors. The current report's statement that the noise-specific oracle itself tied at 2,402 conflates these roles; its table and JSON show 2,401. The difference is one error and paired p=1, but the wording is still a documented report inconsistency. The raw Phase 2 manifest's ten full-run NPZ hashes passed; the arrays were not decoder-replayed here.

## 6. Rotated surface-code Phase 3A pilot

Phase 3A changed geometry to Stim `surface_code:rotated_memory_z`, d=3, 3 rounds, 9 data qubits, 8 stabilizer ancillas (4 X and 4 Z checks), 24 detectors, one `L0`; Stim reports 26 indexed qubits, of which 17 are active. It used .01 local nonidentity probability after post-Clifford locations, including ancilla participants, and no measurement noise. The model replaces `DEPOLARIZE1/2` instructions by independent `PAULI_CHANNEL_1` channels for each participant; it is not correlated two-qubit gate noise.

Version v1 passed composition fractions directly as probabilities and yielded near-50% residual rates. It is invalid and excluded. Corrected v2, v3, and v4 use the same seeds 31503001–31503003 and identical raw NPZ hashes. They are checkpoints of one pilot, not three replications. Local files show v3 added the ideal-circuit and uncertainty checks; v4 adds the common circuit-structure hash check and updated result metadata. This differs slightly from the supplied handoff's version-delta description, so the actual files/hashes are the record of authority.

The corrected pilot used 12k shots per condition/seed (36k/condition). Under X noise, fixed had 2,528 errors; X specialist 2,520. It changed 12 predictions, with 2 specialist-only and 10 fixed-only failures; exact McNemar p=.0386 unadjusted, about .463 after the 12-comparison Bonferroni gate. Differences by seed were −2,−4,−2. The pilot was inconclusive. V4 raw manifest hashes match all three NPZs; v2/v3/v4 bundles are byte-identical by hash. No selector was built.

## 7. Independent surface-code replication Phase 3B

Phase 3B froze the corrected Phase 3A implementation and protocol before final sampling. It used 20 fresh seed roots and 30k paired shots/condition/root across X, Z, depolarizing, and held-out mixed X/Z (2.4m total). The primary test was X specialist versus fixed under X-biased noise. The source and v4 result hashes were pinned; raw checksums were verified; ideal sampling and aggregate/per-seed arithmetic passed.

Primary result: fixed 43,673/600k; X specialist 43,675/600k. The specialist disagreed with fixed 162 times, with 82 specialist-only and 80 fixed-only errors. Six seeds favored X specialist, 11 favored fixed, and three tied. Mean seed-level rate difference was +0.00000333; bootstrap 95% CI was [−0.0000400,+0.0000433]; exact sign p=.3323; pooled McNemar p=.9374. No confirmed advantage. Secondary tests were Holm-corrected and none supported a specialist advantage. The branch was stopped for this circuit/noise setup. Raw data were hash/shape checked and aggregates reconciled, but decoder outputs were not rerun from all raw shots during this master-document task.

## 8. Current and proposed next work

No Phase 4A experiment has been run. A bounded proposal is included separately. It would first validate explicit two-qubit gate-noise and measurement-noise construction, then compare fixed nominal matching to an independently calibrated decoder on paired test shots. It should stop before any selector or classifier if the calibrated model does not produce useful, repeatable correction changes. This proposal remains unapproved future work (evidence level 5).
