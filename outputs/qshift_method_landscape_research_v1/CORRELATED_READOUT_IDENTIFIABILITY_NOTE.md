# Correlated-readout nuisance: detector-only identifiability limit

## Scope

This is an observation-space algebraic stress argument, not a circuit-level hardware model and not a claim that the current Stim circuit contains correlated readout errors. The pinned Q-SHIFT source model uses categorical one- and two-qubit gate channels, independent measurement flips, and independent Bernoulli spatial-burst sites. This note asks what detector-only features could identify if an additional nuisance happened to induce the same detector masks as the declared burst.

## Exact alias under identical detector masks

Let `D0` be any base detector vector. At burst site `j`, let `B_j ~ Bernoulli(p_b)` and a hypothetical correlated-readout nuisance `R_j ~ Bernoulli(p_r)` be independent. Assume both toggle the same detector mask `s_j` and do not affect the detector-only observation through any other route. The observed detector vector is

`D = D0 XOR (B_j s_j) XOR (R_j s_j)`.

The net toggle is Bernoulli with probability

`q = p_b(1-p_r) + (1-p_b)p_r = p_b + p_r - 2 p_b p_r`.

Every detector-only statistic, including all 40 marginal bits and the five specified cofire features, depends on `(p_b,p_r)` only through `q` under this construction. The two-column Jacobian of the moment map factors through the scalar `q`, so its rank is at most one. At an interior point, `dq/dp_b = 1-2p_r` and `dq/dp_r = 1-2p_b`; multiple parameter pairs can yield the same detector distribution. This is global non-identifiability for this explicitly matched-mask stress, not merely poor conditioning.

For example, `p_b=0.010, p_r=0` and `p_b=0, p_r=0.010` produce exactly the same detector law under the matched-mask construction. This equality is algebraic and does not use sampling. If the two mechanisms induce different masks, temporal dependence, or other detector effects, this exact alias need not hold; those properties must be specified and checked from a concrete physical circuit model before claiming separability.

## Consequences for the current feature estimator

The five pair-cofire indicators can identify the presence of joint detector activity relative to a model that permits only independent per-bit measurement flips. They cannot attribute that activity to the named spatial-burst cause if an unmodeled nuisance has the same detector-mask law. Correlation-aware PyMatching changes how a supplied model is decoded; it adds no information to the detector-only estimator and cannot break the statistical alias.

This argument does not establish that actual correlated readout generates the Q-SHIFT burst masks. It identifies an adversarial structural boundary for a future, explicitly specified mismatch analysis. A physically grounded extension would need to declare which jointly measured qubits can share readout faults, their circuit locations and probabilities, derive their detector/observable signatures deterministically, and then compare feature-map ranks and profile collisions. No such mechanism was silently added to the current model.

## Implications for method design

1. The present exact categorical-circuit results support local identification of the two parameters in the declared model, conditional on fixed independent measurement noise and scalar gate-channel assumptions.
2. They do not establish cause attribution when correlated readout is allowed as an unrestricted nuisance.
3. A conservative online controller should treat excess pair-cofire residuals as a mismatch/alarm signal, not as proof of burst-probability increase. Until nuisance calibration or a validated model distinguishes causes, fallback to a robust fixed decoder is more defensible than asserting physical attribution.
4. The proposed alarm's false-positive and detection behavior remain uncalibrated; this note supplies no operating-characteristic estimate.

No Stim sampling, decoder evaluation, outcome access, or training was performed.
