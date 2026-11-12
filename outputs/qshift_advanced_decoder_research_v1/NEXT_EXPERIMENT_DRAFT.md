# Next experiment draft — not frozen, not authorized

**Purpose:** specify the next reviewable development question after Phase 1. This file is a design draft only. It does not authorize seed creation, Stim sampling, training, or evaluation.

## Research question

Under the fixed distance-3, five-round synthetic burst model, does a causal detector-only change-triggered update policy reduce unconditional logical error versus the strongest pooled detector-calibrated burst-aware static PyMatching model, while remaining competitive in calibration and online compute cost under stationary, drifting, transient, and measurement-mismatch conditions?

This tests a causal policy, not a claim of a new decoder family. Ordinary matching and explicit correlation-aware matching are distinct decoding modes and must be reported separately.

## Model and scope

Start from the existing distance-3 rotated Z-memory circuit with 40 detectors, one observable, gate/readout probability 0.003, and the already declared neighboring `X8 X10` common-cause event inserted at five round boundaries. Candidate burst probabilities are `0, .004, .008, .012, .016`. Do not add new physical locations or alter detector/logical definitions in this first follow-up. Any extension requires a new protocol version.

Scenarios: (1) stationary burst probability; (2) abrupt step-up; (3) abrupt step-down; (4) smooth drift; (5) short transient. Add measurement-noise mismatch by evaluating with a declared readout probability different from the calibration profile, while preserving all other channels. The mismatch value, schedule lengths, and exact segmentation must be selected and frozen before creating new seeds.

## Arms

1. Fixed nominal `p=0`, ordinary decode.
2. Strong pooled detector-calibrated static burst-aware PyMatching, selected/fitted once on a separate development calibration partition.
3. Existing Q-SHIFT one-time batch-profile calibration.
4. Causal trailing-window profile recalibration.
5. Causal EWMA profile estimator.
6. Causal periodic recalibration.
7. Proposed change-triggered controller using the existing profile estimator, change detector, hysteresis, minimum dwell, and cached graph bank.
8. Privileged true-`p` matcher as a nondeployable diagnostic only.

For each primary deployable arm, replay the same chronological detector stream. Do not give any controller logical labels, true generating parameters, burst-occurrence flags, future samples, or scenario labels. Use the same model family, parameter grid, template data, observation history, graph cache, and maximum calibration/update opportunity. If a policy cannot use all opportunities, report that as its cost saving. On/off correlation-decoding mode must be set at both graph construction and `decode_batch`; do not silently combine modes.

## Split and sampling plan

Proposed first reviewable scope: 20 independent chronological streams per scenario, with 1,000 detector-only warm-up/calibration shots and 1,000 scored shots per stream, plus 60,000 independent template shots; five scenarios yields 260,000 unique shots. No training partition is needed for this non-neural policy comparison. If tuning the change threshold, use separate development tuning streams and do not score those as evaluation streams. The 260,000 total is an initial budget proposal, below 300,000; the owner may approve a different explicit ceiling.

Seeds must be newly generated only after the owner approves this scope, and collision screened against permitted development metadata. Do not inspect any sealed allocation to perform collision screening. Preserve inventory, environment, circuit/DEM/model hashes and all failures.

## Outcomes and analysis

Primary: paired root/stream-level difference in unconditional LER for event-triggered minus pooled detector-static, averaged equally over nonstationary conditions declared in the freeze. Report stationary harm separately as a no-harm guard. Report absolute effects, paired discordances, stream-cluster uncertainty, per-scenario outcomes, and low-noise harm. Do not treat shots inside a stream as independent clusters.

Operational outcomes: adaptation delay in shots from a declared change point to first accepted model update and to stable post-change parameter error; false alarms per stationary 1,000 scored shots; graph switches; decoder-build and decode CPU; peak RSS; calibration-shot count; CPU-inclusive and amortized cost sensitivity at prespecified horizons. The cost horizon must be frozen before sampling.

Candidate pass rule (to be frozen only after review): require the 95% stream-cluster interval for event-minus-pooled-static to be below zero and point benefit to exceed a practically meaningful threshold selected before sampling; also require the upper one-sided harm bound in stationary/low-burst strata to remain under an owner-approved no-harm margin. No target is changed after observing pilot results. Given prior pilots, a design may reasonably stop at a bounded pilot if event updates do not clear both the accuracy and cost criteria.

## Compute limits and stopping

Proposed ceiling: 1 hour wall time, 2 GiB process RSS, ≤300,000 unique shots. Stop if the intended configuration exceeds the ceiling, a protocol/hash/seed guard fails, any controller input includes labels/true parameters/future shots, the cache is inconsistent, or any arm fails to decode the exact paired detector shape. Failures remain in the record. No 11.736M study is included.

## Remaining pre-run gates

- Independent supervisor review of Phase 1 report and this protocol.
- Separate explicit owner approval for this concrete sampling scope and budget.
- Resolve PR #1 supervisor checkpoint 4 correction/review state; do not alter its V2.4 implementation in this branch.
- Freeze exact mismatch probability, scenario chronology, primary conditions, no-harm/practical-benefit margins, cost accounting horizon, source and environment hashes, and analysis before generating inventory.
- Implement and test causal input isolation, same-array replay, graph-cache equivalence, completion/resume safety, paired outcome logging, and independent saved-array audit without opening Stage 5 material.
- Verify correlation flags at both construction and decode time.
