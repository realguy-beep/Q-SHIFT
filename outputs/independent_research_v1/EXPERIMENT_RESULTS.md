# Experiment and evidence results

## New deterministic feasibility check

**Question:** Can Stim build a non-approximated detector error model for the Q-SHIFT categorical circuit so that the planned matched-DEM-family mechanism experiment is executable with PyMatching?

**Method:** In the isolated Python 3.12 environment, loaded the tracked Q-SHIFT Phase 2B circuit builder read-only and generated all six distance-3, five-round circuits (two memory bases by three Pauli-composition regimes). Called `circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=False)` for each circuit. No shots were generated and no outputs were written to the original Phase 2B directory.

**Result:** 0/6 conversions succeeded. All failed immediately with Stim `ValueError`: `PAULI_CHANNEL_2` requires `approximate_disjoint_errors=True` for error analysis. Runtime was under 0.01 seconds total. This deterministically confirms the pretest blocker described in the existing `outputs/correlation_mechanism_audit/FOLLOWUP_PROTOCOL.md`.

**Interpretation:** The proposed exact-vs-approximate DEM family cannot be implemented through this Stim circuit-to-DEM route for these categorical two-qubit channels. This does not establish that the approximation caused or did not cause the earlier correlation-mode interaction. It means the follow-up's primary contrast cannot be executed as written. A substitute must model categorical gate outcomes natively and be validated against the exact small-instance reference before sampling.

## Previously completed development evidence reviewed

The repository's separate `outputs/correlation_pilot/` is already a complete, independently rescored 720,000-shot development pilot. Its pooled fixed correlated arm had 3,349 errors and the uncorrelated arm had 3,532, with equal-stratum paired difference -0.00025417 and root-bootstrap 95% interval [-0.00035000, -0.00016250]. Its predeclared practical gate failed because the upper interval endpoint did not meet -0.0002. It is prior work, not an experiment run by this expedition. Its paired-error pattern is condition dependent and does not validate adaptive mode selection.

No confirmatory data were accessed. No experiment in this package establishes performance on an untouched test set or hardware.

## Categorical sum-product prototype on exact toys

**Hypothesis:** A loopy sum-product approximation over native categorical fault-location variables could preserve mutually exclusive Pauli outcomes while estimating logical-class probabilities, avoiding DEM splitting at the local channel level.

**Prototype:** `categorical_bp.py` keeps the outcome alphabet at each toy fault location and imposes detector and hypothesized logical parity checks. It compares Bethe partition estimates for logical 0 and 1. Tests use the existing independently validated one-qubit and two-qubit categorical toy models, then score BP decisions against their exhaustive exact posterior. No stochastic samples are used.

**Outcome:** The implementation returned normalized probabilities and converged on every toy syndrome, but its decoding quality is unacceptable on the one-qubit toy. It agrees with exact MAP on 2/4 syndromes and has exact-under-toy LER 0.057354 versus exact MAP 0.002646. On the two-qubit toy it agrees on 4/4 syndromes and has LER 0.060000, equal to exact MAP for that fixture. The same code therefore has a sharp topology-dependent result, not general validation.

The tests confirm interface, bounds, and full syndrome coverage. They do not certify algorithmic correctness or quality. The global observable-parity check creates additional loops. The hypothesis is rejected in this form. The result reinforces the need to validate posterior mass and logical decisions against exhaustive categorical references per topology before considering any circuit-scale approximation. No Q-SHIFT distance-3 experiment was run.

## Documented approximation-threshold sensitivity preflight

Stim's v1.16.0 documentation permits a probability threshold for approximating disjoint errors. To see whether this offers a distinct valid model family at Phase 2B's configured probabilities, generated each of the six circuits in memory and tried thresholds 0.001, 0.0018, 0.003, and 1.0 with graph decomposition enabled. For successful conversions, hashed the DEM and PyMatching weighted graph. This generated no shots and wrote only `approximation_threshold_scan.json`.

At 0.001, conversion failed in all three biased regimes because a `PAULI_CHANNEL_2` argument was 0.00178571, above the permitted maximum threshold. The balanced regimes converted. At 0.0018, 0.003, and 1.0, every condition converted, and within each condition all three successful thresholds produced exactly the same DEM and graph hashes (142 edges). Thus no alternate successful model family was found over this predeclared threshold set. This is a deterministic semantic sensitivity preflight, not a performance comparison.

## qecsim planar MPS runtime and validity preflight

Installed qecsim 1.0b9 in the isolated research environment. On identical IID depolarizing code-capacity errors at p=0.05, qecsim's untruncated planar MPS (`chi=None`, column contraction) and planar MWPM both returned recoveries in the codespace on 100 shots at d=3 and d=5. The small preflight counts were 4/3 errors at d=3 and 3/0 at d=5 (MWPM/MPS); these are not performance evidence and were not used to adjust the declared noise or seed plan.

The MPS decode time averaged 0.864 ms at d=3 and 60.9 ms at d=5. Scaling the measured decode times to the declared 5,000 shots per distance projects roughly 309 seconds of MPS decode work, already over the five-minute total cap before MWPM, generation, and bookkeeping. Per the protocol, the 5,000-shot screen was stopped before launch. Peak RSS was 147,200 KiB. qecsim emitted `Failed to load clib: libpypm.so.` and used its Python path; this warning does not invalidate return codes, but the comparison's runtime is implementation-specific. The result is a runtime feasibility gate for this exact, untruncated setup only. No Q-SHIFT circuit-level or measurement-noise samples were generated.

## Fixed-bond MPS versus MWPM code-capacity screen

After the untruncated runtime stop, a separate preregistered fixed-χ=16 run used 5,000 identical IID depolarizing physical-error samples per distance (p=0.05) with perfect syndrome information. Every recovery returned to the code space. At d=3, MPS had 123 logical failures (LER .0246; Wilson 95% CI [.0207,.0293]) versus MWPM's 206 (.0412; [.0360,.0471]); the paired difference was −.0166 (normal 95% interval [−.0206,−.0126], McNemar p=3.49e−17). At d=5, MPS had 30 failures (.0060; [.00421,.00855]) versus 92 for MWPM (.0184; [.0150,.0225]); paired difference −.0124 (interval [−.0161,−.00874], McNemar p=9.33e−12).

The fixed-bond decoder used about 0.988 ms/decode at d=3 and 13.74 ms/decode at d=5, versus 0.181 and 0.507 ms for qecsim's Python MWPM path. Total run time was 80.4 s and peak RSS 118,636 KiB. This is promising evidence that bounded-bond MPS can improve this particular perfect-syndrome depolarizing comparison, at a substantial latency cost. It does not establish a gain on Q-SHIFT's repeated noisy circuit, other noise models, other p values, or larger distances; p=.05 and only two distances make it unsuitable as a threshold or scaling claim. Follow-up should first establish model compatibility and test a circuit-level surface-code setting with a strong correlated matching baseline, if an efficient implementation is available.

## Known-profile basis alignment at distance 7

Extended the fixed known-profile rotated-memory comparison to d=7, 13 rounds, p=.003 gate/measurement channels and bias ratio 10. The d=3 generated circuits remained byte-identical to the existing source builder; X and Z memory had matched resources within each biased profile (118 physical qubits, 624 detectors, 1 observable, and 2,184 two-qubit channel pairs). Used fresh direct source-circuit samples, the same approximate DEM conversion threshold (.0018), and correlation-enabled PyMatching. A scalar preflight exceeded the five-minute extrapolation and stopped; the batched decoder passed 100/100 scalar-agreement checks per condition and projected below the cap. The full 500,000-per-cell run then completed in 34.6 s.

Under X bias, aligned X-memory had 5/500,000 failures (LER 1e−5, Wilson 95% CI [4.27e−6, 2.34e−5]) versus 1,009/500,000 for Z-memory (.002018, CI [.001897,.002146]); rate ratio .00496 (conditional exact 95% CI [.00161,.01017]). Under Z bias, aligned Z-memory had 3/500,000 (6e−6, CI [2.04e−6,1.76e−5]) versus 1,227/500,000 for X-memory (.002454, CI [.002321,.002595]); ratio .00244 (CI [.000504,.00590]). The p-value for the second comparison underflows to zero in SciPy's floating representation and should be read as extremely small, not as a literal probability of zero.

The direction is now consistent at d=3, 5, and 7 for the studied fixed bias profiles, but the aligned d=7 estimates have only 3–5 failures. Treat the ratios as strong finite-sample evidence of direction and large effect in this synthetic known-profile model; absolute LER and distance-scaling precision are weak. This remains a static code/circuit design comparison with one matched decoder family, not evidence for online adaptation, unknown bias, hardware performance, or a 10,000-fold improvement over the strongest same-code baseline.

## Detector-only bias identification

Trained a four-feature linear discriminant on 100,000 fresh d=3 Z-memory circuit shots for each extreme profile (10:1 X and Z bias). Features were normalized detector-event rates grouped by detector coordinate and early/late time; detector samples only were used. The classifier was frozen before evaluating independent 1,000-window streams at d=3,5,7. With a 500-shot calibration window it classified the direction correctly in all 2,000 tested windows at each distance (95% exact lower bound .998); with 100 shots it classified all windows at d=5 and d=7, and 99.5% at d=3. At 25 shots, accuracy was 88.8% at d=3 and 100% at d=5,7. These results apply to the exact synthetic 10:1 noise families and fixed Z-memory calibration design.

A predeclared cross-strength test then froze that same binary model and evaluated fresh streams at bias ratios 2,5,10. Direction accuracy with 500 calibration shots was 94.9%, 100%, and 100% at d=3; 99.3%, 100%, and 100% at d=5; and 99.35%, 100%, and 100% at d=7. At ratio 2, 25-shot accuracy ranged from 64.1% at d=3 to 84.4% at d=7; 100 shots raised it to 77.6%, 91.5%, and 92.0%. A separate three-class model trained to distinguish balanced from extreme bias tended to classify moderate ratios as balanced, especially at higher distances. This shows that direction and magnitude/near-balanced detection are different inference tasks. At ratio 1 either basis is equivalent in this model.

