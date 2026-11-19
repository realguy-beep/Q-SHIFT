# Research recommendations

## Current ranking

1. **Keep dense VE stopped; exact coalesced signature inference is a bounded-fragment tool.** It solved six final layers/36 locations/18 detectors in6.1s, but a seventh layer reached20 detectors and exceeded the 1M-state cap. Full-circuit support is untested and likely requires a different structured representation; do not extrapolate isolated-fragment MAP risks.
2. **Treat the d3 round-count result as a duration/resource frontier.** Three rounds reduced per-attempt LER and used 40% fewer two-qubit pairs than five rounds, but it also stores the state for less time. A next comparison should match elapsed storage time and explicitly model idle errors before recommending fewer rounds.
3. **Keep bias-strength mismatch as a distance-specific question.** The fresh d3 validation favored assumed ratio10 over ratio5, but the d5 comparison was near-neutral. A deterministic graph audit found the same topology and similar weight perturbation at both distances, so no mechanism is established for the different LER result. Do not infer a size-independent ratio10 setting; any next study should focus on syndrome/decision interactions before proposing adaptation or defaults.
4. **Do not expect a ratio5/10 selector to deliver large LER gains by itself.** On the replayed samples, even an oracle choosing the right output for every syndrome where the two matchers disagree could improve on the best fixed model by at most 4.7% at d3 and 6.9% at d5. This is sample-specific, but it makes this two-model selector a low-priority route toward the 10,000-fold target; a useful new decoder must correct failures shared by both models.
5. **Audit rather than repeat BP+OSD claims.** The expedition brief reports a 1.2-million-shot Stage S screen with min-sum 0.9 worse and OSD_CS-40 plus BP-200 near neutral, but the records are not present in published `main`. Do not run a near-identical parameter sweep. First obtain an independent, authorized source for the exact method/configuration from a checkout already permitted for research.
6. **Do not add an adaptive wrapper to the current bank.** Q-SHIFT's Phase 4C comparison, Phase 5 work, correlation pilot, and uncertainty-selection study do not show that an adaptive policy beats a strong fixed baseline by a robust practically important margin.
7. **Separate decoder and code changes.** If future work seeks an operating map or XZZX comparison, declare physical qubit, round, and runtime budgets and call it code/circuit co-design. Existing d=3/5/7 headroom work does not constitute a threshold estimate.
8. **Treat 99.99% as a distant statistical target.** At LER baseline 0.005, the target is 5e-7. About 6 million independent zero-error candidate shots are required just to put a one-sided 95% IID bound at that target. Root clustering, multiple conditions, model selection, and baseline uncertainty increase the evidence requirement.

## Do not advance

Do not advance the current categorical Bethe prototype, claim the correlation pilot proves broad superiority, describe a finite d=3/5/7 screening as a threshold, or claim that Stage S data were locally verified. Confirmatory testing requires separate authorization and a newly frozen protocol.

## Remaining unknowns

- Whether a structured native-categorical factor graph can scale beyond tiny exactly enumerable circuits with calibrated posterior error.
- Which physical fault mechanisms explain the correlation-mode heterogeneity.
- Whether a practical noise-profile selector can predict incremental logical utility under causal, detector-only inputs. Existing selection evidence is discouraging.
- Whether larger-distance code/circuit design can approach the ratio target under a matched resource budget. No current evidence answers this.

The existing correlation pilot also puts a sharp empirical ceiling on selector-only work: a label-aware oracle choosing between its two outputs could reduce the uncorrelated baseline's 3,532 errors by at most 763 (21.6% relative) on the 720,000 observed development shots. Both modes remain wrong together on 2,769 samples. A useful new decoder would need complementary predictions that correct those shared failure cases; a more elaborate controller over the same pair cannot achieve the aspirational 99.99% reduction in this sample.

The new BP+LSD distance-3 screen is a negative signal: the tested LDPC 2.4.1 settings lost to correlation-enabled PyMatching on all six conditions (321 vs 138 failures total), despite returning valid syndromes. Do not respond with a parameter sweep on the same inspected samples. Any further BP+LSD study should first identify a specific model/inference mismatch, predeclare a changed mechanism, and use fresh development seeds; confirmatory claims still require separate authorization.


