# Failure and blocker analysis

## Exact DEM conversion gate

The proposed mechanism follow-up in the existing Q-SHIFT research-direction materials assumes an alternate non-approximated DEM family. Direct testing on all six Phase 2B circuit conditions shows Stim refuses to analyze the `PAULI_CHANNEL_2` operations unless `approximate_disjoint_errors=True`. The failure happens at circuit conversion, before any sampling. Repeating the call or increasing resources cannot resolve this semantic/API constraint.

A DEM represents independent mechanisms. Mutually exclusive categorical Pauli-pair outcomes are not equivalent to independent fault mechanisms in general. Enabling the approximation changes that representation. Reusing the same approximate DEM with correlation on/off validly isolates the decoder option conditional on that DEM, as the existing pilot did, but cannot attribute any observed interaction to information loss in the conversion.

The existing exact categorical decoder study provides an exhaustive toy reference, but its scalability report estimates 2^609 full-circuit assignments. It has no exact structured inference cost result for the d=3 circuit. Therefore neither unrestricted enumeration nor a direct exact-DEM substitute is presently justified for the full circuit.

## Prior correlation pilot

The prior development pilot showed a favorable aggregate point estimate but failed its prespecified practical gate and contained adverse strata. Selecting a post-hoc same-name regime rule or training a per-syndrome selector on its sparse disagreements would reuse outcomes already inspected. That would be hypothesis generation, not an independent validation. The raw bundles are not present in this worktree, so no secondary reanalysis was attempted.

## External-source access

An attempt to query the arXiv API returned an egress tunnel `403 Forbidden`. The official Stim source documentation on `raw.githubusercontent.com` was reachable. DOI resolution through `doi.org` also returned `403`. The repository contains a prior focused literature comparison with detailed citations, but this expedition has not independently fetched every primary paper or revalidated each 2024–2026 source. Literature claims that depend on unavailable sources remain provisional.

## Categorical sum-product prototype

The first implementation estimated logical parity from the product of individual location beliefs. It achieved LER 0.084708 on the one-qubit exact toy. That calculation incorrectly treated beliefs conditioned on shared detector checks as independent for logical parity. The revised prototype added a global logical-parity factor and compared two Bethe partition estimates. It reduced toy risk to 0.057354 but remained far above exact MAP risk 0.002646, agreeing on only two of four syndromes. On the two-qubit fixture it matched exact MAP, which shows that a single positive toy is not a validation of this method.

Likely issue: the global logical parity factor creates loops in the factor graph, and the Bethe approximation is not accurate enough for the one-qubit fixture. A later nontrivial tree control matched exact posteriors to 2.22e-16, supporting correct message/partition calculations on that acyclic topology. The one-qubit loopy failure remains severe, while the two-qubit loopy toy has matching MAP decisions but 0.26 maximum posterior error. This narrows the likely cause to loopy approximation/topology; it does not prove correctness on all trees or identify a loop correction. Keep the candidate stopped before circuit evaluation until a new method passes multiple exact cyclic fixtures under a predeclared risk/calibration gate.

## Exact categorical variable-elimination feasibility

A new exact log-domain elimination implementation passed exhaustive posterior and independent forced-Stim mapping checks on the existing distance-1 categorical repetition fixtures. During development, a strict MAP comparison disagreed on a two-qubit syndrome because floating-point roundoff broke a posterior tie; matching the reference's 1e-15 tie policy fixed it. A later 2x2 grid reference exposed a factor-axis bug from a noncanonical (unsorted) prefix-parity scope; factor scopes are now sorted and table axes mapped by variable ID. The final results reproduce exact toy joint masses and risks to floating-point precision. These were code/algorithm defects caught by exact controls, not circuit-sample evidence.

The corrected ordering kept intermediate tables small on synthetic sparse grids through 7x7, but grew to 65,536 entries at 9x9 and 524,288 at 11x11. This topology stress test stops before the 1,000,000-entry cap and does not represent Phase 2B's high-domain categorical gates or temporal detector graph. A bounded three-location fragment has since been mapped from the actual Phase 2B circuit, but it is too small to establish meaningful circuit-level scalability.

The first attempt to extract detector effects from a bounded Phase 2B layer used Stim's `compile_detector_sampler` separately on each deterministically forced circuit. That API reports events relative to the circuit's own deterministic reference, so it erased the forced-fault difference and produced a false zero-support result. The artifact is marked invalid and preserved. The corrected mapper instead reads raw measurement records, evaluates detector/observable record parities explicitly, and differences them against one shared noiseless source-circuit reference. The final-round three-location fragment then passed 256 combined-fault XOR checks and exhaustive 16^3 model-vs-elimination joint-mass comparison (max discrepancy 2.2e-16); its width was 2 with at most 512 intermediate entries. Expanding to all six pairs in this one layer passed an independent sparse XOR-convolution reference on all 1,024 reachable syndromes (max joint error 1.1e-16) and 512 combined-fault checks; width4/max factor131,072. It took 95 s for the isolated layer, with every other circuit fault suppressed. This is not a full decoder.

The next two adjacent final-round channel layers were checked without inference-table allocation. Weighted min-fill predicted a 17.2-billion-entry factor. Seven alternative orderings were no better (the best was tied; natural/reverse/interleaved orders were larger). This exceeds the fixed 1,000,000-entry cap by over four orders of magnitude, so dense exact elimination stopped before inference. The one-layer result should not be extrapolated to temporal scaling. This is a limitation of the tested dense factorization/orderings, not a lower bound against tensor networks, custom finite-state contraction, or approximate inference.

## Round-count screen builder repair

