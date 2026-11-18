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

The bounded exact variable-elimination prototype establishes exactness only on small categorical tree/repetition models, verified against exhaustive enumeration and forced Stim outcomes. A synthetic pairwise grid remained under a one-million-entry factor cap at 11x11 binary locations, but its induced width reached 18. Phase 2B has higher-cardinality two-qubit categorical faults and a space-time detector graph that has not been mapped to this factorization. The full-circuit posterior gap and any decoder headroom therefore remain unknown.

A deterministic fragment from one final-round Phase 2B layer maps three 16-state Pauli-pair locations to six detectors and the logical observable. Forced Stim outcomes, 256 combined-fault XOR checks, and all 4,096 categorical configurations agree; variable elimination needs at most 512 entries. This confirms the local factor construction on one slice. It omits all other fault locations and their temporal interactions, so it does not bound full-circuit decoding cost or recoverable logical-error headroom.

Extending to all six target pairs in that same layer touched 10 detectors and 1,024 reachable syndromes. Exact XOR convolution and variable elimination agreed to 1.1e-16 on joint masses with width4 and 131,072 entries, taking 95 seconds for all reachable syndromes. Its isolated-layer MAP LER (1.06e-5) excludes every other fault location; it is not a full-circuit risk estimate and does not answer the decoder-headroom question.

Adding the immediately adjacent channel layer (12 categorical locations) raises the best tested dense-elimination intermediate to 17.2 billion entries. Eight simple scope orderings all exceeded the one-million cap, and inference was not attempted. Thus exact one-layer capability does not currently scale across even two neighboring gate layers in this representation. The full-circuit logical-class posterior and error-floor gap remain unresolved.

At fixed d=3, the standard five-round circuit is not a universal minimum-LER schedule in the tested model: 3-round attempts had lower LER and 40% fewer two-qubit channel pairs, while 7/9-round attempts had higher LER and more gate opportunities. However, rounds also set the physical storage duration. These per-attempt rates cannot establish superiority at equal memory time; that requires a matched-time schedule including idles or another declared time/resource budget.

The checkerboard local-H XZZX screen is a finite-size code/circuit co-design result. This exact gate-level transform increased one-qubit H/noise targets by 150–167% and worsened LER in all four tested d=3/5 and X/Z-biased cells. It rejects this transpilation under the declared noisy-H model, not XZZX with a native schedule. A fair follow-up would need a concrete native-gate schedule and matched physical noise/resource budget; no threshold or arbitrary-state-memory conclusion follows from this screen.

No positive lower bound on the achievable LER for the exact Q-SHIFT circuit has been established in this checkpoint. The numerical sample bounds above are statistical requirements, not a physical error floor proof. Further study must distinguish irreducible logical mechanisms at fixed distance from recoverable model or inference errors.

## Empirical ceiling for the existing correlation-mode pair

The independently audited Q-SHIFT pilot reports 3,532 errors for pooled-fixed uncorrelated matching and 3,349 for the same DEM with correlated matching, among 720,000 paired development shots. The predictions differ on 1,343 shots: 763 are off-only failures and 580 are correlated-only failures. An oracle selector that sees both predictions and the true observable could correct at most the 763 off-only failures relative to the uncorrelated baseline. Its residual errors would be at least 3,532 − 763 = 2,769, an empirical relative reduction ceiling of 763/3,532 = 21.6%. The actual correlated arm reduces errors by 183/3,532 = 5.18% in this sample.

At the same baseline LER, a 99.99% relative reduction would require at most 0.3532 expected errors in 720,000 shots, compared with the 2,769 errors that both current predictions make together on this observed sample. This is a descriptive sample-specific ceiling for selection between these two prediction arrays. It is not a population bound, and it says nothing about a new decoder that corrects cases both current modes miss. It does show that an adaptive controller over only these two modes cannot plausibly close the target gap on the existing pilot distribution.

## Logical-class posterior benchmark

For binary logical observable L and syndrome S under a fully specified channel, the minimum achievable average LER among deterministic decoders that only observe S is the Bayes risk

`LER_ML = Σ_s min(P(S=s,L=0), P(S=s,L=1))`.