The exact categorical importance sampler has been implemented and independently checked against raw Stim circuit sampling. The likelihood ratio is valid, but a uniform fivefold tilt does not reliably lower overall estimator variance: the 16-replicate macro SD was 12% higher, with pronounced condition dependence. Treat it as a correct weighting framework, not an efficiency result. A useful next study needs a prospectively derived proposal that targets rare logical failures without extreme weights, then a fresh independent variance comparison.

The cross-entropy product proposal was a principled way to use failure-conditioned categorical marginals, but it failed the independent validation gate in all six conditions and sometimes had very low failure ESS. Do not tune its shrinkage or proposal values on the inspected validation data. A next rare-event method should model joint progress or fault clusters, not only independent per-location marginals, and must retain independent validation.

Under a known stable Pauli bias, memory-basis alignment is a low-overhead baseline worth preserving: these matched distance-3 circuits show 5×–11× LER reductions without changing the qubit, detector, round, or error-rate budget. It is established bias-aware code configuration, not an adaptive result. Any dynamic controller should be compared against the correct fixed aligned basis and include the cost and error of estimating a changing bias.

The d=5 screen points in the same direction at matched distance-5 resources, with 36×–45× lower observed LER for the aligned memory basis in the biased profiles. The aligned cells had only six failures each, so treat the absolute-rate estimate as coarse. A d=7 extension found the same direction with 5 and 3 aligned failures against 1,009 and 1,227 mismatched failures in 500,000 shots per cell. This strengthens the fixed-profile code-design result but still gives sparse aligned counts and cannot support a threshold or scaling-law fit.

The intermediate-bias screen shows a fixed aligned memory basis can be worthwhile by a 2:1 bias ratio in these distance-3 circuits, and the measured benefit grows at 5:1 and 10:1. This narrows the static configuration evidence without locating an exact switch point. A runtime adaptation policy still needs to beat a calibrated fixed basis using a noise estimate available before each memory run, with estimation latency and error included.
# Bounded-bond tensor decoding

Keep χ=16 planar MPS as a promising research candidate: on paired qecsim IID depolarizing code-capacity samples at p=.05 it reduced LER relative to qecsim MWPM at d=3 and d=5, with all recoveries valid. The d=5 decoder cost was roughly 13.7 ms/sample (about 27x its MWPM comparator), so it is not yet a plausible drop-in real-time decoder. Do not transfer this gain to Q-SHIFT's noisy repeated-measurement circuits. The next useful experiment is a small, fixed-parameter circuit-level compatibility study against correlation-enabled matching, preceded by a check that the MPS method represents the same circuit noise and detector information. This is higher value than tuning χ on the current code-capacity sample.

The straightforward checkerboard-H XZZX circuit transform should not advance under the tested gate-noise model: it adds substantial single-qubit H noise and raised LER in every d3/d5 biased cell. A hardware-native XZZX schedule could avoid that overhead, but it needs a separate gate decomposition and physical noise budget before testing.

# Detector-only bias selection

The strongest new adaptive candidate is a very small detector-only classifier that estimates the sign of an X/Z Pauli bias before a separate logical-memory run. A binary LDA trained only on d=3, ratio-10 synthetic calibration streams retained direction accuracy across d=3,5,7 and ratios 2,5,10. At d=3, a direct independent-stream experiment with 500 calibration shots and equal X/Z profile weights reduced LER 16.6% versus fixed Z at ratio 2, 52.4% at ratio 5, and 71.7% at ratio 10. The same run matched the known-profile oracle at ratios 5 and 10. A model-based alternating-profile replay found no tested schedule beat the best fixed basis on correct outputs per total circuit shot at dwell times up to 10,000 logical shots; at 100,000-shot dwell, best tested ratio-5/10 schedules exceeded it by only about 0.10%/0.21%. Treat those as plug-in projections, not change-point evidence. This is development evidence on the exact simulator's finite profile family, not hardware or arbitrary-state memory. The separate balanced-vs-biased classifier was much less reliable at intermediate bias, so a direction selector should not be advertised as a bias-magnitude detector.