Finally, an end-to-end synthetic development screen used the frozen binary classifier on 1,000 independent 500-shot detector-only calibration windows per profile, followed by separate 100-shot logical-memory batches for both bases under each profile. Correlation-enabled PyMatching and the same approximate DEM threshold were used throughout. Under equal X/Z profile weights, selected-policy LER was .00405 at ratio 2 versus .004855 for the predeclared static-Z baseline (16.6% lower; stratified window-bootstrap 95% interval for policy-minus-static [-.001125,-.000490]); at ratio 5, .00198 versus .00416 (52.4% lower; interval [-.00246,-.00190]); at ratio 10, .001165 versus .00412 (71.7% lower; interval [-.00323,-.00267]). The policy matched the observed known-profile oracle at ratios 5 and 10 and was close at ratio 2. The direct logical streams were fresh and independent of calibration streams.

The first implementation pass reversed the classifier's sign convention and selected the opposite basis. It was marked invalid, preserved in `adaptive_basis_end_to_end_first_pass_reversed.json`, and rerun with the same fixed seeds after adding an explicit training-label polarity check. The reported results above are only from the corrected selector. These are development simulations of stable, known synthetic profile families with equal prior weight. The compared LER is per logical shot: each selected 100-shot memory batch used a 500-shot calibration window, while fixed-Z used no calibration. The policy therefore spent five calibration shots per logical shot in this deliberately short horizon; longer amortization and equal total-workload comparisons are needed. Stationarity, transfer to real devices, other circuit models, drift, and the fair cost of repeated recalibration remain unresolved; this is not a deployed adaptation claim or a confirmatory result.

## Frozen bias selector under total-rate drift

As a follow-up, calibration windows remained at gate/measurement p=.003, but independent logical-memory outcomes were generated after both rates doubled to p=.006, with the same X/Z bias direction and ratio. The classifier was not retrained. The .0018 DEM conversion threshold failed deterministically before any shots because a channel probability reached .00357; the test used a shared .004 threshold, selected from the exact maximum channel probability, across every p=.006 arm. Under equal profile weights, policy LER was .014785 versus static-Z .016845 at ratio 2 (12.2% lower; bootstrap delta interval [−.00263,−.001495]), .00776 versus .015715 at ratio 5 (50.6%; [−.00850,−.00742]), and .004325 versus .01493 at ratio 10 (71.0%; [−.01117,−.01006]). At ratios 5 and 10 the selected-basis policy matched the observed known-profile oracle in these samples; at ratio 2 it was close.

This checks a twofold total-rate change after calibration while the dominant Pauli direction remains stable. It does not test an X↔Z change point, hidden spatial variation, device noise, calibration amortization, or equal total-workload utility. Results remain development-only. The decoder used the same per-test-circuit approximate DEM and correlation-enabled PyMatching at the fixed .004 conversion threshold.

## Exploratory calibration-cost frontier

Re-scored prefixes of the same seeded calibration windows and reused the same independent logical outcome arrays; no new sample streams were generated and the classifier was not refit. At 25/100/500 calibration shots per 100 logical shots, the projected policy reductions versus static Z were 5.1%/11.6%/16.6% at ratio 2, 27.8%/49.6%/52.4% at ratio 5, and 57.5%/71.2%/71.7% at ratio 10. The ratio-2, 25-shot interval included zero; other listed policy-minus-static bootstrap intervals were below zero. Calibration expenditure was 0.25/1/5 shots per logical shot respectively. Prefixes are nested, so these estimates are correlated and the lower-budget endpoints are exploratory rather than confirmatory. They expose a practical tradeoff: fewer calibration shots reduce overhead but leave more direction mistakes, especially at weak bias.

## BP+LSD development screen on Phase 2B circuits

LDPC 2.4.1's `BpLsdDecoder` accepted the flattened approximate DEMs in all six distance-3 Phase 2B conditions (40 detector checks, 578–586 fault variables, one observable). A preflight showed the 5,000-shot-per-condition plan was well within the runtime cap. The main run sampled 5,000 fresh shots from each original Stim circuit (30,000 total), using the same circuit outcomes for correlation-enabled PyMatching and BP+LSD. All decoders used the same `decompose_errors=True`, `approximate_disjoint_errors=0.0018` decoder model. The BP+LSD fault vectors reproduced every observed detector syndrome (0 invalid outputs).

With min-sum BP (scale 0.9, 200 iterations) and LSD order 0, `LSD_0`, `LSD_E`, and `LSD_CS` each produced 321 logical failures, versus 138 for correlation-enabled PyMatching. Each method was worse in all six conditions. The pooled paired LER increase was 0.00610 (0.01070 vs 0.00460); the equally weighted six-condition macro delta was also 0.00610, with a descriptive across-condition t interval of 0.00270 to 0.00950. That interval summarizes these six fixed conditions and is not a population generalization interval. Discordant outcomes were 223 BP+LSD-only failures and 40 PyMatching-only failures. The methods had identical aggregate outputs in this run; no LSD variant showed a benefit at the fixed configuration.

This is a negative, development-only result for one distance, one approximate DEM threshold, and one BP/LSD configuration. It does not establish that BP+LSD is generally inferior, nor does it support integration. The result suggests that simply treating each approximate DEM instruction as a binary fault variable and applying low-order BP+LSD does not improve over the strong correlation-enabled matching baseline on these circuit samples. Possible causes include loopy inference, the categorical-to-DEM approximation, and poor calibration of the binary fault-variable posterior; the run does not isolate these mechanisms. Full condition-level intervals and runtime are in `bplsd_results.json`. The initial analysis artifact lacking the later syndrome-validity check is preserved as `bplsd_first_pass_unverified.json`; all reported counts come from the corrected rerun.

## Likelihood-ratio importance sampling for the DEM surrogate

Exhaustive enumeration of an 8-state toy with three independent faults verified likelihood-ratio normalization to 1 and reproduced the exact logical failure probability 0.34 to floating-point precision. The six Phase 2B approximate DEMs were then sampled directly and under a uniform 5x odds tilt, while decoding with the same original-probability correlation-enabled PyMatching. The preflight had 5,000 shots per arm/condition and reduced estimated relative SE by at least 25% in all six conditions, passing the predeclared gate.

The fresh 20,000-per-arm screen also reduced estimated relative SE in all six conditions: importance/direct SE ratios were 0.437–0.509. Weighted estimates ranged from 0.000985 to 0.00824; direct estimates ranged from 0.00100 to 0.00900. Effective sample sizes among weighted failure shots were 104–719, and maximum absolute log weights were 14.0–17.2; no nonfinite weights occurred. An eight-replicate, 5,000-per-arm follow-up found at least 25% lower between-replicate standard deviation in five of six conditions. The one exception (`z` memory, balanced) had an SD ratio of 1.12. Across conditions, paired-replicate mean estimator differences were small relative to their estimated standard errors; see `rare_event_replication_check.json`.

This is positive evidence that a simple fivefold odds tilt can improve the precision of LER estimation for this approximate independent-mechanism DEM and fixed decoder. It is not an estimator for the original categorical circuit distribution: the categorical-to-DEM approximation remains in the target itself. It also does not establish that a rare-event estimate is more accurate than a much larger direct circuit sample. There is no Q-SHIFT circuit-level rare-event result or 99.99% reduction claim. Full seeds, weights, condition estimates, and replicate summaries are stored in the three `rare_event_*.json` artifacts.

## Exact categorical circuit weighting follow-up

To test the DEM limitation, the sampler was instrumented at the source `PAULI_CHANNEL_2` locations. Each target pair was replaced by a mutually exclusive `E`/`ELSE_CORRELATED_ERROR` chain with probabilities normalized against identity, and a private four-bit Pauli-pair label was carried on idle flag qubits and measured at circuit end. The proposal multiplied every nonidentity pair probability by five relative to identity and renormalized; weights used the exact categorical ratio. All other noise instructions stayed unchanged. A synthetic validation checked all 15 Stim argument positions in four X/Z basis combinations (60 one-hot checks), the direct and tilted categorical frequencies, all two-qubit data Pauli actions, and independence of consecutive target-pair chains. A rec-based noiseless detector/observable fixture was unchanged. An independent 20,000-shot-per-condition comparison between the instrumented direct arm and each unmodified Stim circuit had max absolute standardized LER difference 0.701 (all six under the 4-SD gate).

On 20,000 direct and 20,000 tilted samples per condition from the exact categorical Phase 2B circuit, fixed correlation-enabled PyMatching had direct LERs from 0.00065 to 0.00800 and importance estimates from 0.00105 to 0.00872. Direct and weighted estimates differed by at most 1.81 combined standard errors. Estimated relative SE was lower in five of six conditions; the failure-weight ESS ranged from 21 to 357. This first screen looked promising but was not sufficient to claim stable efficiency.

Two independent blocks of eight replicates each (5,000 direct and 5,000 tilted shots per condition per replicate) challenged that result. Across the combined 16 replicates, mean direct/weighted estimates agreed within 1.37 standard errors in all six conditions, supporting the likelihood-ratio calculation. But the between-replicate weighted/direct SD ratios were 0.516, 0.789, 1.638, 0.783, 0.827, and 1.078 in condition order. The equal-weight six-condition macro SD ratio was 1.12, so the fivefold tilt did not reliably reduce overall estimator variance under the exact categorical circuit distribution. In particular, it increased variance in z-memory/z-biased. The channel instrumentation and weight estimator are validated; this fixed global tilt is not an established efficiency improvement. Do not integrate it as a decoder or cite the DEM-surrogate variance gain as a circuit-level gain. Results are in `categorical_importance_*.json` and `categorical_sampler_crosscheck.json`.

## Cross-entropy categorical proposal

To address the global-tilt failure, trained per-location categorical proposals as the forward-KL product-marginal projection of the logical-failure-conditioned trajectory distribution. Training used 100,000 independent fivefold-tilted source-circuit trajectories per condition, exact source/proposal weights, and 50 baseline-distribution pseudocounts per location. Validation used separate 20,000-shot direct, global-fivefold, and cross-entropy arms per condition. No validation outcomes were used to update proposals.

