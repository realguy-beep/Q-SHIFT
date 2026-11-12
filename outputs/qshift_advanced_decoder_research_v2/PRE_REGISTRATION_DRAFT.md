# Phase 2 Pre-registration Draft

**Not registered; no sampling authorized.** The fields below must be reviewed, completed, hashed, and approved before any future run.

## Question and population

Evaluate detector-only causal decoder adaptation on the existing d=3, five-round rotated Z-memory and graphlike `X8 X10` burst model under four prespecified nonstationary schedules. A fifth core stationary setting/set of settings is a harm check. Measurement-noise mismatch is a separately reported stress stratum. This is a synthetic development domain, not a hardware claim.

## Primary outcome and estimand

For every independent stream, compute per-shot unconditional logical loss for event-triggered ordinary MWPM and pooled detector-only burst-aware static ordinary MWPM on the same scored shots. Compute the paired stream mean difference (event − static). Within each of four nonstationary scenarios, average stream means equally; average the four scenario means equally. No adaptive selection on evaluation outcomes.

## Primary decision rule

Practical threshold: absolute improvement 0.0002. Declare the primary result successful only if the upper endpoint of a one-sided 95% stream-cluster interval for the primary estimand is strictly less than −0.0002. A value below zero but above −0.0002 does not meet the practical criterion. Report estimate, interval, each scenario estimate, stream-level differences, discordant pairs and all exclusions. The threshold and interval procedure must be approved before data generation.

## Uncertainty and multiplicity

Proposed uncertainty unit: independent generated stream/root, stratified within each scenario and resampled while retaining each stream's paired shot outcomes across arms. The exact cluster interval algorithm, number of replicates, randomization seed source (if bootstrap randomness is used), and small-cluster diagnostics remain to be frozen. No shot-level bootstrap. If primary stream count is small, do not represent nominal intervals as confirmatory.

Only ordinary mode/event-minus-static is primary. Correlation-aware mode, mode interaction, other adaptive/static/oracle contrasts, scenario-level tests, parameter-estimation diagnostics and operational metrics are secondary. Supervisor must choose a fixed hierarchical gate or multiplicity correction (e.g., Holm within declared secondary families); otherwise report secondary intervals descriptively without pass/fail language.

## Arms and information boundaries

Include nominal fixed p=0; pooled burst-aware static; batch-profile Q-SHIFT; trailing window; EWMA; periodic recalibration; event-triggered policy; privileged true-p diagnostic. Any supervised development-label-selected static decoder is secondary and privilege-labeled. Each adaptive policy uses only strictly prior detector data. Update after block b may affect only block b+1 or later. No deployable policy sees observables, logical labels, scenario identity, schedule, or true p. Correlation mode must be explicitly enabled at construction and every decode call.

All policies share data, p-grid/cache, calibration budget, tuning opportunities, and block boundaries. Calibration/tuning/evaluation roots must be disjoint. Thresholds, window length, EWMA alpha, periodic interval, profile model, candidate selection rule, initialization, dwell and hysteresis are frozen from development/tuning data before evaluation. The strong static comparator receives at least as much detector-only calibration information as any adaptive arm.

## Schedule, budget and exclusions

Exact burst probability values, change times, shot/block counts, mismatch probability, graph p-grid, warm-up and calibration allocation, stream count, hardware/software version and total budget are supervisor decisions still open. Candidate budgets are A=280k, B=1.2M, C=10.26M; none is selected. Exclude only prespecified invalid streams or detector-generation failures, never based on outcome; log all attempted streams and reasons. Avoid seeds overlapping any protected evaluation inventory without opening those inventories; an authorized custodian may certify separation.

## Secondary metric definitions

- Stationary harm: event minus static unconditional LER under no-change conditions; margin to freeze before sampling (provisional +0.0002).
- Adaptation delay: shots from scripted transition to first subsequent decoded block whose selected p-grid graph is closer to the new regime's nearest grid point than the prior regime's graph; right-censor when unobserved by next transition/end.
- False alarm: accepted event in constant-probability segment per 1,000 eligible detector shots; separately log raw crossings.
- Switch: change in cached graph index used for the next block; do not count initial selection.
- Cost: template/graph construction, calibration, tuning, detector-profile/statistic processing, switch-selection, decode CPU/wall, total cost at frozen deployment horizon, peak process RSS and stored bytes. State allocation of shared cache cost.
- Parameter-estimation error is diagnostic; it is not a surrogate efficacy endpoint.

## Stopping, integrity and reporting

Stop before evaluation for hash mismatch, seed/root overlap certification failure, chronology violation, flag mismatch, data/outcome alignment error, calibration leakage, unequal information, unsupported resource envelope, or shot-budget overrun. Stop development escalation if practical precision is infeasible under observed dependence or if event cost/false-alarm constraints cannot be met without retuning on evaluation. Do not alter hypotheses, margins, endpoints, or scenario weights after evaluation access. Preserve all negative results and audit logs. No independent confirmation claim from development data.

## Open freeze fields

Supervisor/owner must approve: final scenario probabilities/timing; exact stationary set and mismatch design; static mixture calibration rule; event/trailing/EWMA/periodic tuning sets and candidate spaces; stream-cluster interval implementation; stationary non-harm margin; deployment horizon and cost rule; budget and resource limits; whether a variance reconnaissance is justified; seed separation certification approach; and independent reviewer/auditor. Until approved and separately authorized, status remains draft/no experiment.
