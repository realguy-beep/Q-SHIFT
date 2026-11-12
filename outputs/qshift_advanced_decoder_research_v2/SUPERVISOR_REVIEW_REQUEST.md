# Supervisor Review Request — Q-SHIFT Phase 2

**Decision requested:** review this protocol and determine whether a separate, bounded development variance/resource feasibility run is justified. This request is not permission to sample. No data generation or decoder benchmark has been performed for this draft.

## Recommended decisions

1. Keep ordinary MWPM as the sole primary mode and event-minus-pooled detector-only burst-aware static as the sole primary contrast. Keep explicitly correlation-aware MWPM as a separate secondary mode with both constructor and decode flags audited.
2. Preserve the existing circuit and `X8 X10` burst process. Do not change the mechanism based on the prior invalid on/off preflight or the different correlation pilot.
3. Treat the proposed 0.0002 absolute LER improvement as a practical threshold, with strict one-sided upper 95% bound below −0.0002; approve or replace it before any new evaluation.
4. Keep measurement-noise mismatch as a separate stress condition and report separately. Do not add it to the four-scenario primary average.
5. Do not proceed directly to the 10.26M candidate. A 20-stream pilot cannot resolve the margin; moderate design is also weak under modest ICC. First decide whether an approved variance reconnaissance can estimate paired discordance and between-stream variability.
6. Freeze a deployment horizon and charge event calibration/tuning. Pilot 2's lower online CPU did not offset its 6.922 CPU seconds of event-specific tuning on the observed 160-stream horizon.

## Questions requiring decision

- Are Pilot 2 schedule values and block timing scientifically suitable for the Phase 2 question, or should a new schedule be proposed without changing the original mechanism?
- Which stationary probabilities and how many independent stream roots are required for a harm/false-alarm assessment?
- What pooled detector-only mixture and calibration allocation define “strong static” without leakage?
- Should the supervised development-label-selected static arm be included as a secondary reference, with its data advantage disclosed?
- What stationary non-harm margin and total-cost deployment horizon should be frozen?
- Which change detector parameter candidates and fair tuning budget should be allowed for event, trailing-window, EWMA and periodic baselines?
- Which stream-cluster confidence interval procedure is acceptable for the final cluster count? Who independently validates its implementation?
- Is a separate nonconfirmatory variance/resource preflight justified, and what fresh development budget and stop limits apply?
- Who can certify seed separation from protected evaluation material without revealing or opening the sealed inventory?
- Is the correlation-aware mode secondary as proposed, given the graphlike event and the historical flag-omission issue?

## Material risks

- The detector profile's identifiability for burst probability under measurement mismatch remains unproved; detector feature mapping may confound burst and measurement error. A sensitivity audit of the deterministic feature map can be proposed, but must not be represented as empirical identifiability.
- The graphlike burst can be decoded with ordinary matching; correlation-aware headroom may be small. Historical on/off evidence is not a valid X8X10 test where decode flags were omitted.
- Pilot 2 did not clear its frozen LER success rule in either mode and response delays were slower than EWMA on two change schedules. This argues against presuming event-trigger superiority.
- Clustered uncertainty with only 20 roots per condition is weak; shot counts do not substitute for independent roots.
- Runtime/RSS at V2.4 are unknown. Prior Pilot 2 runtime is not a transferable benchmark.
- More than two modes and many policy contrasts invite selective reporting. The ordinary-mode primary and declared secondary family must be frozen before evaluation.

## Approval gates

No sampling, decoder benchmark, training, seed generation, authorization record, sealed-outcome access, PR creation, or protocol freeze is requested here. Before any experiment: approve the scientific question, scenarios and margins; approve a fresh data budget and resource limits; certify seed/root separation; freeze code/config/source hashes and statistical analysis; independently audit chronology, flags, alignment, fairness and outputs; then issue separate explicit authorization. The large candidate requires a later review after variance/resource evidence.
