# Q-SHIFT Phase 2 — Specialist Decoder Investigation

## Conclusion

**Composition-specific PyMatching models did not provide a credible advantage over one fixed nominal PyMatching model.** The oracle specialist selector chose fixed matching for every test condition across all 10 seeds. The detector-based specialist selector was therefore not implemented, in accordance with the predeclared usefulness gate.

This agrees with the Phase 1 finding: detectors can often indicate the noise regime, but identifying a regime is not enough if its specialist decoder does not improve residual logical error. Phase 2 also finds that, for this distance-3 repetition-memory instance, the X-, Z-, and depolarizing-specialist matchers produced exactly the same corrections as fixed matching on every tested sample, despite different DEM weights. The measurement-only specialist changed very few corrections and usually made performance worse.

## Design and calibration

The ideal circuit is unchanged: Stim `repetition_code:memory`, distance 3, 3 rounds, 5 qubits, 8 detectors, and one `L0` observable. The Phase 1 channel builder injects `PAULI_CHANNEL_1` after each CX participant and optional X measurement flips before Z-basis M/MR. Data composition comparisons use total nonidentity probability 0.01 per active qubit per CX; measurement-only has p=0.01 per measurement. Mixed X/Z and data-plus-measurement are held out from the four specialist families. See [config.json](config.json) and the Phase 1 audit for the exact convention.

Each independent seed has 30,000 calibration shots per specialist, 10,000 validation shots per test condition, and 30,000 untouched test shots per condition. Calibration fits the total local p by maximum detector-pattern likelihood over `{0.006, 0.008, 0.010, 0.012, 0.014}`, using independent 20,000-shot Stim reference samples per grid point. The composition family is known, but the fitted p uses detector bits only; the sampled observable labels are not read by the fit. All 40 specialist-by-seed fits selected p=0.010. DEMs use Stim `approximate_disjoint_errors=True` for multi-component Pauli channels. This is simulator calibration from a known channel family, not hardware calibration.

Specialist DEMs were created separately for X-dominant, Z-dominant, depolarizing, and measurement-only conditions. The fixed baseline is the nominal depolarizing DEM at p=0.01. A further noise-specific oracle matcher uses the actual test composition. The validation-selected oracle specialist chooses among fixed and four specialists by validation residual count, with ties favoring fixed. That choice is frozen before test evaluation. Every model is tested on the same detector shots for each condition.

## Cross-evaluation results

Counts are residual observable errors across 300,000 paired test shots per condition (10 seeds × 30,000). Each cell lists `errors / rate`. Wilson 95% rate intervals and per-seed values are in [specialist_results_v1.json](results/specialist_results_v1.json).

| Test condition | Raw flips | Fixed nominal | Noise-informed oracle | X specialist | Z specialist | Depolarizing specialist | Measurement specialist |
|---|---:|---:|---:|---:|---:|---:|---:|
| X-dominant | 8,137 | 749 / 0.2497% | 749 / 0.2497% | 749 / 0.2497% | 749 / 0.2497% | 749 / 0.2497% | 978 / 0.3260% |
| Z-dominant | 1,726 | 22 / 0.0073% | 22 / 0.0073% | 22 / 0.0073% | 22 / 0.0073% | 22 / 0.0073% | 38 / 0.0127% |
| Depolarizing | 5,908 | 457 / 0.1523% | 457 / 0.1523% | 457 / 0.1523% | 457 / 0.1523% | 457 / 0.1523% | 584 / 0.1947% |
| Measurement-only | 2,954 | 93 / 0.0310% | 92 / 0.0307% | 93 / 0.0310% | 93 / 0.0310% | 93 / 0.0310% | 92 / 0.0307% |
| Held-out mixed X/Z | 4,373 | 261 / 0.0870% | 261 / 0.0870% | 261 / 0.0870% | 261 / 0.0870% | 261 / 0.0870% | 339 / 0.1130% |
| Held-out data + measurement | 8,783 | 820 / 0.2733% | 820 / 0.2733% | 820 / 0.2733% | 820 / 0.2733% | 820 / 0.2733% | 1,048 / 0.3493% |

### Specialist usefulness gate

The gate covered 24 specialist-condition comparisons. It required lower paired test errors, an exact McNemar p below 0.05 after Bonferroni correction over 24 comparisons, and a seed-bootstrap 95% interval with its upper bound below zero. **No comparison passed.**

