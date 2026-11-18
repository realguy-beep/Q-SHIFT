# Claude handoff — interim research checkpoint

This is an interim advisory note from isolated branch `codex/qshift-independent-research-v1`. The current research checkpoint is not an integration request or a performance claim.

## Most useful finding

The proposed correlation-mechanism follow-up requiring a non-approximated DEM cannot be implemented for Phase 2B's categorical `PAULI_CHANNEL_2` circuits through Stim's circuit-to-DEM API. A deterministic check failed on all six basis/composition conditions because Stim requires `approximate_disjoint_errors=True`. That conversion check itself generated no shots. A later BP+LSD development screen sampled 30,000 original-circuit events while both decoders used the same approximate DEM; it is described below. Do not replace the channel with independent Pauli faults and keep the same hypothesis.

## Prior Q-SHIFT evidence

- The 720,000-shot correlation-mode development pilot already exists and was independently rescored. Correlated mode made 3,349 versus 3,532 pooled-fixed errors, but its primary interval did not meet the preregistered practical margin and two same-name strata were worse. This supports a condition-dependent association only.
- The existing uncertainty-selection review reports no-go results, including weak calibration-utility prediction and a below-chance current-syndrome signal.
- The exact categorical reference is validated on tiny toys. Full d=3 enumeration covers 2^609 fault assignments and is infeasible.
- A new generic loopy sum-product Bethe prototype passed a hand tree control but had LER 0.057354 versus exact MAP 0.002646 on one exact toy, and only matched the other toy. It is stopped before circuit evaluation.
- A paired BP+LSD screen on 5,000 distance-3 circuit samples in each of six Phase 2B conditions found 321 errors per tested LSD variant versus 138 for correlation-enabled PyMatching. All returned fault estimates reproduced their observed detector syndromes, and BP+LSD was worse in every condition. The screen uses one approximate DEM threshold and one fixed min-sum/LSD configuration; treat this as a negative development result, not a general BP+LSD conclusion.
- The exact-categorical sampler instrumentation was validated on synthetic channels and independently crosschecked against unmodified Stim circuits (max absolute standardized LER difference 0.701). A global fivefold odds tilt gave direct/weighted agreement, but in 16 replicates its six-condition macro SD was 12% higher; results varied substantially by stratum. It is a correct weighting framework, but this proposal is not a robust efficiency gain and should not be integrated as such.
- A forward-KL cross-entropy proposal built from weighted failure-conditioned categorical marginals also failed its predeclared variance gate in all six fresh validation conditions; several strata had very low failure-weight ESS. Do not tune it on those validation outcomes. A future rare-event proposal likely needs joint fault structure/progress, with a new independent validation split.
- Same-resource memory-basis analysis of two independent exact circuit sample sets supports matching the stored logical basis to known bias: 80.6% fewer failures for X-memory under X bias and 91.0% fewer for Z-memory under Z bias; balanced noise showed no meaningful difference. This is a static known-profile configuration baseline only and does not establish adaptive tracking or scalability.
- A d=5/9-round extension showed the same alignment direction under X/Z bias with 36×–45× lower observed LER, using matched 64-qubit/216-detector resources. Each aligned cell had six failures in 50k shots, so absolute rates remain coarse; this is not a threshold result.
- Intermediate d=3 bias ratios add a static configuration baseline: at 2:1, the matched memory basis had 26–35% fewer errors; at 5:1, it had 68–76% fewer. The data do not pinpoint a crossover or validate runtime adaptation.
- A d=7 (13-round) extension under known 10:1 bias preserved matched circuit resources (118 qubits, 624 detectors, 2,184 two-qubit channel pairs) and the same direction: aligned LER 5/500k under X bias and 3/500k under Z bias, versus 1,009 and 1,227 mismatched failures. Exact rate-ratio intervals remain broad because aligned counts are sparse. This is stronger finite-distance static co-design evidence, but it does not validate unknown-profile adaptation or give a threshold.
- qecsim fixed-χ=16 planar MPS beat qecsim MWPM at d=3 and d=5 on ideal-syndrome IID depolarizing samples at p=.05 (123 vs 206 and 30 vs 92 failures in 5,000 paired shots). It cost 13.74 ms/sample at d=5 versus 0.507 ms for the Python MWPM path. Treat this as a promising code-capacity result only; repeated noisy-circuit compatibility is untested and latency is high.
- A frozen two-class detector-only LDA trained on d=3 ratio-10 profiles generalized to ratio 2/5/10 and distances 3/5/7. At ratio 2, direction accuracy with 500 calibration shots was 94.9%, 99.3%, and 99.35%; at ratios 5 and 10 it was 100% on the tested windows. A separate balanced-vs-biased three-class model did not generalize well to moderate bias, so magnitude detection remains a different unresolved task.
- The frozen classifier was evaluated end to end on independent d=3 calibration and logical streams: with 500 detector shots per job it reduced equal-prior LER versus fixed Z by 16.6% at ratio 2, 52.4% at ratio 5, and 71.7% at ratio 10, with cluster-bootstrap intervals below zero for policy-minus-fixed LER. This is a synthetic development result under stable, exactly specified profiles. Calibration overhead, drift, model mismatch, and hardware transfer remain untested. One initial implementation pass inverted the score-to-basis sign; it is explicitly preserved as invalid and excluded. The corrected code checks training-label polarity.
- The direct LER comparison is per logical shot. Each 100-shot selected-memory batch used a separate 500-shot calibration window, while static Z required no calibration; this test did not equalize total circuit-shot cost or evaluate amortization across longer stable runs.
- If those 500 calibration shots yield no useful logical output and cost the same as one memory circuit, a plug-in throughput calculation requires about 618k/228k/169k logical shots per calibration at ratios 2/5/10 before calibrated selection produces more correct outputs per total circuit shot than static Z. This assumes long stability not yet measured; see `FUNDAMENTAL_LIMITS.md` and `calibration_amortization.json`.
- A secondary exploratory rescore of nested 25/100/500-shot calibration prefixes per 100 logical shots produced reductions of 5.1/11.6/16.6% at ratio2, 27.8/49.6/52.4% at ratio5, and 57.5/71.2/71.7% at ratio10. The ratio2/25-shot interval included zero. These windows reuse the primary streams and are correlated; do not select a confirmatory budget from this rescore.
- A further rate-shift check retained 12.2/50.6/71.0% LER reductions versus static Z at ratios 2/5/10 when calibration stayed at p=.003 and logical runs doubled to p=.006, with bias direction unchanged. All arms used approximate DEM threshold .004 because .0018 could not convert the high-rate channels. This only demonstrates limited stable-direction robustness; it does not test an X↔Z change point or hardware drift.
- Scope correction: the basis selector changes the logical observable under test. It is relevant only if the workload can choose which logical basis to store; it is not a full arbitrary-qubit memory or decoder-only result. A direct same-Z-observable decoder-bank comparison found 775 vs 779 failures for selected profile graphs vs a pooled static graph over 200k shots; the paired bootstrap interval included zero. Profile labels were accurate, but decoder gain was not resolved.
- A checkerboard local-H XZZX transform kept the abstract Z-memory observable, detector count, and two-qubit gate count fixed but added 150–167% one-qubit H/noise targets. Its LER was worse than CSS in all tested d3/d5 and X/Z-biased conditions (1.33×–19.8×). Do not integrate this simple transpilation. Native XZZX schedules require a separate resource/noise model.
- A model-based replay of existing calibration/logical windows under equal-dwell alternating X/Z bias found no tested periodic schedule beat the best fixed basis on correct outputs per total circuit shot at dwell <=10k shots. At 100k dwell, the best plug-in gains were only 0.10% and 0.21% at ratios5 and10; ratio2 remained below static. This is not a causal change-point or device result and has no uncertainty propagation. Full schedule grid and assumptions are in `temporal_basis_replay_protocol.md` and `temporal_basis_replay_results.json`.
- A d3 rounds3/5/7/9 screen found per-attempt LER increased monotonically with round count in all four X/Z profile/basis cells; 3 rounds used 72 versus 120 two-qubit pairs at 5 rounds. These runs have different storage durations, so no equal-time claim follows. The next useful comparison is a fixed-time schedule with explicit idle noise; see `round_count_frontier_protocol.md` and its result/preflight artifacts.
- A paired d3 bias-strength screen compared matching models assuming ratios 2/5/10 against actual X/Z-biased circuits at each ratio. Fixed assumed-ratio10 had the lowest equal-weight LER across the 12 cells and was lower than the correctly specified-ratio reference by 0.000273 (conditional MC 95% interval [-.000323,-.000222]). This is a development-only robustness signal with same-screen model selection; it does not justify deploying ratio10. See `bias_strength_robustness_protocol.md` and `bias_strength_robustness_results.json`.
- A fresh frozen ratio10-vs-ratio5 check on 16 new d3 conditions (actual strengths 2/3.5/5/10) confirmed the macro direction: ratio10-minus-ratio5 LER was -0.000222 (conditional MC interval [-.000263,-.000181]); only two of four ratio2 cells favored ratio10. This validates the fixed-grid result within the simulator, not as a general decoder setting. See `bias_strength_frozen_validation_protocol.md` and its results artifact.
- The fixed ratio10-vs-ratio5 test at d5 did not replicate the d3 advantage: paired macro delta was +.000020 (95% conditional MC interval [-.000006,+.000046]). Treat this as inconclusive/near-neutral, not equivalence. The mismatch effect is not established across code distances; see `bias_strength_distance5_validation_protocol.md` and results.
- A deterministic graph audit found ratio5/ratio10 matching topologies and logical-fault labels identical at both distances (142 edges d3, 950 d5); median common-edge weight changes were similar (.131/.128). The performance difference is not due to edge addition/removal, but the causal syndrome/decision interaction remains untested. See `bias_graph_mechanism_protocol.md` and results.
- Exact-seed replay decomposition reproduced all archived counts. Ratio10 changed 0.069% of d3 predictions and fixed 730 errors while introducing 375; at d5 it changed 0.028% and fixed 210 while introducing 242. Conditional accuracy on changed decisions was 66.1% at d3 and 46.5% at d5. This decomposes the result but does not identify why those syndromes change. It uses no new unique samples; see `bias_strength_decision_replay_protocol.md`.
- Coarse predeclared detector-weight bins suggest d3 ratio10 disagreements cluster at weights3–8 and are mostly beneficial, while d5 disagreements mostly fall at weight9+ and are near chance. Detector totals differ by distance, so these raw weights are not directly comparable; treat this only as a lead.
- The sample-specific oracle that selects the correct answer whenever ratio5 and ratio10 disagree could improve over the best fixed model by at most 4.7% (d3) or 6.9% (d5) on the replayed samples; both-wrong events remain. This is not a population bound, but ratio-only selection cannot plausibly reach the large target without a decoder that corrects shared failures.