The first round-count preflight called the source `noise_model.build_circuit` at rounds=3; that helper has an assertion for the standard five-round detector count and stopped before sampling. The preflight then used the existing scaled Stim builder from `code_distance_scaling.py`, which replaces Stim's depolarizing instructions with the source X/Z Pauli-channel probabilities and was byte-identical to the source builder at rounds=5 for all four profile/basis cells. No data from the failed call were generated. The resulting comparison remains per-attempt with different physical memory durations; it cannot be interpreted as a fixed-time optimum.

## Thresholded DEM sensitivity route

The official Stim CLI permits a maximum probability threshold for approximating disjoint errors. A fixed threshold of 0.001 cannot convert any of the biased conditions because one two-qubit Pauli-pair event has probability 0.00178571. Thresholds 0.0018, 0.003, and 1.0 all convert, but produce identical DEM and matching graph hashes within every condition. This threshold family therefore provides no alternate matching model at the tested probabilities. Changing the gate probabilities or threshold after observing decoder outcomes would be a different study and is not supported by this static check.

## BP+LSD fixed-configuration screen

LDPC 2.4.1 BP+LSD was applied to a binary fault-variable matrix formed from each flattened approximate DEM. This is a representable model for the chosen DEM, and every returned estimate matched its input detector syndrome. However, the three tested LSD method labels all yielded 321 logical failures on 30,000 original-circuit samples, versus 138 for correlation-enabled PyMatching; each lost in all six conditions.

The negative result could reflect low-order BP on loopy checks, a poor binary posterior under the DEM approximation, the chosen min-sum/iteration settings, or differences in how the library's LSD fallback selects among valid fault explanations. The data do not distinguish these causes. Because the output syndromes were valid and the baseline was built from the same approximate model, the comparison is useful as a method feasibility result. It does not test other LSD configurations, larger distances, or a native categorical decoder. No post-hoc tuning was done.

## Importance-sampling scope and efficiency

The first likelihood-ratio estimator is exact for the independent Bernoulli mechanisms represented in a flattened approximate DEM, but it estimates risk under that surrogate. It does not remove the approximation to the source's categorical two-qubit channels.

A follow-up directly instrumented the source `PAULI_CHANNEL_2` channels as mutually exclusive `E`/`ELSE_CORRELATED_ERROR` branches and recorded each outcome. Synthetic channel checks, all 15 argument-order tests, multi-pair independence checks, and a raw Stim circuit LER crosscheck passed. This supplies a valid exact categorical likelihood ratio for the fixed decoder. However, the global fivefold tilt was not a reliable variance reduction: across 16 replicates its macro between-replicate SD was 12% higher than direct sampling, with condition-specific SD ratios 0.52–1.64. In particular, z-memory/z-biased variance increased. Therefore the method is a valid weighting framework, but this proposal does not justify an efficiency or rare-event precision claim across all conditions.

A cross-entropy product proposal then used separate fivefold-tilted training trajectories to estimate each fault location's failure-conditioned categorical marginal, with 50 baseline pseudocounts. It failed the predeclared SE gate in all six validation conditions. The validation estimates remained within three combined SE of direct/global estimates, but the product proposal sometimes had fewer than 10 effective weighted failures and reached max weight 77.3. This suggests that matching one-location conditional marginals did not capture enough joint failure structure; this is a plausible explanation, not a proven one. Do not continue by tuning the shrinkage mass on the inspected validation results.
# Fixed-bond MPS limitations

The χ=16 MPS result is positive only in qecsim's ideal-syndrome code-capacity depolarizing model at p=0.05. It does not address repeated syndrome extraction, measurement faults, the categorical two-qubit circuit channels used by Q-SHIFT, noise mismatch, or a distance sequence beyond d=3,5. The comparator is qecsim's Python MWPM path because its optional `libpypm.so` extension was absent, so measured absolute latency is implementation-dependent. MPS decoding cost rose from 0.988 ms/sample at d=3 to 13.74 ms/sample at d=5, about 27x the corresponding MWPM time at d=5. The paired advantage is clear in this sample, but one noise rate and 5,000 shots per distance do not support an asymptotic claim. No tuning of χ or p was performed after seeing the result.

# Bias-profile inference limitations and implementation correction

The high accuracy of the frozen two-class X-vs-Z classifier is conditional on a specific synthetic noise family: the same gate/measurement error rates, categorical channel construction, Z-memory calibration circuit, and stable profile during calibration and use. Its training used extreme 10:1 profiles; tests at ratios 2–5 show that direction remains identifiable with 500 shots in this model. It does not establish calibration transfer to hardware, changing bias within a memory job, changes in total error rate or correlation structure, or net operational benefit after calibration cost. A separate balanced-vs-biased three-class model often classified moderate ratios as balanced and had low basis-action accuracy there. This is a classifier-design/identifiability limitation, and demonstrates that “which direction?” and “is there enough bias to reconfigure?” require separate validation.

The first end-to-end policy script used the correct trained coefficient vector but reversed its sign-to-basis mapping. Its output is preserved as an invalid first pass and excluded from all findings. Before rerun, the selector was corrected and an assertion now checks that the training-class means land on the declared X/Z sides of the decision boundary. The corrected result uses the predeclared same seeds. This was a software polarity error, not evidence against the estimator.

The doubled-total-rate robustness screen initially attempted to reuse the .0018 approximate-DEM threshold, which failed because a p=.006 categorical fault probability exceeded it. No logical samples were generated under that failed setup. A deterministic probability calculation established a maximum event probability of .003571; the prospectively updated screen used .004 for all arms. This changes the approximation threshold from the nominal-rate tests, so the rate-shift comparison is internally matched but not a direct absolute comparison against the p=.003 sample.

# Same-observable decoder selection result

Although the detector-only classifier identified the X/Z profile in all 2,000 calibration windows, a same-circuit, same-Z-observable comparison of profile-specific matching graphs against a static pooled graph found only four fewer failures in 200,000 test shots (775 vs 779); its paired window-bootstrap interval includes zero. This is a negative development result for the claim that accurate profile labels alone yield a meaningful decoder improvement. For this circuit/noise pair the pooled graph was already close to the profile-conditioned graphs. The result is limited to one distance, one bias ratio, and one pooled-model construction.

