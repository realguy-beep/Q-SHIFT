# Q-SHIFT Phase 2B — Deterministic Identifiability Audit

**Status:** deterministic model analysis only; sampling remains unauthorized.
**Checkpoint:** `7476945de0ef63886bc32b3a9d581e2aadd11888`, branch `qshift-advanced-research`.
**Scope:** existing distance-3, five-round rotated Z-memory; balanced Phase 2B Pauli channels at p=.003; five independent `X8 X10` burst locations; 45 extracted detector features. No circuit, frozen protocol, decoder, or historical result was modified.

## Finding

**Classification A for local structural identifiability of the tested 45-feature mean map; classification C for practical confounding in the existing one-parameter estimator under measurement mismatch; global identifiability remains unproven (D for that broader claim).** B, severe local ill-conditioning, was not indicated at the tested points.

The exact categorical circuit-level expectation map has Jacobian rank 2 at the nominal point `(p_burst=.008, p_measure=.003)`, the mismatch point `(.008,.006)`, and all four tested parameter boundaries. At the nominal point, raw Jacobian singular values are **13.4898** and **3.2752** (condition number **4.1188**); the feature-column cosine is **0.4431**. After whitening by the exact single-shot 45-feature covariance, singular values are **65.4524** and **23.5440** (ratio **2.7800**). The approximate DEM map gives nearly the same figures: raw condition **4.1187**, whitened condition **2.7806**. These are local mean-feature geometry results, not finite-sample guarantees or full-distribution identification proofs.

The existing detector-only estimator is one-dimensional: it fits burst p along templates made at assumed measurement p=.003. Deterministic projection of the exact circuit expectation at true `(p_burst=.008,p_measure=.006)` onto that profile estimates **p_burst=.01091**, bias **+.00291** (36.4% of the true burst probability). The same bias occurs under the approximate DEM projection (.01091). Yet its normalized profile residual is small: mean squared standardized residual **.001214** (RMS **.0348** feature-scale units). Thus this stress can materially bias burst estimation without producing an obvious profile-fit failure. The full 45-vector contains information that separates the two parameters; the current scalar projection discards that second degree of freedom.

No exact duplicate mean profiles occurred on the tested 44-point grid (`p_burst=0,.002,…,.020`; `p_measure=.000,.003,.006,.010`). This finite grid does not prove injectivity over the continuous parameter rectangle. The nearest different-pair grid profiles were `(0.018,.006)` and `(0.020,.003)`, with standardized RMS distance **.03495**. More directly, the mismatched `(0.008,.006)` expectation projects near `(0.01091,.003)` with standardized RMS residual .0348. This is a practical near-alias for the scalar estimator, not an exact collision of the full two-parameter feature means.

## Physical mapping and feature information

The deterministic single-fault signature calculation confirmed that the five injected burst sites toggle these detector pairs in order:

| Burst site after MR boundary | Detector mask | Extracted feature index | Extracted feature |
|---:|---|---:|---|
| 1 | D8, D10 | 40 | D8∧D10 |
| 2 | D16, D18 | 41 | D16∧D18 |
| 3 | D24, D26 | 42 | D24∧D26 |
| 4 | D32, D34 | 43 | D32∧D34 |
| 5 | D36, D38 | 44 | D36∧D38 |

At nominal p, the five pair-cofire probabilities under the exact categorical circuit algebra are approximately **.0081896, .0081896, .0081896, .0081896, .0081171**. With burst fixed .008 and measurement p raised from .003 to .006, they become **.0084214, .0084214, .0084214, .0084214, .0085379**. Measurement noise therefore affects even the burst-pair cofire features; pair selection alone does not eliminate confounding.

The strongest local burst derivatives include D36 (**.9634**) and D8/D16/D24/D32 (about **.9630**), plus the five pair-cofire features (about **.933–.956**). The strongest measurement derivatives include D37 (**4.7271**), D38 (**4.6964**), D39 (**2.9452**) and D36 (**2.8611**). In particular, D37 and D39 have zero local burst derivative in this model but nonzero measurement sensitivity. Such features let a joint profile distinguish burst from measurement changes, provided the estimator actually models both parameters.

## Circuit versus DEM

The original circuit contains mutually exclusive `PAULI_CHANNEL_1` and `PAULI_CHANNEL_2` outcomes. Stim refuses conversion without `approximate_disjoint_errors`; its documented DEM semantics require independent error mechanisms and explicitly describe this option as approximating disjoint alternatives ([Stim error-analysis option](https://github.com/quantumlib/Stim/blob/main/doc/usage_command_line.md), [DEM semantics](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md)).

I separately computed the exact expectation under the original independent **categorical location** model and under the independent-mechanism distribution emitted by the repository’s `decompose_errors=True, approximate_disjoint_errors=True` conversion. At nominal p, maximum absolute feature-mean difference is **3.272×10⁻⁵** (RMS **2.136×10⁻⁵**); the five cofire differences are around **−0.29×10⁻⁶ to −0.72×10⁻⁶**. The DEM-local Jacobian and profile projection are explicitly labeled DEM-level; they are not being called exact circuit-level results. Full derivation and validation are in the neighboring reports and `analysis_results.json`.

## Implications and limits

- The five hand-selected pairs do directly capture the five physical burst signatures, but they are not sufficient to isolate burst p from measurement p. Other detector rates, notably D37 and D39, carry measurement-only local information.
- The current profile estimator uses 45 features but collapses them to a one-parameter weighted distance with p_measure fixed. Under the specified measurement mismatch this yields material burst-p bias.
- A future estimator could fit `(p_burst,p_measure)` jointly or first run a detector-only model-mismatch diagnostic. This is a research direction, not an implementation or authorization.
- PyMatching’s correlation-aware decode mode cannot repair this estimator issue. It changes how a decoder maps a given detector syndrome to a correction; it does not change observed detector features, infer physical p, or remove profile projection bias. No decoder was evaluated here.
- Local rank and a finite-grid collision screen do not prove global identifiability over a continuous domain. Practical accuracy depends on sample size, temporal dependence, calibration variance, gate/readout nuisance parameters and model misspecification; none were estimated from new data.

## Source trail

The implementation and estimator inspected here are `outputs/phase2b_pauli_bias/noise_model.py`, `outputs/phase3a_correlated_noise_preflight/simulator.py`, `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py`, and `outputs/qshift_v2_pilot2_v1/controller.py` plus `run_pilot2.py` and `PILOT2_CONFIG.json`. The historical research context read in full was Phase 1 (`outputs/qshift_advanced_decoder_research_v1/PHASE1_REPORT.md`, `LITERATURE_MATRIX.md`, `NEXT_EXPERIMENT_DRAFT.md`, `SOURCE_HASHES.json`), Phase 2 (all seven files in `outputs/qshift_advanced_decoder_research_v2/`), and Phase 2A (all six files in `outputs/qshift_advanced_decoder_research_v2_review/`). Their paths and SHA-256 values are recorded in `SOURCE_MANIFEST.json`; this audit adds a separate deterministic analysis and does not rewrite those packages.

**Recommendation:** continue protocol design only if the planned estimator explicitly models measurement noise as a nuisance parameter or declares `p_measure=.003` a fixed trusted assumption. Keep the `.006` mismatch condition as a separate stress stratum: it is informative because it exposes a 36.4% burst estimate bias while retaining a deceptively good scalar profile fit. It is a single stress point, not sufficient robustness coverage; wider measurement and gate/readout mismatch ranges require supervisor selection before a future evaluation. No sampling is recommended or authorized by this audit.