- X, Z, and depolarizing specialists each had zero prediction disagreements with fixed matching across all six test conditions and all 300,000 shots per condition. Their DEM probabilities/weights differed, but the selected correction did not.
- Measurement-only matching disagreed on at most 0.094% of shots and was substantially worse on four conditions. On measurement-only noise it had 92 errors versus fixed's 93, a one-error difference with exact paired p=1; this is not evidence of improvement.
- The noise-specific oracle matcher had the same test errors as fixed on five conditions and one fewer on measurement-only. Its aggregate across 1.8 million shots was exactly tied with fixed: 2,402 errors each, paired p=1.
- The validation-selected oracle specialist picked fixed matching for every condition and every seed (60 of 60 choices). Its test result tied fixed at 2,402 / 1.8 million, paired p=1. Validation provided no reason to select a specialist.

Shot-level paired McNemar tests, 24-way adjusted p-values, paired confidence intervals, prediction-disagreement rates, and seed-bootstrap intervals are recorded per condition and specialist in the JSON. Test data did not select model weights or the oracle strategy. The oracle strategy was chosen on validation and evaluated once on independent test data.

## Why the specialists did not help

The X-, Z-, and depolarizing specialists have different edge probabilities, but on this short repetition-memory graph the relative path ordering for every observed detector pattern remained unchanged. Thus PyMatching returned identical corrections. A noise-specific weight model cannot improve residuals if it induces the same decision boundary as nominal matching. This is a structural result for this particular code, circuit, and p range—not a general theorem about matching.

The measurement-only DEM has a different, smaller graph (9 edges versus 18 in the data-channel models), but its corrections rarely differed and mostly introduced errors on data-dominated and held-out mixture conditions. The one-error reduction on measurement-only is statistically unsupported. This is a failed specialist, retained rather than hidden.

## Runtime and memory

Measured batched decoding took approximately `0.093–0.103` microseconds per shot for the specialists and `0.099` microseconds per shot for fixed matching on this local Python 3.12 / Stim 1.16 / PyMatching 2.4 / NumPy 2.5 environment. These are local batch throughput figures, not hardware latency. DEM text occupied about 350 bytes for measurement-only and 788–794 bytes for data specialists; each PyMatching Python wrapper reports 48 bytes, which omits native graph allocation. Edge counts were 9 and 18 respectively. Per-seed specialist runtimes/metadata are in the JSON; fixed and all condition-specific DEM sizes are in [model_metadata.json](results/model_metadata.json).

## Phase 1 comparison

Phase 1 used a lookup decoder and detector-window composition recognition. It found 94.4% trained-regime recognition, but guarded adaptation made no switches and tied fixed PyMatching; a rate-only selector switched and performed worse. Phase 2 replaced lookup specialists with PyMatching DEM specialists calibrated from detector likelihood plus known composition family. Despite accurate p recovery on the discrete grid, specialists still did not change corrections for the data channels. The oracle model selector also stayed fixed. Together, the phases suggest the bottleneck is not just regime recognition; the current small repetition-code matching decision is insensitive to these composition-specific weight changes.

## Decision on detector-based selection and unfamiliar mixtures

Experiment D was **stopped before selector implementation** because the specialist usefulness gate failed. Building a selector among models that show no validated benefit would add overhead without a demonstrated opportunity to improve decoding. Consequently, no Phase 2 claims are made about detector-only switching delay, false-switch rate, or adaptive-selector overhead.

The held-out mixed X/Z and data-plus-measurement conditions were evaluated against every specialist. Fixed and noise-informed matching tied on both. The measurement specialist performed worse. There is no basis for forcing these mixtures into a known specialist class; a conservative fixed-model fallback remains appropriate. A novelty detector is not implemented because no specialist passed the usefulness gate.

## Preserved artifacts, limitations, and next step

- Reproducible source: [run_specialist_study.py](run_specialist_study.py).
- Full configuration: [config.json](config.json).
- DEM and graph sizes: [model_metadata.json](results/model_metadata.json).
- Raw calibration, validation, and test arrays: `raw/`, with SHA-256 manifest next to the result.
- Graph: [specialist cross-evaluation](results/specialist_results_v1_cross_evaluation.png).
- Smoke and failed plotting run outputs remain in `results/`; they are not included in claims.

The study is bounded to distance 3 / 3 rounds, four training compositions, fixed p=0.01, one observable, and idealized Stim channels. DEM approximation and simulator-known composition are limitations. No hardware integration or runtime telemetry was used.

**Recommendation:** stop lookup and simple weight-specialist adaptation for this circuit. The next scientifically useful step is to increase code distance/rounds or introduce nonuniform fault locations/correlations that can change the optimal matching boundary, then repeat the same paired cross-evaluation. Do not build a selector until a specialist first demonstrates a replicated, multiplicity-adjusted advantage.