The larger basis-alignment LER reductions score different logical observables: X-memory reports an X observable and Z-memory reports a Z observable. Those comparisons are valid for known-basis memory tasks but do not show that a general logical-qubit channel or a fixed-observable decoder improves. Any arbitrary-state memory claim needs both conjugate logical error channels and a task-matched objective.

# Local-H XZZX transpilation screen

The fixed checkerboard local-H transform produced deterministic detectors and matched qubits, rounds, detectors, and two-qubit pairs, but its exact CNOT conjugation required H-CX-H in many locations. Modeling the extra H gates with the same one-qubit Pauli noise raised H/noise targets by 150% at d3 and 167% at d5. The XZZX-transformed circuit then had higher LER than CSS in all four d3/d5 × X/Z-bias cells, by 1.33× to 19.8×. The negative result applies to this explicit gate-level transpilation and noise model. It should not be generalized to an XZZX schedule compiled to native two-qubit gates or a device where single-qubit frame changes are effectively noiseless.

## Bias-strength misspecification

On 12 paired d3 conditions, the correlation-enabled matching model built at assumed bias ratio10 had lower equal-weight macro LER than models built at ratios5 and2, including on actual ratio2 and5 samples. This challenges the expectation that a decoder trained at the true channel ratio necessarily wins under this approximate DEM plus matching decoder. The ratio10 decoder was chosen from a three-model grid evaluated on the same development streams, so its apparent macro advantage is exploratory and selection-biased. The screen cannot support ratio10 as a deployable default without independent fresh validation and additional actual ratios.

A fresh-seed ratio10-vs-ratio5 run retained the macro ratio10 advantage and added an actual ratio3.5 condition, so the original ranking was not solely a same-sample fluctuation. Still, the actual-ratio2 conditions had mixed cell-level results, and only one distance, channel family, DEM conversion, and decoder were studied. The strongest defensible reading is a reproducible finite-grid sensitivity of matching weights to bias assumptions; causal mechanism and broader robustness remain unisolated.

At d5, the same frozen ratio10-vs-ratio5 contrast was near zero (+.000020, conditional MC 95% interval [-.000006,+.000046]) and did not reproduce the d3 ranking. Thus the earlier effect is not shown to scale with distance. The d5 aligned-rate cells are sparse, so this does not establish equivalence; it is a no-clear-difference result under this sample size and condition grid.

A deterministic graph audit found identical ratio5/ratio10 topology and logical-fault labels in every d3/d5 profile/basis pair, with comparable median edge-weight changes (.131 at d3, .128 at d5). Thus edge addition/removal is not the explanation. The audit does not resolve how different syndrome distributions interact with those weights; no raw detector arrays were saved in the robustness results, so that causal path remains untested.

An exact-seed replay reproduced every stored error total and decomposed decoder disagreements. On d3, ratio10 altered 1,105/1.6M logical predictions and was correct in 730 versus 375 errors introduced (66.1% conditional success). On d5 it altered 452/1.6M and fixed 210 while introducing 242 (46.5%). This explains the net margin at the level of paired outputs but not why a given syndrome's preferred logical class changes. Because the replay reuses archived seeds, it is not independent confirmation.

On the predeclared detector-weight bins, d3's ratio10 disagreements mostly occurred at weights3–8 and were usually beneficial; high-weight disagreements were mostly harmful but sparse. At d5 most disagreements were weight9+ and close to a coin flip. Raw click counts use different detector totals across distances (40 versus216), so these categories are not comparable normalized coordinates. This is a descriptive lead for a future error-mechanism study, not an established causal explanation.


## Shared-failure pair-channel composition

An instrumented actual-ratio10 screen in two high-LER mismatched-basis cells per distance found shared-both-wrong events contained about 1.94 pair-channel faults/shot at d3 and 4.67 at d5, versus .35 and 2.14 in both-correct samples. Bias-aligned XX/ZZ pair events were enriched 5.7–5.8× per shot among d3 shared failures and 2.28× at d5. One-qubit and measurement faults were not individually tracked; this covers only two profile/basis cells. It is descriptive fault composition, not an error-floor or decoder-impossibility result.

## Dense VE stop and sparse categorical inference

Dense VE exceeded its fixed cap at two adjacent layers, but an exact sparse XOR-state DP plus independent half-convolution solved that isolated fragment, and sparse DP plus Walsh-Hadamard convolution solved three final layers. A first Walsh implementation mistakenly divided by N^(L-1) and disagreed by .95; the sparse independent DP caught this before reporting, and the correct inverse transform divides by N once. Final sparse/Walsh agreement is 1.22e-15. This fixes the local scaling conclusion: dense VE is stopped, while exact sparse signature contraction remains feasible for fragments with only 12 touched detectors. It still scales exponentially in syndrome support and is not full-circuit decoding.

Four adjacent final layers (24 categorical locations) also remained at 12 touched detector bits and passed sparse/Walsh exact cross-checks at 2.78e-15. This is favorable temporal locality in the chosen final circuit slice; it cannot be extrapolated to earlier layers or the complete 40-detector circuit without measuring their support growth.

The fifth-layer sparse preflight reached 18 detector bits (524,288 joint state upper bound) and a conservative 251.7M-transition estimate, above the predeclared 100M cap. It stopped before probability expansion. This is a compute-budget stop for this DP protocol, not an information-theoretic lower bound or proof that Walsh/tensor methods cannot proceed.