## Suggested next implementation

The independent branch now has a log-domain exact variable-elimination prototype that keeps local Pauli outcomes categorical. It matches exhaustive joint masses, posteriors, MAP decisions, and risk on one tree and two cyclic repetition toys. All six 16-state pair locations in one final-round d=3 Phase 2B layer passed an independent sparse XOR-convolution reference on 1,024 syndromes (max joint error 1.1e-16, width4, 131,072 table entries, 95s); 512 combined forced-Stim checks also passed. Synthetic binary grids reached 524,288 entries at 11x11. This is one isolated layer, not a full-circuit decoder/LER result. A scope-only audit of the two adjacent final-round channel layers found no viable dense order under the 1M cap: best of eight required 17.2B entries, so inference stopped. Do not continue this dense factorization. A different exact tensor/finite-state representation would need a new exact fragment protocol. See `categorical_phase2b_two_layer_preflight.json` and the six-location artifacts.

## Avoid

- Repeating the already completed correlation pilot or fitting a selector to its inspected outcomes.
- Advancing the tested BP+LSD configuration without a mechanistic correction; its fixed development comparison was worse than the strong matching baseline in all six conditions.
- Calling correlated matching maximum-likelihood decoding.
- Presenting the Stage S BP+OSD figures as independently verified. Stage S artifacts were not present in published `main`, and Claude's branch was not inspected.
- Claiming 99.99% reduction from current finite-distance results. With baseline LER 0.005, the candidate ceiling would be 5e-7 and approximately 5,991,464 zero-error IID shots would be needed for a one-sided 95% bound at that ceiling.