The cross-entropy proposal failed its predeclared advancement gate in all six conditions: it did not reduce estimated standard error by at least 25% versus both direct and global-tilt sampling in any condition. It often had higher SE than global fivefold tilt, with the largest instability in z-memory/z-biased (relative SE 0.334; failure-weight ESS 9.0; maximum weight 19.7) and x-memory/x-biased (relative SE 0.292; ESS 11.8). The validation weighted estimates remained within three combined standard errors of both comparators in every condition, so the likelihood ratio remained numerically consistent, but the conditional-marginal product did not create an efficient proposal. Largest observed weight was 77.3. This negative result is consistent with failure depending on cross-location correlations that the independent product projection omits; the experiment does not prove that explanation. The proposal is not advanced and was not tuned on validation data. See `categorical_cross_entropy_results.json`.

## Memory-basis alignment under known Pauli bias

The exact direct-arm sample from the importance screen and the independent unmodified-circuit crosscheck each supplied 20,000 shots per distance-3 condition. Pooling these independent draws gives 40,000 shots per memory basis/noise profile. Both orientations use 26 physical qubits, 40 detectors, five rounds, 120 two-qubit channel pairs, and the same 0.003 gate and measurement error rates; only memory basis and the corresponding measurement channel differ. Decoding used correlation-enabled PyMatching built from each source condition's same approximate DEM.

Under X-biased noise, X-memory had 51/40,000 logical failures (LER 0.001275) versus 263/40,000 for Z-memory (0.006575): 80.6% fewer errors, rate ratio 0.194 (conditional exact 95% CI 0.141–0.257, p=1.43e-35). Under Z-biased noise, Z-memory had 28/40,000 failures (0.000700) versus 312/40,000 for X-memory (0.007800): 91.0% fewer errors, rate ratio 0.0897 (95% CI 0.0614–0.1323, p=7.80e-62). Under balanced noise, rates were 187/40,000 and 197/40,000 (0.004675 and 0.004925), with no meaningful basis difference (X/Z ratio 1.05, 95% CI 0.858–1.280, p=0.646).

This supports a simple known-profile code/circuit choice: align the stored logical basis with the calibrated stable bias. It is not an adaptive-policy result, a decoder gain, or a new code family. It cuts LER by roughly 5×–11× in these two biased distance-3 settings, far short of the 10,000× aspirational target. The evidence does not test bias drift, estimation overhead, or larger-distance scaling. See `basis_orientation_results.json`.

## Distance-5 basis-alignment scaling check

Built distance-5 rotated-memory circuits with nine rounds and the same 0.003 gate/measurement rates and 10:1 X/Z bias ratio. The research builder reproduced the source d=3 circuits byte-for-byte in all six configurations. At d=5 the X and Z memory circuits had matched resources: 64 physical qubits, 216 detectors, 720 two-qubit channel pairs, and nine rounds. The screen used 50,000 exact source-circuit samples per biased condition/basis, with correlation-enabled PyMatching from each matching approximate DEM.

For X-biased noise, X-memory had 6 failures (LER 0.00012) versus 217 for Z-memory (0.00434): aligned/mismatched rate ratio 0.0276 (conditional exact 95% CI 0.0100–0.0543). For Z-biased noise, Z-memory had 6 failures (0.00012) versus 270 for X-memory (0.00540): ratio 0.0222 (95% CI 0.00808–0.0436). These samples support the same bias-alignment direction at d=5, with larger relative gains than at d=3. Each aligned estimate is based on only six failures, so absolute-rate precision is limited. This two-distance comparison is not a threshold estimate, does not test higher distances or bias drift, and still falls short of a 10,000× reduction. Data are in `code_distance_results.json`.

## Bias-strength crossover at distance 3

To identify whether basis alignment only helps under extreme bias, evaluated fresh exact circuits at X/Z bias ratios 2 and 5, with the same total gate/measurement error rates, five rounds, and matched X/Z memory resources. Each condition used 50,000 source-circuit samples and correlation-enabled PyMatching from its approximate DEM. At ratio 2, X-memory under X bias had LER 0.00418 versus 0.00568 for Z-memory (aligned/mismatched ratio 0.736, 95% CI 0.613–0.876); Z-memory under Z bias had 0.00398 versus 0.00616 (ratio 0.646, CI 0.538–0.768). At ratio 5, the aligned/mismatched ratios were 0.325 for X bias (LER 0.00202 vs 0.00622, CI 0.257–0.403) and 0.239 for Z bias (0.00180 vs 0.00752, CI 0.188–0.298).

Together with ratio 1 (balanced) and ratio 10, the direction is consistent: there is no clear basis effect at ratio 1; alignment already reduces observed LER at ratio 2, with larger benefits at ratios 5 and 10. These four sampled ratios do not locate an exact crossover or justify interpolation, and the result assumes the bias profile is known and stationary. It informs a fixed configuration choice only. See `bias_crossover_results.json`.

## Empirical two-decoder selector ceiling

From the prior pilot's independently audited counts, uncorrelated and correlated modes disagree on 1,343/720,000 samples. Correlation-only errors are 580, and uncorrelated-only errors are 763. An oracle choosing the correct output on every discordant shot would reduce baseline errors from 3,532 to 2,769, a 21.6% relative reduction ceiling on this observed sample. The actual correlated mode improves by 183 errors, or 5.18% relative. Both modes are wrong on 2,769 same-prediction cases. A selector between these two outputs has no route to fix those cases. This is descriptive development evidence, not a generalization bound; a genuinely new decoder could add complementary corrections.

## Same-observable decoder selection

To separate decoder adaptation from changing which logical observable is scored, fixed the circuit to Z-memory and decoded its same detector/observable streams under three correlation-enabled PyMatching graphs: an X-profile DEM, a Z-profile DEM, and a static pooled graph built from elementwise-averaged channel probabilities. A frozen detector-only classifier selected between the two profile graphs from independent 500-shot calibration windows. All profile circuits matched the source builder and all decoders had 40 detector nodes and 142 graph edges.

The classifier chose the correct profile in all 2,000 calibration windows. On 100,000 logical shots per profile, selected-bank LER was .003875 versus .003895 for the pooled graph (775 vs 779 total failures); policy-minus-pooled 95% window-bootstrap interval [−.00009,+.00005] includes zero. The X-profile graph fixed across both profiles also had .003895 LER; the Z-profile graph fixed had .00403. The oracle profile graph produced the same .003875 as the selected bank. Thus profile identification was highly accurate, but it added no statistically resolved decoding gain over the static pooled graph in this fixed-observable screen.

This is a small d=3, ratio-10 development result with one pooled-model construction and a single logical observable. It does not rule out gains under other rates, distances, correlations, or stronger decoder families. It does show that the much larger basis-alignment reductions above cannot be interpreted as decoder-selection gains: those runs changed the logical observable/memory task being scored. For arbitrary logical-qubit memory, both conjugate logical error channels must be assessed.

The conjugate memory tests show the tradeoff directly: at 10:1 X bias, X-memory LER was .001275 and Z-memory LER .006575; at 10:1 Z bias, Z-memory was .000700 and X-memory .007800. Choosing the low-error observable does not remove errors in its conjugate channel. These marginal LERs are not a complete logical process characterization.

## Alternating-profile resource replay

To extend the calibration-cost analysis to direction changes without drawing another circuit stream, replayed the saved independent classifier confusion counts (25/100/500-shot prefixes) and basis-specific logical failure batches under deterministic equal-dwell X↔Z profile alternation. Across 144 combinations of bias ratio, calibration budget, update interval, and dwell, the controller could improve LER per logical attempt but generally lost throughput after charging calibration shots as unusable circuit resources.

For dwell periods up to 10,000 logical shots, none of the tested schedules exceeded the best fixed X/Z basis on correct outputs per total circuit shot. At 100,000-shot dwell, the best tested ratio-5 schedule (100 calibration shots per 100,000-shot update) had a projected 0.104% throughput gain; ratio 10 (25 calibration shots per update) had 0.205%; ratio 2 remained 0.014% below static. These are deterministic plug-in projections over one synthetic profile family. They omit uncertainty propagation, classifier retraining, within-window change detection, device drift, and any possibility that calibration shots produce useful logical output. The result suggests that adaptation can have operational value only when profile persistence is long relative to calibration cost; it is not a measured change-point result. Reproduce with `temporal_basis_replay.py`; full schedules are in `temporal_basis_replay_results.json`.

## Exact variable-elimination feasibility for categorical faults

Implemented log-domain dense factor variable elimination with one mutually exclusive categorical variable per location, exact detector-parity factors, and a prefix logical-parity chain. Weighted min-fill elimination matched exhaustive posterior masses, normalized logical posteriors, MAP decisions, and MAP risks on the single-location tree and both distance-1 repetition fixtures; maximum mass/posterior discrepancy was 2.8×10⁻¹⁶. Forced individual Pauli outcomes through Stim on both circuit-backed toys and reproduced their joint syndrome/logical masses independently.

To inspect topology-driven state growth, evaluated one consistent syndrome on synthetic square-grid incidence models. Exact elimination used width/intermediate table sizes of 3/16 at 2×2, 4/32 at 3×3, 6/128 at 5×5, 9/1,024 at 7×7, 15/65,536 at 9×9, and 18/524,288 at 11×11 (entries). The 2×2 mass also matched exhaustive enumeration to 3.5×10⁻¹⁸. Runtime for the largest tested single target was 0.38 s in this environment. This shows exact inference can remain practical on this sparse grid topology through 121 binary variables, but width and table size rise quickly.

The grid is not a mapped repeated-measurement Q-SHIFT circuit: it uses binary faults, simple pairwise edge checks, and only one target syndrome for sizes above 2×2. It therefore does not establish an exact-decoding result or cost bound for Phase 2B. The next gate is a noiseless semantic mapping of a bounded native-categorical circuit fragment to local factors and its induced-width estimate; do not scale this prototype to full circuits before that mapping and a circuit-fragment reference pass. Full toy/grid diagnostics are in `categorical_elimination_results.json`.

