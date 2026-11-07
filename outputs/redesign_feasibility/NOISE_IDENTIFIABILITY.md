# Noise identifiability from detector histories

## The distinction to preserve

The research should not ask whether a classifier can assign a regime label. It should ask whether past detector data identify **the parameter combinations that change useful matching decisions**, with enough precision and speed to matter. A physical state may be unidentifiable but decoder-equivalent; an identifiable rate may be irrelevant to the logical decision.

## Structural identifiability gate

For a frozen model family with parameter vector `θ`, define its predicted distribution over the permitted observed detector features as `P(S | θ)`. Before evaluating a tracking policy, check:

1. **Injectivity up to decoder equivalence:** distinct `θ` values that imply different target decoder weights or corrections must not generate the same observed syndrome distribution under the selected circuit and observables. Parameter symmetries that leave the decoded logical frame unchanged may be quotiented out, but must be recorded.
2. **Local information rank:** calculate or approximate the Jacobian of expected detector/correlation statistics with respect to `θ` and the Fisher-information matrix under the declared observation model. Require full rank for the decoder-relevant subspace and predeclare a minimum condition-number/eigenvalue criterion. An ill-conditioned direction is treated as practically non-identifiable even if algebraically distinct.
3. **Finite-window distinguishability:** on independent development data, evaluate whether competing parameter states can be discriminated at the intended window length with calibrated uncertainty and adequate power. A classifier's accuracy on labels is not a substitute for calibrated parameter recovery.
4. **Model adequacy:** test residual detector correlations and goodness-of-fit. A wrong Pauli/independence model can create confident but misleading estimates. For categorical channels, preserve their correlation structure or explicitly quantify DEM approximation error.

Wagner et al. establish an algebraic identifiability result for Pauli channels with correlations up to the code's pure distance and include measurement noise through data-syndrome codes. This theorem gives a principled starting point, not a blanket guarantee for finite, nonstationary, circuit-level windows. [Wagner et al.](https://doi.org/10.22331/q-2022-09-22-809). Bayesian/SMC work treats parameter uncertainty and time variation, but its model assumptions and computational cost must be checked for Q-SHIFT's circuits. [Kobori & Todo](https://doi.org/10.1103/wg5h-spy6).

## Detector statistics

The current Q-SHIFT selector uses smoothed per-detector Bernoulli rates and a summed composite score (see `headroom.py`, `detector_profiles` and `marginal_scores`). This omits cross-detector and temporal correlations; multiple mechanisms can produce similar marginals. It should remain a baseline/diagnostic, not be promoted as a general noise estimator. Use time-ordered syndrome correlations, detector-pair statistics, or a validated circuit-likelihood/particle-filter method appropriate to the channel. Avoid fitting unrestricted parameters when there are fewer informative statistics than unknowns.

Boundary events and logical observables are especially important. The online estimator cannot observe the true logical labels, and detector marginals alone may leave boundary-event rates underdetermined. The offline evaluation may use observables to score predictions, but no observable, residual logical error, or test outcome may flow back into the online estimate.

## Change detection versus state estimation

Test stable noise as a false-alarm control. For abrupt changes, report detection delay and state/parameter interval coverage. For gradual drift, report tracking lag and error across frequency or slope. If the drift timescale is shorter than the window needed to achieve the required uncertainty, the correct result is “not trackable under this data rate,” not a forced regime assignment. If detector data identify a noise change but the corresponding decoder correction distribution is unchanged, that is no decoding opportunity—not estimator failure.

## Practical stopping rule

Stop the online branch before final testing if (a) the decoder-relevant information matrix is rank-deficient or too ill-conditioned at the maximum feasible window; (b) uncertainty intervals do not contract enough to change a model safely; (c) change detection delay is longer than typical dwell time; or (d) identifiable shifts produce no stable fixed-vs-specialist utility difference in independent development calibration. Preserve the negative finding and continue only with a revised observable/noise model that has a scientific justification.
