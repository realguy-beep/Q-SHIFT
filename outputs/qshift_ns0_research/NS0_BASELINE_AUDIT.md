# NS-0 baseline and evidence audit

**Checkpoint:** `5c8f50d00f003f3f79a3d07e00541ad2a3378523` (`qshift-advanced-research`).

**Classification:** read-only source/result audit; no experiment, training, decoder evaluation, seed allocation, or protected Stage 5 outcome access.

## Decision-relevant baseline

The reported **21.9%** error-reduction number is **not verified** by an accessible, cited repository report/result. A scoped search of the tracked research reports and result summaries outside protected Stage 5 paths did not find that number or a calculation that yields it. Do not describe it as validated.

The nearest explicit result is the Phase 4 development report, which says **22.727% relative reduction** on an *equal-weight average of the four nonzero burst settings* (p-burst `.004`–`.016`), not on all shots/conditions. Recomputing its table gives 506 fixed errors versus 391 detector-estimated errors across those four equally sized cells: `(506-391)/506 = 22.727%`. Including the p=0 cell gives 590 versus 474 errors and `(590-474)/590 = 19.661%`. These are distinct development summaries. The report states 7 roots per condition, a synthetic distance-3/five-round Z-memory circuit and no independent confirmation. The quoted 21.9% cannot be substituted for either value without tracing its original numerator, denominator, condition weights and artifact.

## Existing evidence ledger

| Method / claim | Saved evidence | Status and limits |
|---|---|---|
| Fixed nominal PyMatching | `outputs/stage4_noise_adaptive_development_v1/STAGE4_RESULTS.md`; `outputs/qshift_v2_dev_v1/REPORT.md` | Strong recurring conventional comparator. Phase 4 table: 590/87,500. Synthetic d=3/five-round evidence only. |
| Batch detector-estimated Q-SHIFT | Phase 4 report and `RESULTS.json` | 474/87,500 vs fixed 590/87,500; privileged true-p reference 476/87,500. Reported primary development interval was root-clustered; seven roots/condition. The estimate/model family is narrow and not hardware validated. |
| Calibrated static PyMatching | `outputs/phase4c_strong_baselines/stage2/STAGE2_RECOVERED_RESULTS.md`, `STAGE2_RECOVERED_STATISTICS.md`, `STAGE2_RECOVERED_LIMITATIONS.md` | 60 saved roots were re-decoded; equal-regime calibrated-minus-pooled-fixed `+0.00001556` LER, stratified bootstrap 95% CI `[-0.00004889,+0.00007667]`, sign-flip p `.66658`. Calibration arrays/traces were not saved, so calibration provenance could not be independently refit. This is not evidence that calibrated beats a tuned fixed baseline. |
| Correlation-aware PyMatching | `outputs/phase3a_correlated_noise_preflight/PHASE3A_FINAL_REPORT.md`; `outputs/qshift_v2_dev_v1/REPORT.md` | Phase 3A was plumbing/preflight; 256-shot smoke had identical corr-on/off predictions while burst-inclusive graph changed 3 predictions vs the frozen model. The later v2 pilot had 10 streams (2/schedule), 7,000 total generated shots, no paired per-shot error log, and descriptive ordinary/correlation-on counts of 99 vs 115 errors over 21,000 policy predictions/mode. Neither result establishes correlation-aware benefit. |
| Causal / adaptive Q-SHIFT | `outputs/qshift_v2_dev_v1/REPORT.md`; Phase 4 report | The v2 event arm did not consistently beat EWMA/trailing/static; threshold was uncalibrated, response delay and per-arm costs were not measured, and only two streams/schedule were run. Phase 4 batch estimation improved a synthetic burst setting but is not evidence for causal online switching. |
| Neural decoders | `outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/POSITIONAL_CNN_REPORT.md`; `outputs/cnn_architecture_stage2_v1/CNN_STAGE2_RESULTS.md`; `outputs/cnn_stage3_residual_gate_v1/CNN_STAGE3_RESULTS.md`; `outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/post_run_audit/FINAL_RESEARCH_REPORT_AUDITED.md` | Multiple paired development comparisons did not beat fixed PyMatching. Detailed audit in `PREVIOUS_NEURAL_FAILURE_AUDIT.md`. |

### Correlation flag audit

The Phase 3A builder converts with `decompose_errors=True, approximate_disjoint_errors=True`, and constructs matchers using `Matching.from_detector_error_model(dem, enable_correlations=...)`. In the historical Phase 4 path the object was constructed with `enable_correlations=True`, but `decode_batch` omitted its own `enable_correlations` argument; PyMatching defaults that decoding option to false. The v2 development pilot explicitly passed the same on/off choice at decode time. PyMatching documents a two-pass procedure that uses decomposable hyperedge metadata, not general exact hypergraph ML. Stim's DEM is an independent-mechanism representation; Phase 2B's categorical Pauli-channel conversion requires the declared disjoint-error approximation. Therefore “correlation-aware” describes a decoder mode and input representation, not proof of circuit-level optimality.

## Source/version map

The present advanced branch is at Phase 3B implementation readiness; it contains Candidate A/B finite-history estimator code and a gated, resumable runner, but **no generated finite-history histories and no decoder comparison**. The 101,000-shot pipeline pilot and 3.03-million-shot estimator study remain proposals, not results. The v2 event-controller pilot is a separate historical development package. Phase 3B's own readiness report explicitly says no sampling or decoder evaluation occurred and that a future sampling run needs a separate authorization.

Primary local files inspected are enumerated in `NS0_RESEARCH_DECISION.md`; their SHA-256 values are recorded in the git tree at this NS-0 commit via the file content and checkpoint. Protected Stage 5 paths/outcomes were not read or used. No frozen file, sealed artifact, other branch, or website worktree was modified.

## Recommendation

Keep PyMatching as the mandatory incumbent. Before building another adaptive estimator or changing the controller, test whether a decoder with genuinely different inference—first HAMLD—has paired utility headroom over both nominal and a properly selected static matching baseline on Q-SHIFT's actual circuit. If it does not, an adaptive selector over that candidate cannot create useful decoding headroom. Treat the 21.9% number as unresolved until its source is supplied or found in an authorized, unsealed historical artifact.