### Three-location native Phase 2B fragment

Mapped the first three target pairs of the final-round `PAULI_CHANNEL_2` instruction in the source d=3, five-round Z-memory / X-biased ratio-10 circuit. Each is a full 16-state categorical variable with source probabilities. A shared noiseless circuit reference and raw record-parity extraction produced exact fault effects on six touched detectors and the logical observable. Across 256 deterministic combined-fault cases, Stim's observed effects matched XOR composition. Exhaustive enumeration of all 4,096 assignments agreed with variable elimination on all 64 reachable syndromes and both logical classes to max joint-mass error 2.2×10⁻¹⁶. Induced width was 2; the largest intermediate table had 512 entries. No stochastic Q-SHIFT shots were generated.

This is a small final-layer slice with all other noise set to identity. The initial mapping attempt is invalid because Stim's detector sampler uses each deterministic circuit's own reference and hides injected fault deltas; it is preserved in `categorical_phase2b_fragment_first_layer_results.json`. The corrected raw-record method is in `categorical_phase2b_fragment.py`. This does not test interactions across rounds, the complete categorical channel set, or a decoder's LER/runtime. Next, run a separate width-only preflight before expanding to all six pair locations in this same layer.

Expanded to all six target pairs in that same final-round channel instruction only after a scope-only preflight predicted induced width 4 and 131,072 maximum table entries, below the one-million cap. The six 16-state variables touch 10 detectors. A sparse exact XOR-convolution over all 16^6 probability assignments produced 1,024 reachable syndromes; variable elimination matched every joint syndrome/logical mass with max error 1.1×10⁻¹⁶ and max posterior error 2.5×10⁻¹⁵. Another 512 forced combined faults matched local XOR composition. The isolated layer's exact MAP LER is 1.06×10⁻⁵, but this is not a full-circuit estimate: every other noise location was set to identity, and it cannot be compared to the Phase 2B baseline. Runtime was 95 s for the complete all-syndrome elimination in this implementation/environment. Artifacts: `categorical_phase2b_six_location_protocol.md`, `categorical_phase2b_six_location_preflight.json`, `categorical_phase2b_six_location.py`, and `categorical_phase2b_six_location_results.json`.

### Dense-elimination stop at two adjacent layers

A width-only preflight mapped the final two adjacent `PAULI_CHANNEL_2` layers in that same circuit (12 locations, each 16 states; all other faults identity). It touches 10 detectors. The fixed weighted-min-fill order predicts width9 and a 17,179,869,184-entry intermediate. Seven alternate scope-only orders (weighted min-product, unweighted min-fill, min-degree, natural, reverse, and two carry/location interleavings) were all worse or tied; the best remains 17.2 billion entries. No dense inference table was allocated. This stops the current dense variable-elimination approach at one layer under the one-million cap. It does not rule out specialized tensor contraction or methods that exploit further algebraic structure. Full ordering diagnostics are in `categorical_phase2b_two_layer_preflight.json`.

## Distance-3 syndrome-round resource frontier

Compared 3, 5, 7, and 9 extraction rounds at fixed d=3, gate/measurement p=.003, 10:1 bias, both X/Z profiles and memory bases. Each cell used 200,000 new circuit shots with correlation-enabled PyMatching built from its matching approximate DEM; all basis/profile resources matched within each round count. The source five-round builder and the scaled Stim builder were byte-identical for all four round-5 cells. Two-qubit channel-pair opportunities were 72/120/168/216 at 3/5/7/9 rounds (26 qubits throughout).

LER per attempt rose monotonically with rounds in all four profile/basis cells: X-memory under X bias .000915/.001415/.001785/.002050; Z-memory under X bias .004225/.007700/.010845/.015115; X-memory under Z bias .005060/.008300/.011480/.014375; Z-memory under Z bias .000775/.001505/.002100/.002865. Compared with the five-round standard, the 3-round rate ratios ranged 0.515–0.647, the 7-round ratios 1.26–1.41, and the 9-round ratios 1.45–1.96; the corresponding exact conditional intervals are in `round_count_frontier_results.json`.

This is a per-attempt comparison with different storage durations. Three rounds mean a shorter memory job, so the lower LER cannot be called an improvement at equal elapsed time. It also used 40% fewer two-qubit channel pairs than five rounds, while 7/9 rounds used 40%/80% more. The results show this simulator's finite-size resource/error tradeoff and do not establish an optimum for a fixed-duration workload, an asymptotic law, or a decoder gain.

## Checkerboard XZZX circuit co-design screen

Applied a fixed local-H transform to the checkerboard data qubits of the CSS rotated-memory circuit, converting resets/measurements and conjugating the CX schedule exactly. CNOT conjugates requiring H-CX-H received the same one-qubit Pauli noise after each added H. Qubit, detector, round, and two-qubit-pair counts matched; single-qubit H/noise targets increased from 40 to 100 at d=3 and from 216 to 576 at d=5 (150% and 167% overhead).

Under the source 10:1 profiles at p=.003 with correlation-enabled matching, the transformed XZZX implementation had higher LER in all four cells: d3 X bias .009594 vs CSS .007216 (ratio 1.33, 95% exact conditional CI [1.27,1.39]); d3 Z bias .006532 vs .000982 (6.65, [6.05,7.31]); d5 X bias .006752 vs .004534 (1.49, [1.41,1.57]); d5 Z bias .003332 vs .000168 (19.83, [15.92,24.66]). The screen therefore rejects this straightforward local-H transpilation under the declared noisy-H cost model. It does not reject XZZX generally: a hardware-native XZZX schedule could avoid much of the inserted H overhead and requires a separately specified resource/noise model.

## Bias-strength decoder robustness screen

At d=3 and five rounds, generated 12 independent circuit conditions (actual X/Z bias strengths 2/5/10 crossed with both profile directions and both memory bases). Each had 100,000 fresh samples, decoded by matching models built at each assumed strength 2/5/10 on the same detections. All circuits retained 40 detectors and one observable; resources matched within actual strength. A 100-shot/cell preflight passed, and the main run completed in 2.8 seconds.

Across the 12 equally weighted cells, macro LER was .005522, .005216, and .005022 for assumed strengths 2, 5, and 10. Paired Monte Carlo contrast for assumed-10 minus assumed-5 was -0.000194 (conditional 95% interval [-0.000242, -0.000146]); assumed-10 minus assumed-2 was -0.000500 ([-0.000567, -0.000433]). These intervals summarize sampling variation on these fixed conditions, not uncertainty across noise families. The correctly specified model's macro LER was .005294; fixed assumed-10 was lower by .000273 (paired conditional interval [-.000323, -.000222]). Thus correct specification was not uniformly best for this correlation-enabled matching implementation and approximate DEM construction.

This is a useful robustness signal, not evidence that ratio10 is universally optimal. Per-cell performance varied, the grid contains only three strengths and one circuit/noise family, and choosing the lowest macro decoder after viewing these data incurs selection optimism. It does not establish a calibrated ratio selector, adaptation gain, or hardware robustness. Full paired cell results and seeds are in `bias_strength_robustness_results.json`.

## Frozen ratio-10 versus ratio-5 validation

Following the predeclared independent check, evaluated only the ratio10 and ratio5 matching models on fresh samples at actual ratios 2, 3.5, 5, and 10, crossed with both profile directions and memory bases (16 cells, 100,000 samples/cell). The 100-shot/cell preflight passed and projected 11.8 seconds; the main screen took 2.5 seconds. All streams were decoded by both fixed models.

The equal-weight macro LERs were .0050025 (assumed10) and .0052244 (assumed5). The frozen paired contrast, ratio10 minus ratio5, was -0.0002219 (conditional Monte Carlo 95% interval [-0.0002626,-0.0001812]). The ratio10-minus-ratio5 equal-weight contrasts by actual strength were -.000180 at ratio2, -.000215 at ratio3.5, -.000260 at ratio5, and -.0002325 at ratio10; only two of four ratio2 profile/basis cells favored ratio10, while all four cells at ratios5 and10 did. These fixed-grid intervals reflect only sample variation.

This independent run confirms the earlier macro direction on fresh seeds and the new intermediate strength, reducing the same-screen selection concern. It remains a finite d3 simulator result over one bias family, with heterogeneous ratio2 outcomes. It does not establish universal robustness, true maximum-likelihood decoding, a noise-profile selector, or hardware value. The predeclared protocol and full per-cell data are in `bias_strength_frozen_validation_protocol.md` and `bias_strength_frozen_validation_results.json`.

## Distance-5 frozen bias-strength comparison

Extended the fixed assumed-ratio5/10 comparison to rotated-memory d=5 circuits with nine rounds. Actual ratios 2/3.5/5/10 were crossed with both bias directions and memory bases (16 cells; 100,000 fresh shots/cell). The custom ratio10 circuits were byte-identical to the existing scaled d5 builder; all actual circuits had 216 detectors/one observable. Preflight passed and projected 92 seconds; the main run completed in 23 seconds.

Equal-weight macro LER was .0019131 for assumed ratio5 and .0019331 for ratio10. The paired ratio10-minus-ratio5 contrast was +0.0000200 (conditional Monte Carlo 95% interval [-0.0000060,+0.0000460]), which includes zero. Across actual strengths 2, 3.5, and 5, macro contrasts were small positive values; at actual ratio10 the contrast was slightly negative. This does not reproduce the d3 ratio10 advantage and provides no evidence that either assumed ratio is better at d5.

The fixed ratio10-versus-ratio5 effect is therefore distance-dependent or unresolved at d5 under the available precision. Do not promote the d3 result to a size-independent robustness rule or threshold claim. Full paired results and the exact protocol are in `bias_strength_distance5_validation_results.json` and `bias_strength_distance5_validation_protocol.md`.

## Deterministic matching-graph audit