This is a maximum-posterior logical-class decoder. It is distinct from choosing a most likely physical fault, an MWPM correction, or a mode among existing decoders. A quantitative decoder-only headroom claim requires either a trustworthy estimate of this quantity or a defensible lower bound for the exact circuit/noise distribution. Q-SHIFT has exact toy values, but no validated full d=3/d=5 logical-class posterior. Therefore the remaining recoverable inference gap and any fixed-distance physical error floor are unknown.

## Calibration overhead versus logical throughput

The detector-only policy experiment reports LER per logical-memory shot. It used C=500 full-circuit calibration shots before each N=100 logical shots and did not charge the fixed-Z baseline for calibration. If calibration shots cannot themselves produce useful logical outputs, a throughput comparison has a different break-even condition. With adaptive LER p_A and static LER p_S, adaptive correct outputs per total circuit shot exceed the static rate only when

`N > C(1-p_S)/(p_S-p_A)`.

Using the observed d=3 direct-development rates and C=500 gives illustrative minimum amortization horizons of about 618,000 logical shots at ratio2 (p_A=.00405, p_S=.004855), 228,000 at ratio5 (.00198 vs .00416), and 169,000 at ratio10 (.001165 vs .00412). These plug-in values have sampling uncertainty and assume each calibration shot consumes the same resources as one logical shot while yielding no usable logical result. They do not negate the per-logical-shot LER gain; they show that operational value depends on calibration reuse and the chosen resource objective. The fixed test did not measure stability over these long horizons.

## Observable-specific memory is not a full logical-qubit channel

The X-memory and Z-memory Stim circuits prepare and score different logical observables. Selecting between them after learning the noise profile is meaningful when the workload can choose which logical eigenstate/observable to store. It is not a same-task comparison for an arbitrary encoded qubit, whose logical X and Z channels both matter. The d=3 detector-selected basis experiment therefore supports a known-basis memory configuration result only. It does not establish improved arbitrary-state quantum memory or a decoder-only gain.

A direct same-observable check held the Z-memory circuit and observable fixed and selected between two profile-conditioned PyMatching graphs using detector calibration. The selected bank had 775 failures versus 779 for a pooled static graph in 200,000 shots; its bootstrap interval included no change. This small result suggests that profile inference can be accurate while decoder selection yields little gain when the static graph already captures the relevant syndrome statistics. The tested graph family and one d=3 condition do not bound all decoder improvements.

The conjugate-basis samples illustrate why the task distinction matters. At d=3 and 10:1 X bias, X-memory LER was .001275 while Z-memory was .006575; at 10:1 Z bias, Z-memory was .000700 while X-memory was .007800. The adaptive basis selector reports the lower of these task-specific rates, but the high-error conjugate channel remains. These marginal tests do not fully characterize the joint logical Pauli channel or process fidelity; they are enough to show that a selected-basis LER cannot stand in for arbitrary-state memory performance.

An exploratory replay of the saved calibration and logical windows modeled equal-duration alternation between X- and Z-biased profiles. At dwell periods up to 10,000 logical shots, none of the tested calibration budgets (25/100/500 shots) and update intervals (100/1,000/10,000/100,000 shots) produced more correct outputs per total circuit shot than the best fixed basis. At 100,000-shot dwell, only ratio-5 and ratio-10 schedules slightly exceeded the fixed-basis throughput (about 0.10% and 0.21% on the best tested grid points); ratio 2 did not. These are plug-in scenario projections with no uncertainty propagation, not a measured change-point system. They reinforce that large LER-per-attempt reductions do not ensure resource-level value when profiles switch and calibration is charged.


## Exact parity-state extension (development fragment)

For a binary logical observable, the joint posterior over syndrome and logical bit can be represented by two arrays over syndrome alone: P(s)=P(s,L=0)+P(s,L=1), and Z(s)=P(s,L=0)-P(s,L=1). This suffices to recover both logical-class masses and the conditional MAP risk `sum_s (P(s)-|Z(s)|)/2`, halving state count. The seven-layer d3 circuit-tail implementation used 1,048,576 states and exactly matched an independent Walsh calculation, a six-layer joint reference, and 512 forced Stim compositions. Its isolated risk is 0.00104093. This establishes a useful exact representation for the selected tail only; it does not establish full-circuit decoding feasibility or a physical LER floor. Cost remains exponential in touched detector count (20 bits here), and memory/rounding/runtime limits must be assessed at each scope.


