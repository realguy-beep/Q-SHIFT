# Q-SHIFT Phase 2 — Research Protocol Draft

**Status:** draft for supervisor review; no experiment authorized.

**Source branch/base:** `qshift-advanced-research` at `5c2e701bee4eed17b4fb6201123341c488a0002e`.
**Scope:** detector-only causal adaptation for the existing distance-3 rotated Z-memory, five-round circuit and graphlike `X8 X10` burst model. This document does not change that model or any frozen implementation.

## 1. Research question and claim boundary

Can a detector-only, event-triggered controller choose cached matching graphs after detecting a change in burst probability, and reduce unconditional logical-error risk versus a well-calibrated pooled burst-aware static decoder, while maintaining acceptable stationary risk and total compute cost? Does that answer change when matching is explicitly correlation-aware?

The narrow proposed claim is conditional: **on the frozen synthetic circuit and burst schedules, a prespecified causal event-triggered policy has a practically meaningful lower stream-paired LER than pooled burst-aware static ordinary MWPM across the four nonstationary schedules, without exceeding a predeclared stationary-harm bound or deployment-horizon cost bound.** The practical absolute risk difference is 0.0002. A result that only excludes zero but not the practical margin does not support this claim.

The claim fails if the primary interval does not clear the practical margin, if the static or adaptive arms have unequal information, if any update uses current/future detectors or labels, if measurement mismatch erases the effect beyond the predeclared margin, or if calibration plus runtime costs do not amortize at the frozen horizon. A negative result is scientifically informative.

## 2. Novelty and prior art

