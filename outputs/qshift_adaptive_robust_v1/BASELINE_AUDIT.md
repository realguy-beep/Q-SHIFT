# Baseline audit: what Q-SHIFT has actually established (2026-11-18)

**Scope.**
- **Starting point:** branch `codex/qshift-correlated-decoder-v1-6` at records commit `cdbd9d8fb`. This audit lives on the new branch `codex/qshift-adaptive-robust-v1`, created from that commit.
- **No historical file was modified.** Every number below is quoted from a committed study record. Each entry is labelled with what was re-checked in this milestone and what is relied on from prior records.

## 1. What was inspected and re-checked in this milestone

| Item | How it was checked here | Result |
|---|---|---|
| Git state | `git status`, log, branch | Tree was clean at `cdbd9d8fb`, with origin in sync |
| Core interfaces (`qshift_core_v1/contracts.py`, `controller.py`, `decoder_runtime_v2.py`) | Source read | Typed `DecoderProtocol`, `DecoderRegistry`, and `SafeDecoderSelector` (causal, confidence gate, hysteresis, dwell, fixed non-experimental fallback, detector-only `NoiseEstimate`). Never used to produce performance results (status record agrees) |
| Regression tests, before any change | Run | See §4 |
| d=5 BP+OSD implementation (`qshift_scalable_decoder_dev_v3_2/ldpc_bposd.py`) | Source read; called directly in the floor diagnostic | ldpc 2.4.1 on the undecomposed DEM matrix (`dem_to_matrix(merge=True)`). The prediction is the exact parity `L·ê`. All 56 Stage S failures reproduced deterministically |
| d=5 low-p Stage S and Stage E | Records read; Stage S dev arrays re-decoded (development only); Stage E rows **not read** | Matches `DEV_SELECTION.json` and `results_v1/ANALYSIS.json` |
| Mismatch diagnostic | `DIAG_RESULTS.md` read | Matches `RESEARCH_STATUS.md` |
| Stage 5, strong fixed baselines, Phase 4C, neural | Final reports and status read | Quoted, not re-run |

## 2. Evidence matrix

**Legend:**
- **C:** confirmed. A frozen, pre-registered, fresh-seed evaluation that passed its integrity checks.
- **D:** development-only.
- **F:** failed or inconclusive.
- **O:** oracle or privileged information.
- **U:** implemented but unvalidated.

All entries are simulation only. **"R" is the relative LER reduction against a named comparator. It is not decoding accuracy**: all decoders here have > 99.9% shot accuracy at d=5, p ≤ 0.003.

| Line of work | Class | What it shows | Privileged information used | Key record |
|---|---|---|---|---|
| d=3 exact DEM decoding (V1.4B, V1.5) | C (V1.5), D (V1.4B) | Exact decoder −61% vs correlated matching (Astar). About 80% of the gap is background inference, not burst handling | V1.5 uses the true burst support (O) | `qshift_correlated_decoder_v1_5/results_v1/RESULTS.md` |
| d=3 learned support (V1.6 gate, V1.6b) | F (V1.6: detector-only support not identifiable), C (V1.6b) | Device-level support plus a *labeled* logical stage: −61.5% known, −52.4% sealed hidden | Uses labeled calibration shots (logical labels during calibration) | `qshift_correlated_decoder_v1_6b/results_v1/RESULTS.md` |
| d=5 serial BP+OSD, static prior (Phase 2) | C | −64.8% [61.2, 68.4] vs Astar; −46% at q=0 | True support (O) | `qshift_scalable_decoder_eval_d5_phase2_v1/results_v1/RESULTS.md` |
| d=5 robustness (F2, P2, P4) | C | 20.9% / 78.1% / 56.8% | True support (O) | `qshift_d5_robustness_v1/results_v1/RESULTS.md` |
| d=5 learned support (Phase C) | C | K 59.8%, H 44.8% vs *true-support* Astar | Learner assumes the **true base model**; uses labeled calibration shots | `qshift_d5_learned_support_v1/results_v1/RESULTS.md` |
| d=5 base-model mismatch (Phase A) | D, negative | Learner fails under ±17% p and under Z-bias | none (diagnostic) | `qshift_d5_model_mismatch_v1/DIAG_RESULTS.md` |
| d=5 low-p Stage E | C overall; **target F** | 94.0% [92.3, 95.5] at p=0.001; 93.1% at p=0.0015; 95% target not met | True support and exact base model (O). The regime was chosen for reachability | `qshift_d5_lowp_regime_v1/results_v1/RESULTS.md` |
| d=7 BP+OSD and parallel belief-matching | F (STOP) | Ties or loses to Astar | n/a | `qshift_scalable_decoder_eval_d57_v1/`, `qshift_belief_matching_d7_v1/` |
| Stage 5 detector-profile adaptive PyMatching (d=3) | C vs **nominal** fixed | Endpoint B passed; no-harm passed | Privileged true-p arm reported separately | `stage5_final_evidence/FINAL_STAGE5_REPORT.md` |
| Strong fixed baselines v1 (d=3) | D, with a disclosed protocol deviation | Adaptive ≈ pooled-static: −2.9e-5 absolute, far below the 2e-4 practical benchmark | Legacy pooled estimator leaked condition tags (deviation, reconstructed) | `RESEARCH_STATUS.md` §Strong fixed-baseline |
| Phase 4A/4B/4C calibrated matching | D / PASS WITH DEVIATION / null | 4C: calibrated − pooled-fixed = +1.6e-5, p = 0.67 | Calibration arrays missing (4C) | `RESEARCH_STATUS.md` |
| Neural / CNN / hybrid residual | D, negative | All neural candidates worse than PyMatching | n/a | `RESEARCH_STATUS.md`, `neural_decoder_diagnostic/` |
| Typed decoder registry and `SafeDecoderSelector` | U | Infrastructure only | n/a | `core_system_upgrade_v1/` |
| Belief-matching adapter (`research_adapters`) | U, not runnable here | Needs the `beliefmatching` package, which is not installed | n/a | `dashboard/tests/test_beliefmatching_ns2c_integration.py` |

