# Pair-cluster categorical importance sampling

## Hypothesis and scope

The prior failure-conditioned cross-entropy proposal estimated each two-qubit channel independently and passed its predeclared variance gate in 0/6 conditions. Its low weighted-failure ESS suggests that important conditional dependence between faults is lost. Test a product of joint proposals over fixed, physically local two-channel clusters. This is a rare-event estimator for the original categorical Phase 2B circuit distribution with a fixed correlation-enabled PyMatching decoder; it does not change or claim to improve the decoder.

## Fixed grouping and proposal

In each flattened `PAULI_CHANNEL_2` instruction, pair adjacent two-qubit channel instances in target order. The audited z-memory circuit has 20 such instructions, six channel pairs each, yielding 60 two-location clusters and no singleton clusters. Do not alter grouping based on outcomes. Each cluster has 256 joint categories, including identity/identity. Estimate the failure-conditioned joint category distribution from separate globally fivefold-tilted training samples, weighted by the exact source/proposal likelihood ratio. Apply additive shrinkage of 50 source-distribution trajectory equivalents per cluster: `q_g(c)=(weighted_failure_count_g(c)+50*p_g(c))/(weighted_failure_total+50)`. Freeze all proposals before validation. Since base channel locations are independent, `p_g` is the exact product categorical distribution for the two locations.

Instrument each cluster as one mutually exclusive 256-branch correlated Pauli channel on its four data qubits and add private category flags. Use a 9-bit direct encoding of categories 0..255: the no-branch all-zero flag word denotes identity/identity, while each nonidentity joint category has its own explicit flag word. The proposal likelihood ratio is the product over clusters of `p_g(c)/q_g(c)`. Validate exact support, normalization, and the instrumented Pauli action before any performance interpretation.

## Fixed development design

Use the six existing distance-3 conditions (memory basis z/x crossed with x-biased/balanced/z-biased regimes), same fixed approximate-DEM-derived correlation-enabled PyMatching comparator used by the existing exact-categorical sampler. Training uses 100,000 samples/condition from the global fivefold-odds tilt; independent validation uses 20,000 samples/arm/condition for direct source, global tilt, and pair-cluster proposal. Seeds in condition order: training 202611701–706, direct 202611711–716, global tilt 202611721–726, cluster 202611731–736. Add a distinct 100-shot-per-arm instrumentation/runtime preflight using seeds 202611741–764; preflight samples are excluded from performance metrics. Use same decoder, source circuit, logical observable, and underlying shots protocol across arms.

Report weighted LER, standard error and relative standard error, failure-weight ESS, maximum absolute log weight, proposal mass diagnostics, and runtime for each condition. Advancement requires the candidate's validation standard error to be <=75% of both direct and global-tilt standard errors in at least four of six conditions, all weighted estimates to remain within three combined standard errors of each comparator, finite weights, full categorical support, and passed forced-outcome checks. This is a development gate only; no confirmatory claim or integration follows.

## Resource gates and stops

Before main runs, verify exactly 60 groups/condition, 256 positive proposal categories/group, <=20,000 extra Stim instructions per proposal circuit, successful compilation, exact recovery of sampled group categories from flags, detector/observable invariance, and all 256 isolated forced category outcomes across representative groups. Stop if the 100-shot-per-arm preflight projects over 300 seconds for training plus validation across all six conditions, any gate fails, any proposal has missing support, or likelihood weights are nonfinite. No parameter or grouping search is allowed after observing validation. No Stage S, sealed, or confirmatory data are accessed.