## Native-gate XZZX finite-size observation

A direct Stim `XCX` implementation removes extra one-qubit H targets while preserving qubits, detectors, rounds, two-qubit interaction count, and source PAULI_CHANNEL_2 targets. At d3/d5, 500k shots/cell under the explicit equal-duration/equal-noise CX/XCX/CZ assumption gave XZZX/CSS ratios 0.662/0.376 for X-biased noise and 3.86/11.24 for Z-biased noise. This shows that the code orientation and bias direction interact in the tested decoder/circuit. It is not an information-theoretic bound, threshold, or evidence that XZZX is inherently inferior; native XCX/CZ hardware noise equivalence remains unverified.


## Complementary XZZX orientation result

One fixed complementary checkerboard orientation improved over the original orientation for Z-biased d3/d5 simulation, but its LER remained 3.04x/6.16x that of CSS at matched resources. This is not a general code limit: it is evidence about two fixed orientations with correlation-enabled matching and a specific native-gate noise assumption.


## Spatial heterogeneity check

Under a synthetic stable spatial map that doubles/halves rates relative to the .003 mean (actual 1.5x/.5x factors), even the decoder with the exact profile map achieved less than a 1% equal-weight relative reduction over a pooled graph on d3. This is evidence about one approximate-DEM decoder and two hotspot orientations, not a fundamental limit on spatial adaptation. It suggests the present graph representation is relatively insensitive to this mild local rate pattern.


## Distance-9 basis-alignment uncertainty

At d9, 500k shots gave 1 aligned failure against 408 mismatched failures for one X-biased profile. The point ratio .00245 is consistent with a broad exact ratio interval [.0000619,.01373], which includes improvements much smaller than the aspirational 10,000-fold reduction. This shows how rapidly evidence becomes sample-limited as the aligned LER falls; it neither proves a floor nor establishes exponential distance scaling.


## Biased MPS scope boundary

At p=.05 in perfect-syndrome planar code capacity with X:Y:Z=10:1:1, fixed chi=16 planar MPS outperformed bias-aware MWPM in d5 on two 5k-sample roots and directionally in d3 (one of two roots had a paired interval spanning zero). Its d5 decoding latency was about 31x higher. These results establish neither a Q-SHIFT repeated-circuit gain nor a usable lower LER bound; measurement faults, spacetime correlations, and categorical two-qubit gate channels are absent.


## Tensor-train rank of the exact seven-layer tail

For the exact 20-detector P/Z posterior, natural temporal detector order gives maximum tensor-train ranks 91 at relative Frobenius tolerance 1e-10 and 30 at 1e-6. The fixed rank<=64 high-accuracy gate therefore fails. The finding is representation/order specific and cannot be generalized to the full circuit or all tensor-network contractions.


## d9 shot budget for the 99.99% relative target

The mismatched d9 baseline observed 408/500,000 failures, LER 0.000816; its exact two-sided 95% lower endpoint is 0.00073876. A 10,000-fold reduction would require candidate LER <= 8.16e-08 using the point baseline, or <= 7.39e-08 under this conservative baseline endpoint. Under an optimistic single-condition IID binomial model, zero candidate failures require 36,712,404 shots using the point baseline and 40,550,810 using the lower endpoint. If one candidate failure occurs, the corresponding exact one-sided 95% upper-bound requirements rise to 58,135,593 and 64,213,866. These are lower-bound evidence budgets before independent roots, multiple conditions, baseline uncertainty, or model selection; they are not a physical lower bound. Full calculation: `d9_relative_target_sample_budget.json`.


## All-location fault composition under ratio-sensitive decoding

The preflight passed synthetic flags for all 15 two-qubit Paulis, all three one-qubit Paulis, and explicit X/Z error events (zero data/flag mismatches). Both d3 conditions had 120 two-qubit pairs and 40 one-qubit locations; explicit measurement targets were 49 for Z-memory/X-biased and 49 total for X-memory/Z-biased. Source and instrumented samples had unchanged 40-detector/one-observable layout, and failure-rate differences were below 1.1 combined standard errors. The 200,000-shot main screen took 3.73 seconds.

