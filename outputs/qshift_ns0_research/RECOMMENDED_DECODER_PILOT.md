# Recommended first decoder pilot (proposal only)

**Status: not run and not authorized.** This pilot is a small development comparison to determine whether a materially different decoder has static headroom before proposing an adaptive controller. It is not a confirmatory study and does not authorize seed generation or sampling.

## Design

### Gate 0: reproducibility and interface, deterministic only

Pin an exact public HAMLD commit, license and dependency lock; build from a clean environment; reproduce its documented d=3 surface-code / Stim DEM path; record the paper's chosen contraction/order/truncation settings and exact input DEM. Confirm the PyMatching graph/decoder correlation flags at graph build and decode. Do not proceed if the published example cannot be reproduced or the Q-SHIFT circuit's full DEM is rejected or silently altered. This gate can be performed without generating new Q-SHIFT outcomes.

### Gate 1: paired Q-SHIFT development comparison

- **Circuit:** existing Phase 2B Z-memory rotated surface code, d=3, five rounds, 40 detectors, one logical observable; use the existing balanced categorical gate channel at gate probability `.003`, measurement probability `.003`, with the existing Phase 3A spatial common-cause X burst at qubits `(8,10)`.
- **Conditions:** stationary nominal (`p_burst=0`) and stationary burst (`p_burst=.01`). No measurement/gate mismatch in this first test. Do not change placement, channel order or detector definitions.
- **Allocation:** 12 independent fresh development roots per condition, 10,000 shots/root (240,000 paired shots). Each root and all arms share the same generated detector/observable rows. Root is the uncertainty cluster; 12 roots are feasibility-scale, not a formal power claim.
- **Arms:** (1) fixed nominal PyMatching (`p_burst=0`); (2) detector-only calibrated static PyMatching, selected on a distinct tuning-root allocation and frozen before pilot roots; (3) same DEM/weights with ordinary versus explicit correlated PyMatching decode as a paired ablation; (4) HAMLD using a frozen DEM/profile selected without pilot labels. A privileged true-parameter model may be shown as a clearly labeled diagnostic, never as deployable. If gate 0 indicates HAMLD cannot represent the injected event/categorical DEM, stop rather than silently substitute a model.
- **Baseline selection:** freeze a candidate burst-probability grid before generating pilot outcomes. Select the primary static matching profile by minimizing detector-only 45-feature profile discrepancy on independent tuning roots; specify scale, grid tie rule and budget in the freeze. Label any logical-label-selected choice as privileged and secondary. Never tune on pilot roots. Use the same detector availability, calibration budget and graph/model caching policy for deployable arms.
- **Noise representation:** generate/score outcomes from the original categorical Stim circuit with its burst injection. Separately record each candidate DEM conversion and any disjoint-error approximation. A decoder's approximate DEM is its model input; it does not replace the circuit-level outcome distribution. Do not call the comparison exact circuit-level ML.

## Endpoints and feasibility rule

Primary: paired root-level `HAMLD LER − detector-calibrated static PM LER`, shown by condition and equal-weight across the two conditions with a two-sided 95% root-cluster interval. Include the nominal p=0 PM baseline and ordinary/correlation-on ablation. Report unconditional LER, paired candidate-only/baseline-only failures, shot disagreement, per-root deltas, and all null/harmful results. There is no power or practical margin claim in this proposal; the lead must set a decision margin before authorization. The pilot is only a screen for technical viability and stable direction, not a superiority declaration.

Record DEM/template construction time, per-syndrome median and p95/p99 decode latency, CPU/RSS and peak memory, failure behavior, parameter/profile cache size, and calibration time separately. Do not pool preprocessing with per-shot decode latency. Preserve complete root outcomes, code/config/input hashes and any failed build/run artifacts.

## Stop/go logic for later design (not experiment authorization)

Stop if code/license or environment is unresolved; exact candidate input cannot be established; paired sample identity fails; the candidate receives more information than its declared arm; a result depends on one root; the candidate is predictively identical or worse without a plausible practical margin; or its latency/resources violate an owner-set cap. If a consistent static headroom signal appears, ask for a separately reviewed protocol with fresh development streams, broader noise/mismatch conditions, a prespecified root-cluster analysis and a new causal adaptation hypothesis. Only after a selected decoder has measurable static utility should causal switching among its parameterized models be tested against static and strong detector-only online baselines.

## Why this comes first

Q-SHIFT's existing estimator work has no decoder evaluation, and its prior neural residual experiments mostly copied PyMatching or made net-harmful corrections. The first unknown is whether another decoder changes decisions in a useful way on this circuit. A static paired comparison answers that before the extra confounding from controller delay, false alarms, calibration and switch cost is introduced.