This basis selector changes which logical observable is prepared and scored. Use it only when the workload can choose the logical basis before encoding; it does not demonstrate improved arbitrary-qubit memory. A same-Z-observable test of detector-selected profile matching graphs found 775 versus 779 errors against a pooled static graph in 200,000 shots, with no resolved difference. Accurate noise labels did not translate into a meaningful decoder gain in that condition. Keep code-basis selection and decoder selection as separate claims.

Next, if adaptation is pursued, evaluate a causal change-point controller against static and periodic baselines in a new frozen protocol, with equal total resources and uncertainty propagated. The current temporal replay is a scenario calculation, not a change-point experiment. Keep the classifier frozen and do not integrate based on current development results alone.

One limited robustness check now doubles gate and measurement p after nominal-rate calibration while preserving X/Z bias direction. The frozen selector retained 12.2%, 50.6%, and 71.0% LER reduction versus static Z at ratios 2, 5, and 10. This supports robustness to total-rate change for a stable direction in the simulator. A plug-in alternating-profile replay found no throughput gain through 10,000-shot dwell and only 0.10%–0.21% at ratio5/10 with 100,000-shot dwell. Direction changes, spatially varying noise, device calibration, and uncertainty in long-run cost remain unresolved.

An exploratory rescore using calibration prefixes of 25/100/500 shots per 100 logical shots showed reductions versus static Z of 5.1/11.6/16.6% at ratio2, 27.8/49.6/52.4% at ratio5, and 57.5/71.2/71.7% at ratio10. The 25-shot ratio2 interval included zero. Use this only to design a future frozen budget tradeoff; the nested prefix analysis is correlated and not the primary endpoint.

The direct experiment uses 500 calibration circuits per 100 logical circuits. If calibration circuits cannot carry useful logical output, a simple correct-output-per-circuit-shot calculation requires calibration reuse over roughly 169k–618k logical shots, depending on bias, before this selector beats static Z on throughput. This plug-in calculation assumes stable noise for the full horizon; no such stability has been shown. Future work should define the operational objective (LER per logical attempt versus correct-output throughput), account for reusable calibration, and measure how quickly bias direction drifts.



# Exact logical-parity contraction

The new P/Z syndrome representation extends exact categorical tail inference from six to seven final channel layers while preserving all logical posterior information. The d3 tail used 14.5s and matched independent Walsh inference and the prior joint six-layer reference below 6e-16; all 512 forced Stim checks passed. Keep it as an exact-prototype tool for investigating local posterior contributions. Do not present its 0.00104 tail MAP risk as circuit-level LER or infer a global decoder gain. Extending it to the full circuit still faces exponential detector support and requires a new bounded plan.


# Pair-cluster rare-event estimation

Do not advance the fixed adjacent-pair cluster proposal: it passed its estimator-compatibility checks but its efficiency gate was 0/6. Validation max |log weight| reached 23.7, and biased-condition training failure ESS was near 100. Avoid tuning the proposal against the inspected validation streams. Any future rare-event method should model broader failure progress or use a separate prospectively derived structure, then pass fresh independent validation before any efficiency claim.


# Native-gate XZZX

The native-XCX follow-up removes the extra H-noise cost of the earlier transpilation and passes exact Clifford/resource checks. Keep this as conditional code-design evidence: under equal native entangler noise, the fixed checkerboard orientation helped X-biased noise at d3/d5 (0.66/0.38 of CSS LER) and hurt Z-biased noise (3.86/11.24 times CSS). Do not recommend XZZX as a universal replacement. A narrowly scoped complementary-orientation test may resolve whether this is primarily orientation matching; hardware claims require measured XCX/CZ error rates and durations.