The fifth-layer sparse-dictionary protocol stopped at its 100M Python-transition cap, but a separately predeclared vectorized XOR-kernel protocol passed the same 524,288-state space with ~251.7M array updates and Walsh reference in5.92s, using ~23MiB estimated work memory. This shows the earlier stop was implementation-budget-specific rather than an output-state impossibility. A sixth layer still needs its own state/memory preflight; full-circuit support remains the limiting issue.

The final six-layer preflight narrowly exceeded the raw 16-outcome update cap, but exact per-location signature coalescing collapsed 576 labels to 296 unique `(detector,logical)` signatures. The coalesced vectorized DP and Walsh reference then passed at 524,288 states in6.10s, with2.32e-16 mass difference. This is an exact algebraic simplification, not probability pruning. Scope remains the isolated tail; added earlier channel layers can increase detector support exponentially.

The seventh temporal layer adds two detector support bits, doubling the joint signature bound from 524,288 to 2,097,152; the fixed 1M-state cap fails before inference. Do not infer that every exact representation must fail at seven layers, but the current dense-signature DP/Walsh route is now beyond its declared memory/state budget.


The seven-layer joint-state method stopped at its predeclared 1M-state cap. A separately designed parity-state formulation removed the redundant logical dimension without dropping information. It passed cross-checks, so the earlier stop was a representation boundary, not an inference boundary. The new method still has exponential syndrome-state cost and was only applied to a 42-location tail; its exact MAP risk cannot be interpreted as full-circuit LER.


## Pair-cluster rare-event proposal

The pair-cluster proposal is correctly instrumented and likelihood weighted: a synthetic uniform test observed all 256 two-channel categories with no flag/Pauli mismatch, and all six Q-SHIFT estimates remained within three combined SE of both comparators. It nevertheless failed its variance-advancement gate in all six conditions. One plausible mechanism is sparse failure-conditioned cluster coverage: only about 20–37 of 256 weighted failure categories were observed per cluster on average, and biased-condition training failure ESS was 113–129. The fitted proposal then had longer log-weight tails than the global fivefold tilt. Do not tune shrinkage or cluster boundaries on this validation set. The result rejects this fixed adjacent-pair/product proposal at the declared sample budget; it does not reject all cluster or sequential rare-event methods.


## Native-gate XZZX orientation interaction

Removing explicit H-gate overhead did not produce a uniform XZZX benefit. At the same d3/d5 finite resources and under matched native entangler noise, XZZX improved the X-biased cells (rate ratios 0.662/0.376) but was substantially worse in Z-biased cells (3.86/11.24). Thus the prior XZZX degradation cannot be attributed solely to added H noise: the fixed checkerboard orientation is aligned with one bias orientation and misaligned with the other under this circuit/decoder. This is development evidence under a hypothetical equal-noise XCX/CZ native gate model; it does not justify switching codes at runtime or extrapolating to hardware. A single complementary orientation test could discriminate an orientation effect, but no pattern sweep should follow.


## Complementary XZZX orientation on Z-biased noise

The single complementary checkerboard reduced Z-biased LER relative to the original XZZX orientation by about 14% at d3 and 21% at d5, which supports a real orientation effect. It nevertheless remained 3.04x/6.16x worse than CSS. The orientation adjustment therefore did not rescue this XZZX family for the tested Z-memory Z-biased task. Do not continue searching checkerboard variants on these same conditions; a useful new direction would require a different code schedule or decoder mechanism and a fresh protocol. The equal native CX/XCX/CZ noise assumption remains unverified for hardware.


## Spatial local-rate decoder screen

A true-map local DEM gave only a small, one-sided benefit over the pooled mean graph: 2.3% relative reduction for west-hot and a 0.5% increase for east-hot. The macro reduction was under 1%, with only 288–331 discordant paired outcomes/profile. The local graph also decoded slightly slower. Under this fixed 1.5x/.5x two-zone map and d3 circuit, spatial calibration did not pass the prospective utility gate. This does not show local calibration is useless for stronger/more complex heterogeneity, but the tested profile supplies no reason to pay calibration/selection costs. The DEM itself uses the same approximate disjoint-error conversion for both arms.


## Tensor MPS biased-code-capacity replication

The fixed chi=16 MPS improvement replicated directionally across two independent sample roots under the X-biased code-capacity model. At d5 both roots showed fewer errors with MPS; at d3 the second root's paired interval crossed zero. This is a positive small-code-capacity result, not a robust circuit-level decoder result. The principal practical limitation is runtime (about 31x bias-aware MWPM at d5); the principal model limitation is perfect syndrome extraction and a single-qubit code-capacity channel. qecsim's planar MPS decoder expects a planar code and perfect syndrome, whereas Q-SHIFT supplies a repeated noisy spacetime detector history with categorical two-qubit gate faults. Applying it directly to the terminal syndrome would discard information and be an unfair comparison. A spacetime tensor decoder is a separate algorithmic project and requires a new bounded protocol.


The documented row/column-averaged qecsim contraction did not change any logical predictions relative to column mode on 5k biased code-capacity samples at either d3 or d5, while roughly doubling d5 runtime. This rejects the fixed mode-a ablation at chi16 for this sampled condition; no further contraction-mode tuning is justified on the same streams.


The natural-order exact tail posterior is not sufficiently compressible for the predeclared rank-64/1e-10 tensor-train gate: P and Z both require rank 91 at the hardest cut. At looser 1e-6 relative Frobenius tolerance the maximum rank is 30, but the protocol forbids advancing based on that post-result observation. This closes the exact-fidelity MPS prototype at this fixed ordering; it does not rule out approximate decoders or other orderings.


## All-location fault composition under ratio-sensitive decoding

The preflight passed synthetic flags for all 15 two-qubit Paulis, all three one-qubit Paulis, and explicit X/Z error events (zero data/flag mismatches). Both d3 conditions had 120 two-qubit pairs and 40 one-qubit locations; explicit measurement targets were 49 for Z-memory/X-biased and 49 total for X-memory/Z-biased. Source and instrumented samples had unchanged 40-detector/one-observable layout, and failure-rate differences were below 1.1 combined standard errors. The 200,000-shot main screen took 3.73 seconds.

