# Top Research Directions

All directions below are hypotheses for future, separately authorized work. No stochastic experiment is authorized by this package.

## 1. Detector-only event-triggered recalibration with explicit abstention

**Hypothesis:** a predictable detector-only alarm, under a continuously certified null envelope and declared state validity, can reduce adaptation lag relative to equally informed periodic recalibration without exceeding a deployment false-switch budget.

**Mechanism and inputs:** completed-shot detector features, a fixed categorical-model statistic, cached graph bank, and a controller that changes only future shots. No labels or hidden p values enter decisions.

**Closest prior art:** CUSUM/e-detectors, Bhardwaj et al. drift estimation, DGR pseudo-label graph reweighting, QAdapt and calibration-conditioned decoders. A contribution must be the specified information set, risk-valid state machine and comparison, not the generic idea of adaptation.

**Baseline/falsifier:** same-history trailing-window, EWMA and periodic recalibration, plus strong static PyMatching. Falsified if the policy has no prespecified adaptation/utility improvement, exceeds the risk budget, or safe-state logic prevents timely action.

**Complexity/failure:** moderate controller complexity; validity depends on nuisance envelope, one-sided null, state reset, alpha spending, horizon, indifference band and a meaningful graph action. Current e-factor does not establish decoder utility.

## 2. Q-SHIFT edge-moment estimator as transparent baseline

**Hypothesis:** the five burst pair signatures provide an interpretable detector-only rate estimate competitive with the 45-feature profile for finite histories.

**Mechanism:** published edge-moment inversion; use past detector observations only and estimate window-average rate under shotwise drift.

**Closest prior art:** Bhardwaj et al. syndrome edge-moment estimation and Remm et al. syndrome-correlation calibration. The contribution would be a model-specific mapping and robust finite-history evaluation, not the inversion itself.

**Falsifier/baseline:** compare with the source-faithful profile, bounded pair likelihood/composite estimator, and strong same-history calibration baselines. Falsified by excessive clipping/zero-boundary mass, nuisance bias, or no utility after graph selection.

**Complexity/failure:** low computational complexity; rare cofires at p=.002 make finite histories sparse. Multi-edge dependence, measurement/gate mismatch and window lag require paired root-level evidence.

## 3. Nuisance-aware model-adequacy gate

**Hypothesis:** detector-only residual checks can identify when the assumed burst/measurement/gate family is inadequate and safely abstain from adaptation.

**Inputs:** same causal detector history and a prespecified physical-model family; output is mismatch/abstention, not attribution to a specific cause.

**Closest prior art:** decoder-model compatibility/postselection, syndrome-statistics calibration, Bayesian syndrome inference, and robust sequential testing. Novelty requires a clearly different estimand and explicit rejection/yield accounting.

**Falsifier:** if distinct nuisance mechanisms are observationally aliased, the gate cannot attribute cause; it may still detect lack of fit. Failure to control false rejection under the null also falsifies usefulness.

## 4. Stronger decoder versus adaptive controller, kept separate

BeliefMatching, harmonized ensembles, BP+OSD/LSD, soft-information, leakage-aware, and neural/state-space decoders may strengthen a static decoder. Their gains do not establish drift estimation or adaptation. Compare representation and model information explicitly; proceed only if deterministic integration and resource evidence justify it.

## Novelty boundary

Syndrome-only drift estimation, adaptive weights, Bayesian syndrome inference, decoder switching, model-compatibility scoring, and neural noise-conditioned decoding all have prior art. A publishable contribution would need a narrow new result such as a verified sequential risk guarantee under a Q-SHIFT-specific nuisance envelope plus a causal, matched-information demonstration against periodic controls. No novelty claim is established by this survey.