The only preregistered complementary checkerboard test improved the original XZZX orientation for Z-biased noise but still lost to CSS by factors 3.04 at d3 and 6.16 at d5. Stop this checkerboard family at these fixed schedules. Do not run more pattern sweeps on these conditions; any future XZZX work should start from a different native schedule/noise model or decoder mechanism. Native CX/XCX/CZ equal-noise assumptions must be replaced with measured hardware characterization before deployment claims.


Do not advance a detector-only east/west hotspot selector from the tested model: the true-map local graph reduced macro LER by only 0.9%, missed its 10% gate, and slightly harmed the east-hot profile. A stronger or hardware-calibrated spatial mismatch would need independent motivation before new experiments.


A d9 basis-alignment extension kept the same matched circuit/resources but observed only one aligned failure in 500k shots. Its ratio interval [.0000619,.01373] cannot certify a 10,000-fold gain or a scaling trend. Treat d3–d9 as finite-size known-profile configuration evidence, not threshold data. Any larger-distance study needs an explicit shot/runtime plan and independent-root replication; do not append shots to this already inspected stream.


The fixed chi=16 MPS result is worth keeping as a biased code-capacity direction: d5 improved in both 5k independent roots, while d3 was less certain. Do not integrate it into Q-SHIFT based on this evidence. qecsim's decoder consumes perfect planar syndromes and cannot use Q-SHIFT's repeated spacetime detector record; a circuit-compatible tensor decoder would need an explicit temporal contraction model and an equal-information baseline. Its d5 latency is already about 31x bias-aware MWPM.


The qecsim averaged row/column MPS mode produced exactly the same predictions as column mode at both distances and cost about twice as much at d5. Do not advance mode a or tune contraction settings for this sample. Any tensor follow-up should address the missing spacetime detector structure directly.


The natural detector-order exact tensor-train audit missed its rank-64/1e-10 gate (max rank 91). Do not build an exact-fidelity MPS prototype from this tensor ordering. A lower-rank 1e-6 approximation is only a future hypothesis and would need a new protocol with direct risk/error calibration against the exact fragment before any circuit-scale use.


At the d9 mismatched baseline, the aspirational 1e-4 relative rate corresponds to candidate LER 8.16e-08. The one-failure exact evidence budget is already about 58,135,593 IID shots in one condition, before roots or multiplicity. Do not treat a zero count in a few hundred thousand shots as evidence for the target.


## All-location fault composition under ratio-sensitive decoding

The preflight passed synthetic flags for all 15 two-qubit Paulis, all three one-qubit Paulis, and explicit X/Z error events (zero data/flag mismatches). Both d3 conditions had 120 two-qubit pairs and 40 one-qubit locations; explicit measurement targets were 49 for Z-memory/X-biased and 49 total for X-memory/Z-biased. Source and instrumented samples had unchanged 40-detector/one-observable layout, and failure-rate differences were below 1.1 combined standard errors. The 200,000-shot main screen took 3.73 seconds.

At 100,000 shots/condition, ratio-5/ratio-10 models failed on 753/752 Z-memory X-biased shots (61 prediction disagreements) and 769/766 X-memory Z-biased shots (95 disagreements). The both-wrong groups contained 722 and 720 shots; ratio-10-fixes-ratio-5 groups contained 31 and 49, while ratio-10-breaks-ratio-5 contained 30 and 46. In both conditions, mean tracked two-qubit faults were about 0.349 per both-correct shot and 1.87 per both-wrong shot. In the biased Pauli outcome counts, XX was most frequent in the X-biased Z-memory both-wrong group (794 events), while ZZ was most frequent in the Z-biased X-memory both-wrong group (800). One-qubit and explicit measurement-fault counts also differed across outcome groups; see the JSON for full counts.

The decoder-disagreement groups are small, particularly the 30–49-shot fix/break groups. These are conditional fault associations from one fixed development stream, not causal attribution, evidence that one fault channel caused decoding errors, or a hardware noise claim. The new instrumentation extends the earlier two-qubit-only report; it does not change the prior conclusion that raw fault burden alone cannot explain decoder behavior. No sealed or confirmatory data were accessed.