Compared correlation-enabled PyMatching graphs at assumed ratios5 and10 for each profile/basis at d3 and d5 (eight pairs, no stochastic shots). All eight pairs had identical graph topology and logical-fault edge labels: 142 edges at d3 and 950 at d5. Ratio changes only altered probabilities/weights on those same edges. Mean absolute common-edge weight change was .238 at d3 and .249 at d5; median changes were .131 and .128, respectively. About 74.6% of common d3 edge weights and 70.3% of d5 weights were higher under assumed ratio10. The median absolute edge error-probability change was nearly identical (.000353) at both distances.

This audit rules out an obvious explanation based on adding/removing matching edges when the assumed ratio changes. The scale-specific LER pattern is not explained by a gross difference in graph topology or overall weight perturbation. It does not establish a causal mechanism; syndrome distributions and decoder decisions differ with distance, and those require a separate analysis. Full graph summaries are in `bias_graph_mechanism_results.json`.

## Paired decoder-decision replay

Replayed the exact d3 and d5 validation seeds and first verified all 32 per-cell error counts against the archived result files. No new unique samples were generated. On d3, the two models changed their logical correction on 1,105/1.6M shots (.0691%); ratio10 fixed 730 ratio5 failures and broke 375 ratio5 successes. It was correct on 66.1% of disagreement cases (descriptive Wilson 95% interval 63.2%–68.8%). On d5, models disagreed on 452/1.6M shots (.0283%); ratio10 fixed 210 errors and introduced 242, for 46.5% conditional success (41.9%–51.1%).

This outcome decomposition explains the observed macro contrast descriptively: ratio10's changed decisions were usually helpful at d3 but approximately balanced/slightly harmful at d5. The d5 conditional interval includes chance-level 50%; these are not decoder-performance CIs across independent samples but binomial summaries of the archived disagreement subsets. The reason those syndromes are ranked differently is still unknown. Full per-cell and distance/actual-ratio aggregates are in `bias_strength_decision_replay_results.json`.

The predeclared coarse syndrome-weight bins show a suggestive pattern. At d3, 1,022 of the 1,105 disagreements fell in weight-3–8 syndromes, where ratio10 was correct in 678 cases (66.3%); in the 29 weight-9+ disagreements it was correct in only 11 (37.9%). At d5, 363 of 452 disagreements were weight-9+ and ratio10 was correct in 168 (46.3%); only six disagreements were weight-3–4. These weights count clicks over 40 d3 or 216 d5 detectors, so cross-distance bins are not normalized. The result suggests the changed-decision population differs, but cannot identify the fault geometry or establish causality.

The same replay gives a sample-specific output-selection ceiling. Even a perfect selector that knows which of the two decoded answers is correct on every disagreement would remain wrong on all both-wrong cases. Relative to the best fixed model observed on these streams, that oracle could reduce errors by at most 4.69% at d3 (ratio10 fixed) and 6.86% at d5 (ratio5 fixed). This is not a population bound, but it shows that selecting only between these two weight settings cannot approach a large relative LER reduction on the observed cases.

## Two-qubit fault composition in shared failures

Instrumented only the mutually exclusive `PAULI_CHANNEL_2` outcomes at actual ratio10, preserving one-qubit and measurement channels. Tested the high-LER mismatched-basis cells (X-bias/Z-memory and Z-bias/X-memory) at d3 and d5, with 100,000 main samples/cell. The 5,000-shot independent preflight compared original versus instrumented LER in all four cells; maximum absolute standardized difference was .85. The main run completed in 16.8 seconds.

Across the two conditions per distance, shared-both-wrong shots had a mean 1.94 two-qubit pair faults at d3 and 4.67 at d5, compared with .35 and 2.14 among both-correct shots. In each cell the Pauli pair matching the injected bias (XX under X bias, ZZ under Z bias) was enriched among shared failures: approximately 5.7–5.8× per shot at d3 and 2.28× at d5 relative to both-correct shots. The ratio10-fix/break groups were small (d3: 91 fixes/67 breaks; d5: 37 fixes/41 breaks), so their detailed Pauli composition is unstable.

This indicates shared errors tend to involve multiple pair-channel faults, including the dominant biased pair type. It does not establish that these faults are uncorrectable by a better decoder: one-qubit and measurement faults were not individually flagged, the observation is limited to two high-LER cells, and raw fault locations are not summarized into a new decoding method. Full group counts are in `shared_failure_fault_mechanism_results.json`.

## Sparse exact inference across two and three categorical layers

The dense two-layer VE preflight predicted a 17,179,869,184-entry intermediate for 12 native 16-state fault locations. A separate exact sparse XOR-state method aggregated probability by compact detector/logical signatures. For two layers it reached all 1,024 syndromes/2,048 joint logical states using 4.42M sparse transitions/join operations; direct sparse DP and independent six-plus-six half convolution agreed to 1.33e-15, and 512 forced combined-fault tests matched Stim. Runtime was 4.85s. The isolated-fragment MAP risk was 9.94e-5, not a full-circuit LER.

Extended to the final three layers (18 native categorical locations; 16^18 configurations). The preflight found 12 touched detectors, bounding the output space at 8,192 joint states. Exact sparse DP and an independent Walsh-Hadamard XOR convolution agreed over all 4,096 syndromes/8,192 logical states to 1.22e-15; all 512 forced combined-fault checks passed. The sparse DP used 1.22M transitions, the Walsh method about 2.02M operations, and the run took 4.63s. Isolated three-layer MAP risk was 2.23e-4; every other stochastic circuit location was identity.

This shows that dense VE's intermediate-width failure is representation-specific for this fragment, not a limit on all exact methods. Sparse signature methods instead scale with the touched detector/logical state space, which grows exponentially and will become prohibitive for a full circuit. The work does not provide a full-circuit posterior or decoder LER. Artifacts and protocols are `categorical_two_layer_sparse*` and `categorical_three_layer_*`.

The same sparse method passed on the final four layers (24 locations, 12 touched detectors): 8,192 joint states, DP/Walsh max difference 2.78e-15, normalization 0.9999999999999988, 512 forced-fault checks, and 3.55s runtime. The isolated-fragment MAP risk was 4.31e-4. Despite doubling categorical locations from the two-layer slice, the compact detector support remained 12 for this temporal region; this favorable locality should not be assumed farther into the circuit. No stochastic samples were generated.

The predeclared fifth-layer preflight mapped 30 categorical locations but expanded support to 18 detectors. Its full signature-state bound was 524,288 and conservative sparse-DP work bound 251,658,240 transitions, above the fixed 100M cap. The protocol therefore stopped before posterior mass expansion. This is the current sparse-DP budget boundary; the preflight does not prove the exact posterior is impossible under another representation, and no cap was raised post hoc.

A separate vectorized-signature protocol then applied each local XOR kernel as NumPy array permutations, with Walsh-Hadamard convolution as an independent exact reference. It passed at the same 524,288-state bound: DP/Walsh maximum mass difference 3.55e-15, 262,144 reachable syndromes, normalization passed, and 512 forced combined-fault checks matched Stim. It evaluated 251.7M vectorized state updates plus 308.8M Walsh operations, estimated peak working memory ~23 MiB, and completed in 5.92s. The five-layer isolated MAP risk was 6.06e-4, not a full-circuit result. Thus the earlier five-layer stop is specific to the fixed Python sparse-dictionary operation cap; vectorized signature convolution passed under its separate predeclared caps.

A sixth-layer run passed after exact per-location signature coalescing. The 36 categorical locations' 576 raw outcome labels collapsed to 296 distinct detector/logical signatures, a 48.6% reduction in vector updates. Vectorized DP and independent Walsh convolution agreed over all 524,288 states to 2.32e-16; 262,144 syndromes were reachable, normalization passed, and 512 forced combined-fault tests matched Stim. It used 155.2M state updates, 368.6M Walsh operations, estimated ~23MiB, and took 6.10s. Isolated six-layer MAP risk was 8.66e-4, not a full-circuit LER. Coalescing is exact because only outcomes with identical detector and logical signatures are merged; all original probabilities are summed.

The seventh-layer structural preflight found 42 categorical locations touching 20 detectors. The joint state bound is 2,097,152, above the unchanged 1,000,000-state cap; its raw transition estimate also exceeds the compute budget. The preflight stopped before mass expansion. This records a state-space boundary after the six-layer exact pass and is not a lower bound for tensor/MPS or other structured representations.


## Exact seven-layer syndrome/logical-parity inference

The separately predeclared parity-state method passed on the final seven PAULI_CHANNEL_2 layers of the d3 five-round Z-memory/X-biased-ratio10 circuit. It propagated 1,048,576 syndrome states, with 788,529,152 P/Z vector updates and 1,803,550,720 Walsh operations, in 14.51s. P and Z agreed with independent Walsh inference to 7.77e-16 and 3.33e-16; six-layer P/Z aggregation agreed with the prior full joint result to 5.55e-16. Mass normalization error was 1.55e-15; all 512 forced Stim combinations passed. The exact isolated-tail MAP risk was 0.00104093, not a full-circuit LER. No stochastic samples were generated. See `categorical_seven_layer_parity_results.json` and its protocol.


## Pair-cluster categorical importance sampling

The preregistered independent-product proposal over adjacent two-channel clusters completed the six-condition d3 development screen. The six circuits contain 120 two-qubit pair events grouped into 60 fixed two-location clusters. Synthetic instrumentation exercised all 256 joint categories with zero flag/Pauli mismatches; instrument size was 15,987 Stim instructions and the preflight projected 45.2 seconds, below the fixed 300-second gate. Main training/validation completed in 60.3 seconds. The advancement criterion passed in 0/6 conditions. Cluster relative SE was lower than global-tilt SE in two conditions but did not beat both direct and global tilt by the required 25% in any of the six. All six validation estimates were within three combined SE of both comparators, supporting estimator compatibility but not efficiency. Cluster validation maximum absolute log weights ranged 17.84–23.67 versus 11.44–16.27 under global tilt, and failure-weight ESS was often low (28–505); training failure ESS fell to 113–129 in two biased conditions. This rejects the tested cluster proposal/shrinkage at this budget, not all structured rare-event proposals. No confirmatory data were accessed. See `categorical_cluster_importance_protocol.md`, preflight, and results JSON.