## Status and reproduction

`EXPERIMENT_RESULTS.md`, `FAILURE_ANALYSIS.md`, `LITERATURE_SURVEY.md`, and `FUNDAMENTAL_LIMITS.md` contain scope and limits. Reproduce the exact sample-count calculation with `python3.12 outputs/independent_research_v1/zero_failure_bounds.py`. The BP+LSD fixed-seed development run can be reproduced with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bplsd_feasibility.py`. Reproduce exact-channel importance weighting with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_importance_sampler.py` and its `--replicates 8 --shots 5000` options; crosscheck the direct sampler with `categorical_sampler_crosscheck.py`.

Reproduce the distance-7 known-profile extension with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_alignment_distance7.py`. The fixed-bond MPS screen is `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_truncated.py`.

The detector-only bias estimator and cross-strength checks are reproduced by `bias_identification.py`, `bias_strength_identification.py`, and `bias_binary_cross_strength.py`. The direct frozen-policy validation is `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_end_to_end.py`.

A sample-specific oracle ceiling further limits selector-only proposals for the existing correlation pair. It could choose the correct output on at most 763 uncorrelated-only failures out of 3,532, leaving 2,769 errors, so the observed ceiling is a 21.6% relative reduction. Both modes fail together on those 2,769 samples. A new decoder needs complementary corrections on shared failure cases.
- A 400k-shot actual-ratio10 fault-composition screen found shared failures contained ~1.94 pair-channel faults/shot at d3 and ~4.67 at d5; bias-aligned XX/ZZ events were enriched 5.7–5.8× and 2.28× over both-correct shots. This points toward multi-fault shared-error correction but excludes one-qubit/measurement fault attribution and covers only two conditions per distance. See `shared_failure_fault_mechanism_protocol.md`.
- Dense VE's two-layer stop is representation-specific: exact sparse XOR aggregation solved the final two and three native categorical layers (12/18 locations, 10/12 touched detectors), with independent representation agreement at 1.33e-15/1.22e-15 and 512 forced-fault checks each. These are isolated slices, not a full-circuit decoder; state-space growth remains exponential in detector support. See the `categorical_*_sparse*` artifacts.
- A fourth final layer also passed (24 locations, still 12 touched detectors, 8,192 states, DP/Walsh difference 2.78e-15). This shows favorable locality in that final slice, not full-circuit scaling.
- The fifth-layer preflight hit 18 detectors and a 251.7M conservative transition bound, exceeding its fixed 100M cap, so no posterior expansion ran. Exact sparse work is currently demonstrated through four final layers only.
- A separate vectorized XOR-kernel protocol passed the five-layer state space: 524,288 states, DP/Walsh agreement 3.55e-15, 512 forced-fault checks, ~23MiB, 5.92s. The dictionary stop was implementation-specific. Full-circuit scaling is still untested.
- Exact signature coalescing then passed six layers/36 locations: 576 raw outcomes reduced to 296 signatures; DP/Walsh difference 2.32e-16, 524,288 states, 512 checks, 6.10s. Probability mass is preserved by summing only identical detector/logical signatures. Full-circuit support is still untested.
- Seventh-layer preflight reached 20 detectors/2,097,152 states and stopped at the fixed 1M cap before inference. Current exact vectorized slice limit is six final layers; this is not a bound on other tensor representations.


## New exact tail-inference result

A parity-compressed exact method was tested on the final seven channel layers of a d3 circuit. For each syndrome it tracks total mass P and signed logical mass Z, allowing exact binary logical MAP risk without carrying the logical bit as another state dimension. The 20-detector / 1,048,576-state fragment passed independent Walsh and six-layer joint-distribution checks (<6e-16), plus 512 forced Stim compositions, in 14.5 seconds; its isolated risk is 0.00104093. Artifacts and fixed protocol: `categorical_seven_layer_parity.py`, `_results.json`, and `_protocol.md`. This is a feasibility result for a tail fragment only, not a full-circuit decoder result.


## Pair-cluster importance-sampling result

A development-only proposal grouped adjacent two-qubit channel pairs within each `PAULI_CHANNEL_2` instruction (60 two-location clusters, 256 joint categories) and trained cluster distributions from likelihood-weighted failures. Synthetic instrumentation and weighted estimates validated; all six validation estimates were within 3 combined SE of direct and global tilt. However, its predeclared variance gate passed 0/6: the proposal never reduced SE by 25% versus both baselines in four conditions. Max |log weight| was 17.8–23.7 and biased-condition training failure ESS was about 113–129. Keep the existing global-tilt estimator as the more stable tested method; do not tune the cluster proposal on its validation data. Details: `categorical_cluster_importance_results.json` and its fixed protocol.


## Native-XCX XZZX result

A new finite-distance screen compiled marked-control H-CX-H into native XCX, avoiding the prior extra H targets. Exact tableau conjugations, noiseless detectors, DEMs, fixed noise targets, and equal qubit/detector/round/two-qubit resources passed. Under a stated hypothetical equal-duration/equal-noise CX/XCX/CZ model, 500k shots/cell gave XZZX/CSS LER ratios at d3/d5 of 0.662/0.376 for X-biased noise but 3.86/11.24 for Z-biased noise. This indicates a strong bias-orientation interaction; it is not a universal gain and depends on native-gate noise equivalence. Artifacts: `xzzx_native_xcx.py`, protocol, preflight, and result JSON.


## Complementary XZZX orientation result and decision

A fresh Z-biased d3/d5 screen compared CSS, the original native-XCX checkerboard, and one complementary checkerboard. The complement was 14%/21% better than the original but still had 3.04x/6.16x CSS LER at matched physical resources. Combined with the original orientation helping X-bias but hurting Z-bias, the evidence shows orientation-by-noise dependence but no universal XZZX benefit. Stop this fixed checkerboard family unless a different schedule/noise model or decoder is proposed. This remains conditional on equal CX/XCX/CZ noise/duration. Artifacts: `xzzx_native_orientation.py`, protocol, preflight, results.


## Spatially heterogeneous noise result

A d3 Z-memory X-biased test used two synthetic two-qubit hotspot maps (1.5x/.5x, equal average p=.003) and compared pooled matching with a graph built from the exact local map on the same 200k syndrome rows/profile. Local-minus-pooled LER was +.000035 east-hot (95% paired interval [-.000143,.000213]) and -.000170 west-hot ([-.000336,-.000004]); equal-weight relative reduction was only 0.93%, so the predeclared 10% gate failed. This provides no support for a detector-only spatial selector for this map. Approximate-DEM threshold .003 was applied identically after a no-shot preflight showed .0018 was below the maximum local categorical component. Synthetic stress test only; not hardware calibration. Artifacts: `spatial_noise_decoder.py`, protocol, preflight, result JSON.


## Distance-9 basis-alignment extension

At d9/17 rounds, X-biased ratio10, p=.003, 500k shots/arm yielded one aligned X-memory failure versus 408 mismatched Z-memory failures. Ratio .00245, conditional exact 95% CI [.0000619,.01373]. The point estimate is lower than d7's .00496, but uncertainty is broad and does not support a 10,000-fold claim or scaling law. No extra shots were appended. Artifact/protocol: `basis_alignment_d9_results.json`, `basis_alignment_d9_protocol.md`.


## Biased code-capacity tensor MPS result

With qecsim 1.0b9, `BiasedDepolarizingErrorModel(bias=5, axis='X')` gives a 10:1:1 X:Y:Z ratio. Fixed `PlanarMPSDecoder(chi=16,mode='c')` beat bias-aware `PlanarMWPMDecoder` at d5 on two independent 5k-sample roots: 76 vs 118 failures, then 75 vs 101. At d3 it had 175 vs 191 in the first root (paired CI narrowly below zero) and 182 vs 197 in the second (CI crossed zero). d5 latency was about 31x MWPM. This is code-capacity only. qecsim MPS accepts a perfect planar syndrome; Q-SHIFT requires noisy repeated spacetime detectors and categorical gate faults, so direct application is not information-fair. Keep as a research candidate, but no Q-SHIFT integration or circuit-level claim without a new spacetime tensor algorithm. See `tensor_mps_biased*` artifacts/protocols.


## MPS contraction-mode ablation

Under the same X-biased code-capacity model, qecsim chi16 mode `a` and mode `c` gave exactly identical logical predictions on 5k paired shots at d3 and d5 (zero discordants). Mode a cost ~1.6x/~2x decoding time. No reason to prefer it. The broader MPS code-capacity gain still lacks a repeated-measurement/spacetime interface.


## Exact tail tensor-train audit

Natural detector-order TT-SVD of the exact seven-layer P/Z arrays gave max rank 91 at 1e-10 relative Frobenius error and rank 30 at 1e-6. The preregistered rank<=64 at 1e-10 gate failed, so no MPS prototype followed. This is specific to the stored detector order and tail fragment. Artifact/protocol: `categorical_seven_layer_tt_results.json` and `categorical_seven_layer_tt_protocol.md`.


## d9 rare-event sample budget

The observed d9 mismatched rate was 408/500k=.000816. A 1e-4 relative target corresponds to 8.16e-8 candidate LER; an exact baseline lower endpoint gives a conservative 7.39e-8 target. An optimistic IID calculation requires 36.7M / 40.6M zero-failure shots, or 58.1M / 64.2M shots if one candidate failure occurs. These are single-condition minimum evidence counts and exclude multiplicity/root effects. See `d9_relative_target_sample_budget.json`.


### All-location fault composition screen

## All-location fault composition under ratio-sensitive decoding

The preflight passed synthetic flags for all 15 two-qubit Paulis, all three one-qubit Paulis, and explicit X/Z error events (zero data/flag mismatches). Both d3 conditions had 120 two-qubit pairs and 40 one-qubit locations; explicit measurement targets were 49 for Z-memory/X-biased and 49 total for X-memory/Z-biased. Source and instrumented samples had unchanged 40-detector/one-observable layout, and failure-rate differences were below 1.1 combined standard errors. The 200,000-shot main screen took 3.94 seconds.

At 100,000 shots/condition, ratio-5/ratio-10 models failed on 753/752 Z-memory X-biased shots (61 prediction disagreements) and 769/766 X-memory Z-biased shots (95 disagreements). The both-wrong groups contained 722 and 720 shots; ratio-10-fixes-ratio-5 groups contained 31 and 49, while ratio-10-breaks-ratio-5 contained 30 and 46. In both conditions, mean tracked two-qubit faults were about 0.349 per both-correct shot and 1.87 per both-wrong shot. In the biased Pauli outcome counts, XX was most frequent in the X-biased Z-memory both-wrong group (794 events), while ZZ was most frequent in the Z-biased X-memory both-wrong group (800). One-qubit and explicit measurement-fault counts also differed across outcome groups; see the JSON for full counts.

The decoder-disagreement groups are small, particularly the 30–49-shot fix/break groups. These are conditional fault associations from one fixed development stream, not causal attribution, evidence that one fault channel caused decoding errors, or a hardware noise claim. The new instrumentation extends the earlier two-qubit-only report; it does not change the prior conclusion that raw fault burden alone cannot explain decoder behavior. No sealed or confirmatory data were accessed.


For X-biased ratio-10 memory, compare code proposals against the tested X-aligned CSS configuration, not only a mismatched CSS memory. The d3/d5/d7/d9 point ratios favor alignment, but d9 has only one aligned failure; no asymptotic claim is warranted. See `basis_scaling_synthesis_results.json`.


For X-biased workloads, the native-XCX XZZX comparison must include CSS with X-memory alignment. In the saved d3/d5 streams, native XZZX Z-memory had 3.57x and 13.48x the aligned-CSS LER under matched counted qubit, detector, two-qubit, one-qubit-noise, measurement-target, and tick resources. Existing reported XZZX/CSS results used CSS Z-memory, so qualify them as a same-basis comparison. Native gate equivalence is still assumed, and the streams are unpaired.


A fresh d5 2x2 development screen passed equal-resource gates (500k per cell): CSS-X 79 errors, CSS-Z 1,848, native XZZX-X 604, XZZX-Z 670. XZZX-X/CSS-X=7.65 (95% conditional interval 6.04–9.79); XZZX-Z/CSS-Z=.363 (.331–.396). Practical takeaway: keep CSS-X as the X-bias baseline; XZZX only improves the mismatched CSS-Z task in this model. Native CX/XCX/CZ noise/duration equivalence is assumed, not measured.


For an explicitly equal mix of separate X/Z memory tests, post-hoc pooled failures were 1,274/1,000,000 for XZZX and 1,927/1,000,000 for CSS (rate ratio .661, conditional 95% interval .615–.710). This gives a concrete code-design tradeoff: CSS-X is much better for known X memory; XZZX is more balanced and wins the post-hoc equal-basis mix. The weighting was not predeclared, the streams are simulated, and it is not a full arbitrary-state logical channel.


Independent d5 replication (500k/cell) reproduced the equal-weight separate-memory workload result: XZZX/CSS=.662 (95% conditional interval .616–.710). XZZX-X/CSS-X remained 6.18 (4.96–7.78); CSS X/Z=.0498. If a workload needs equally many separate X and Z memories, evaluate XZZX under an explicitly fixed weighting; if the logical basis is known X, use CSS-X as the current strong configuration. These are simulated development findings, not arbitrary-state or device claims.


A fresh d3/d7 extension found equal-weight separate X/Z memory XZZX/CSS ratios 1.18 (1.13–1.23) and .279 (.239–.325), respectively; the independently replicated d5 ratio was .66. XZZX-Z/CSS-Z improved from .72 at d3 to .17 at d7, while XZZX-X/CSS-X remained worse (3.78 at d3; 12.57 at d7, with only 7 CSS-X failures). This motivates a d9 finite-size check if useful, but does not support asymptotic extrapolation. Keep CSS-X for known X memory; XZZX may suit a balanced separate-basis workload.


The d9 XZZX/CSS factorial produced CSS-X/Z 1/260 failures and XZZX-X/Z 10/18 (500k/cell). Equal-weight separate X/Z task ratio was .107 (95% interval .070–.159); XZZX-Z/CSS-Z=.069, but XZZX-X/CSS-X=10 with a wide interval. This is an 89% aggregate reduction at d9, far from 99.99%, and not an arbitrary-state channel. Recommend only as a workload-specific code-design candidate; require device gate characterization before hardware claims.


At d11, CSS-X and XZZX-X each had 0/500k failures; CSS-Z had 67 and XZZX-Z 3. Equal-weight separate X/Z task rate ratio XZZX/CSS=.0448 (95% interval .0090–.1366), 448x above 1e-4. The run took 281.9s and 2.69 GiB. This supports a finite-size balanced-workload tradeoff but leaves X-memory comparison unresolved and is not arbitrary-state or hardware evidence. The next distance may exceed the 300s screen; do not launch without a preflight.


The d11 equal-weight CSS point LER .000067 implies candidate target 6.7e-9 for 10,000x reduction. The XZZX point is 3e-6 (about448x above). Optimistic one-sided IID evidence alone would take ~447M zero-failure candidate shots (or708M with one), before baseline uncertainty/roots/model-selection. A genuinely lower-rate mechanism is needed before a huge run is useful.


The d13 preflight passed structural checks but projected 454.7s for 500k per cell, above the 300s cap; no d13 main data exist. The current full factorial runtime envelope ends at d11. Any d13 follow-up needs a prospectively designed streaming/faster decode or a high-efficiency estimator, not post-hoc reduction of shots.


At d7/13 rounds/p=.003 the equal-weight separate X/Z XZZX/CSS ratios were .853 at 2:1 bias (95% interval .736–.988), .608 at 5:1 (.529–.697), and .279 at 10:1 (.239–.325). At 2:1, XZZX-X/CSS-X=1.44 and XZZX-Z/CSS-Z=.60. This shows a bias-dependent workload tradeoff; it is not a single universal code recommendation. Hardware gate equivalence remains unverified.


At d7, the 5:1 robustness screen gave CSS-X/Z 27/526 and XZZX-X/Z 158/178 failures (500k/cell). Equal-mix XZZX/CSS=.608 (95% interval .529–.697); XZZX-X/CSS-X=5.85 and XZZX-Z/CSS-Z=.338. Combined with 2:1=.853 and 10:1=.279, this supports a bias-strength interaction. It remains simulator-only with unverified gate equivalence.

## Latest independent throughput checks

The d13 bit-packed sampler and PyMatching batch API matched ordinary samples and predictions exactly, but projected 358s for the fixed four-cell main vs the 300s gate; no main was run. A separate Fusion Blossom 0.2.13 custom graph screen had zero mismatch vs ordinary PyMatching MWPM on 1,000 d3 samples, but serial decoding throughput was only 6.5–15.3% of PyMatching. Artifacts and reproduction commands are in `outputs/independent_research_v1/` (`xzzx_d13_bitpacked*`, `fusion_blossom_d3_screen*`). These are development-only, do not address correlated matching, and make no hardware gate-equivalence claim.

## Exact-tail ordering challenge

A hash-verified min-fill order on the 20-detector seven-layer exact posterior increased max P/Z ranks at 1e-10 from 91 to 151/150. No alternative ordering was tested. Artifact/protocol: `categorical_seven_layer_minfill_results.json` and `categorical_seven_layer_minfill_protocol.md`.

## Sequential detector-only calibration lead

The frozen-feature Gaussian SPRT was independently validated at ~4% X/Z profile-selection errors using a mean 24.83 detector-only calibration shots. On fresh d3 logical streams it reduced equal-weight separate-memory LER to .001386 from .004198 static Z, but calibration every 100 logical attempts reduced correct-output yield to .800. Reusing the decision for a stable 100k-attempt job gives a bootstrap plug-in yield .998403 vs .995802 static Z (difference CI [.002425,.002781]); this assumes no profile drift and is not a direct 100k run. Next useful challenge: withheld noise-composition mismatch and actual profile change, plus direct cost at realistic reuse horizons. X/Z terminal readout/fault-axis differences remain. See `adaptive_basis_sprt_*` artifacts.

### Robustness caveat for the sequential profile lead

At measurement p=.006 with gate p=.003, the frozen nominal SPRT made 17.6% Z-profile errors. A fresh pooled-variance SPRT still made 12.0%, failing the preregistered gate; fixed 100-shot LDA scored better in one stream but is not independently verified. This rejects general robustness and prevents treating the 100k stable-profile utility projection as deployable guidance. Artifacts: `adaptive_basis_sprt_measurement_shift_*` and `adaptive_basis_sprt_common_variance_*`.
