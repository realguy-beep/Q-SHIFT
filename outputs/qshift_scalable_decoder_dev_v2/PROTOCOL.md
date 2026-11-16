# Scalable correlated decoder development protocol V2

Status: deterministic development protocol, frozen before V2 implementation changes. No stochastic sampling, new detector generation, held-out evaluation, dependency installation, or performance claim is authorized. Source base: `84ff46a4eac4dfc4769521508243065fbfebb7d9` (V1 prototype); V1 files and results remain historical and unchanged.

## 1. Question and diagnosed failure modes

Determine whether the V1 sum-product detector-factor BP has implementation defects beyond expected loopy-graph approximation, and whether corrected semantics yield useful, reproducible deterministic inference at d=3/5/7. V1's fixture observations are inputs for diagnosis, not tuning targets.

Before V2 code changes, two source-defined tiny cases were checked by exact enumeration:

- With two `p=0.1,0.2` mechanisms each flipping `D0` and `L0`, logical parity equals the observed detector. Exact `P(L=1|D0=0)=0` and `P(L=1|D0=1)=1`; V1's product of individual fault marginals returned approximately 0.0526 and 0.5740. This is a demonstrated logical-joint approximation limitation, not a detector-message equation error.
- A `p=1` mechanism fixing `D0,L0` returned an estimate for impossible syndrome `D0=0` instead of rejecting it. This is a boundary-probability/feasibility defect.

V1's tree fixture's detector marginals matched exact enumeration. The documented LLR parity-check update and variable update are algebraically correct on this tree fixture. Do not treat loopy nonconvergence by itself as an implementation bug.

The V1 d=3 DEMs differ structurally by q: q=0 has 443 positive-probability mechanisms, 1,188 variable-detector incidences, and incidence cycle rank 706; q=0.01 has 448 mechanisms, 1,203 incidences, and cycle rank 716. Thus the convergence contrast is confounded by a changed factor graph as well as probabilities. The `^` marker is a suggested decomposition of one DEM error mechanism, not an additional independent event; preserve all targets under one mechanism. See Stim's DEM semantics: https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md (sections “error instruction” and “separator target”).

## 2. Fixed V2 implementation decisions

Keep the V1 factor-to-variable parity equation, synchronous flooding schedule, LLR representation, damping 0.5, 50-iteration cap, tolerance 1e-8, and clipping epsilon 1e-12. Do not tune these parameters to match the fixture predictions.

Implement only these justified corrections/clarifications:

1. Remove p=0 mechanisms exactly; absorb p=1 mechanisms into fixed detector and logical parity offsets; infer only over 0<p<1 mechanisms.
2. Build a GF(2) detector-support basis for the remaining positive-probability mechanisms. Reject an input syndrome if it is outside the affine reachable set after fixed p=1 offsets. This must be exact, independent of BP convergence.
3. Use stable log-odds construction for interior probabilities and validate configuration (`iterations > 0`, finite `tolerance > 0`, `0 <= damping < 1`, and `0 < clip < 0.5`). Preserve the bounded tanh/atanh rule and report its numerical clipping.
4. Report detector-factor message convergence residual separately from logical confidence. Name the logical value `logical_p1_approx`; mark its method as a product-of-marginals approximation. Keep a hard prediction only as an explicitly approximate threshold decision. Do not label it an exact logical-class posterior.
5. Parse repeated detector targets and observable targets by parity. Treat `^` as a decomposition hint while preserving the containing mechanism support. Fail closed on unsupported DEM instructions/targets and invalid probabilities.

No schedule change, OSD, new decoder, dependency change, or performance-based tuning is in scope.

## 3. Deterministic validation plan

Use source-defined small DEMs only, with an independently written exhaustive enumerator over at most 12 Bernoulli mechanisms. No Stim sampler, random generator, saved evaluation archive, or evaluation label is permitted.

Required cases:

- Acyclic/tree DEM: every syndrome's detector and logical conditional probabilities agree with exhaustive enumeration within 1e-10 where exact inference is expected.
- Duplicate detector signatures, hyperedges, `^`-separated components, logical-only mechanisms, and duplicate logical signatures.
- A correlated-logical case that documents expected product-marginal error rather than hiding it.
- p=0 removal; p=1 fixed support/logical offset; impossible affine syndrome rejection; deterministic repeated outputs.
- Interior probabilities near representable zero/one, finite messages/probabilities, normalized posterior range, invalid configurations, invalid syndrome shape/bits.
- q=0/q=0.01 d=3/5/7 preconstructed circuit fixtures from the V1 fixture definition. Record all six cases; compare d=3 outputs with the existing exact DEM decoder and preserve every disagreement. No parameter selection may depend on which case agrees.

Report separately: (a) implementation correctness against exact toy cases; (b) approximate inference error on loopy fixtures; (c) convergence/failure; (d) runtime; (e) memory observation and its measurement limits. Use the V1 fixture syndromes only; no generated detector events. Each distance/condition subprocess timeout is 120 seconds; total verification compute ceiling is 30 minutes. Stop at timeout or on any sampling, protected-data, identity, or semantics ambiguity.

## 4. Alternative-method decision

Do not install packages. Record whether `ldpc` and `beliefmatching` are already importable in the existing environment only. Evaluate BP+OSD and BeliefMatching conceptually using a compatibility matrix; select no replacement decoder in V2. BP+OSD is a plausible next candidate because a DEM can be represented as parity-check columns over independent fault mechanisms, including hyperedges, but its output is a likely fault pattern and does not by itself compute the most likely logical class. BeliefMatching may fit graphlike correlated decompositions but cannot silently erase higher-order DEM mechanisms. Any integration or dependency installation needs a separate protocol/approval.

## 5. Decision gate

- **GO** only for continued deterministic engineering if all correctness, boundary, reachability, repeatability, and output-contract tests pass, all six fixtures complete within limits, and reports accurately distinguish approximation from exactness. GO does not authorize sampling or claim accuracy superiority.
- **REVISE** for bounded nonconvergence, material logical-approximation error, d=3 disagreement, performance failure, or incomplete fixture coverage.
- **STOP** for invalid detector/observable semantics, unsupported DEM content silently accepted, hidden data access, sampler invocation, or integrity failure.

Even a GO does not authorize stochastic evaluation, a scientific freeze, dependency installation, or publication superiority claims. Any later evaluation requires a separately preregistered protocol and owner authorization.