## Native-XCX XZZX finite-distance screen

A predeclared alternative implemented the same checkerboard local-H code transform with native `XCX` for marked-control interactions and `CZ` for marked-target interactions. Stim tableau identities, noiseless detector/observable determinism, DEM construction, matching scalar/batch decoding, fixed resources, and unchanged two-qubit noise targets passed. The transform removed the prior extra H-gate/noise overhead: at d3, XZZX and CSS both had 40 H targets, 40 one-qubit noise targets, and 120 two-qubit interactions; at d5, both had 216 H targets, 216 one-qubit noise targets, and 720 interactions. Under the explicit assumption that native CX/XCX/CZ have equal duration and the same PAULI_CHANNEL_2 error, 500,000 shots/cell found XZZX/CSS LER ratios 0.662 (95% conditional exact interval 0.627–0.697) and 0.376 (0.347–0.407) for X-biased noise at d3/d5, but 3.86 (3.50–4.26) and 11.24 (8.50–14.80) for Z-biased noise. This is a strong orientation-by-bias interaction under one simulator model, not a universal XZZX gain. The main run used 4M shots in 11.8s. Results are finite-size, and hardware transfer requires measured native-gate error rates/durations. See `xzzx_native_xcx_protocol.md` and results/preflight JSON.


## Complementary native-XCX XZZX orientation

A single complementary checkerboard orientation `(x+y) mod 4 = 0` was tested on fresh Z-biased ratio-10 streams against CSS and the original `(x+y) mod 4 = 2` orientation, at d3/d5 (500,000 shots/variant/distance). Clifford, noiseless detector/observable, matched-resource, and unchanged two-qubit channel checks passed. The complementary orientation was better than the original by 13.7% at d3 (complement/original ratio 0.863, conditional exact 95% interval 0.806–0.922) and 21.5% at d5 (ratio 0.785, interval 0.701–0.876), but remained worse than CSS: complement/CSS ratio 3.04 (2.75–3.35) at d3 and 6.16 (4.91–7.68) at d5. Thus the tested complementary orientation partly reduced, but did not remove, the Z-bias penalty. Together with the X-bias benefit of the original orientation, these results show orientation dependence under the stipulated native-gate noise model, not a practical universal XZZX advantage. Stop this fixed checkerboard family here; no additional pattern search is justified by these results.


## Spatially heterogeneous two-qubit noise

The corrected preflight passed with 120 channel-pair locations split 60/60 and exact mean two-qubit probability .003 for both east-hot and west-hot maps. On 200,000 paired shots/profile, local-map and pooled matching were nearly tied. East-hot LER was .007565 local versus .007530 pooled (paired delta +.000035, normal 95% interval [-.000143,.000213], exact McNemar p=.742). West-hot LER was .007120 local versus .007290 pooled (delta -.000170, interval [-.000336,-.000004], p=.052). Equal-weight relative reduction was 0.93%, far below the predeclared 10% advancement gate, and east-hot did not improve. No detector-only selector study is warranted for this exact two-zone model. This is synthetic d3 robustness evidence, not a hardware model or an adaptive result. See the spatial protocol and JSON artifacts.


## Distance-9 known-profile basis alignment

The d9 preflight passed and projected under the 300s cap. At d=9, rounds=17, p=.003, X-biased ratio10, 500,000 independent shots per basis produced 1 aligned X-memory failure (LER 2e-6) and 408 mismatched Z-memory failures (LER 8.16e-4). The aligned/mismatched point ratio is .00245; its conditional exact 95% interval is [0.0000619, 0.01373], far too broad to resolve the 10,000-fold target. The d7 point ratio was 5/1009=.00496; the d9 point estimate is lower, but sparse aligned counts do not establish a distance-scaling law. No extra shots were added after seeing the outcome. See `basis_alignment_d9_results.json`; this is development-only finite-size evidence.


## Fixed-bond MPS under X-biased code-capacity noise

Using qecsim's `BiasedDepolarizingErrorModel(bias=5, axis='X')` (axis/off-axis probability ratio 10), p=.05, and 5,000 paired errors/distance, chi=16 MPS reduced failures versus bias-aware MWPM from 191 to 175 at d3 (8.4%; paired 95% interval for MPS-minus-MWPM LER [-.00629,-.00011]) and 118 to 76 at d5 (35.6%; interval [-.01177,-.00503]). MPS decode time was about 6x MWPM at d3 and 31x at d5. A fresh-seed replication again favored MPS at both distances: d3 182 vs 197, paired interval [-.00666,+.00066] crossing zero; d5 75 vs 101, interval [-.00843,-.00197]. This supports a directional code-capacity MPS signal, especially at d5, but d3 is uncertain, each root has only 5,000 shots, and this model has perfect syndrome/no repeated measurement faults. No Q-SHIFT circuit shots were generated. See primary and replication artifacts/protocols.


## MPS averaged-contraction mode ablation

On a fresh 5,000 paired biased-code-capacity sample per distance, qecsim `PlanarMPSDecoder(chi=16, mode='a')` produced exactly the same logical predictions as mode `c`: 0 discordant shots at d3 and d5, and identical failure counts (176 and 55 respectively). Thus the averaged contraction gave no observed LER change, while decode time was about 1.6x mode c at d3 and 2.0x at d5. It did not pass the predeclared advancement gate. Both modes remained below bias-aware MWPM on this sample, but this does not expand the circuit-level scope. See mode-ablation artifacts.


## Exact seven-layer tensor-train compressibility audit

The exact P(s) and Z(s) arrays were matricized at all 19 cuts in the frozen 20-detector order. Maximum rank was 91 for each array to relative Frobenius error 1e-10, and 30 at 1e-6. The predeclared exact-fidelity prototype gate (rank <=64 at 1e-10) failed; no tensor-train decoder was implemented and no stochastic samples were generated. This is an ordering-specific compressibility result for the seven-layer tail, not a lower bound for other detector orderings or a full-circuit network.


## d9 evidence budget calculation

Using the observed mismatched LER 0.000816 (408/500k), a 1e-4 relative-rate target is 8.16e-08. The exact baseline 95% lower endpoint (0.00073876) implies a conservative target 7.39e-08. Even in an optimistic IID single-condition design, about 36,712,404 zero-failure candidate shots are needed at the point baseline; a single candidate failure raises this to 58,135,593. This is a mathematical sample-size requirement, not a new experiment or proof of physical feasibility.


## All-location fault composition under ratio-sensitive decoding

The preflight passed synthetic flags for all 15 two-qubit Paulis, all three one-qubit Paulis, and explicit X/Z error events (zero data/flag mismatches). Both d3 conditions had 120 two-qubit pairs and 40 one-qubit locations; explicit measurement targets were 49 for Z-memory/X-biased and 49 total for X-memory/Z-biased. Source and instrumented samples had unchanged 40-detector/one-observable layout, and failure-rate differences were below 1.1 combined standard errors. The 200,000-shot main screen took 3.73 seconds.

At 100,000 shots/condition, ratio-5/ratio-10 models failed on 753/752 Z-memory X-biased shots (61 prediction disagreements) and 769/766 X-memory Z-biased shots (95 disagreements). The both-wrong groups contained 722 and 720 shots; ratio-10-fixes-ratio-5 groups contained 31 and 49, while ratio-10-breaks-ratio-5 contained 30 and 46. In both conditions, mean tracked two-qubit faults were about 0.349 per both-correct shot and 1.87 per both-wrong shot. In the biased Pauli outcome counts, XX was most frequent in the X-biased Z-memory both-wrong group (794 events), while ZZ was most frequent in the Z-biased X-memory both-wrong group (800). One-qubit and explicit measurement-fault counts also differed across outcome groups; see the JSON for full counts.

The decoder-disagreement groups are small, particularly the 30–49-shot fix/break groups. These are conditional fault associations from one fixed development stream, not causal attribution, evidence that one fault channel caused decoding errors, or a hardware noise claim. The new instrumentation extends the earlier two-qubit-only report; it does not change the prior conclusion that raw fault burden alone cannot explain decoder behavior. No sealed or confirmatory data were accessed.


## Secondary distance-trend synthesis for fixed basis alignment

Across saved d3/d5/d7/d9 X-bias ratio-10 screens, aligned/mismatched failure counts were 51/263, 6/217, 5/1,009, and 1/408. Point rate ratios fell from .194 to .0276, .00496, and .00245. A descriptive Poisson log-linear fit gives per-2-distance rate multipliers .095 aligned and .496 mismatched. Aligned counts are sparse (especially 1 at d9), distance and rounds co-vary, and this is not a threshold/scaling-law claim. At d9 the point ratio remains 24.5x above the 1e-4 aspirational relative target. No new samples were generated; see `basis_scaling_synthesis_results.json`.


## XZZX comparator audit against aligned CSS

The native-XCX XZZX screen compared Z-memory XZZX only with CSS Z-memory, a mismatched basis under X-biased noise. Against the previously measured X-aligned CSS stream at matched qubit, detector, two-qubit, one-qubit-noise, measurement-target, and tick resources, XZZX/CSS rate ratios were 3.57 (conditional 95% interval 2.70–4.80) at d3 and 13.48 (6.17–36.85) at d5. The original XZZX benefit over mismatched CSS Z remains valid, but does not survive the stronger aligned-CSS comparator. This is an independent-stream cross-screen comparison under the explicit native-gate equivalence assumption, not a paired run or general XZZX result. No new samples.


## d5 CSS/XZZX by memory-basis factorial screen

At X-bias ratio 10:1 and p=.003, four fresh 500k streams passed equal-resource preflight (qubits, detectors, observables, two-qubit interactions, one-qubit noise targets, ticks, and measurement targets). CSS-X had 79 failures; CSS-Z 1,848; XZZX-X 604; XZZX-Z 670. XZZX-X/CSS-X was 7.65 (conditional 95% interval 6.04–9.79), while XZZX-Z/CSS-Z was .363 (.331–.396). CSS basis alignment gave .0427 (.0337–.0536) X/Z; within XZZX, X/Z was .901 (.806–1.008). This fresh d5 stream replicates that XZZX improves over mismatched CSS Z-memory but loses to aligned CSS-X. Development-only code/configuration evidence; native-gate equivalence and logical-basis scope remain limitations. See the protocol and JSON.