For fixed known X bias, preserve memory-basis alignment as the strongest tested code-configuration baseline. The d3–d9 synthesis suggests rapidly improving finite-size ratios, but sparse aligned counts and distance-round confounding rule out a scaling claim. Any future code comparison must use aligned CSS as a strong baseline and report matched physical-qubit/round resources.


Revise the X-bias code-design baseline: use X-aligned CSS as the static comparator before considering XZZX. The reported XZZX improvement over CSS Z-memory is real for that memory task, but the aligned CSS stream was better at both tested distances. Do not promote XZZX from this evidence.


The fresh d5 factorial confirms the strongest tested X-bias memory choice is CSS-X among these cells. Keep XZZX as a possible Z-memory improvement over CSS-Z under the stated native-gate model, but do not recommend it over aligned CSS for X-biased memory.


Workload matters: choose CSS-X for a known X-memory workload. If X- and Z-memory tasks are separately requested with equal weight, this d5 screen's post-hoc average favors XZZX by 34%; that is worth a fresh prospectively weighted replication only if such a workload is operationally relevant. Do not call this arbitrary-state logical-qubit performance.


The d5 equal-weight X/Z memory-task tradeoff is now reproduced on an independent development stream: XZZX/CSS=.662. This justifies keeping XZZX for a prospectively specified balanced-basis workload study, while preserving CSS-X as the baseline for known X-memory workloads. Hardware gate equivalence and arbitrary-state performance remain open.


The equal-weight X/Z memory-task tradeoff merits one larger finite-size check: d3 favored CSS, d5/d7 favored XZZX increasingly. Continue to label this as separate memory tasks. Use aligned CSS-X for a known X-memory workload. Do not extrapolate the d7 result or drop the gate-equivalence caveat.


A fresh d9 screen supports a balanced separate-basis XZZX/CSS tradeoff through d9 (aggregate ratio .107), but the improvement is driven by Z memory and CSS-X remains better for known X memory. Treat this as a task-mix design option under an unverified gate assumption; do not claim it approaches the 10,000-fold target.


The balanced separate-memory trend continues through d11 (point ratio .0448), but the exact interval is broad and X-memory comparisons are zero-failure. Treat this as a promising code-design tradeoff for that task mix, not a 10,000-fold result. d11 already approaches the per-run 300s limit; any larger-distance plan needs a fresh feasibility gate and should not assume runtime scales linearly.


Do not scale the d11 XZZX run just to narrow a relative-rate interval around a point rate 448x above the target. Progress toward 10,000-fold reduction requires a mechanism that lowers the rate, plus very large independent evidence; ordinary extra sampling alone is not a path to the target.


Do not pursue d13 with the current 500k-per-cell four-circuit batch under a 300s cap; it projects 455s. The balanced code-design sweep should pause at d11 until a faster or more sample-efficient method is justified. Focus next on a different research family or a concrete decoder acceleration hypothesis.


The d7 two-basis screen supports a bias-dependent configuration choice: at 2:1, XZZX has only a 15% equal-mix point advantage and is worse for X memory; at 5:1/10:1 the average gains are larger. Keep CSS-X as the known-X-memory baseline. Any operating rule needs a predeclared workload mix and measured gate-family calibration.


At d7 and 5:1 bias, XZZX's equal-mix point gain is 39%, but XZZX-X remains 5.85x worse than CSS-X. Preserve an axis-specific decision rule and require the actual workload mix before considering an XZZX deployment.

The d13 bit-packed Stim/PyMatching route preserved predictions but still projected above the fixed runtime cap. Fusion Blossom's serial custom-graph route was successfully wired, then rejected as a runtime candidate after measuring 6.5–15.3% of PyMatching throughput on d3. Keep both as documented negative scalability evidence; do not elevate either to a deployment recommendation.

The graph-derived min-fill detector ordering worsened exact-tail TT ranks (151/150 vs 91 natural-order). Do not spend effort implementing an exact MPS for this ordering; any new ordering strategy needs independent structural justification and a prospective protocol that reports all evaluated orders.

