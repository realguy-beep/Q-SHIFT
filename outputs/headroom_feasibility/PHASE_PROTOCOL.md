# Calibration Headroom and Power Feasibility Protocol

**Status:** prospective development/feasibility study. No final confirmatory data will be generated in this phase. Historical Phase 4A–4C and Phase 5 files are read-only.

## Research question

Does a practical PyMatching model bank show stable regime-dependent logical-error utility beyond a calibration-selected pooled fixed decoder, across rotated surface-code X- and Z-memory at distances 3, 5 and 7?

This phase measures static utility headroom. Regime identity is known only for defining calibration/evaluation strata; no adaptive selector is evaluated. A regime-matched candidate is an optimistic calibration feasibility diagnostic, not a deployable strategy.

## Historical evidence and calibration approaches

Phase 4A/4B use native Stim depolarizing gate errors and measurement noise. Their calibrated model is selected by detector-only composite Bernoulli likelihood: candidate-specific detector marginals are estimated from a separate template bank with Jeffreys smoothing; calibration detector counts are scored under those profiles. Observable labels are excluded from this detector-fit choice. Their fixed comparator is nominal (.003,.003).

Phase 4C Stage 1 instead uses calibration observable labels to select pooled, minimax and regime-specific fixed decoders from nine candidates. Stage 2 uses the Phase 4A detector-marginal fitting method for its calibrated model and compares it with the Stage 1 pooled model. Its held-out predictions were independently re-decoded, but calibration arrays and fitting traces are missing. The current pilot therefore records two distinct model-choice channels: detector-marginal fit (Phase 4A-like) and calibration-LER utility choice (Phase 4C-like). Evaluation labels choose neither.

## Circuit, regimes and decoder banks

Use Stim rotated surface-code memory X and Z circuits, distance d in {3,5,7}, rounds r=d. Preserve generated detector and observable annotations. Native circuits use the same gate/readout convention as Phase 4A: native after-Clifford DEPOLARIZE1/2 with gate p and basis-appropriate premeasurement error with measurement p. Native generating regimes are:

| Regime | Gate p | Measurement p |
|---|---:|---:|
| data-heavy | .006 | .001 |
| nominal | .003 | .003 |
| measurement-heavy | .001 | .006 |

The native candidate decoder bank is the fixed ordered 3×3 Cartesian grid with gate and measurement p independently in {.001,.003,.006}. Each DEM is generated from its candidate Stim circuit; no approximate-disjoint-errors conversion is requested for this native depolarizing family. Ordinary PyMatching is used.

The Pauli-biased family is a separate sensitivity family modeled on Phase 2B, not pooled with native depolarizing results. Total local nonidentity probability is .003 per one- and two-qubit gate-noise invocation; measurement flip probability is .003. Three candidates/regimes are X-biased, balanced and Z-biased with 10:1:1 dominant:other Pauli weights. The two-qubit categorical pair probabilities sum to .003 and follow the Phase 2B product-weight rule. These channels are represented in Stim as PAULI_CHANNEL_1/2. Matching DEM creation uses decompose_errors=True and approximate_disjoint_errors=True, with correlated matching enabled; the approximation is recorded and not claimed to be exact.

## Partitions, seeds and resource limits

For each family×distance×memory×regime, use five independent calibration roots and five independent development-evaluation roots, with 5,000 shots/root. Generate 5,000 detector-only template shots per candidate per bank using a separate template namespace. No root or seed is reused between template, calibration, evaluation, noiseless diagnostic, noisy diagnostic, benchmark or bootstrap streams. A machine-readable inventory is collision-screened against recoverable historical seed records before sampling. Its coverage limitation is explicit: unrecoverable historical random streams cannot be ruled out.

There are 36 bank×regime cells (2 families × 3 distances × 2 bases × 3 regimes). At five roots × 5,000 shots per cell, the planned total is 900,000 calibration shots and 900,000 independent development-evaluation shots. Templates use 54 native candidates plus 18 Pauli-biased candidates × 5,000 shots = 360,000 shots. The diagnostics and benchmarks use 12 banks × (256 noiseless + 512 sensitivity + 1,000 benchmark) = 21,216 additional shots. The planned total is therefore 2,181,216 shots, below the 3 million pilot cap. The pilot has a 1,800-second wall cap and a 2 GiB process-RSS cap. Benchmark and circuit preflight are recorded before calibration/evaluation scaling. Any circuit, seed, memory or resource failure stops the affected run and preserves its partial evidence; shot counts will not be silently reduced.

## Selection and evaluation

For each bank, use only calibration labels to compute candidate residual logical-error rates. The pooled fixed choice minimizes the equal-weight mean of the three calibration-regime rates; ties go to the lowest bank index. The regime utility choices minimize each regime’s calibration LER, with the same tie rule. Separately, compute the Phase 4A-style detector-marginal fit on calibration detector data only. Store calibration shots, labels, predictions, profile templates and selected indices for audit.

Then sample an independent development-evaluation stream. Decode every detector batch with every candidate. On identical detector samples and labels, recompute logical residuals, paired specialist-minus-pooled errors, both discordance directions, prediction disagreement, and root-wise rates. Save packed detector arrays, labels and predictions atomically. No evaluation labels are used to choose a model.

Root bootstrap intervals and candidate-choice frequencies summarize development uncertainty; no test-of-superiority p-value is used as confirmatory evidence. A per-root minimum-LER candidate is reported only as a retrospective ranking diagnostic.

## Prespecified headroom gate

An eligible bank stratum is one family×memory basis×distance. A family/basis pair passes only if at least two distinct distances each satisfy all conditions:

1. At least two generating regimes have different calibration-LER-selected specialist indices, and each selected index differs from the pooled fixed index.
2. Root-bootstrap probability that each regime-specific candidate is its regime’s calibration-best candidate is at least 0.80.
3. On independent evaluation roots, each specialist lowers LER against pooled fixed by both at least 5% relative and at least 0.0001 absolute.
4. At least four of five evaluation roots favor each specialist, and the 95% root-bootstrap interval for specialist-minus-pooled LER lies wholly below zero.
5. The same pair of regimes exhibits different specialist indices at both qualifying distances.

This is a conservative go/no-go feasibility rule, not a multiple-comparison-adjusted inferential claim. All 12 bank strata are reported, including failures. Detector-model recovery alone does not pass the gate; only paired LER utility counts. A test-label oracle is never used as evidence for the gate.

## Power feasibility boundary

Only if the headroom gate passes will this phase estimate a confirmatory paired adaptive-minus-pooled-fixed endpoint, choose a practical margin, model root-cluster variance and simulate power under the 24 CPU-hour/20-million-test-shot planning caps. If the gate fails, stop and mark power planning as blocked by absent stable utility headroom. No final adaptive test shots are allowed in this phase.