A post-hoc equal-weight average over the two separate memory-basis tasks was .001274 for XZZX and .001927 for CSS, rate ratio .661 (conditional 95% interval .615–.710). This would favor XZZX by 33.9% for an explicitly equal X/Z memory-test mix, while CSS-X remains far better for a known X-memory task. The equal weighting was selected after inspection and is not an arbitrary-state channel metric or a predeclared primary endpoint.


## Independent replication of the d5 XZZX/CSS basis factorial

A fresh 500,000-shot-per-cell replication passed the 300s projection gate (18.54s projected; 18.19s measured) and equal-resource checks. CSS-X/Z had 93/1,866 failures; XZZX-X/Z had 575/721. The fixed equal-weight separate-memory endpoint again favored XZZX: rate ratio .662 (95% interval .616–.710). XZZX-X/CSS-X was 6.18 (4.96–7.78), and XZZX-Z/CSS-Z was .386 (.354–.421). The CSS X/Z ratio was .0498 (.0400–.0614). This reproduces a workload tradeoff in an independent development stream; it is neither confirmatory nor arbitrary-state evidence.


## d3/d7 distance extension of the CSS/XZZX basis tradeoff

Fresh 500k-per-cell 2x2 streams gave CSS-X/Z vs XZZX-X/Z failures of 656/3,729 vs 2,479/2,693 at d3, and 7/767 vs 88/128 at d7. The equal-weight separate-memory rate ratio XZZX/CSS was 1.18 (1.13–1.23) at d3, then .279 (.239–.325) at d7; the independent d5 discovery and replication each gave about .66. XZZX-Z/CSS-Z ratios were .722 (.687–.759) at d3 and .167 (.137–.201) at d7. XZZX-X/CSS-X was 3.78 (3.47–4.12) at d3 and 12.57 (5.85–32.18) at d7, with sparse CSS-X errors at d7. This supports a finite-size workload interaction, not an asymptotic scaling law. Equal resources passed within each distance. A preflight report bug on a zero-failure cell was fixed and documented before main sampling; no main data were generated by the failed attempt.


## d9 XZZX/CSS basis-workload challenge

At d9/17 rounds and 500k independent shots/cell, CSS-X/Z had 1/260 failures; XZZX-X/Z had 10/18. The primary equal-weight separate-memory XZZX/CSS rate ratio was .107 (95% conditional interval .070–.159), an 89% point reduction. XZZX-Z/CSS-Z was .0692 (.0404–.1116); XZZX-X/CSS-X was 10.0 (1.42–433.98), with only 11 combined failures. Resource counts matched across qubits, detectors, interactions, noise targets, ticks, and measurement targets. Preflight projected 155.6 seconds; main took 163.0 seconds with peak RSS 1.49 GiB. This extends the d3/d5/d7 finite-size workload trend, but remains a synthetic, one-distance development result and far from 10,000-fold reduction.


## d11 challenge of the balanced-memory XZZX/CSS result

At d11/21 rounds and 500k shots/cell, CSS-X and XZZX-X each had zero failures; CSS-Z had 67 and XZZX-Z had 3. The equal-weight separate-memory XZZX/CSS rate ratio was .0448 (95% conditional interval .0090–.1366), based on 70 combined failures. The XZZX-Z/CSS-Z ratio was also .0448; X-vs-X has no informative rate ratio because both cells had zero failures. Per-cell Wilson one-sided upper for zero counts is about 7.68e-6. This continues the balanced-workload trend but remains 448x above the 1e-4 target at the point estimate. Preflight projected 217.6s; main completed in 281.9s (<300s) and used 2.69 GiB peak RSS. Do not infer arbitrary-state or asymptotic performance.


## d11 relative-target evidence budget

The observed equal-weight CSS point LER was 6.7e-5, so a 1e-4 relative target would require candidate LER 6.7e-9. The d11 XZZX point was 3e-6 (ratio .0448), about 448 times above that target. Even assuming the baseline is known and IID sampling, a one-sided 95% upper bound at the target needs about 447M zero-failure candidate shots; allowing one observed failure needs about 708M shots. These are optimistic Poisson rare-event budgets and ignore baseline uncertainty, multiple conditions, roots, and model selection. More samples at the observed XZZX rate would not establish the target.


## d13 scaling feasibility stop

The corrected 10k/cell preflight passed resource equality and decoder checks but projected 454.7 seconds for the fixed 500k/cell main screen, exceeding the 300-second cap. No performance results are available at d13. The first attempt's output typo is preserved; identical seeds were replayed and unique preflight samples counted once. This marks the runtime boundary for the current four-cell PyMatching screen.


## d7 XZZX/CSS bias-strength robustness

At 2:1 X bias, 500k shots/cell gave CSS-X/Z 120/281 failures and XZZX-X/Z 173/169. The equal-weight separate-memory XZZX/CSS ratio was .853 (95% interval .736–.988); XZZX-X/CSS-X=1.44 (1.14–1.84), XZZX-Z/CSS-Z=.601 (.494–.730). At the same d7/p/round design, the 5:1 screen gave .608 (.529–.697), and the 10:1 screen gave .279 (.239–.325). Thus the balanced-task XZZX advantage strengthens with bias in these three finite points, but basis-specific direction remains mixed. These are development simulations under unverified native gate equivalence.


## d7 XZZX/CSS robustness at 5:1 bias

At ratio5:1, 500k shots/cell gave CSS-X/Z 27/526 failures and XZZX-X/Z 158/178. The equal-weight separate-memory XZZX/CSS ratio was .608 (95% interval .529–.697); XZZX-X/CSS-X=5.85 (3.87–9.16), XZZX-Z/CSS-Z=.338 (.284–.402). Preflight projected 53.82s and the main took 66.76s. Together with 2:1 (.853) and 10:1 (.279) at d7, the advantage is bias-strength dependent.

## d13 bit-packed sampling and decoding throughput

A fresh 50,000-shot-per-cell preflight (200,000 total) matched Stim detector/observable samples exactly after packing and matched PyMatching predictions exactly in all four d13 conditions. One hundred scalar-versus-batch checks per cell also agreed. Packed main-screen projection was 358.13s, above the 300s limit, so no main samples were run. Packed decoder speed ratios varied from 0.75x to 1.39x; the exact output artifact is `xzzx_d13_bitpacked_preflight.json`.

## Fusion Blossom custom-graph feasibility

On 1,000 fresh d3 samples, a custom graph exported from PyMatching and quantized to even integer weights gave zero prediction mismatches against ordinary PyMatching MWPM. Fusion Blossom serial Python decoding throughput was 6.5%–15.3% of PyMatching over the four cells. This validates graph/API wiring but rejects the serial path as a throughput solution on the measured workload. See `fusion_blossom_d3_screen_results.json`.

## Min-fill ordering of the exact seven-layer posterior

A deterministic min-fill ordering derived from the detector event primal graph produced maximum ranks 151 for P and 150 for Z at 1e-10 relative Frobenius tolerance, compared with 91 for both in natural order. The predeclared rank-64 gate fails; no alternate order was tried. This rejects the selected min-fill heuristic for this exact tail without establishing a general lower bound. See `categorical_seven_layer_minfill_results.json`.

## Sequential detector-only profile calibration

A frozen Gaussian SPRT over the existing four detector-rate LDA score features used a Wald threshold log(19) and a 500-shot cap. In the independent 2,500-window/profile validation, errors were 102/2,500 for X-biased (4.08%, exact 95% interval upper 4.93%) and 96/2,500 for Z-biased (3.84%, upper 4.67%). Mean cost was 24.83 calibration shots across profiles. The fixed 25-shot LDA baseline erred on 10.12%/10.84%; the retrospective matched fixed Gaussian-LLR baseline erred on 12.20%/10.92%. At 100 shots both fixed approaches were more accurate, but cost four times as many shots. The score model and decision threshold were frozen in the replication.

The direct development LER screen paired 2,500 calibration decisions/profile with 100 logical attempts/decision and fresh X/Z memory streams (one million logical samples). Equal-profile SPRT LER was .001386 (exact 95% interval .001285–.001493), versus .004198 (.004021–.004381) for static Z, a 67.0% point reduction; paired block-bootstrap LER delta was [-.002996,-.002628]. Fixed 25-shot LDA gave .001800; fixed 100-shot LDA .001138; 500-shot LDA/oracle .001090. At one calibration per 100 logical attempts, calibration overhead drove correct-output yield to .8000 vs .9958 for static Z.

A deterministic stable-profile utility projection, bootstrapping the same independent calibration and logical streams, estimated at a 100,000-attempt dwell: SPRT LER .001349, about 49.7 calibration shots per two-profile cycle, and correct-output yield .998403 vs .995802 for static Z. The bootstrap yield difference was [.002425,.002781]. This is an expected-value projection under profile stability. The direct grouped 10,000-attempt replay has an interval crossing zero; no drift or hardware evaluation was run. X/Z share the main counted circuit resources but differ in terminal readout and one-qubit fault composition. Full records: `adaptive_basis_sprt_*_results.json`.

## Sequential profile calibration under measurement-noise composition shift

Keeping gate p=.003 and X/Z bias ratio10 while increasing measurement p from .003 to .006 shifted score distributions: X-biased mean/variance changed from nominal -0.110/0.207 to -0.131/0.274; Z-biased changed from +0.109/0.183 to +0.085/0.250. The frozen class-specific Gaussian SPRT then made 36/1,000 X-profile errors (3.6%, exact 95% CI 2.5%–4.9%) and 176/1,000 Z-profile errors (17.6%, 15.3%–20.1%), at mean costs 18.7/28.6 shots. Fixed 100-shot LDA had 4 and 51 errors, respectively, but this is a single stress stream.

