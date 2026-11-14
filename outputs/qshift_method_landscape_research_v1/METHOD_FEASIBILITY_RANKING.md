# Method Feasibility Ranking

This is a research-priority ranking from saved evidence through checkpoint 138, not a decoder-performance ranking. The underlying weighted matrix contains 18 scored candidate rows; unscored entries are not given invented values.

## Priority order

1. **Strong selected/pooled static PyMatching — 4.55/5; retain as primary comparator.** Strongest established baseline and straightforward resource path. Freeze its finite candidate grid and selection objective; do not call it globally optimal. Static performance is not adaptive evidence.
2. **Published edge-moment estimator mapped to Q-SHIFT — 4.10/5; promising, validation required.** Deterministic population recovery is strong under independent graph-edge assumptions and Q-SHIFT's five burst signatures. Finite-history rare-event behavior is a serious limitation, especially at low burst rate; nuisance robustness and causal window tuning remain open.
3. **Existing burst profile plus detector-only causal trigger and cached bank — 3.90/5; high-priority hypothesis.** Fits the scientific question and information set, but existing profile is batch-oriented and no fully wired streaming controller was found. Model adequacy and decision-state validity precede decoder utility.
4. **Syndrome-only DEM probability/aggregate estimation — 3.85/5.** Relevant to detector-only adaptation, but exact signatures, nuisance identifiability and finite-history validation are needed.
5. **Trailing-window/EWMA/periodic recalibration — 3.85/5; mandatory strong baselines.** Causal, interpretable, and low complexity. They may provide the same or better response under the declared drift; no controller can claim value without matched comparisons.
6. **DEM topology discovery/CAHR and data-driven correlated-mechanism augmentation — 3.55/5 each.** Useful when the model is structurally wrong, but representation complexity and information parity must be controlled.
7. **DGR graph reweighting — 3.30/5.** Uses prior matchings as pseudo-labels; long history/feedback and model-specific convergence are concerns.
8. **Bayesian TN + SMC/MCMC — 3.25/5.** Strong model-based inference idea, but runtime and exact-model dependence are high risk.
9. **Model compatibility/postselection — 3.15/5.** Potential system metric, but rejection/yield changes the estimand and is not unconditional decoder improvement.
10. **BeliefMatching — 3.10/5.** Credible decoder method for circuit noise and hyperedges; separate from causal adaptation and must receive parity of DEM/model information. Existing implementation has compute limitations.
11. **Variational logical-risk TN learning — 3.10/5; RL-inspired LER prior search — 3.60/5 only in labeled offline selection.** These require a separate supervised/oracle information track, not detector-only online claims.
12. **BP+OSD/BP+LSD — 2.70/5.** Research-only/high risk for this small graphlike case absent a target-specific need.
13. **Calibration-conditioned FiLM — 2.65/5; Mamba/state-space supervised decoder — 2.60/5.** Relevant adjacent decoder architecture, but training labels, input scale, and deployment differ from the controller problem.
14. **Physical-control RL — 2.90/5.** Scientifically relevant to active hardware control, but incompatible with a software-only cached decoder selector.

The matrix also marks Chamberland et al.'s syndrome-statistics learner and PriorGuard as unscored adjacent prior art/safety adjuncts, not failed candidates.

## Evidence confidence

High for static source facts and deterministic algebra reproduced in saved scripts. Moderate for mapping published estimator equations to the declared Q-SHIFT categorical model. Low/unknown for finite-history estimator accuracy, practical alarm delay, resource costs, adaptive LER benefit, and independent reproducibility. Paper performance claims remain specific to each paper's code, noise, distance, hardware, training, and metric.

## Recommendation

Do not authorize a broad decoder tournament. First correct and independently review the fixed-point threshold audit and complete the controller's null/state/reset specification. If later authorized, start with a small development-only matched-information comparison: strong static PyMatching, detector-calibrated static, trailing window, EWMA, periodic recalibration, and a one-sided alarm-only candidate with safe fallback. BeliefMatching may be included only as a separate algorithm/representation arm with model-information parity.