**Two readings to keep apart:**
1. **Adaptiveness vs a better static decoder.** The strongest positive results (Phase 2, robustness, Stage E) come from a *static* decoder that models the full hypergraph DEM. They do not come from adaptation. The adaptive results are Stage 5 (beats *nominal* matching) and strong-fixed v1 (≈ pooled static). Together they show no adaptive gain over a strong static comparator.
2. **Burst handling vs background inference.** At d=5, BP+OSD is 46% better than matching even at q=0. A large share of every quoted R is therefore background-decoding quality rather than correlated-error handling.

## 3. Discrepancies between records (documented, not resolved by preference)

1. **The V1.4 "90% not reachable" gate vs Stage E's 94.0%.** V1.4 bounded *burst-oracle* ceilings at d=3/5/7 under its own decoder definitions. It found best point ceilings of 0.90–0.93 at d=5, p ≤ 0.002, with lower bounds 0.40–0.49. Stage E measured BP+OSD vs re-selected Astar at p=0.001 at 94.0%. The two use different decoders, comparators and uncertainty definitions, so they do not contradict each other numerically. But the REPORT's earlier sentence "not reachable in this noise family" was too strong. The records commit `cdbd9d8fb` has already replaced it.
2. **Stage S runtime and floor estimates.**
   - Stage S `DEV_RESULTS.md` projected "30–40 min" for Stage E. The preflight projected 3.4 h. The actual run took 73 min.
   - Stage S's in-sample R of 96.9% rested on 4 L2 background errors, and the frozen floor came out about 1.7× higher. Both points are disclosed in REPORT §6.
3. **`RESEARCH_STATUS.md` "Recommended next step"** (pooled-calibration path, CNN) predates the correlated-decoder line and was not updated by later records. It is stale, not contradictory. A new recommendation is in `DECISION_REPORT.md`.
4. **Hash mismatch, dashboard structured protocol.**
   - The file is `outputs/neural_decoder_diagnostic/structured_diagnostic_config.json`. Its sha256 is `35ea9d9b…`; its freeze (`structured_diagnostic_freeze.json`) records `1ef0e84b…`.
   - Both files arrived in the repository's first commit (`82a32b43e`, 2026-11-07), and the mismatch is not a line-ending artifact (the file is LF with no CRLF).
   - The dashboard test `test_structured_api_uses_frozen_multiregime_allocation_and_keeps_test_reserved` therefore errors. The test is doing its job.
   - **Not modified.** The correct action is an owner decision: locate the original config bytes, or record the deviation.
5. **"No adaptive advantage over strong fixed PyMatching" (status header) vs Stage 5 "Endpoint B passed".** These are consistent: Stage 5's comparator was *nominal* fixed matching. Only the strong-fixed and Phase 4C studies compared against a strong static matcher, and both were null.

## 4. Regression tests, run before any change in this milestone

| Suite | Result |
|---|---|
| `dashboard/tests` (unittest discover) | 120 tests, 118 pass, **2 errors, both pre-existing**: (a) `beliefmatching` not installed (environment); (b) the hash mismatch in §3.4 |
| `qshift_d5_lowp_regime_v1/tests` | 13 pass (4 + 9) |
| `qshift_d5_model_mismatch_v1/tests` | 6 pass (pytest; `unittest discover` finds 0 because the file uses pytest-style functions) |
| `qshift_d5_learned_support_v1/tests` | 24 pass |
| `qshift_d5_robustness_v1/tests` | 9 pass |
| `phase4c_strong_baselines/adaptive/test_core.py` | 6 pass |

The same suites were re-run after this milestone's changes (`DECISION_REPORT.md` §2). This milestone adds files only, in a new directory, and changes no existing source.