At 100,000 shots/condition, ratio-5/ratio-10 models failed on 753/752 Z-memory X-biased shots (61 prediction disagreements) and 769/766 X-memory Z-biased shots (95 disagreements). The both-wrong groups contained 722 and 720 shots; ratio-10-fixes-ratio-5 groups contained 31 and 49, while ratio-10-breaks-ratio-5 contained 30 and 46. In both conditions, mean tracked two-qubit faults were about 0.349 per both-correct shot and 1.87 per both-wrong shot. In the biased Pauli outcome counts, XX was most frequent in the X-biased Z-memory both-wrong group (794 events), while ZZ was most frequent in the Z-biased X-memory both-wrong group (800). One-qubit and explicit measurement-fault counts also differed across outcome groups; see the JSON for full counts.

The decoder-disagreement groups are small, particularly the 30–49-shot fix/break groups. These are conditional fault associations from one fixed development stream, not causal attribution, evidence that one fault channel caused decoding errors, or a hardware noise claim. The new instrumentation extends the earlier two-qubit-only report; it does not change the prior conclusion that raw fault burden alone cannot explain decoder behavior. No sealed or confirmatory data were accessed.


The d3/d5/d7/d9 basis-alignment synthesis suggests stronger finite-distance suppression in aligned than mismatched CSS memories, but the aligned tail counts (51, 6, 5, 1) are too sparse to establish asymptotic scaling. The d9 ratio point remains above the 1e-4 target and its exact interval spans orders of magnitude. Do not extrapolate the Poisson line to claim the target is reachable.


The XZZX X-bias result used CSS Z-memory as its reference. Same-resource X-aligned CSS streams already in the record had lower LER than XZZX Z-memory at d3 and d5. This changes the practical code-design recommendation: first select the memory basis for the known bias, then compare codes. The cross-screen comparison is descriptive, unpaired, and depends on equal CX/XCX/CZ duration and noise.


The fresh d5 factorial clarifies the code/basis interaction. XZZX-X and XZZX-Z were similar, but both had about eight times the CSS-X failure rate. XZZX-Z still beat CSS-Z by about 2.8x. Thus the initial XZZX gain reflects the choice of comparator memory basis; it does not outperform the best known-bias CSS configuration. The 2x2 comparison is one finite-size simulator screen under an unverified native-gate assumption.


An equal-weight post-hoc average across X- and Z-memory tasks favors XZZX (.001274 vs CSS .001927), even though CSS-X is the best individual cell. This is a workload weighting tradeoff, not arbitrary-state performance. Do not generalize it without a workload definition and an independent confirmatory design.


The independent d5 replication confirms the equal-weight X/Z task average but also confirms that CSS-X is much better than either XZZX basis for a known X-memory task. Thus the code-selection rule is workload-specific: XZZX is a candidate for balanced separate basis tasks, while CSS-X remains the selected baseline for X memory under known X bias. The equal weighting and simulator noise do not establish arbitrary-state or hardware performance.


Across d3/d5/d7, the XZZX/CSS ratio for an equal-weight separate X/Z task mix moved from 1.18 at d3 to about .66 at d5 and .279 at d7. XZZX improved increasingly over CSS-Z, but lost badly to CSS-X; its d7 CSS-X ratio is imprecise because CSS-X had only 7 failures. These finite-size tradeoffs do not justify extrapolation. The d3/d7 preflight first encountered a zero-denominator reporting bug; it was fixed and the unchanged seed stream passed all actual circuit gates before main sampling.


At d9 the balanced-task XZZX gain is driven by Z-memory: 18 XZZX-Z errors vs 260 CSS-Z, while CSS-X had 1 failure vs 10 XZZX-X. The equal-weight aggregate .107 therefore masks a severe known-X-memory tradeoff and sparse X-memory counts. The result is not an arbitrary-state channel and relies on equal native gate noise/duration. Do not report only the aggregate.


The d11 balanced aggregate is driven by 3 versus 67 Z-memory failures; both X-memory cells had zero failures in 500k. Therefore the X-memory architecture comparison is unresolved, not tied. The aggregate rate ratio .0448 has a broad exact interval (.009–.137), and does not establish the 1e-4 goal. The run took 282s, leaving little headroom under the 300s cap.


The current four-cell d13 screen is too expensive under the 300-second run cap: preflight projects 454.7s. Do not reduce shot count or split conditions after seeing results to force a d13 claim; a new computational design is required. The d11 result is the highest-distance full factorial checkpoint.


At d7 and 2:1 bias, XZZX improves the equal-weight memory-task average only modestly (.853) and does so by reducing Z-memory errors; XZZX-X is 1.44x worse than CSS-X. The 5:1 and 10:1 aggregate gains are larger (.608 and .279). This is a bias-strength interaction, not a universal code winner or an arbitrary-state result.


The d7 5:1 condition shows the equal-mix XZZX benefit is not confined to 10:1, but XZZX-X still loses to CSS-X by 5.85x. The aggregate .608 is therefore a basis-mix outcome; use the separate basis rates whenever the workload axis is known.

## d13 bit-packed throughput path

The packed sampler reduced sampling time, and packed PyMatching outputs exactly matched ordinary outputs, but total projected time remained 358.13s against the fixed 300s cap. Decode speed was inconsistent and slower for CSS-X. The API substitution preserves decisions but does not supply enough end-to-end throughput under this protocol; the predeclared stop rule correctly prevented a main run.

## Fusion Blossom serial integration

Custom graph conversion was feasible after even-integer weight quantization, with no prediction mismatches on 1,000 d3 samples. The Python serial solver was slower than PyMatching by roughly 6.5–15.3x in these cells. This small screen does not rule out Fusion Blossom's parallel partitioned solver at larger scales, but provides no reason to spend the current d13 budget on the serial path. Correlation-enabled equivalence was not tested.

