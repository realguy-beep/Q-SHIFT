# Preliminary feasibility analysis

## Definition and immediate consequence

For a fixed circuit, noise model, decoder information set, and shot distribution, define

\[R = 1 - \mathrm{LER}_{candidate}/\mathrm{LER}_{baseline}.\]

A relative reduction of 99.99% requires candidate LER no greater than one ten-thousandth of baseline LER. It is a ratio claim and does not itself imply high absolute logical reliability. It also cannot be assessed fairly when the candidate receives oracle noise parameters, additional syndrome information, or a different code/resource budget than its comparator.

Using example baseline rates visible in Q-SHIFT development results, target candidate rates would be 1e-7 for baseline 1e-3, 5e-7 for baseline 5e-3, and 1.4333e-6 for baseline 0.014333. With zero candidate failures in N independent Bernoulli shots, the exact one-sided 95% upper confidence limit is 1 - 0.05^(1/N). Requiring that upper limit to be at or below the target rate takes, respectively, 29,957,322, 5,991,464, and 2,090,093 zero-failure shots. Reproduction: `python3.12 outputs/independent_research_v1/zero_failure_bounds.py`.

These are optimistic IID shot counts. They do not account for multiple regimes, root clustering, model selection, paired comparisons, baseline uncertainty, or a multiplicity-adjusted confirmatory design. If physical noise roots are heterogeneous, effective information can be lower. A paired study must predeclare its paired estimator and uncertainty procedure. Zero errors in a finite sample do not establish zero LER.

## Decoder limits and code changes

For a fixed stabilizer code and circuit, maximum-likelihood decoding is optimal only relative to the specified noise distribution and permitted observations. A posterior over logical classes sums the probability of all physical faults in each class. Minimum-weight matching generally optimizes a representative fault under a graphlike approximation, not the full degenerate class probability. This leaves theoretical headroom in principle, but neither the gap nor its practical accessibility is established for Q-SHIFT's d=5 circuit by the audited reports reviewed so far.

A decoder-only comparison holds the code, circuit, physical noise, measurement schedule, and information set fixed. Increasing distance, adding rounds, changing to XZZX or another code, or changing syndrome extraction alters resources and often the error mechanisms. Those are legitimate engineering directions, but their gain must be reported separately from decoder gains.

No positive lower bound on the achievable LER for the exact Q-SHIFT circuit has been established in this checkpoint. The numerical sample bounds above are statistical requirements, not a physical error floor proof. Further study must distinguish irreducible logical mechanisms at fixed distance from recoverable model or inference errors.

## Empirical ceiling for the existing correlation-mode pair

The independently audited Q-SHIFT pilot reports 3,532 errors for pooled-fixed uncorrelated matching and 3,349 for the same DEM with correlated matching, among 720,000 paired development shots. The predictions differ on 1,343 shots: 763 are off-only failures and 580 are correlated-only failures. An oracle selector that sees both predictions and the true observable could correct at most the 763 off-only failures relative to the uncorrelated baseline. Its residual errors would be at least 3,532 − 763 = 2,769, an empirical relative reduction ceiling of 763/3,532 = 21.6%. The actual correlated arm reduces errors by 183/3,532 = 5.18% in this sample.

At the same baseline LER, a 99.99% relative reduction would require at most 0.3532 expected errors in 720,000 shots, compared with the 2,769 errors that both current predictions make together on this observed sample. This is a descriptive sample-specific ceiling for selection between these two prediction arrays. It is not a population bound, and it says nothing about a new decoder that corrects cases both current modes miss. It does show that an adaptive controller over only these two modes cannot plausibly close the target gap on the existing pilot distribution.

## Logical-class posterior benchmark

For binary logical observable L and syndrome S under a fully specified channel, the minimum achievable average LER among deterministic decoders that only observe S is the Bayes risk

`LER_ML = Σ_s min(P(S=s,L=0), P(S=s,L=1))`.

This is a maximum-posterior logical-class decoder. It is distinct from choosing a most likely physical fault, an MWPM correction, or a mode among existing decoders. A quantitative decoder-only headroom claim requires either a trustworthy estimate of this quantity or a defensible lower bound for the exact circuit/noise distribution. Q-SHIFT has exact toy values, but no validated full d=3/d=5 logical-class posterior. Therefore the remaining recoverable inference gap and any fixed-distance physical error floor are unknown.
