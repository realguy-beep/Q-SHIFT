# Q-SHIFT Phase 2B Findings

## Study and result

Phase 2B tested whether changing Pauli composition at the same total gate-fault probability makes different PyMatching models useful in different noise regimes. It used distance-3, five-round rotated surface-code memories in both Z and X bases. Each of the six basis-by-noise conditions had 20 independent held-out roots and 10,000 paired shots per root: **1,200,000 held-out shots in total**. Three decoders processed each identical detector sample. Selection was performed only on separate calibration arrays.

The primary comparison was the calibration-selected regime-informed model minus the calibration-selected global fixed model, equally averaged across the six basis/regime cells. It was **0 errors different**: A and B each made **5,532/1,200,000 errors (LER 0.461%)**. The root-stratified 95% bootstrap interval was **[0, 0]**, and the two-sided root-cluster sign-flip p-value was **1.0**. In every basis, calibration selected the same decoder for all three generating regimes, so the regime-informed diagnostic and the global fixed model made the same predictions on every held-out sample. The test-label per-regime oracle also made 5,532 errors. This experiment therefore found **no held-out advantage or regime-level oracle headroom**.

## Decoder behavior

The decoder bank does make different logical predictions. Paired disagreement ranged from **0.0525% to 0.4195%** of shots across basis/regime/model pairs. The most disagreement was between decoder indices 0 and 2 in Z-memory balanced noise (839/200,000 shots). These are measurable but sparse prediction differences; they do not imply the model selected from a regime label will be better.

Calibration selected zero-based decoder index **2 (Z-biased)** as the global model for Z-memory, and index **0 (X-biased)** for X-memory. It selected that same index in every corresponding noise regime. The held-out rankings matched those selections in all six cells. The balanced fixed model made **6,644 errors**, 1,112 more than the selected fixed models. In the twelve predeclared alternative-model comparisons against the selected fixed baseline, eleven alternatives were significantly worse after Holm adjustment; the remaining comparison was not significant and did not favor the alternative. Thus the bank has useful **basis-specific fixed-model behavior**, but the tested Pauli composition did not establish regime-specific decoder specialization.

| Memory and generating regime | Selected global and regime decoder | Errors / shots | LER |
|---|---:|---:|---:|
| Z-memory, X-biased | 2 | 1,461 / 200,000 | 0.7305% |
| Z-memory, balanced | 2 | 934 / 200,000 | 0.4670% |
| Z-memory, Z-biased | 2 | 282 / 200,000 | 0.1410% |
| X-memory, X-biased | 0 | 265 / 200,000 | 0.1325% |
| X-memory, balanced | 0 | 1,012 / 200,000 | 0.5060% |
| X-memory, Z-biased | 0 | 1,578 / 200,000 | 0.7890% |

The hindsight per-shot oracle made **4,251 errors**, a 1,281-error lower-bound difference from the global fixed baseline. This oracle uses the true logical outcome to choose a decoder independently for each shot and is unattainable; it is not evidence of adaptive performance. Its gap from the regime oracle indicates that a coarse regime label alone does not identify which decoder will succeed on a particular syndrome.

## Answers to the research questions

1. **Does Pauli bias create meaningful prediction differences?** Yes, the models disagree on some paired detector samples, but disagreement is under 0.5% in every tested cell. Accuracy differences are clearer: several alternative models perform worse than the calibration-selected fixed model.
2. **Do generating regimes favor different models on calibration data?** No. The selected model was stable across the three regimes within each memory basis; selection changed by memory basis instead.
3. **Does regime-informed selection beat the strongest global fixed model?** No. Both make exactly 5,532 errors, with a zero difference, 95% CI [0,0], and p=1.0.
4. **Is a gain statistically or practically supported?** No regime-aware gain was observed. The selected basis-specific models do outperform the balanced fixed comparator, but that is a fixed-model choice and does not demonstrate adaptation.
5. **Does a gain remain in robustness checks?** There is no positive B−A gain in either memory basis or any of the six individual cells. The result is consistent across the tested bases and regimes.
6. **Is there enough headroom to justify a causal adaptive controller?** Not for this decoder bank and noise family. Calibration did not identify regime-dependent utility, and the regime-aware comparator tied the global fixed strategy exactly.

## Limitations and next step

The simulator samples categorical Pauli channels, whereas Stim's detector error model uses the documented `approximate_disjoint_errors=True` conversion. PyMatching's correlated mode uses available decomposition information but cannot remove that approximation. The 10:1:1 bias is an experimental sensitivity setting, not a hardware measurement. There is no leakage, coherent error, inter-gate crosstalk, non-Markovian drift, or within-circuit change. No hardware integration was attempted.

The most justified next step is to verify the result with a decoder that models the categorical biased channels more faithfully, or with an independently motivated hardware-calibrated Pauli model, under a separately frozen held-out protocol. Do not add an adaptive selector to this bank based on the unattainable per-shot oracle.

All claims above are development research findings, not hardware validation. See `PHASE2B_PROTOCOL.md`, `NOISE_MODEL_SPECIFICATION.md`, `STATISTICAL_ANALYSIS.md`, and `PHASE2B_ANALYSIS_AUDIT.json` for protocol, approximation, inference, and evidence-integrity details.