Sequential calibration is a promising efficiency refinement for the already tested two-profile detector-only selector: at about 25 shots it achieved ~4% profile classification error and reduced LER on the equal-weight separate-memory simulator task. It does not improve the static decoder itself and loses throughput when recalibrated every 100 attempts. The only positive throughput evidence is a stable-profile 100k-dwell bootstrap projection, not a direct long-dwell or change-point measurement. Do not recommend deployment until an independent stable-duration test and a deliberately shifted/noisy calibration robustness study pass, with actual X/Z gate/readout noise characterized.

The sequential calibration lead is fragile to noise composition. Doubling measurement p at fixed gate p raised nominal Gaussian-SPRT Z-profile error to 17.6%; a pooled-variance redesign still had 12.0% error. Keep the method scoped to the nominal simulator profile. A fixed 100-shot LDA prefix was better in this stress sample, but requires independent replication before any robustness claim.

Reject the tested Gaussian CUSUM for profile switching: it detects changes quickly but false-switches too often even under nominal stable noise. Robust adaptation remains unresolved; retain static or periodically calibrated baselines until a detector passes independent false-switch and cost tests under both nominal and shifted profiles.

Do not use the single shortest graphlike pattern as a practical error-floor estimate: its lower bound is 10–12 orders below measured development LER. A meaningful floor calculation needs degenerate mechanism multiplicity or logical-class posterior mass. Avoid repeating this representative-path analysis across larger distances without a multiplicity method.


## Round-wise rate heterogeneity follow-up

The exact temporal-map decoder reduced LER by 2.84% on two reversed synthetic round-rate profiles, below the 10% advancement gate. Although compute overhead was only 2–4%, any causal estimator and switching policy would add cost. Keep the result as a robustness characterization; do not build an online selector for this pattern unless a realistic measured profile or a concrete mechanism predicts materially larger gains.


## Equal-duration syndrome schedule

A first matched-duration d3 screen favored three active rounds plus two data-idle cycles over five active rounds (macro cell RR=.762 on two aligned workloads). Preserve as a candidate, not yet as guidance: replicate with fresh roots and explicitly limit interpretation to the assumed biased idle channel. The model used p=.003 per idle cycle on data qubits and gave the shorter arm 42 total one-qubit targets versus 40 in the five-round arm.


### Equal-duration schedule replication

The fresh independent seed stream preserved the effect direction and macro result (mean cell RR=.773); the Z-aligned cell was stronger (.641, 95% .570–.721), while X alignment was near-neutral (.906, .809–1.014). Keep as a promising finite-distance code/circuit design candidate. Before a handoff recommendation, vary only the assumed idle channel in one predeclared robustness stress; do not expand round counts or profiles.


### Equal-duration idle-model robustness decision

The twofold idle-noise challenge fails the preregistered across-cell robustness gate. Retain only as a Z-aligned d3 simulator lead (RR=.753, 95% .676–.839); X alignment was near-neutral/slightly worse (RR=1.016, .914–1.129). Do not recommend three-plus-idle for both workloads or invest in an online schedule selector without a measured idle model and explicit task mix.


### Distance-5 schedule result

Do not scale the d3 three-plus-idle result into a general schedule recommendation. At d5 Z alignment the five-plus-idle schedule was statistically inconclusive around parity (RR=1.05, 95% .83–1.33) and excludes a 20% or larger gain. The candidate has no demonstrated distance-5 benefit under this idle model.


### D5 schedule branch stop

The targeted seven-round d5 screen was inconclusive and failed its frozen gate (RR=.843, 95% .674–1.056). Stop round-count exploration at d5; no tested shorter-active schedule passes a robust evidence gate. The d3 result remains model- and distance-specific.


## Selective escalation lead

A fixed disagreement-triggered BP+LSD hybrid reduced macro LER by 14.3% on one 600k-shot d3 stream, with zero invalid escalated syndromes, but took 8.44x the correlation-enabled matcher even though only 0.26% of cases escalated. It fails the frozen runtime gate. Preserve as a possible ambiguity signal for a faster local solver; do not integrate this BP+LSD implementation. Fresh efficacy replication is pending, but it cannot change the current cost rejection.


