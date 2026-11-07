# Phase 3B Draft — Spatial Common-Cause Burst Feasibility

**Status: draft only; not frozen and not executed.** This document does not authorize Phase 3B sampling.

## Question and hypothesis

Under a clearly specified spatial common-cause noise event, does a PyMatching DEM that includes the joint event lower Z-memory logical error rate relative to the frozen no-burst Phase 2B PyMatching model? Can a detector-only residual CNN learn useful corrections from the same sample distribution? The result may be null or negative; no adaptive superiority is presumed.

## Circuit and noise conditions

- Stim rotated surface-code Z-memory, distance 3, five rounds, 40 detectors, one observable.
- Frozen Phase 2B categorical Pauli generator: balanced regime, gate probability 0.003, measurement probability 0.003, bias ratio 10.
- Control: no added spatial burst (`p_burst=0`).
- Correlated condition: `CORRELATED_ERROR X8 X10` immediately after each of the five `MR` boundaries, independently with `p_burst=0.01` per round.
- Qubits 8 and 10 are adjacent data qubits at coordinates `(1,3)` and `(3,3)`. Circuit structure, detector order, and observable ID remain fixed.
- This is a synthetic cross-location stochastic channel, not a hardware-calibrated rate. All conclusions are limited to this distance, basis, location pair, and noise setting.

## Decoder arms and information access

1. Frozen Phase 2B PyMatching from the no-burst nominal DEM.
2. Burst-informed PyMatching from the burst-inclusive DEM, using the known `p_burst` and location. This is a privileged model-informed reference.
3. Position-preserving residual CNN on the same detector/observable samples, trained with the residual target `observable XOR frozen-PyMatching`; inference uses detector samples only.

For both matching constructions, use identical DEM conversion options: `decompose_errors=True, approximate_disjoint_errors=True`. Save the actual DEM text and hash. A secondary `enable_correlations=False` ablation may use the exact same burst-inclusive DEM; it is not a distinct policy if its predictions are identical. No model gets test labels, future detector samples, burst event flags, or hidden state at inference.

## Sample allocation and partitions

Use five independent roots per condition (ten root-condition cells). Every partition uses a separate seed stream, disjoint from all recoverable historical seeds and from the other partitions. No random stream is reused between conditions.

Per root-condition cell:

| Partition | Shots |
|---|---:|
| Training | 10,000 |
| Monitoring / best-checkpoint selection | 2,000 |
| Probability calibration | 2,000 |
| Threshold selection | 2,000 |
| Final paired development evaluation | 12,000 |
| **Total** | **28,000** |

Across ten cells this is **280,000 unique production shots**. Reserve at most 20,000 additional unique shots for prespecified circuit/seed diagnostics, keeping the complete new-shot cap at **300,000**. Any allocation to diagnostics reduces final-development shots; it may not increase the cap. Do not run a confirmatory test in this phase.

Train/monitor/calibration/threshold streams may be used only for their named purpose. The final development labels are accessed once after weights, temperature, and threshold are frozen. There is no independent-test allocation in this phase.

## Selection and scoring

- Restore the CNN checkpoint with lowest monitor NLL.
- Choose probability temperature using the calibration split only.
- Choose one residual correction threshold on the threshold-selection split only; no threshold scan may use final-evaluation labels.
- Use the same final detector arrays and observable labels for all three decoders within each root-condition cell.
- Save detectors, observables, all predictions, frozen choices, per-shot residual correction decisions, and file hashes.
- Report candidate-only/fixed-only failures, useful/harmful residual corrections, correction precision/recall, switch-free fallback frequency, runtime, and memory.

## Endpoints and uncertainty

**Primary development estimand:** at `p_burst=0.01`, equal-root mean of `(burst-informed PyMatching LER − frozen PyMatching LER)`. Negative favors the burst-informed model.

Secondary paired estimands: residual CNN minus frozen PyMatching and residual CNN minus burst-informed PyMatching at `p_burst=0.01`; the no-burst control contrast; and correlation-option on/off if predictions differ. Report aggregate counts and rates, per-root paired differences, candidate-only/fixed-only discordances, and per-condition results.

Use two-sided 95% intervals over independent root clusters and a root-stratified bootstrap (100,000 resamples, RNG seed allocated only after collision screening). With five roots per condition, intervals are exploratory and bootstrap resolution is limited. Use exact two-sided root sign-flip enumeration as a descriptive sensitivity analysis; with five roots its minimum attainable p-value is 0.0625. Shot-level exact McNemar p-values are descriptive and not treated as independent-root inference. Holm-adjust the three prespecified secondary paired comparisons. No pilot p-value is a confirmatory significance claim.

## Prespecified feasibility gate

**GO only to design a separate confirmatory study** if all of the following hold on the held-aside development partition:

1. At `p_burst=0.01`, burst-informed PyMatching reduces LER versus frozen PyMatching by at least **0.0002 absolute**.
2. At least **4/5 roots** favor the burst-informed decoder.
3. The root-bootstrap 95% interval's upper endpoint is below zero, with no single root contributing more than half of the aggregate improvement.
4. In the no-burst control, the two matching models produce identical or practically equivalent predictions/LER; any difference must be investigated as a modeling artifact.
5. For a neural-specific follow-up, the residual CNN must separately show at least 0.0002 absolute improvement over frozen PyMatching, at least 4/5 favorable roots, and useful corrections without a rise in harmful corrections. A burst-aware matching improvement alone does not establish neural or adaptive value.

Failure of a gate is **NO-GO** for scaling this decoder design. A confidence interval spanning zero or the practical margin is **INCONCLUSIVE** and also stops expansion in this bounded phase. No test-driven changes or automatic increase in shots are permitted.

## Resource and stop limits

Target RTX 4050 Laptop GPU (6 GB): maximum 4 hours wall time, 2.5 hours GPU time, process RSS 3.5 GiB, CUDA allocation 4.5 GiB, and minimum 10 GiB free disk. Stream and atomically checkpoint data. Stop on hash/seed/data-leakage errors, non-finite training, invalid labels, failed DEM/matching construction, resource-limit breach, or any evidence that a final label entered selection. Preserve completed development data; do not restart automatically.

## Required freeze package before any Phase 3B sampling

Freeze the exact generator and pair, `p_burst`, decoder DEMs, source/config hashes, package versions, all streams and seed allocation, training/selection code, statistical code, and decision criteria. Verify detector/observable hashes and paired-array identity in a diagnostic. Phase 3A has not frozen Phase 3B's seed list or authorized this experiment.
