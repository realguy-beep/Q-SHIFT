# Comprehensive Research Report

**Status:** Final synthesis prepared on receipt of STOP, 2026-11-14 (Asia/Calcutta). This summarizes saved work through checkpoint 138. No post-STOP research, literature search, tests, shots, or feasibility calculations were started.

## Executive conclusion

Q-SHIFT's strongest defensible near-term question is whether a causal detector-only policy improves on a strong, equally informed static or periodically recalibrated PyMatching baseline under the declared shotwise burst model. The repository work establishes deterministic model structure and useful detector statistics. It does not establish finite-history estimator accuracy, graph-switch utility, lower logical error rate, or readiness for an autonomous bidirectional controller.

The best immediate engineering baseline remains strong selected/pooled static PyMatching. The simplest promising detector-only estimator is the published syndrome edge-moment inversion mapped to the five Q-SHIFT burst signatures. A bounded e-factor is a distinct alarm-only hypothesis. Its guarantees are conditional on the stated categorical law, nuisance envelope, predictable inputs, and state/null validity; they do not specify a decoder action. BeliefMatching is a separate decoder-feasibility track, not evidence for adaptive switching.

## Project evidence inspected

The saved checkpoint records targeted inspection of Phase 4A/4B/4C, NS-4A readiness, strong static and adaptive prototypes, the 45-feature estimator, generic selector, V6/V7 engineering reports, and BeliefMatching setup/decode sources. In inspected source, the profile estimator is a batch burst-profile fit using 40 detector marginals plus five burst-pair cofires, with template knots `[.002,.010,.018]`; it is not a streaming change detector. The generic selector supports provenance, confidence, hysteresis and dwell concepts but was not found wired to a chronological estimator. The headroom score is a separate marginal/composite feature path.

The historical adaptive-versus-pooled result (mean absolute LER difference `-0.00002917` over four nonzero settings) is recorded as nonconfirmatory and affected by a disclosed pooled-calibration deviation/reconstruction. It is not evidence of adaptive advantage. The selected X8/X10 event is graphlike, but the prior correlation-mode smoke was prediction-identical; no correlation-decoding gain is established.

## Literature and method coverage

The saved literature ledger covers classical matching and correlation-aware matching; BeliefMatching; BP, BP+OSD/LSD, union-find, tensor-network, renormalization, exact/MAP and hypergraph/DEM methods; neural and hybrid decoders; detector/DEM estimation; Bayesian and graph-moment estimation; CUSUM, e-processes, BOCPD and composite quickest detection; sliding windows/EWMA/periodic recalibration; decoder-prior optimization; ensembles and decoder switching; leakage/soft information; systems monitoring and physical-control RL; and statistical/reproducibility controls.

Sources include foundational and recent primary papers and official implementation evidence, including DGR, Bhardwaj et al., Remm et al., QAdapt, Bayesian syndrome inference, Wagner et al., BeliefMatching, BP+OSD/LSD, decoder-model compatibility, calibration-conditioned FiLM, DEM estimation/reconstruction/augmentation, decoder-prior optimization, PriorGuard, ReloQate, Chamberland et al., AlphaQubit, Mamba/state-space decoding, real-time decoder switching, sliding-window kinetics, E-detectors, and quickest-detection work. Provenance is in `LITERATURE_DATABASE.md` and `SOURCE_VERIFICATION.md`.

The saved weighted matrix has **18 scored candidate rows**. A unique-paper count was not maintained: the ledger mixes papers, grouped entries, duplicate status updates, source/code records, and citation-chain notes. Thus an exact unique-paper count cannot be recovered honestly without post-STOP bibliography reconciliation. The ledger contains dozens of distinct work records; no exact unique count is asserted here.

## Deterministic Q-SHIFT evidence

The exact categorical circuit's 45 population features were computed by deterministic fault propagation and categorical parity products, with direct XOR recursions as independent arithmetic checks. Approximate DEM expectations were computed separately under an independent-mechanism law; they are not exact circuit expectations. At nominal conditions the exact-circuit/DEM mean gap was about `3.27e-5`; the maximum reported grid gap was about `3.30e-5`. Five pair signatures carry strong burst sensitivity. Exact categorical checks found no nonburst single-fault alternatives sharing those five supports, and no jointly affecting alternative among the audited mutually exclusive site groups.

