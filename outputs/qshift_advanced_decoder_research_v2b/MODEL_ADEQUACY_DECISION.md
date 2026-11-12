# Model adequacy decision

## Classification

| Claim | Classification | Basis and limit |
|---|---|---|
| Local structural identifiability of the 45-feature mean map for `(p_b,p_m)` in the tested categorical circuit model | **A — structurally identifiable at tested points** | Rank 2 at nominal, mismatch and tested boundaries. This is local, finite-point evidence; no continuum proof. |
| Severe local collinearity / poor conditioning | **B — not supported at tested points** | Raw Jacobian condition 4.12 nominal; covariance-whitened condition 2.78. These are geometry diagnostics, not estimator performance guarantees. |
| Existing burst-only profile under measurement mismatch | **C — materially confounded** | At true `(.008,.006)`, it returns `.01091` while assuming measurement p=.003: bias +.00291 (36.4% of burst p) with RMS profile residual .0348. |
| Global identifiability and adequacy for the original circuit distribution from the generated approximate DEM | **D — inconclusive** | Finite-grid collision checks cannot prove global uniqueness; moment similarity does not imply distribution equivalence. |

“A” means the two parameters move the local mean vector in linearly independent directions in the tested model. It does not mean the profile estimator is unbiased under misspecification, nor does it show practical accuracy with any sample size. “B” is deliberately separated from “C”: local rank and conditioning are acceptable while a misspecified one-dimensional fit still has substantial bias.

## Measurement mismatch condition

The currently specified stress (`p_b=.008`, actual measurement p=.006 while fitted templates assume .003) is scientifically informative: it tests whether the burst estimator mistakes readout changes for burst changes, and deterministic projection predicts 36.4% relative bias with a deceptively small residual. It is sufficiently challenging to expose this particular failure mode, but insufficient as a general robustness test. It tests one fixed offset and no calibration uncertainty, time-varying measurement drift, gate-channel mismatch, or correlated readout process. Any future evaluation must prespecify a broader mismatch range and whether p_m is fixed, jointly estimated, or treated as nuisance. Selecting that range from future evaluation outcomes would be leakage.

The feature audit supports deterministic structural checks before any study: confirm feature-to-fault mapping; inspect rank and covariance-scaled singular values over the prespecified parameter domain; compute exact categorical-vs-DEM moment discrepancy; and verify that nuisance perturbations do not alias the target parameter beyond an owner-approved tolerance. These require model algebra only and no Stim sampling.

## Correlation-aware decoding is not an estimator fix

PyMatching's correlation-aware option affects decoding conditional on a detector syndrome and matching model. It cannot add information to the extracted detector vector, correct an estimator that fixes p_m incorrectly, or establish physical parameter identifiability. It may affect logical correction risk under correlated faults, a distinct question that needs decoder evaluation. The presence of a graphlike burst signature is not evidence by itself that correlation-aware decoding improves logical performance. No decode was executed here.

## Decision

**GO:** continue deterministic protocol design. Replace or augment the burst-only profile with an explicit joint `(p_b,p_m)` fit or a prespecified detector-only mismatch alarm; specify treatment of nuisance calibration and its uncertainty. Keep exact categorical-circuit and approximate-DEM calculations labeled separately.

**NO-GO:** no sampling, decoder comparison, pilot, freeze, or full study is recommended or authorized by this audit. Before a future request for experimental authorization, owners should resolve the nuisance model, robustness grid, practical precision target, and whether the target estimand is conditional on a realized calibration/template or averages over calibration randomness. No results here constitute independent confirmation.