A predeclared common-variance SPRT was tested on fresh nominal and shifted streams. It retained <=5% upper error bounds for both nominal profiles and shifted X-biased profile, but shifted Z-biased error was 120/1,000 (12.0%, exact CI 10.1%–14.2%). The common-variance variant therefore fails its robustness gate. No logical LER test followed. This is one controlled composition shift, not general robustness evidence; see `adaptive_basis_sprt_measurement_shift_results.json` and `adaptive_basis_sprt_common_variance_results.json`.

## Detector-only change detection and false switching

Both Gaussian LLR CUSUM variants detected all 100 profile transitions in each alternating sequence, with median delays of 27–33 shots and p90 65–74 shots; periodic 100-shot LDA updated at 100-shot cadence. But stable controls produced 25–50 false switches per 100k nominal calibration shots for CUSUM, and 147–271/100k in shifted Z-biased controls. Periodic LDA had fewer nominal false switches (about 4.6–7.8/100k) but more in shifted controls. The CUSUM's ideal likelihood-ratio threshold did not transfer to the non-Gaussian simulator score distribution. It is rejected as an adaptive controller. No logical outcomes were generated. See `adaptive_basis_change_detection_results.json`.

## Single-pattern circuit-level logical lower bound

For d3/five-round ratio10 X-biased aligned memory, Stim's shortest graphlike paths used three physical two-qubit Pauli outcomes in both CSS-X and native-XCX XZZX-X. The selected undetectable pattern plus the all-identity pattern establish exact decoder-independent LER lower bounds 3.07e-15 and 3.07e-13, respectively. Observed development LERs were .001312 and .004958, so the bounds are only 2.3e-12 and 6.2e-11 of those rates. This single-pattern bound is valid but too weak to constrain decoder headroom or the aspirational relative target. No stochastic samples were generated. Artifact: `graphlike_fault_floor_results.json`.


## Round-wise gate-rate heterogeneity

For two reverse five-round profiles with factors [0.25, 1.75, 1, 0.25, 1.75] and [1.75, 0.25, 1, 1.75, 0.25], the exact-map decoder reduced failures from 1,709 to 1,655 and 1,512 to 1,474 on paired 200k streams. Paired deltas were -0.000270 (95% CI [-0.000450, -0.000090], McNemar p=.0039) and -0.000190 ([-0.000349, -0.000031], p=.0226). Equal-weight macro relative reduction was 2.84%, below the preregistered 10% gate; decode time was 1.02–1.04x pooled. This is an oracle-known synthetic d3 rate-map result, not online adaptation. Full details: `../independent_research_v2/temporal_rate_hotspot_report.md`.


## Equal-duration three-round plus idle versus five active rounds

At equal five-cycle storage duration, three active d3 syndrome rounds followed by two biased data-idle cycles reduced LER versus five active rounds on the two aligned workloads. X alignment: 557/500k (.001114) vs 657/500k (.001314), RR .848 (95% .757–.949). Z alignment: 469/500k (.000938) vs 694/500k (.001388), RR .676 (.601–.760). The equal-weight mean cell RR=.762 passes the fixed .90 gate. The three-plus-idle arm uses 72 rather than 120 two-qubit pairs, but 42 rather than 40 one-qubit Pauli targets after adding 18 data-idle targets. This is an unpaired finite-sample simulator result under a fixed p=.003 biased idle assumption; fresh-seed replication is required. Details: `../independent_research_v2/equal_duration_rounds_report.md`.


### Independent-seed replication of equal-duration schedule

A separate 500k/arm/cell stream again favored three active rounds plus two p=.003 biased data-idle cycles over five active rounds. X alignment: 575 vs 635 errors, RR=.906 (95% .809–1.014); Z alignment: 456 vs 711, RR=.641 (.570–.721). Equal-weight mean cell RR=.773. Both cells favored the candidate by point estimate; the X interval includes 1. This independently reproduces direction and the aggregate advancement gate under the same assumed idle model, not hardware validity. See `../independent_research_v2/equal_duration_rounds_replication_report.md`.


### Twofold idle-rate robustness challenge

With only the idle arm's data Pauli p increased to .006, X-aligned three-plus-idle had 694/500k errors versus 683 for five active rounds (RR 1.016, 95% .914–1.129); Z-aligned had 580 vs 770 (RR .753, .676–.839). Mean cell RR=.885, but the preregistered robustness rule required both cells' point ratios below 1; it therefore fails on X alignment. This is a one-point synthetic stress. The Z result remains positive; the X result is near-neutral and uncertain. See `../independent_research_v2/equal_duration_rounds_idle_2x_report.md`.


## Distance-5 equal-duration schedule extension

For Z memory/Z bias at d5, five active rounds plus four p=.003 biased data-idle cycles had 146/1,000,000 failures (.000146; Wilson 95% .000124–.000172), versus 139 (.000139; .000118–.000164) for nine active rounds. RR=1.050 (95% .833–1.325); no benefit was observed, and the interval excludes a 20% or larger reduction under the log-normal approximation. Resources: same 64 qubits/readout targets; 400 two-qubit pair sites and 220 one-qubit targets with five+idle versus 720 and 216 with nine active. This does not reproduce the d3 Z-aligned benefit; see `../independent_research_v2/equal_duration_d5_report.md`.


## Distance-5 intermediate schedule challenge

At d5 Z alignment, seven active rounds plus two p=.003 biased data-idle cycles yielded 140/1M errors vs 166/1M for nine active rounds, RR=.843 (95% .674–1.056). The point estimate favored seven-plus-idle, but the frozen advancement gate required upper CI <1 and failed. No sample expansion or additional round count followed. See `../independent_research_v2/equal_duration_d5_intermediate_report.md`.


## Selective BP+LSD escalation on matching disagreement syndromes

On six fresh d3 conditions (100k each), a fixed policy flagged only syndromes where correlation-enabled and ordinary PyMatching differed, then used `LSD_CS` on flagged cases and correlated matching otherwise. It flagged 1,567/600,000 samples (0.261%); all flagged BP+LSD fault estimates reproduced the syndrome. Equal-weight macro LER fell from .005253 to .004503 (14.28% reduction); all six point estimates improved, with per-cell reductions 4.1%–39.5%. However, corrected end-to-end decode time includes correlated matching, the ordinary-matching flag pass, and BP+LSD on flags: mean 8.44x correlated matching, above the 2x gate. Thus it fails practical advancement despite an accuracy signal. See `../independent_research_v2/selective_bplsd_escalation_report.md`.


### Independent replication of selective BP+LSD escalation

A fresh 600k-shot stream reproduced the accuracy result: macro LER .005213→.004533, a 13.0% reduction. The disagreement rule flagged 1,530 cases (0.255%); all escalated syndromes were valid and no condition was harmed by >5% (X-memory/X-bias was 131 vs 132 errors). Full runtime remained 8.24x baseline, so the practical gate fails independently as well. This verifies the syndrome ambiguity signal but rejects the current escalator. Details: `../independent_research_v2/selective_bplsd_escalation_replication_report.md`.


## Fast supervised selector on matching-disagreement syndromes

A per-condition L2 logistic classifier trained only on detector bits plus the outputs of correlation-enabled and ordinary matching for flagged syndromes passed held-out validation. Across six d3 conditions, macro LER fell .005156→.004271 (17.2%); paired macro delta 95% interval [-.000917,-.000853]. Per-cell reductions ranged 4.2%–35.7%; total inference cost (both matching passes plus classifier) was 1.35x correlated matching. Fresh independent training and validation seeds reproduced the effect: .005155→.004321 (16.18%; macro delta 95% [-.000866,-.000802]), with per-cell reductions 3.9%–34.2% and cost 1.36x. On that replication validation stream, flagged BP+LSD gave .004468 (13.34% reduction) at 8.28x cost; the logistic selector had fewer errors in five of six conditions. The learned selector passes the development gate, but remains synthetic, per-condition supervised, and untested under model shift. See `../independent_research_v2/fast_flagged_logistic_report.md` and its replication report.


## Frozen logistic selector under doubled measurement noise

With model coefficients frozen from nominal p_measure=.003 training, the six-condition d3 selector retained a 13.03% macro LER reduction when measurement p increased to .006 (gate noise remained .003), at 1.351x total inference cost. On a fresh independent seed stream the reduction was 13.11% at 1.349x. Paired macro difference 95% intervals were [-.000915,-.000820] and [-.000919,-.000824], respectively; each of the six per-condition intervals favored the selector on both streams. No shift samples entered training or calibration. An actual-profile matcher was included as a profile-matched diagnostic, not an optimality bound. This is evidence for this specific twofold measurement-flip shift across the six fixed d3 simulator conditions only. Full counts, per-cell results, and reproduction: `../independent_research_v2/fast_flagged_logistic_measurement_shift_report.md`.


## Distance-5 transfer of flagged logistic selector failed

The d5-specific, 218-feature logistic policy was fit on independent six-condition training streams and evaluated on separate 1M-shot/cell validation streams. Macro LER rose from .001959 to .0019855 (+1.35% relative); only two of six cells improved. Paired macro difference was +.0000265 (approximate 95% CI [.0000133,.0000397]). Runtime was 1.379x and passed, but the frozen >=10% accuracy gate failed; no replication or tuning was performed. Thus the d3 method's benefit did not transfer to this d5 setup. Details: `../independent_research_v2/fast_flagged_logistic_d5_transfer_report.md`.


## Frozen logistic selector under reduced bias ratio

At gate/measurement p=.003, the ratio-10 selector and matchers were frozen while biased physical channels changed to ratio 5. Two independent d3 streams gave macro LER .005377→.004412 (17.95%) and .005291→.004349 (17.81%), at 1.347x/1.364x total inference cost. Paired macro difference 95% intervals were [-.001015,-.000916] and [-.000992,-.000893]; all six per-cell intervals favored the selector on both streams. Balanced cells were unchanged-profile controls. This supports only the tested single-axis shift at d3; see `../independent_research_v2/fast_flagged_logistic_bias_shift_report.md`.
