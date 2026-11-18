# Research recommendations

## Current ranking

1. **Resolve the native categorical inference path at toy scale.** The exact-vs-approximate DEM mechanism follow-up cannot use a non-approximated DEM for the Phase 2B categorical circuit. Exact enumeration already validates tiny toys but full d=3 brute force is infeasible. The new loopy Bethe prototype failed one exact toy and must not proceed to the circuit. A revised region-graph or variable-elimination method should pass exact posterior agreement on multiple graphs and report intermediate-state width before any larger use.
2. **Audit rather than repeat BP+OSD claims.** The expedition brief reports a 1.2-million-shot Stage S screen with min-sum 0.9 worse and OSD_CS-40 plus BP-200 near neutral, but the records are not present in published `main`. Do not run a near-identical parameter sweep. First obtain an independent, authorized source for the exact method/configuration from a checkout already permitted for research.
3. **Do not add an adaptive wrapper to the current bank.** Q-SHIFT's Phase 4C comparison, Phase 5 work, correlation pilot, and uncertainty-selection study do not show that an adaptive policy beats a strong fixed baseline by a robust practically important margin.
4. **Separate decoder and code changes.** If future work seeks an operating map or XZZX comparison, declare physical qubit, round, and runtime budgets and call it code/circuit co-design. Existing d=3/5/7 headroom work does not constitute a threshold estimate.
5. **Treat 99.99% as a distant statistical target.** At LER baseline 0.005, the target is 5e-7. About 6 million independent zero-error candidate shots are required just to put a one-sided 95% IID upper bound at that target. Root clustering, multiple conditions, model selection, and baseline uncertainty increase the evidence requirement.

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

The strongest new adaptive candidate is a very small detector-only classifier that estimates the sign of an X/Z Pauli bias before a separate logical-memory run. A binary LDA trained only on d=3, ratio-10 synthetic calibration streams retained direction accuracy across d=3,5,7 and ratios 2,5,10. At d=3, a direct independent-stream experiment with 500 calibration shots and equal X/Z profile weights reduced LER 16.6% versus fixed Z at ratio 2, 52.4% at ratio 5, and 71.7% at ratio 10. The same run matched the known-profile oracle at ratios 5 and 10. This is development evidence on the exact simulator's stationary noise families; it does not address drift or hardware model shift. The separate balanced-vs-biased classifier was much less reliable at intermediate bias, so a direction selector should not be advertised as a bias-magnitude detector.

This basis selector changes which logical observable is prepared and scored. Use it only when the workload can choose the logical basis before encoding; it does not demonstrate improved arbitrary-qubit memory. A same-Z-observable test of detector-selected profile matching graphs found 775 versus 779 errors against a pooled static graph in 200,000 shots, with no resolved difference. Accurate noise labels did not translate into a meaningful decoder gain in that condition. Keep code-basis selection and decoder selection as separate claims.

Next, challenge this policy under profile drift and misspecified calibration, include calibration shot/round cost, and compare with a periodically recalibrated fixed basis using the same total shot budget. Keep the classifier and threshold frozen before any such evaluation. Do not integrate based on the current development results alone.

One limited robustness check now doubles gate and measurement p after nominal-rate calibration while preserving X/Z bias direction. The frozen selector retained 12.2%, 50.6%, and 71.0% LER reduction versus static Z at ratios 2, 5, and 10. This supports robustness to total-rate change for a stable direction in the simulator. It leaves direction changes, spatially varying noise, device calibration, and resource amortization unresolved.

An exploratory rescore using calibration prefixes of 25/100/500 shots per 100 logical shots showed reductions versus static Z of 5.1/11.6/16.6% at ratio2, 27.8/49.6/52.4% at ratio5, and 57.5/71.2/71.7% at ratio10. The 25-shot ratio2 interval included zero. Use this only to design a future frozen budget tradeoff; the nested prefix analysis is correlated and not the primary endpoint.

The direct experiment uses 500 calibration circuits per 100 logical circuits. If calibration circuits cannot carry useful logical output, a simple correct-output-per-circuit-shot calculation requires calibration reuse over roughly 169k–618k logical shots, depending on bias, before this selector beats static Z on throughput. This plug-in calculation assumes stable noise for the full horizon; no such stability has been shown. Future work should define the operational objective (LER per logical attempt versus correct-output throughput), account for reusable calibration, and measure how quickly bias direction drifts.