### Selective escalation replication decision

Two independent streams show 13%–14% macro LER reduction when disagreements between correlated and ordinary matching are routed to BP+LSD. Both streams also show 8.2–8.4x decode cost. Keep the flag as a potentially useful ambiguity signal; reject the present BP+LSD escalation for practical integration. Any faster replacement is a distinct algorithm requiring fresh validation.


## Replicated fast disagreement-subset selector

This is the strongest current low-cost decoder lead: fixed correlated/ordinary matching disagreement flags under 0.6% of samples; a per-condition L2 logistic model trained on those flagged detector syndromes lowered macro LER 16%–17% on two independent held-out streams at 1.35x–1.36x decode time. It beats the same-stream BP+LSD escalator on five of six cells while avoiding its ~8.3x cost. Advance only to a predeclared model-shift robustness challenge and then distance transfer if robust. It is established supervised meta-decoding methodology, not a novelty claim, and no confirmatory evaluation is authorized.


### Fast learned selector after measurement-shift replication

Retain as the strongest current low-cost decoder development lead. Two independent fresh streams show the frozen nominal selector continues to improve macro LER by ~13% when measurement p doubles from .003 to .006, at ~1.35x inference cost. This supports a narrow robustness statement for the tested six d3 simulator conditions. The next useful extension is a prospective distance-transfer feasibility screen that checks feature/model geometry and runtime before sampling; do not assume d3 coefficients transfer, and do not claim broad robustness or deployment readiness. No confirmatory evaluation is authorized. See `../independent_research_v2/fast_flagged_logistic_measurement_shift_report.md`.


### Selector distance-scaling recommendation

The distance-specific d5 fit failed: held-out macro LER worsened 1.35%, and only two of six cells improved, although cost was 1.38x. Do not invest in a replication or describe the d3 selector as scalable to d5. Retain only the bounded d3 simulator lead and its one tested measurement shift. A new d5 algorithm would require a new prospective method and gate, not tuning this failed validation result.


### Selector robustness after second shift challenge

The frozen d3 selector now has two independently replicated single-axis simulator shift results: measurement p .003→.006 and bias ratio 10→5, each with ~13% and ~18% macro gains, respectively, at ~1.35x cost. This supports further bounded d3 study, not broad distributional robustness. The failed d5 screen remains a hard scope boundary. A useful next step would be a predeclared combined shift only if its operating profile is justified; do not extrapolate the two separate shifts to simultaneous mismatch or hardware.


### Combined-shift evidence

The frozen d3 selector also passed one predeclared combined measurement/bias shift on two streams (~14% macro reduction at ~1.35x cost). This is a stronger bounded robustness result than separate-axis evidence alone, but it remains one tested simulator composition and does not generalize to arbitrary drift or hardware. Keep claims scoped to these d3 conditions and shifts; preserve the d5 transfer failure as the distance boundary.


### Shared versus specialized selector

A single pooled d3 selector is a viable lower-complexity option: it passed the same baseline gate on two streams, but specialized per-condition models were measurably better by ~.00010 macro LER on the same validation samples. Keep both design choices explicit; use specialized models when accuracy is primary, and consider pooling only when one model bank is operationally preferable and the observed penalty is acceptable. No noninferiority criterion was set.


### Relative-choice formulation

Keep as a compact interpretable variant, not the preferred accuracy candidate. It passed the base gate twice, but gave up ~.00014 macro LER versus shared absolute-bit selection and ~.00022 versus specialized selection; one cell was near-neutral. Prefer absolute-bit/specialized models when minimizing errors is primary.


### Relative-choice transfer scope

A model trained on two of the three d3 Pauli regimes transferred to the excluded regime when that regime's matching graphs were available, with positive gains in every fold on two streams. This may reduce selector-label requirements across known profile families, but does not support unknown-profile graph selection. All-profile and specialized models are more accurate; d5 transfer remains unproven and was negative.