## Min-fill TT ordering

The fixed min-fill detector order was structurally motivated by event co-occurrence but increased the high-accuracy maximum TT ranks from 91 to 151/150 for P/Z. Event-graph fill is not a reliable proxy for singular-value compressibility on this posterior. The single preregistered order failed; no post-hoc search of orderings was conducted.

## Sequential profile calibration limits

The SPRT improved detector profile decisions over fixed 25-shot baselines at a similar average sample cost, but still made about 4% profile errors. At 100 logical attempts per calibration, direct correct-output yield was only .800 because calibration shots were charged as unusable; static Z yielded .9958. A stable-profile bootstrap suggests the overhead may amortize over 100k logical attempts, but the 10k grouped replay was inconclusive. There is no evidence for mid-run change detection, non-Gaussian score robustness, multi-profile generalization, or hardware drift. X/Z output circuits differ in terminal measurement and fault-axis composition; report these differences whenever aggregating tasks.

## Gaussian profile model under composition shift

The nominal class-specific SPRT was not robust when measurement noise doubled with gate noise fixed. The Z-biased score mean moved toward the decision boundary and both score variances increased; nominal likelihood increments underweighted evidence for that shifted profile. A pooled-variance SPRT reduced Z-profile error from 17.6% to 12.0% but remained above the 5% gate. Fixed 100-shot LDA performed better on this stream, suggesting the variance-sensitive likelihood model caused part of the failure, but its 51/1,000 point error still has uncertainty and was not independently replicated. Do not use nominal Gaussian SPRT as a general adaptive policy.

## Gaussian CUSUM false-switch failure

Fast transition detection did not compensate for frequent false switching. With h=log(200), stable nominal controls produced dozens of false switches per 100k shots, far above the intended per-segment likelihood-ratio bound; shifted Z-biased controls were worse. The score increments are not distributed according to the fitted Gaussian likelihood closely enough for the martingale false-alarm guarantee, and resetting after switches can produce chatter. Do not deploy this CUSUM or claim the nominal threshold controls false alarms. An empirical threshold would require a new independent calibration/validation design and may increase detection delay materially.

## Single shortest-path floor bound is too weak

The selected shortest graphlike physical patterns are real, mutually exclusive circuit events with zero detector parity and logical parity one, so their probabilities paired with the no-error event lower-bound optimal-decoder risk. However, their probabilities are 1e-12–1e-11 of observed LER. The method finds existence, not the multiplicity of comparable logical mechanisms; it cannot explain the observed floor or certify useful decoder headroom.


## Temporal-rate calibration has small oracle headroom

Under the frozen alternating 0.25x/1.75x per-round gate-rate maps, exact profile-specific matching improved both phases, with paired statistical evidence, but the equal-weight LER reduction was only 2.84%. Decode cost was small (1.02–1.04x), yet the effect fails the 10% utility gate before charging any profile-estimation or change-detection cost. Do not promote online temporal rate adaptation from this oracle-map screen. This is a single synthetic d3 pattern and does not rule out stronger or different temporal correlations.


## Equal-duration round-count positive result needs replication

Adding two biased data-idle cycles to the three-round memory schedule preserves elapsed duration and leaves fewer active entangling gates than five syndrome rounds. The initial two aligned d3 cells favored three-plus-idle (cell rate ratios .848 and .676), but this is one seed per cell, uses an assumed idle Pauli channel, and is not hardware-calibrated. The apparent gain may depend on the idle model or code/task alignment. Do not recommend a round-count policy until a fresh independent stream reproduces it and idle-channel assumptions are bounded.


### Equal-duration schedule replication caveat

The fresh stream reproduced the three-round-plus-idle direction and similar macro rate ratio (.773 vs .762 initially), but the X-aligned cell interval now includes parity (RR .906, 95% .809–1.014); only the Z-aligned cell is individually decisive. Both use the same p=.003 idle assumption, so this is independent sampling replication, not model robustness.


### Equal-duration schedule under doubled idle noise

Doubling only the data-idle channel to .006 preserved the Z-aligned benefit but erased the X-aligned direction: RR=.753 (95% .676–.839) for Z, versus 1.016 (.914–1.129) for X. The macro mean RR=.885 does not override the fixed per-cell rule; the robustness challenge fails because X is not below 1. This limits the candidate to a workload-dependent hypothesis and does not warrant a general round-count policy.


### Equal-duration schedule at d5

The aligned Z-memory d5 extension did not show an advantage for five active rounds plus four p=.003 idles versus nine active rounds (RR=1.05, 95% .83–1.33). The interval excludes gains of 20% or more in this cell. This weakens the prospect that the d3 schedule result scales with distance; the d5 sample is finite and does not establish equivalence or harm.


### Distance-5 intermediate schedule was inconclusive

The seven-active-plus-two-idle d5 point estimate favored it over nine active rounds, but uncertainty included parity (RR=.843, 95% .674–1.056). It failed the predeclared gate. Combined with the five-plus-idle result, there is no supported d5 schedule gain. Do not treat the lower point estimate as evidence of benefit or run post-hoc extra shots.


## Selective escalation accuracy-cost tradeoff

Routing only 0.261% of samples to BP+LSD on matching disagreement produced 14.3% lower macro LER on one development stream, but total runtime was 8.44x after accounting for both matching passes needed to compute the flag and the slow BP+LSD calls. The policy fails its 2x runtime gate. Per-condition gains were heterogeneous and the X-memory/Z-biased condition improved only 4.1%. Any continuation must independently verify the accuracy signal and would need a materially faster escalator; do not claim deployable utility.


### Selective escalation independent replication

