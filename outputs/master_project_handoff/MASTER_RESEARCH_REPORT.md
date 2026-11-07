# Q-SHIFT Master Research Report

**Scope.** This is a documentation and evidence-integration pass over the local Q-SHIFT materials available on 2026-11-04. It does not rerun decoding or sampling, and it does not authorize Phase 4A. Earlier phase files remain in their original directories.

## Executive conclusion

The available evidence does **not** establish that adaptive Q-SHIFT decoding improves on fixed PyMatching. Small repetition-code work found pooled lookup usually worse; guarded adaptation selected fixed matching throughout. Specialist PyMatching models did not help on the repetition-code study. A rotated surface-code pilot showed a small X-specialist advantage on three reused seed roots, but its preregistered independent replication did not reproduce it: fixed had 43,673 errors and the X specialist 43,675 on 600,000 paired shots, with near-zero seed-level difference and no statistical support. The correct research conclusion is “no demonstrated adaptive or specialist advantage under the tested models and noise assumptions,” not “Q-SHIFT is impossible” and not “adaptive superiority.”

The most defensible next step is a small, preregistered **model adequacy** study: establish whether the surface-code noise model captures intended gate and measurement faults, calibrate the fixed and specialist DEM weights on separate samples, then compare paired test shots. Do not build an adaptive selector unless a specialist first provides repeatable value.

## Project path and evidence organization

The historical prototype is at `C:\Users\LENOVO\Downloads\Q-SHIFT_v0.1_starter`. Successive research outputs are under this report’s parent `outputs` directory: early experiments, `noise_composition_phase`, `phase2_specialist_decoder`, `phase3_geometry_investigation`, and `phase3b_independent_replication`. The new handoff package is separate in `outputs\master_project_handoff`. `FILE_INVENTORY.md` enumerates discovered local artifacts; `EXPERIMENT_REGISTRY.csv` indexes experiment families and evidence class; `RESULTS_MASTER.json` preserves selected structured outcomes and paths.

## Historical prototype and metric interpretation

The expanded starter dataset has 150,000 rows, 8 detector bits, 1 observable label, and three nominal noise settings. The eight detector patterns occupy only 61 unique vectors; 149,883 complete rows repeat another row. Random row splitting therefore permits repeated patterns and duplicates across partitions. Noise probability and noise group are simulation metadata, not detector-time inputs. A saved pickle exists but was not loaded because unpickling can execute code and its provenance is not needed to evaluate later controlled experiments.

The early classifier had high balanced accuracy largely because it identified the overwhelmingly common no-logical-flip class. The rare positive class was only 200/37,500 in the cited conversation result; precision 0.41 implies many false alarms despite recall 0.98. The accompanying XOR correction experiment was reported to increase residual error from 0.5333% to 0.7573%. These are conversation-reported results without matching local raw artifacts, so they are historical context, not independently verified results. Predicting `logical_error` and XORing its guess is only a valid correction if the label means the sampled logical observable flip, inference uses detectors alone, and evaluation computes `sampled_observable XOR predicted_correction` on independent shots. Training a label classifier alone does not validate decoder performance.

The expanded starter script uses a 105k/22.5k/22.5k train/validation/test split; that differs from the older conversation report's 112.5k/37.5k split. No claim is made that the saved model generated that report.

## Phase 1: noise composition and detector adaptation

The repetition-code experiment used distance 3, three rounds, 8 detectors and one logical observable. Four regimes were trained, two mixtures held out, and ten independent seed families were used in the guarded study. Each condition had 200,000 paired test shots total. The guarded selector required independent validation evidence before selecting a lookup table. It chose fixed PyMatching for all regimes; consequently the adaptive stream tied fixed at 622/480,000 and made zero switches. Regime-label recognition at 94.4% did not translate into better decoding. An earlier rate-only policy performed worse (589 vs 558 errors on a separate stream).

The structured `composition_results_v4_guarded.json` reports fixed/nominal matching equal to oracle matching on all six static conditions. Pooled lookup totals were worse in five conditions and one error better in Z; per-regime lookup totals also exceed fixed in most conditions. **Source discrepancy:** the current Phase 1 `REPORT.md` prints per-regime totals 562, 46, 323, 100, 209, 612; the JSON aggregate prints 565, 44, 374, 89, 185, 634. Raw and manifest files exist, but this handoff did not replay their decoder outputs. The master tables therefore use the structured JSON aggregate as the machine-readable result and retain the report's conflicting figures here. Treat per-regime Phase 1 totals as unresolved until a raw-data replay reconciles them. This discrepancy does not alter the primary guarded result: no adaptive benefit was demonstrated.

