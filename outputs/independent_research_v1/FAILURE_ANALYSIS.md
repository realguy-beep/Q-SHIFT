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

Likely issue: the global logical parity factor creates loops in the factor graph, and the Bethe approximation is not accurate enough for the one-qubit fixture. This explanation is consistent with the topology dependence but is not yet proven by an exact Bethe/free-energy derivation or a tree-topology control. The candidate is stopped before circuit evaluation. A follow-up must separate coding errors from approximation error with hand-computable trees and exact toy posterior checks, and should only proceed if all fixtures meet a prespecified risk/decision agreement gate.

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