Fresh seeds reproduced about 13% macro LER reduction with the fixed syndrome-only flag and zero invalid escalated syndromes, but full decode time was still 8.24x correlated matching. This supports the ambiguity flag as informative and independently confirms the cost failure. The current BP+LSD implementation should remain rejected; an optimized local search would be a new candidate and needs a separate protocol.


## Fast learned selector: positive but model-specific

A low-cost supervised selector trained on the matching-disagreement subset independently reduced macro LER by 17.2% and 16.2% in separate held-out train/validation splits, with 1.35x/1.36x total inference cost. It used true observables only as offline training labels. Per-condition gains were positive in all cells, but asymmetric (about 4% to 36%) and noise profiles were fixed and known. Same-stream BP+LSD comparison favored logistic in five of six cells at much lower cost. Main unresolved risk is distribution shift: measurement-noise mismatch, changing bias, and distance transfer remain untested. Do not interpret as an online noise-adaptation result or hardware decoder.


### Frozen selector shift challenge: specific positive result, broader risk remains

The nominally trained logistic policy did not fail under the prespecified measurement-flip increase from .003 to .006: it reduced macro LER by 13.0% and 13.1% on two independent streams at ~1.35x total inference cost, with all six per-condition paired intervals favoring it. This narrows the model-mismatch concern for that one shift. It does not establish robustness to bias changes, gate-noise shifts, simultaneous changes, unmodeled correlations, distance transfer, or hardware noise. Preserve the two streams as development evidence; do not claim general domain adaptation. Details: `../independent_research_v2/fast_flagged_logistic_measurement_shift_report.md`.


### Distance transfer exposed a boundary for the learned selector

The method was re-fit with d5-specific 218-dimensional features rather than blindly applying d3 coefficients. Despite adequate training data and converged fits, held-out macro LER was 1.35% worse than correlated matching; only two of six cells improved. Full inference cost was acceptable (1.38x), so this is an accuracy/transfer failure, not a runtime rejection. The fixed gate failed and no replication or tuning followed. The current d3 result must not be described as a scalable d5 advantage. This does not rule out a different d5 model or selective decoder, but those would be new candidates. See `../independent_research_v2/fast_flagged_logistic_d5_transfer_report.md`.


### Reduced-bias shift adds a second bounded positive result

The selector frozen at bias ratio 10 retained a 17.8%–18.0% macro LER reduction on two fresh streams at physical ratio 5, at ~1.35x cost, with all per-cell intervals favorable. This reduces concern for that one shift axis at d3. It does not reconcile the negative d5 transfer result or establish robustness to simultaneous shifts, other profiles, or hardware. Balanced cells did not shift and should be recognized as controls. Do not make a general robustness claim. See `../independent_research_v2/fast_flagged_logistic_bias_shift_report.md`.


### Combined shift did not erase the d3 selector benefit

A two-axis challenge combining measurement p .003→.006 with bias ratio 10→5 retained a 14.0%–14.6% macro reduction on two fresh streams, with all per-cell intervals favorable and ~1.35x cost. This addresses interaction for one specified combination, but not arbitrary or larger shifts. It remains limited to d3 simulator conditions and cannot be extrapolated over the failed d5 transfer. The actual-profile matcher remains diagnostic, not an optimality bound. See `../independent_research_v2/fast_flagged_logistic_combined_shift_report.md`.


### Shared pooling passes but gives up some specialization accuracy

One pooled d3 model passed the same baseline advancement gate on two independent streams, reducing macro LER 14%–15% at ~1.36x cost. However, the same-stream specialized models were better by about .00010 absolute macro LER with paired intervals favoring specialization. The shared fit therefore trades a smaller coefficient bank and no condition-model routing for a modest accuracy loss. No noninferiority threshold was declared; do not state that it matches specialized performance. The d5 transfer boundary still applies.


### Relative-choice target passes but gives up selector accuracy

The pooled 40-bit model predicting whether correlated matching is wrong reduced macro LER 12% on two fresh streams at ~1.35x cost. It passed the frozen baseline gate, but shared absolute-bit selection was better by ~.00014 macro LER and specialized selection by ~.00022. One cell was essentially tied on each stream. Treat relative choice as an interpretable compact alternative, not an improvement over the best learned policy.


### Profile holdout supports selector transfer but not unknown-profile decoding

The relative-choice classifier trained without labels from one Pauli regime passed three leave-one-regime-out folds on two fresh runs, with 11.4%–11.5% macro reductions and every held-out cell slightly or substantially improved. However, the matching graphs remained profile-matched, and all-profile/specialized references were more accurate. The experiment does not establish unknown-profile decoding or arbitrary transfer; one d5 screen still failed.


### Cross-basis transfer breaks relative-choice generalization

Although leave-one-regime-out passed when both memory bases appeared in training, leave-one-basis-out failed: macro LER worsened 1.54%, and the X-memory holdout fold worsened 3.72%, with one cell exceeding 5% harm. The model's relative target is not basis-invariant under this encoding. Any transfer statement must specify that training includes the target basis; do not describe this as universal cross-profile or cross-task decoding.


### Ratio-2 bias shift adds static robustness evidence

The frozen d3 selector retained ~17%–18% macro gains when anisotropic profiles were weakened from ratio 10 to ratio 2, on two independent streams and at ~1.35x cost. This extends the tested static bias range but says nothing about temporal drift, graph uncertainty, cross-basis transfer, or distance scaling. Do not merge these boundaries into a general robustness claim.


### Isotropic ratio-1 shift adds bounded static robustness

The frozen ratio-10 selector retained ~16% macro gain at physical ratio 1 on two fresh d3 streams. One first-stream cell interval crossed parity, but point estimates were positive throughout and the independent replication intervals all favored the selector. This extends stationary bias-strength evidence without changing limitations: no temporal shift, graph selection, cross-basis transfer, hardware, or d5 generalization.


