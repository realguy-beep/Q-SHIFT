# Composite post-change quickest-detection literature note

**Status:** working research note; not a frozen protocol or experiment authorization. Reviewed 2026-11-14. No observations were generated.

## Relevance to Q-SHIFT

The relevant Q-SHIFT stream can be represented as one detector vector per completed shot. Under the current stationary-between-changes model, shots are independent and identically distributed conditional on burst and measurement probabilities. The exact categorical circuit law is finite (for the selected ten detector bits, at most 1,024 outcomes) and low-dimensional in physical parameters. This makes parametric composite sequential likelihood methods conceptually plausible. It does not make generic high-dimensional nonparametric density estimation an obvious choice: most outcome cells are rarely occupied in short histories, as the deterministic occupancy audit shows.

## Primary-source findings

1. **Unknown post-change parameter in a GLM.** Lee and Xie (arXiv:2610.16616, 2026) propose a window-limited CUSUM whose post-change GLM parameter is estimated by a variational-inequality procedure. Their likelihood increments use a predictable fit from earlier observations, with the next observation scored before it enters the fitting window. The stated false-alarm result assumes valid predictive densities with common support; their finite-window delay result further needs informative-window curvature, controlled VI optimization error, a bounded parameter set, and a predictive second-moment condition. The first-order minimax statement takes a growing window with fixed dimension and other constants, under its specified asymptotic regime. These assumptions and results are not a ready-made guarantee for a detector-vector likelihood with estimated nuisance parameters and possible smooth drift. [Primary source](https://arxiv.org/abs/2610.16616).

2. **Unknown post-change density.** Liang and Veeravalli (arXiv:2311.15128) study a known pre-change law and an unknown post-change density, proposing window-limited nonparametric GLR-CuSum and adaptive-CuSum variants. Their asymptotic results rely on density smoothness and density-estimator convergence conditions. The Q-SHIFT detector law is discrete, sparse in short windows, and has an available low-dimensional physical model under the exact categorical circuit. Thus their work is useful as a warning about estimator conditions, but is not evidence that KDE or a nonparametric GLR is appropriate here. [Primary source](https://arxiv.org/abs/2311.15128).

3. **Nonstationary post-change laws.** Liang, Tartakovsky and Veeravalli (arXiv:2110.01581) develop window-limited CUSUM and GLR-CUSUM methods when the post-change observations may be nonstationary and cumulative information grows under explicit conditions. Their primary setup assumes independent observations, known pre-change law, and structured uncertainty in the evolving post-change distribution; dependent/nonhomogeneous extensions are discussed separately. It is relevant to a smooth-drift hypothesis only after specifying a trajectory class and checking the information-growth assumptions. It does not validate a stationary post-change GLR for arbitrary drift. [Primary source](https://arxiv.org/abs/2110.01581).

## Consequences for the candidate design

- Keep a **finite-window parametric likelihood/GLR** candidate as a research option because Q-SHIFT has a small physical parameterization and an exactly enumerable detector-vector law. Make the pre-change reference, allowed post-change parameter set, measurement-noise nuisance handling, window, scoring chronology, and threshold calibration explicit.
- Do not import asymptotic optimality claims until the exact assumptions are mapped to the Q-SHIFT process. In particular, a fixed or estimated pre-change parameter, old/new measurement nuisance, model misspecification, DEM approximation, and smoothly changing burst probability are not covered merely by citing an IID unknown-post-change result.
- Prefer the exact categorical law for any theoretical claim about the circuit model. A DEM-based implementation is a distinct approximate model and requires separate validity/robustness analysis.
- Nonparametric post-change density estimation is not currently justified: the state space is large relative to plausible short windows, while Q-SHIFT already supplies a low-dimensional model. The occupancy audit is a sparsity diagnostic, not proof that a parametric finite-window estimator is accurate.
- Q-SHIFT's desired output is decoder policy selection. A change alarm, a parameter estimate, and a useful decoder switch are separate endpoints. None of these papers establishes that detector-only alarm detection improves logical error rate.

## Limits and next deterministic question

The literature leaves a specific design question: can an exact categorical finite-window likelihood score be made predictable and calibrated when both burst and measurement parameters are unknown, while retaining acceptable false-alarm behavior under the declared stationary null? A second, separate question is which trajectory class supports the smooth-drift condition. Both can be analyzed from model laws and theory without sampling, but neither is answered by the current stationary KL/Chernoff calculations.

