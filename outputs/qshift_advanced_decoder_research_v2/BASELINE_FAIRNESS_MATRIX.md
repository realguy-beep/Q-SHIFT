# Baseline Fairness Matrix

All rows below are proposed future protocol arms; none were executed for this draft. Every deployable arm receives the same detector sequence, disjoint template/calibration/tuning allocation, p-grid, cached graph availability, and update boundaries. All arms are scored against the same observable shot outcomes, which are unavailable to the policies.

| Policy | Inputs available to policy | Update/use timing | Calibration and tuning | Cache and compute accounting | Status |
|---|---|---|---|---|---|
| Fixed nominal p=0 ordinary MWPM | No stream data needed after frozen circuit/template | Same graph for all evaluation shots | Common graph template only; no outcome selection | Charge graph build once, amortize at frozen horizon, then decode CPU | Deployable reference |
| Pooled burst-aware static MWPM | Detector-only pooled calibration mixture; no eval data | Select one p before evaluation using a frozen profile-likelihood/template-distance rule, fixed thereafter | Independent calibration roots; fitting and mixture rule frozen; no logical labels for primary static | Same p-grid/cache and calibration shot budget; charge profile fit, selection and shared bank | Strong primary comparator |
| Development-label-selected static p | Detector and logical labels from separate development selection set | Fixed p chosen before evaluation | Disclose extra labeled data, candidate count and selection cost | Same graph bank; disclose supervised privilege separately | Secondary only, unfair as primary detector-only baseline |
| Existing batch-profile Q-SHIFT | Detector-only warm-up profile | One estimate before scored block 1; no later update | Same warm-up length and profile templates; no labels | Include profile extraction and graph selection; cached graph bank | Deployable reference |
| Trailing window | All detector rows strictly before current block; fixed window length | Refit at prespecified block starts; decisions affect next block | Window length fixed on disjoint tuning roots | Same bank; charge feature computation, index choice, decode | Causal adaptive baseline |
| EWMA | Detector-only chronological summaries strictly in past | Update EWMA after block; use on next block | Alpha and initialization fixed from tuning data | Same bank; charge update and decode; no hidden recalibration | Causal adaptive baseline |
| Periodic recalibration | Detector-only observations since last scheduled update | Refit at fixed intervals known in advance; only future blocks | Interval frozen on tuning roots | Same bank; charge every refit/update and decode | Causal adaptive baseline |
| Event-triggered | Detector-only change statistic/profile, strictly past | Update after accepted alarm at block boundary; future blocks only | Threshold/hysteresis/dwell frozen on separate calibration+tuning roots | Same bank; charge statistic, alarm decision, switch and decode; include threshold-tuning amortization | Candidate; no assumed advantage |
| Privileged true-p reference | Exact generating p, possibly block mean | May use oracle schedule at future blocks, strictly diagnostic | No deployable calibration; true p is prohibited for all other methods | Charge its exact graph lookup/decode; report privilege | Diagnostic only, not a lower bound |

## Decoder modes

Run all applicable policies under two separate modes: (1) ordinary MWPM and (2) explicitly correlation-aware MWPM. Use the same generated detector/observable arrays in both. Freeze whether mode comparison is secondary or co-primary; this draft recommends ordinary-only primary because it directly isolates adaptive weight updates and avoids selecting a decoding mode after results. Correlation-aware mode is a prespecified secondary analysis. Do not mix mode observations or treat configuration labels as proof that the mode was enabled.

The Stim detector error model currently uses `decompose_errors=True` and `approximate_disjoint_errors=True`; document the resulting approximation. For each graph construction, set `enable_correlations=MODE_FLAG`; on every call to `decode` or `decode_batch`, also pass `enable_correlations=MODE_FLAG`. A source audit must verify both constructor and decoder call sites. Prior Stage 4/Phase 3A on/off results that omitted the decode keyword are ordinary-default comparisons and cannot validate the correlation-aware mode. Pilot 2 did pass it at both points.

## Equal-information and chronology rules

1. Share calibration/tuning shot allocations across all deployable arms. Separate those roots from evaluation roots. Keep the pooled-static calibration representative of the same intended mixture; freeze a detector-only profile-likelihood/template-distance rule for selecting its one p; do not give adaptive policies extra detector data.
2. Give all policies the same fixed p-grid and graph cache. Reusing constructed graphs is allowed only if the graph weights and mode are identical; otherwise construction is separately charged. Report both shared one-time cost and policy-specific cost.
3. Process detector rows in their original order. A policy chooses the decoder for a block using only strictly earlier rows. Current block rows can update state only after that block has been decoded and scored. Assert chronology mechanically in a future runner.
4. Exclude warm-up/calibration/tuning shots from scored LER. Apply identical exclusion boundaries to all policies.
5. No deployable arm receives observable bits, logical labels, scenario name, schedule, or true p. Static selection for the primary comparator uses the prespecified detector-only mixture/profile rule. The supervised static reference is separately marked.
6. Pair each arm on identical shot arrays. Do not regenerate data per arm, mode, or graph selection.

## Cost report

Report template generation, graph-bank construction, calibration, threshold/window/alpha/period selection, online profile/statistic processing, graph-index switches, decode CPU, wall time, total CPU, peak process RSS, and storage separately. Present total cost at a frozen deployment horizon `H`; event-specific one-time calibration cannot be ignored. Pilot 2 showed an apparent online-CPU advantage but the event's 6.922 CPU seconds of threshold calibration/tuning erased that advantage at its 160-stream horizon. The next protocol must choose and justify H before seeing evaluation outcomes. Timing a shared cache once and charging it only to one arm is unfair; report shared cost explicitly and allocate it consistently.