Three-parameter exact-circuit local Jacobians had rank 3 at each of 75 tested nodes; the nominal-covariance-whitened condition ratio varied about 2.768–2.784. This is finite-grid local rank, not continuum/global identifiability or finite-history recovery. Approximate-DEM results were similar at tested points, but DEM transfer is not automatic: a 250-point screen found an alternative-envelope violation of `5.9848e-8` at one DEM point.

The published edge-moment inverse deterministically recovers burst probability to floating precision under its stated independent graph-edge model for all five Q-SHIFT pair signatures, including tested gate-composition variants and exact/DEM population templates. This does not establish sample performance. Exact finite-count enumeration shows rare-event boundaries: for one pair at 200 shots, the probability of a negative raw inverse was `.5898/.1281/.02749` at burst probabilities `.002/.010/.018`; a bounded one-pair MLE has a zero mass at no cofire. Five-pair dependence and composite-score calculations were also studied deterministically, with asymptotic and finite-count limitations documented.

Three-parameter sensitivity shows detector features respond differently to burst, measurement and scalar gate noise, but nuisance sensitivity remains material. A fixed-gate measurement mismatch counterexample invalidates the earlier fixed-gate e-factor envelope at tested gate values. A subsequently derived robust continuous envelope covers only the explicit balanced categorical model and gate/measurement/burst rectangles. It does not cover approximate-DEM generated streams, arbitrary gate mechanisms, or an online switching controller.

## E-factor/change-detection line

Saved work analyzes a bounded pair-cofire mean statistic, exact rational continuous envelopes, scalar e-processes, finite/infinite change-time priors, alpha spending across externally re-baselined episodes, mean/log concentration bounds, specified ramps, gate mismatch, fixed-point arithmetic, and a four-lambda bank. These are mathematical or deterministic feasibility results, not observed alarms or decoder outcomes.

A one-sided process can control a specified null under its conditional validity premise. The directional pair does not solve autonomous bidirectional switching: an alarm does not prove the opposite regime, the middle band lacks a unique action, null validity can fail after a false state transition, and reset spending alone does not repair that problem. Controller readiness therefore remains **NO-GO**.

**Audit correction required:** final STOP review identified an inversion in checkpoint-133's explicit alpha-threshold crossing predicate: it compared the lower e-value to `alpha` instead of `1/alpha`. The pointwise fixed-point lower-bound comparison was separately described as correct, but the logged explicit crossing count is unsupported until the predicate is corrected and rerun. The prior artifact is preserved. No correction run was performed after STOP. The planned fixed-point audit of the lambda bank was not performed.

## What remains unknown

No deterministic population calculation answers whether any policy reduces unconditional LER or paired logical-error risk. Finite-history performance, false graph switches, delay under realistic streams, deployment runtime, cache/build overhead, end-to-end resource cost, practical-margin justification, robust nuisance handling outside specified rectangles, and external independent reproduction remain open. The existing controller code is not a complete causal stream implementation.

## Final answers

1. **Most promising:** retain strong static PyMatching; investigate the simple published edge-moment estimator and conservative detector-only alarm as separate components, with same-information trailing-window/EWMA/periodic comparators.
2. **Implementable now:** deterministic population calculations and a detector-only estimate are structurally compatible; a validated finite-history causal policy is not demonstrated. PyMatching static baselines are available.
3. **Plausible contribution:** a carefully bounded, model- and nuisance-aware event-triggered controller with a falsifiable benefit over equally informed periodic recalibration. It is not novel merely because it combines known estimators and switching.
4. **Retain/revise/deprioritize:** retain strong static matching and historical results as nonconfirmatory evidence; revise claims about fixed-gate alarm validity and checkpoint-133 threshold counts; deprioritize large neural/TN machinery and generic controller integration until model adequacy and utility are addressed.
5. **Priority:** first finish deterministic arithmetic audit corrections and independent review; then, only under separate authorization, evaluate detector-only change alarms against same-history trailing/EWMA/periodic baselines. BeliefMatching remains a distinct optional decoder track.
6. **Strongest next hypothesis:** for the specified categorical burst model, a detector-only alarm valid over an approved nuisance envelope can signal only future graph updates and reduce adaptation lag versus equally informed periodic recalibration without exceeding a prespecified false-switch/risk budget.
7. **Required before experiments:** correct and independently audit the fixed-point threshold artifact, resolve state reset/indifference-band policy, approve nuisance envelope and horizon/alpha objective, freeze comparator and paired/root analysis, define resource guard and pilot scope, and obtain explicit experiment authorization.