## Phase 2: specialist PyMatching models

Ten seeds tested fixed nominal matching, calibrated composition specialists, and condition-informed matching over six conditions. X-, Z-, and depolarizing-specialist corrections were exactly the same as fixed matching on tested shots. Measurement-only specialist differed rarely and did not yield a validated gain. Validation selected fixed for all 60 seed-condition choices, so the usefulness gate failed and detector-only specialist selection was correctly not implemented. The JSON gives 2,402 fixed errors and 2,401 condition-specific oracle errors over 1.8m shots; the 2,402 validation-selected strategy is a different quantity. The Phase 2 report conflates these in one narrative sentence; its table and JSON distinguish them. One error is not evidence of a useful oracle advantage.

## Phase 3A: surface-code pilot

The geometry changed to Stim `surface_code:rotated_memory_z`, distance 3, three rounds, 24 detectors, one logical Z observable. The pilot used a local single-qubit Pauli channel inserted after CX participant locations and no measurement noise; it is not a correlated two-qubit gate-noise model. Version 1 applied invalid probability scaling and is excluded. Corrected v2/v3/v4 use the same three seed roots and identical raw sample hashes: they are development checkpoints, not independent replications.

Under the primary X-biased condition, fixed made 2,528 errors and the X specialist 2,520 on 36,000 shots. There were 12 disagreements (two specialist-only and ten fixed-only failures); unadjusted exact McNemar p=.0386, but the 12-way adjusted p≈.463. This is exploratory and inconclusive.

## Phase 3B: independent replication

The frozen study used 20 fresh seed roots, 30,000 paired shots per condition and four conditions (2.4m total). The primary X-noise comparison had 43,673 fixed errors versus 43,675 X-specialist errors on 600,000 shots. Specialist and fixed differed on 162 shots: 82 specialist-only errors and 80 fixed-only errors. Six seed roots favored the specialist, 11 favored fixed, and three tied. The mean seed-level rate difference (specialist minus fixed) was +0.00000333, with bootstrap 95% CI [−0.0000400, +0.0000433]; exact seed sign p=.3323 and pooled McNemar p=.9374. No confirmatory benefit was found. Secondary comparisons were Holm-corrected and did not support a specialist advantage.

## Answer to the research question

1. **Can the tested decoder distinguish useful noise composition?** Phase 1 detector windows recognized trained regimes well (94.4% in its particular schedule), but this was a classifier metric. It did not validate that regime recognition changes the best correction. Phase 2 specialist decoders generally returned identical corrections. Phase 3 did not validate a useful specialist distinction in independent replication.
2. **Does adaptation outperform fixed decoding?** No tested deployable adaptive policy has shown a reproducible improvement. Phase 1 guarded adaptation stayed fixed. Phase 2 did not pass the specialist usefulness gate. Phase 3B found no X-specialist benefit.
3. **Does it generalize to unseen mixtures?** No reliable adaptive generalization is established. In Phase 1, held-out mixtures were mapped to nearest known regimes; no novelty detector was demonstrated.
4. **How fast does it adapt?** Phase 1 reported approximately 530 shots to recognize a trained regime change; because it never switched decoders, a decoder adaptation delay is not applicable. There is no validated deployable adaptation latency for a policy that improves decoding.
5. **What is the overhead?** Phase 1 reported approximately 0.32 ms per 500-shot window for estimation/switch bookkeeping, in addition to batched decoding. This is software-specific and its guarded policy made no switches. Other phase timings/memory are local implementation approximations and exclude some native allocations.
6. **What supports or contradicts the hypothesis?** Detector regime classification and a small unadjusted Phase 3A pilot offer motivation, but neither survived an appropriate validation gate/independent replication. The guarded Phase 1, Phase 2 usefulness gate, and Phase 3B replication contradict a claim of demonstrated performance advantage.

## Limitations and provenance

See `METHODOLOGY_AND_LIMITATIONS.md`, `FAILED_AND_NEGATIVE_FINDINGS.md`, and `FILE_INVENTORY.md`. Not all raw NPZ arrays were re-decoded in this documentation pass. Checksums and aggregates were reviewed for Phases 1–3B as noted in the handoff audit, but that is not the same as reproducing every decoder prediction. The local personal-notes DOCX was text-extracted; visual rendering could not be performed because LibreOffice (`soffice.exe`) was unavailable. No hardware integration is claimed.