### Gate-rate robustness did not clear the strict utility gate twice

Doubling gate p to .006 produced 10.01% macro reduction initially and 9.95% on replication. Paired intervals favored the selector in both streams and all cells improved, but the frozen macro threshold failed by 0.05 percentage point on fresh validation. Do not upgrade the gate-shift result based on its paired significance alone; it is a borderline utility-gate miss. The diagnostic graph threshold preflight failure is retained in v2.


### Gate-rate shift is asymmetric

Halving gate p to .0015 gave 23%–24% macro gains on two streams; doubling to .006 gave 10.01% then 9.95% and failed the frozen gate on replication. This asymmetry means the selector's rate robustness is bounded and directional. Keep the doubled-rate borderline result alongside the positive half-rate result; do not state generic gate-rate robustness.


### Measurement-rate shift is robust on both tested sides

Halving measurement p to .0015 gave 18%–19% gains twice, complementing the ~13% gain at doubled measurement p=.006. Both directions passed the frozen gate, unlike doubled gate p, which narrowly missed. This supports only stationary measurement-rate mismatch at d3; temporal correlations and graph uncertainty remain untested.


### One temporal-rate pattern is a positive but narrow result

The stationary selector transferred to two reversed five-round gate-rate maps on Z-memory/X-bias d3 (11.7%–12.5% gain, ~1.36x cost). This reduces concern for that imposed temporal pattern, but it is not online calibration, arbitrary drift robustness, or evidence for other memory/profile tasks. Keep the separate gate-p=.006 borderline result and cross-basis/d5 failures visible.


### A second temporal shape replicated the selector gain

The selector also passed a blockwise hot/cool five-round pattern and reversal (11.8%–12.4% gains, ~1.36x cost). This makes the positive temporal evidence less dependent on one sequence shape, but both tests share Z-memory/X-bias d3, fixed mean rate, and oracle-designed stationary average. No claim of online adaptation or arbitrary drift is warranted.


### Temporal selector benefit is task-specific

The blockwise temporal gain reproduced for Z-memory/X-bias (~13%) but not for X-memory/Z-bias (~0.7%/3.1%); equal-task macro fell below the 10% gate. The earlier temporal result cannot be generalized across bases/tasks, even using separately trained nominal selectors. No replication followed.


## Low-shot selector fit gate and runner ordering

For the proposed 100k-shot training prefix, X-memory/X-biased yielded 93 disagreement-flagged rows (73/20 class split), below the predeclared 100-row floor. A script ordering defect allowed the first three conditions into validation before checking that fourth condition; their partial outcomes were discarded. No macro LER, model retention, or advancement claim is available. Treat the candidate as not train-ready under this protocol, and retain 1M shots/condition as the validated reference.


## Selector training sample-size boundary

The nested 100k prefix failed fit readiness in X-memory/X-biased (93 flags, below the 100-row floor); its partial validation was excluded after a runner-order defect. A separately frozen 500k budget then passed twice and retained 98.4–100.2% of the measured 1M-fit macro gain. These results establish a tested boundary at 500k vs a non-ready 100k prefix, not a smooth learning curve or proof that all budgets below 500k fail.


## Nonparametric score likelihood did not control switching

A smoothed 32-bin detector-score likelihood CUSUM failed false-alarm limits despite fast detection. Nominal controls gave 33–41 false switches/100k; measurement-shifted controls gave 46–170/100k. This shows that replacing Gaussian score densities with a finite-sample histogram alone does not resolve the model-mismatch/false-switch issue. Periodic LDA was quieter on the same sequences. Do not tune this threshold or binning post hoc.


## CUSUM threshold selection variability

Empirical calibration reduced false alarms and preserved change detection, but fresh recalibration selected h=8.327 versus 8.595 initially and narrowly exceeded the shifted-Z false-switch limit (28.9/100k). The original h passed a secondary fresh-stream check. This mixed result does not establish stable threshold selection or robust error control; no further post-hoc threshold adjustment is justified.


## Nonlinear selector optimization stop

A one-hidden-layer 8-unit tanh classifier did not converge within 500 L-BFGS-B iterations on Z-memory/X-biased flagged training data. The frozen protocol stopped without validation. This rejects the chosen implementation budget, not all nonlinear decoders; no post-hoc iteration increase was attempted.


The 500k selector training budget did not show the nominal-only failure feared under a combined measurement/bias shift: two fresh fits retained 97.7–98.1% of corresponding 1M-model gains. This closes only one specific d3 composition challenge and does not erase the d5, cross-basis, or temporal-task boundaries.


## Tensor-network efficacy below fixed gate

Exact d3 planar MPS improved over noise-aware MWPM by 5.55% under p=.05 biased code-capacity noise, but the fixed >=10% practical-effect gate failed. This does not reject MPS for circuit-level or other-distance problems; it gives no Q-SHIFT circuit evidence and was not replicated.


### Frozen histogram CUSUM false-alarm confidence

Although h=8.595 had shifted-Z point rates 24.44 and 23.78 per 100k, same-seed episode-cluster 95% intervals were 20.22–28.89 and 19.33–28.67. Both cross the 25 limit. The threshold therefore lacks precise rate-control evidence in the hardest stratum; point-gate success is not a 95% guarantee.


### Larger shifted-Z stream rejects histogram-CUSUM rate control

A fresh 5,000-episode stream at the unchanged threshold yielded 25.36 false switches/100k with a 95% whole-episode bootstrap interval [23.96, 26.80]. The point estimate exceeded the 25 limit, as did the interval's upper endpoint. This result rejects the present threshold for the tested shifted-Z simulator condition. It does not establish a hardware rate, but does show that the earlier 500-episode point passes were inadequate. Do not tune this threshold using these validation outcomes; a future candidate needs a distinct mechanism and prospective calibration/validation separation.