At 100,000 shots/condition, ratio-5/ratio-10 models failed on 753/752 Z-memory X-biased shots (61 prediction disagreements) and 769/766 X-memory Z-biased shots (95 disagreements). The both-wrong groups contained 722 and 720 shots; ratio-10-fixes-ratio-5 groups contained 31 and 49, while ratio-10-breaks-ratio-5 contained 30 and 46. In both conditions, mean tracked two-qubit faults were about 0.349 per both-correct shot and 1.87 per both-wrong shot. In the biased Pauli outcome counts, XX was most frequent in the X-biased Z-memory both-wrong group (794 events), while ZZ was most frequent in the Z-biased X-memory both-wrong group (800). One-qubit and explicit measurement-fault counts also differed across outcome groups; see the JSON for full counts.

The decoder-disagreement groups are small, particularly the 30–49-shot fix/break groups. These are conditional fault associations from one fixed development stream, not causal attribution, evidence that one fault channel caused decoding errors, or a hardware noise claim. The new instrumentation extends the earlier two-qubit-only report; it does not change the prior conclusion that raw fault burden alone cannot explain decoder behavior. No sealed or confirmatory data were accessed.


A secondary matched-resource synthesis estimates an aligned per-2-distance LER multiplier of .095 versus .496 for mismatched memories under this simulator model. It is a four-point descriptive Poisson fit, with only one aligned d9 failure; it establishes neither a threshold nor an asymptotic exponent. The d9 alignment ratio point is still 24.5x above the aspirational 1e-4 relative target.


The d3/d5 native-XCX XZZX gain under X bias is relative to CSS Z-memory. Against X-aligned CSS, the observed XZZX rate was 3.6x / 13.5x higher at equal counted qubit, detector, round, and two-qubit interaction budgets. Neither finite-size screen supports a threshold conclusion; native gate equivalence remains an assumption.


Fresh d5 2x2 code/basis evidence: CSS-X 79/500k, CSS-Z 1,848/500k, XZZX-X 604/500k, XZZX-Z 670/500k. Under the tested model XZZX improves on CSS-Z but not aligned CSS-X (7.65x higher XZZX-X rate). This bounds one code-selection claim, not the asymptotic XZZX threshold.


A fresh d5 replication found pooled equal-weight X/Z task rate ratio XZZX/CSS=.662 (.616–.710), but XZZX-X/CSS-X=6.18 (4.96–7.78). The tradeoff reproduced on a second independent development stream; still one distance, a synthetic model, and no arbitrary-state logical-channel measurement.


The balanced-memory XZZX/CSS rate ratio was 1.18 at d3, about .66 at d5 on two streams, and .279 at d7. This shows strong distance dependence in the sampled simulator family, but aligned CSS-X has very sparse failures at d7 and XZZX uses an unverified native-gate equivalence assumption. It is not a threshold or scaling exponent; d9 is the next discriminating finite-size point.


The d9 equal-weight separate X/Z memory rate ratio XZZX/CSS is .107 (.070–.159), an 89% reduction, not 99.99%. The known-X basis comparison is sparse and reversed (1 CSS-X vs 10 XZZX-X failures). This bounds the balanced-workload claim at one finite size; it establishes no threshold or full logical-channel behavior.


At d11, equal-weight separate-basis XZZX/CSS=.0448 (.0090–.1366), with only 70 combined errors; X memory had zero errors in each architecture. The point is 448x above the aspirational relative target. The largest tested run now takes 282s/2m shots and ~2.69 GiB, so further same-size evidence has increasing resource cost. This is not an asymptotic exponent.


At d11, the observed comparator point implies target candidate LER 6.7e-9 for a 1e-4 relative rate. An optimistic one-sided 95% IID design would need 447M shots with zero failures (708M allowing one), assuming the comparator rate is known. The observed XZZX point rate is 3e-6, roughly 448 times the target; sample size cannot close a performance gap by itself.
