# Corrected Statistical Design and Numerical Audit

**Review-only; no sampling or stochastic simulation.** This document corrects `outputs/qshift_advanced_decoder_research_v2/STATISTICAL_FEASIBILITY.md` and the analysis passages in the protocol and pre-registration drafts. The original documents remain unchanged.

## Estimand and four-stratum variance

Let `Y_{j,k,s,t}` be unconditional logical loss for policy j, primary scenario k, independent stream s and scored shot t. Define the stream paired mean `D_{k,s}=n_{k,s}^{-1}Σ_t(Y_event−Y_static)`. The primary estimate is `δhat=(1/4)Σ_{k=1}^4 mean_s(D_{k,s})`, with four separately generated strata: abrupt increase, abrupt decrease, smooth drift and transient burst. The mismatch stratum and stationary stratum are secondary; they are not included in this mean.

Conditional on the frozen shared template, calibration and tuning bundle, distinct evaluation roots are the independent units. With `S_k` streams per stratum and sample variance `s²_k` across stream means, the estimated conditional variance is

`Vhat = Σ_k s²_k / (16 S_k)`; `SEhat = sqrt(Vhat)`.

The factor 16 is the square of the four-stratum equal-weight denominator. If strata share S and n and have common paired discordance q and exchangeable within-stream ICC ρ, the shot-level approximation is `Var(Dbar_k) ≈ (q−δ_k²)[1+(n−1)ρ]/(S n)`, bounded above by replacing `q−δ_k²` with q. Therefore

`SE ≈ sqrt( Σ_k q_k[1+(n_k−1)ρ_k]/(16 S_k n_k) )`.

Under equal q, rho, S and n this reduces to `sqrt(q[1+(n−1)ρ]/(4 S n))`, the formula used for the earlier sensitivity table. This reduction is not valid if scenario discordance, stream count, scored length or dependence differs; use the stratum-specific sum instead. Within-stream ICC is only a sensitivity parameter: temporal dependence, event position and heterogeneous stream effects need not be exchangeable.

## Proposed implementable interval

For a future, approved analysis, use a stratified Welch t upper confidence limit on the stream means, conditional on the frozen development bundle. Compute `v_k=s²_k/(16 S_k)`, `Vhat=Σv_k`, and

`νhat = Vhat² / Σ_k [v_k²/(S_k−1)]`.

The proposed one-sided upper 95% bound is `δhat + t_(0.95,νhat) sqrt(Vhat)`. For a two-sided 95% interval replace `t_(0.95,νhat)` by `t_(0.975,νhat)`. This is implementable from one row per stream and preserves the four independently sampled strata. It is a Welch-Satterthwaite approximation, not an exact finite-sample guarantee: it relies on stream means being sufficiently regular, independent within stratum, and independent across scenario roots conditional on the training bundle. Pre-register the calculation and implement it independently before evaluation. Do not substitute shot-level binomial intervals or resample shots.

### Finite-cluster failure conditions