**Established:** adapting decoder weights to changing noise, estimating drift from syndromes, and correlation-aware matching have prior art. Examples include Spitz et al. on adaptive MWPM weights ([Quantum 2, 2018](https://doi.org/10.1002/qute.201800012); [arXiv:1712.02360](https://arxiv.org/abs/1712.02360)), Bhardwaj et al. on syndrome-based drift estimation ([PRX Quantum 7, 033024 (2026)](https://doi.org/10.1103/z1hc-nqw5); [arXiv:2511.09491](https://arxiv.org/abs/2511.09491)), and detector-error-model / matching approaches including DGR ([arXiv:2311.16214](https://arxiv.org/abs/2311.16214)). These references establish context, not equivalence of task or results.

**Existing Q-SHIFT contribution:** a 45-feature detector-only profile estimator, cached p-grid matching, and a causal event controller evaluated in development Pilot 2. This is not independent confirmation. Pilot 2 did not clear its frozen LER rule in either decoder mode, response delays were 45 shots on step-up and 95 on step-down, and its calibration cost failed to amortize on the 160-stream horizon as charged. These observations are planning evidence only.

**Proposed contribution:** a fair, cost-aware comparison of change-triggered and simple causal update policies under matched detector information, explicit chronology, abrupt and gradual drift, transient changes, and measurement-model mismatch. Do not describe adaptation, syndrome estimation, or correlated matching alone as novel, or claim priority without a separate literature review.

**Unproven:** that burst probability is identifiable from the detector-only profile under this circuit; that the `X8 X10` event creates useful correlation-aware headroom; and that event-triggering beats simpler causal baselines after all costs.

## 3. Frozen scientific object and correlation-mode audit

Keep the Phase 1 proposal's distance-3 rotated Z-memory, five syndrome rounds, 40 detector bits, one observable, gate/readout p=0.003, and independent-across-rounds `CORRELATED_ERROR(p) X8 X10` burst mechanism. Evaluate five core conditions (stationary, abrupt increase, abrupt decrease, smooth drift, transient burst) and a separately reported measurement-noise-mismatch stress condition. Freeze schedule timings and probability values before any future data generation; Pilot 2 schedules may be reused only if the supervisor confirms their appropriateness. No circuit expansion is proposed here.

The existing detector error model uses `decompose_errors=True, approximate_disjoint_errors=True`; this is an approximation of categorical multi-qubit mechanisms. The `X8 X10` event is graphlike and can be represented as a matching edge, so explicit correlation-aware decoding is applicable in principle. Actual incremental benefit is unknown. Historical Stage 4 / Phase 3A comparisons that set `enable_correlations` at construction but omit it on decode use the ordinary default and are not valid on/off comparisons. Pilot 2 passes the flag at construction and decode. Future code must explicitly set `enable_correlations` both when building each matcher and in every `decode`/`decode_batch` call. Ordinary and correlation-aware modes are separate arms; report their contrast separately and do not choose the winner after evaluation.

The prior correlation-mechanism pilot used a different native categorical mechanism; its small correlation-mode effect does not establish headroom for `X8 X10`. A richer non-graphlike or higher-order mechanism would be a separately versioned future experiment, not a silent replacement in this protocol.

## 4. Hypotheses and estimands

Let each stream be an independent generated root and let shot loss be `1{decoded observable != true observable}`. Primary estimand is the equally weighted mean of the four scenario-specific stream-average paired differences, `event − pooled-static`, in **ordinary MWPM**. The four scenarios are abrupt increase, abrupt decrease, smooth drift, and transient burst. Pair methods on identical generated shots. Negative favors event adaptation.

- H1 (primary): the upper endpoint of a one-sided 95% stream-cluster interval for the primary difference is below `−0.0002`.
- H2 (stationarity guard): stationary event-minus-static risk is below the owner-approved non-harm margin; freeze that value before sampling. Suggested provisional margin: +0.0002 absolute.
- H3 (causal adaptivity): versus trailing, EWMA, and periodic baselines, report risk, delay, false alarms, graph switches and total cost; these are secondary and cannot replace failed H1.
- H4 (mode interaction): estimate event-minus-static separately in explicitly correlation-aware MWPM and estimate a paired mode interaction. Secondary only; no post hoc mode selection.
- H5 (robustness): report the separate measurement-noise mismatch stress stratum. Do not pool it into the four primary schedules.
- H6 (estimator diagnostic): parameter-estimation error is descriptive and cannot substitute for LER improvement.

## 5. Arms, information and chronology

Required deployable policies: fixed nominal p=0 ordinary matching; strong pooled burst-aware static matching; existing one-shot batch-profile Q-SHIFT; causal trailing-window; causal EWMA; periodic recalibration; event-triggered adaptation. Add privileged true-p only as a diagnostic, clearly marked nondeployable and not a lower bound. A development-label-selected static p may be reported as a secondary supervised reference only with its larger labeled-data privilege explicit. The primary static comparator is a single fixed p estimated from a prespecified detector-only pooled calibration mixture (for example, the closest grid point under a frozen profile likelihood or template-distance rule); do not select it using evaluation logical labels or choose the fitting rule after seeing evaluation outcomes.

All deployable adaptive arms receive the same chronological detector stream, calibration allocation, p-grid, graph bank/cache, and opportunity to update at the same block boundaries. They never receive observables, logical labels, scenario identity, scripted schedule, or true p. At block t, each method decodes using state built only from detector rows strictly before t; after scoring the block, those detector rows become eligible for the next update. No current block may change its own decoder. Warm-up, calibration, tuning, and evaluation roots are disjoint. Controller candidates and thresholds are frozen using tuning roots only.

Baseline details and per-arm accounting are in `BASELINE_FAIRNESS_MATRIX.md`. Cache identical graph objects where valid; report shared one-time bank construction separately from selection and decode costs. Mode-specific graph construction must be charged consistently. Evaluation arrays are shared across arms and modes; no additional generated shots are charged for replaying them.

## 6. Outcomes and analysis

**Primary:** unconditional LER and paired event-minus-static difference per stream, then equal-weight mean over the four nonstationary scenario means. Do not condition on successful parameter estimation or on alarm occurrence.

**Secondary:** stationary harm; each scenario-specific risk; trailing/EWMA/periodic/static/oracle contrasts; ordinary versus correlation-aware differences and interaction; detector-profile parameter error; change detection delay (including right censoring); false alarms per 1,000 constant-condition detector shots; graph switches; graph construction, profile/calibration/tuning, controller and decode CPU; total CPU at a prespecified deployment horizon; peak process RSS; and storage. Define a false alarm as an accepted event during a constant-probability segment, separate raw threshold crossings from accepted switches. Define delay from scripted change to first subsequent block whose graph index is closer to the new regime's nearest grid point than the old one.

Use paired stream-level differences and stratified cluster resampling by independent stream within condition. A future confirmatory analysis should use a prespecified cluster bootstrap or a validated cluster-robust alternative, with stream as the resampling unit; bootstrap replicates retain all paired arms and shots from each sampled stream. Report interval method, number of replicates, finite-cluster limitations, and raw stream summaries. The 20-stream Pilot 2 percentile bootstrap is a development interval, not a confirmatory test.

One primary contrast/mode means no primary multiplicity adjustment. Treat correlation-aware primary-like contrast, per-scenario contrasts, baseline matrix, parameter error and other secondary tests as secondary; use a fixed hierarchical gate or Holm adjustment within declared families. Report estimates and intervals even when no secondary test passes. Do not select mode, schedule, threshold, horizon or subgroup from evaluation results.

The practical effect is absolute 0.0002 LER. Require the one-sided 95% upper confidence endpoint below −0.0002, not merely below zero. Exact power is not identifiable without stream-level paired discordance and ICC estimates; Section `STATISTICAL_FEASIBILITY.md` gives analytical sensitivities, not power claims.

## 7. Decision gates and validity checks

Stop before evaluation if: stream/seed separation is not independently verified without accessing sealed inventories; warm-up or tuning overlaps evaluation; baseline inputs or calibration privilege differ without disclosure; decode/build correlation flags mismatch; policy chronology is noncausal; detector arrays/outcomes are misaligned; generation budget exceeds frozen cap; source/config hashes are absent; or required measurements breach the approved resource limits. Stop escalation if the pilot cannot estimate discordance/ICC with useful precision, if the practical effect cannot be resolved under a plausible dependence range, or if measured runtime/RSS violates the approved budget.

Reject a comparison as unfair if strong static receives weaker calibration than adaptive policies, or adaptive policies receive extra labeled outcomes. Reject event policy as noncausal on any same-block/future feature dependency. Do not tune the primary threshold or practical margin after evaluation. Preserve negative runs and all failed audits. Development results do not establish independent confirmation.

## 8. Resource and approval status

Known resource notes are approximately 2.38 GiB free system RAM, 2 GiB per-process RSS ceiling and 247.52 GiB disk; V2.4 end-to-end performance is not benchmarked. Pilot 2's 45.59 seconds / 129.2 MiB are from an earlier run and do not validate V2.4 or a larger design. The proposed confirmatory candidate's raw detector+observable table is about 420.7 MB decimal if all 10.26M shots are retained at 41 bytes/shot; storing 16 one-byte arm/mode predictions for every shot raises this simple lower-level estimate to about 584.8 MB before metadata, copies, Stim/PyMatching native allocations, logs or archives. Chunking is required. RSS and runtime remain unknown until a separately authorized resource preflight; no benchmark was run for this draft.

**Recommendation:** do not authorize the large study now. First obtain supervisor decisions on the primary mode, scenario schedules, mismatch condition, static calibration definition, practical/stationary margins, method family/multiplicity, and amortization horizon. Then authorize a bounded, nonconfirmatory variance/resource feasibility run only if it can estimate stream discordance and ICC; revise budget based on those observed development quantities, freeze the complete protocol, and seek separate approval for confirmatory sampling. No experiment is authorized by this draft.