### Basis transfer limitation

Do not deploy a relative-choice classifier trained on one logical memory basis to the other: the leave-one-basis-out screen worsened macro LER and violated the per-cell gate. The positive leave-one-profile-out result only applies when the target basis was represented in training and its matching graph is profile-matched.


### Static bias-strength range

The fixed d3 selector has now passed ratio 5, ratio 2, and a ratio-5 plus doubled-measurement joint shift. These support a bounded stationary Pauli-composition range. Do not extrapolate to time-varying or unknown matcher graphs; cross-basis transfer and d5 transfer failed.


### Static isotropic limit

The ratio-10 frozen selector also performed well when physical channels became isotropic at ratio 1. This is a useful stationary composition boundary point, not evidence for time-varying noise or an unknown matcher graph. Preserve the basis and d5 failures in any summary.


### Gate-rate shift limitation

Do not include doubled gate noise in the selector's positive robustness envelope: the initial 10.01% gain narrowly passed, but independent replication was 9.95% and failed the fixed utility gate. The effect is real by paired error comparison but misses the practical threshold. No extra shots were taken.


### Gate-rate robustness remains asymmetric

A half-rate shift is strongly positive, but a double-rate shift misses the frozen utility gate on replication by 0.05 point. Do not include doubled gate noise in the validated envelope and do not generalize from the half-rate result.


### Measurement-rate range

Both tested stationary measurement-rate shifts (half and double) passed. Keep that as a narrow d3 robustness statement. It does not imply tolerance to time-varying measurement noise, detector correlations, or unknown profile graphs; the doubled gate-rate challenge remains borderline.


### Temporal-rate evidence

A fixed selector transferred to one alternating five-round gate-rate pattern on Z-memory/X-bias. Preserve it as a narrow development lead only; do not claim online rate estimation or arbitrary drift robustness. A broader temporal study needs a concrete measured pattern and must retain the other task limits.


### Two tested temporal maps

The selector passed alternating and blockwise five-round rate patterns for Z-memory/X-bias d3. Retain as a simulator lead only; a next step needs a real operating time profile and explicit online-policy objective. Do not generalize to arbitrary temporal drift or other bases.


### Temporal task scope

Do not recommend the selector for temporal gate-rate variation across both logical tasks. The same pattern passed for Z-memory/X-bias but missed the aggregate gate when X-memory/Z-bias was included. Any further temporal work should name the task explicitly and have an application-specific task mix.


### Training budget for the fast selector

Use 1M training shots per condition as the evidenced setting. A nested 100k budget produced fewer than 100 flagged rows in X-memory/X-biased and stopped at fit readiness. Partial validation from the first three cells was discarded; no accuracy comparison is available. Do not reduce the training budget based on this screen.


### Selector training budget updated by independent evidence

Use 500k labeled training shots per d3 condition as a supported alternative to 1M: two fresh validation streams passed the fixed utility, harm, retention, and runtime gates. Do not lower to 100k based on the current evidence; that prefix failed the training-readiness minimum in one condition. No d5 training-volume claim.


### Sequential adaptation update

Do not deploy the tested Gaussian or histogram-likelihood CUSUMs: both were too prone to false switching. The histogram variant retained 19–28-shot transition detection but exceeded stable false-switch limits by large factors. Periodic 100-shot LDA was quieter in this screen, but still has a nonzero shifted false-switch rate and calibration cost. No logical utility or hardware conclusion follows.


### Sequential calibration threshold remains unproven

The frozen h=8.595 met limits on two validation streams, but fresh re-estimation of h missed the shifted-Z false-switch gate. Do not claim a robustly calibrated adaptive controller. Any future hardware-directed work needs a prospective, broader calibration envelope and separate utility/overhead validation.


### Nonlinear selector prototype

Do not advance the tested 8-unit MLP: it failed optimizer readiness before validation. Keep logistic regression as the evidenced selector. Any future neural candidate needs a separately predeclared optimizer and convergence feasibility gate.