At 20 streams/stratum, t and cluster-bootstrap tails can be unstable. Rare binary losses create stream means with many zero-error or zero-discordance clusters; then resampling cannot create missing tail configurations and variance estimates may be zero or spuriously small. One influential stream, highly unequal cluster sizes, informative stream failure, cross-stream common RNG, or unmodeled shared calibration randomness also invalidates nominal coverage. Percentile cluster bootstrap is not a cure for very few clusters. Published few-cluster work documents failure of asymptotic and bootstrap methods when clusters are few or leverage/concentration is severe ([MacKinnon & Webb, *The wild bootstrap for few (treated) clusters*](https://doi.org/10.1111/ectj.12107); [cluster-robust inference guide](https://doi.org/10.1016/j.jeconom.2022.04.001)).

Use the following prespecified validity diagnostics, without changing the estimand: report all stream means, `S_k`, distinct nonzero-difference streams, zero-variance strata, maximum absolute stream contribution, leave-one-stream-out estimates, Welch degrees of freedom, and sensitivity to equal-weighted stratum-wise versus pooled estimates. If any stratum has fewer than 20 independent streams or fewer than 10 streams with nonzero paired differences, do not call the interval confirmatory; report the descriptive interval and mark inference unresolved. These are proposed minimum reporting gates, not proof of coverage. Designs A and B are development-only. Design C has many more streams but still needs the stated diagnostics.

As a finite-sample reference, because `D_{k,s}∈[-1,1]`, one-sided Hoeffding bounds with Bonferroni allocation α/4 to each stratum give

`U_H = δhat + (1/4)Σ_k sqrt(2 log(4/α)/S_k)`.

At α=.05 and S=500 this bound adds about 0.1324 absolute LER, far too wide to resolve a 0.0002 margin. This is valid under independent bounded stream means, conditional on the shared bundle, but intentionally conservative. It demonstrates that useful inference requires assumptions/regularity beyond boundedness. Do not treat the Welch interval as guaranteed merely because it is narrower.

## Shared template/calibration/tuning dependence

The stream interval above is **conditional** on a single frozen template set, pooled-static calibration set, and policy-tuning set. All evaluation policies share that bundle, which induces dependence in their marginal risks across streams when the bundle is random. Pairing and stream-cluster variance account for shared detector/observable evaluation shots and policy covariance conditional on the bundle; they do not account for uncertainty from re-fitting the shared bundle.

The recommended next study estimates performance of the actual frozen policy bundle conditional on the one independent development bundle. Its conclusion must be worded that way. If the target instead averages over calibration/tuning randomness, independently repeat the complete template/calibration/tuning procedure in multiple outer bundles, assign separate evaluation roots to each bundle, and treat bundle as the top-level cluster with streams nested within bundle and scenario. One outer bundle cannot estimate that variance. This design expansion changes the inferential target and budget and requires owner approval.

## Deterministic sensitivity audit

Planning formula only: for `q=P(Y_event≠Y_static)` and mean paired difference δ, `Var(D)=q−δ²`; q is not the difference in marginal error rates. For conservative sensitivity use q rather than q−δ². `DE=1+(n−1)ρ` is an exchangeable-correlation approximation. The z multiplier `z_.95+z_.80=2.48647486` describes a normal-theory separation from a one-sided boundary at nominal α=.05 and 80% power **only under independent/approximately normal estimates with known or adequately estimated variance**. It is neither exact power nor a cluster-coverage result. The target practical claim at margin m and true effect δ<−m needs approximate `SE≤(|δ|−m)/2.4865`; if `|δ|≤m`, the target cannot pass by design.

Recomputed q=.006 table below: `95% half-width` is the two-sided normal approximation `1.96 SE`; it is descriptive sensitivity only. “Z separation” is 2.4865 SE, not formal power.

| S per stratum × n | ρ | DE | SE | 1.96 SE | 2.4865 SE |
|---:|---:|---:|---:|---:|---:|
| 20×1,000 | 0 | 1.000 | 0.000273861 | 0.000536768 | 0.000680949 |
| 20×1,000 | .001 | 1.999 | 0.000387201 | 0.000758915 | 0.000962767 |
| 20×1,000 | .01 | 10.990 | 0.000907882 | 0.001779449 | 0.002257426 |
| 50×2,000 | 0 | 1.000 | 0.000122474 | 0.000240050 | 0.000304530 |
| 50×2,000 | .001 | 2.999 | 0.000212097 | 0.000415709 | 0.000527373 |
| 50×2,000 | .01 | 20.990 | 0.000561115 | 0.001099785 | 0.001395198 |
| 500×2,000 | 0 | 1.000 | 0.000038730 | 0.000075910 | 0.000096301 |
| 500×2,000 | .001 | 2.999 | 0.000067071 | 0.000131459 | 0.000166770 |
| 500×2,000 | .003 | 6.997 | 0.000102448 | 0.000200797 | 0.000254733 |
| 500×2,000 | .01 | 20.990 | 0.000177440 | 0.000347783 | 0.000441200 |

For q=.002 multiply SE by `sqrt(1/3)`; for q=.012 multiply by `sqrt(2)`. The expected arm error counts in the earlier table are exactly `N×p`: at 80k shots 240/480/800 for p=.003/.006/.010; at 200k, 600/1,200/2,000; at 900k, 2,700/5,400/9,000; at 4M, 12k/24k/40k.

## Historical development variability (not confirmatory)

I reaggregated the saved Pilot 2 `PILOT2_RESULTS.csv`, filtering to ordinary mode, `event_glr`, and the four conditions step-up, step-down, smooth, transient. For each of 80 streams, `D=(policy_only_error_vs_static_dev−comparator_only_error_vs_static_dev)/1300`. This is the conditional paired stream mean for event versus Pilot 2's development-label-selected static arm. The static arm and event controller were selected from shared development data; it is not the proposed detector-only primary comparator and not an independent replication.

| Scenario | Streams | Mean D | SD of stream D |
|---|---:|---:|---:|
| Step-up | 20 | −0.00015385 | 0.00059059 |
| Step-down | 20 | +0.00003846 | 0.00058397 |
| Smooth | 20 | +0.00003846 | 0.00039263 |
| Transient | 20 | −0.00026923 | 0.00045165 |

Across those scenarios the observed discordant pair rate is 31/104,000 = **0.00029808**. The equal-weight four-scenario point estimate is −0.00008654 (−0.00865 percentage points). Plugging observed scenario stream variances into `Vhat=Σs²/(16S)` gives conditional SE **0.00005723**, Welch df **68.79**, and a one-sided 95% upper endpoint **+0.00000888**. This does not establish even a negative average at that interval, much less clear a practical margin. The low observed q versus planning q=.006 is a useful alternative sensitivity point, but it can be specific to the chosen policies/grid and historical streams; it must not replace a conservative planning range. Calibration/tuning selection uncertainty is excluded. This is not formal evidence for the next design.

## Practical-margin sensitivity

The prior 0.0002 absolute margin equals 0.02 percentage points. It corresponds illustratively to about 3.4% of Pilot 2's 0.5957% static LER (or 3.7% of the older 0.546% reference), but no documented deployment utility, resource tradeoff, or external decision cost supports selecting exactly that value. Keep it provisional. For a hypothetical true benefit of 0.0004, the Gaussian separation formula gives:

| Candidate absolute margin m | Percentage points | Required gap if true benefit=.0004 | Approx SE ceiling |
|---:|---:|---:|---:|
| .0001 | .01 pp | .0003 | .00012065 |
| .0002 | .02 pp | .0002 | .00008044 |
| .0005 | .05 pp | none; true effect is smaller than margin | impossible |

At true benefit .0007, the approximate SE ceilings for m=.0001/.0002/.0005 are .00024131/.00020109/.00008044. At true benefit .0010 they are .00036196/.00032174/.00020109. These are normal-theory sensitivities, not power guarantees. The owner should choose the margin based on a pre-data utility/resource rationale. Never select it from future evaluation results.
