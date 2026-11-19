# Candidate comparison — preliminary screening

Scores are 1 (low) to 5 (high). Improvement and novelty are speculative upside, not evidence. Cost and integration scores are higher when cheaper/easier. Robustness scores higher when the method can handle model uncertainty. This is a screening matrix, not a ranking of demonstrated gains. Literature/source retrieval limits and candidate-specific evidence status are recorded in the survey and novelty assessment.

| Candidate | Family | Upside | Q-SHIFT fit | Theory | Prior evidence | Stim fit | Feasible here | Cost | Robustness | Fair baseline | Novelty | Claude integration | Leakage risk | Initial view |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Syndrome-conditioned logical-class posterior summation on bounded subgraphs | Degeneracy-aware inference | 4 | 4 | 4 | 4 | 4 | 3 | 2 | 2 | 4 | 2 | 2 | 3 | Exact coalesced vectorized XOR DP plus independent Walsh convolution handles six final layers (36 locations/18 detectors, 524,288 states, agreement <2.4e-16) in 6.1s. A seventh joint-state layer initially exceeded the cap, but a parity-compressed P/Z representation then passed exactly at 20 detectors/1.05M states. It remains a tail-only prototype; full-circuit exact decoding is unproven. |
| Tensor-network logical-class contraction | Degeneracy-aware inference | 5 | 3 | 5 | 4 | 3 | 1 | 1 | 2 | 4 | 1 | 1 | 3 | Strong theoretical comparator. qecsim fixed-χ=16 planar MPS beat bias-aware MWPM at d5 in two independent 5k roots under 10:1:1 code-capacity noise; d3 was less certain. d5 latency was ~31x higher. Q-SHIFT spacetime/categorical-gate compatibility remains unimplemented. |
| BP+OSD / generalized BP with calibrated factor graph | Probabilistic decoder | 3 | 3 | 4 | 4 | 2 | 3 | 3 | 2 | 4 | 1 | 3 | 3 | Conservative candidate. Stage S reportedly found min-sum 0.9 worse and OSD_CS-40+BP-200 near neutral, so only proceed with a defined structural change. |
| Learned hyperedge selection followed by matching | Hypergraph / matching | 3 | 4 | 3 | 3 | 4 | 3 | 3 | 2 | 4 | 2 | 3 | 3 | Plausible fit for correlated events, but distinguish real higher-order modeling from a convenient DEM approximation. |
| Belief matching or cluster-based local inference | Probabilistic / matching | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 4 | 2 | 2 | 3 | Candidate for local degeneracy and correlation effects. Build on an auditable small factor graph. |
| Confidence-based selective escalation, matching then local search | Decoder ensemble | 2 | 4 | 3 | 3 | 5 | 4 | 4 | 4 | 5 | 2 | 4 | 3 | Conservative deployment idea. Needs confidence calibration and paired runtime/error tradeoff. |
| Neural-assisted correction proposals with exact syndrome validation | Neural hybrid | 3 | 3 | 3 | 3 | 4 | 2 | 2 | 2 | 4 | 2 | 3 | 4 | Could reduce search; validation enforces syndrome validity but does not guarantee logical class correctness. High leakage and overfit risk. |
| Spatiotemporal graph neural / transformer decoder | Neural | 4 | 3 | 2 | 3 | 4 | 1 | 1 | 2 | 4 | 2 | 1 | 5 | High compute and training-data demand; current neural results and sample size argue against scaling before a concrete representational hypothesis. |
| Bayesian noise-profile inference plus uncertainty-aware decoder selection | Noise inference / adaptation | 3 | 5 | 4 | 3 | 5 | 3 | 3 | 4 | 5 | 3 | 4 | 4 | A frozen detector-only LDA identified synthetic X/Z bias across d=3,5,7; same-observable decoder selection was neutral vs pooled matching at d3, while choosing the measured logical basis reduced task-specific LER 16.6%–71.7%. Basis switching is not an arbitrary-qubit decoder gain; an alternating-profile resource replay found only 0.10%–0.21% projected throughput gains at the longest tested 100k-shot dwell for ratios5/10, and none at shorter dwell. |
| Periodic recalibration under X/Z profile switching | Online adaptation | 3 | 3 | 3 | 2 | 4 | 3 | 3 | 4 | 5 | 2 | 4 | 4 | Plug-in replay on existing independent windows found that LER-per-attempt gains are overwhelmed by calibration cost at dwell times through 10k shots; marginal projected throughput gains appear only at 100k-shot dwell and ratios5/10. No causal change-point detector or device drift was tested. |
| Syndrome-extraction-round count at fixed distance | Code and circuit | 3 | 4 | 3 | 3 | 4 | 4 | 4 | 2 | 4 | 2 | 3 | 2 | At d3, rounds3/5/7/9 produced monotonically increasing per-attempt LER and two-qubit exposure in all four known-profile cells. Three-round jobs have shorter storage duration; equal-time performance is unresolved. |
| Bias-strength-robust matching model | Model robustness | 3 | 4 | 3 | 3 | 5 | 4 | 4 | 3 | 4 | 2 | 3 | 3 | Fresh d3 validation favored assumed ratio10, but d5 ratio10-vs-ratio5 was near-neutral (paired macro delta +.000020, CI crosses zero). The effect appears distance-specific or underpowered; no universal decoder setting follows. |
| Importance sampling for rare logical faults | Rare-event statistics | 4 | 4 | 4 | 4 | 5 | 3 | 3 | 3 | 4 | 2 | 2 | 4 | Exact categorical likelihood weighting works, and global 5x tilt reduced estimator variance in 5–6/6 earlier screens. A new adjacent-pair cluster proposal passed estimator checks but its efficiency gate was 0/6, with sparse failure ESS and larger weight tails. Further structured proposals need a new prospective design. |
| XZZX / code-distance / syndrome-extraction co-design | Code and circuit | 5 | 3 | 4 | 4 | 3 | 1 | 1 | 3 | 3 | 1 | 1 | 3 | A local-H transform paid added noise and lost, but an exact native-XCX schedule removed that cost. Under equal native-entangler noise, original XZZX helped X-bias (0.66/0.38 CSS rate) and hurt Z-bias (3.86/11.24); one complement remained 3.04/6.16x worse than CSS for Z-bias. Strong orientation interaction, no universal gain; hardware gate-noise equivalence is unverified. |

## Proposed feasibility shortlist

1. **Conservative:** selective escalation from fixed PyMatching to a bounded local search, using only syndrome-derived confidence. Check calibration, exact syndrome validity, paired errors, and added latency. Do not treat it as likely to yield orders-of-magnitude gain.
2. **High upside:** degeneracy-aware logical-class probability on tiny exactly solvable instances, then bounded subgraphs. Advancement requires agreement with exhaustive enumeration and a measured width/runtime scaling curve before any d=5 evaluation.
3. **Different mechanism:** Bayesian detector-profile inference under withheld regimes with uncertainty-aware selection. Compare against the frozen pooled fixed decoder and detector-profile calibrated alternatives, with root-held-out splits and explicit no-oracle inputs.

An importance-sampling prototype is a parallel measurement-method candidate, not a decoder. Literature and source review must determine whether it adds information beyond existing saved development arrays. No candidate is authorized for confirmatory evaluation by this matrix.

## Prior-work disposition from the repository audit

- The earlier categorical exact reference already covers two tiny Pauli-channel toys and independent forced-outcome validation. Exact enumeration of the complete d=3 circuit is ruled out by 2^609 assignments. The remaining gap is structured scaling, not another toy enumerator.
- `outputs/matching_representation_investigation/` already compares categorical MAP, exact independent-DEM MAP, standard/correlation-aware matching, separator-free matching, and restricted local posterior methods. Do not repeat those small-fragment experiments.
- `outputs/correlation_pilot/` already contains the correlation-mode pilot. Its aggregate gain is smaller than the preregistered practical gate and heterogeneous by stratum. The raw pilot arrays are absent in this checkout.
- `outputs/competition_pivot/` already reports a no-go for uncertainty-aware decoder selection. Ensemble selection is established literature, and its saved utility predictors were weak. Do not re-train a selector on the same results.
- `outputs/neural_decoder_diagnostic/` reports the position-preserving CNN as still worse than fixed PyMatching. Scaling a neural candidate without a distinct mechanism is not justified.
- The user's initial brief reports Stage S BP+OSD results, but corresponding Stage S files are absent from published `main`. I did not inspect or fetch Claude's branch. Treat those numbers as supplied context until a safe independent source is made available.
- A new, fixed-configuration BP+LSD development screen is now available in `bplsd_results.json`: all three LDPC 2.4.1 LSD method labels produced 321 errors versus 138 for correlation-enabled PyMatching across 30,000 distance-3 circuit samples. This is one approximate DEM and one configuration, and it is a negative feasibility result rather than an exhaustive BP+LSD comparison.
- A likelihood-ratio importance sampler with a fixed fivefold odds tilt was validated against the exact categorical circuit, but 16 fresh replicates showed a 1.12 macro SD ratio (weighted/direct), with per-condition ratios 0.52–1.64. The transformation is valid; variance reduction is not robust for this global proposal.
- A principled forward-KL product of weighted failure-conditioned channel marginals did not reduce SE against both direct and global-tilt arms in any of six fresh validation conditions; max weight was 77.3 and minimum failure ESS was 9.0. A factorized conditional proposal is not sufficient at this shrinkage setting.
- At known stable X/Z bias, same-resource basis alignment yielded 5.2×–11.1× lower observed LER at d=3 and 36×–45× at d=5. Balanced noise showed no d3 basis effect. This is established configuration evidence, not an adaptive or decoder claim; d5 aligned cells had only six failures each.
- At d=3, fresh 2:1 and 5:1 bias screens showed alignment ratios of 0.65–0.74 at 2:1 and 0.24–0.33 at 5:1. This helps bound the known-profile setting, but no exact decision threshold was fit.
- `outputs/headroom_feasibility/` already screens specialized decoder headroom at d=3/5/7 and reaches a no-go under its stated gate. A generic repeat of that grid is not a priority.

The matrix is therefore a landscape of distinct approaches, not a claim that every row is an untested Q-SHIFT candidate. A nontrivial tree control now confirms exact posterior recovery on an acyclic fixture; the one-qubit loopy failure remains severe and a converged two-qubit fixture has large posterior calibration error. The open implementation gap remains structured native-categorical inference with loop correction or bounded exact regions; do not evaluate the current loopy Bethe prototype on circuits.


Spatial robustness update: the exact local-map graph and pooled graph were nearly tied on the fixed 1.5x/.5x two-zone d3 stress test; macro gain .93%, below the declared 10% gate. Do not advance a selector for this profile.


Distance scaling update: a d9 extension observed 1 aligned vs 408 mismatched failures in 500k shots, ratio .00245 with exact 95% interval [.0000619,.01373]. This extends finite-distance evidence but is too imprecise to support scaling or the 1e-4 ratio target.


Exact-inference update: the natural-order seven-layer P/Z tensor-train arrays need maximum rank 91 at 1e-10 (rank 30 at 1e-6), so the predeclared exact-fidelity MPS gate failed.


### All-location fault composition screen

## All-location fault composition under ratio-sensitive decoding

The preflight passed synthetic flags for all 15 two-qubit Paulis, all three one-qubit Paulis, and explicit X/Z error events (zero data/flag mismatches). Both d3 conditions had 120 two-qubit pairs and 40 one-qubit locations; explicit measurement targets were 49 for Z-memory/X-biased and 49 total for X-memory/Z-biased. Source and instrumented samples had unchanged 40-detector/one-observable layout, and failure-rate differences were below 1.1 combined standard errors. The 200,000-shot main screen took 3.94 seconds.

At 100,000 shots/condition, ratio-5/ratio-10 models failed on 753/752 Z-memory X-biased shots (61 prediction disagreements) and 769/766 X-memory Z-biased shots (95 disagreements). The both-wrong groups contained 722 and 720 shots; ratio-10-fixes-ratio-5 groups contained 31 and 49, while ratio-10-breaks-ratio-5 contained 30 and 46. In both conditions, mean tracked two-qubit faults were about 0.349 per both-correct shot and 1.87 per both-wrong shot. In the biased Pauli outcome counts, XX was most frequent in the X-biased Z-memory both-wrong group (794 events), while ZZ was most frequent in the Z-biased X-memory both-wrong group (800). One-qubit and explicit measurement-fault counts also differed across outcome groups; see the JSON for full counts.

The decoder-disagreement groups are small, particularly the 30–49-shot fix/break groups. These are conditional fault associations from one fixed development stream, not causal attribution, evidence that one fault channel caused decoding errors, or a hardware noise claim. The new instrumentation extends the earlier two-qubit-only report; it does not change the prior conclusion that raw fault burden alone cannot explain decoder behavior. No sealed or confirmatory data were accessed.


**Scaling update:** saved d3/d5/d7/d9 X-bias streams give aligned/mismatched point ratios .194/.0276/.00496/.00245; the aligned d9 cell has one error. Treat the log-linear fit as a descriptive synthesis only. Use aligned CSS as the baseline in any XZZX code-design comparison.


**Comparator correction:** native-XCX XZZX beat CSS Z-memory under X bias, but reused matched-resource X-aligned CSS streams had lower LER at d3/d5. XZZX/CSS-aligned ratios were 3.57 and 13.48. Keep XZZX as orientation/code-design evidence, not a leading X-bias recommendation.


**Fresh d5 factorial:** CSS-X/Z had 79/1,848 failures; native XZZX-X/Z 604/670 on 500k streams each. XZZX helps against CSS-Z but loses to X-aligned CSS-X by 7.65x. Keep code-design conclusions workload- and basis-specific.


**Distance interaction:** in equal-weight separate X/Z memory tasks, XZZX/CSS rate ratio was 1.18 at d3, .66 at d5 on replicated streams, and .279 at d7. The XZZX gain appears at the larger tested distances; keep this finite-size and gate-assumption qualified. For known X memory, CSS-X remained better.


**d9 extension:** equal-weight separate-basis XZZX/CSS ratio .107 (.070–.159), with Z-memory ratio .069 and X-memory ratio 10 (sparse). The balanced workload gain persists at d9 but is not an arbitrary-state or 99.99% result; retain the basis-specific tradeoff.


**d11 challenge:** equal-weight separate-basis XZZX/CSS=.0448 (.009–.137), based on 3 vs 67 Z-memory errors; both X-memory arms had zero errors. Runtime 282s and 2.69 GiB. The finite-size tradeoff persists, but d11 is underpowered for X-memory and near the declared runtime cap.


**Scalability boundary:** the d13 four-cell 500k/condition screen projected 455s at preflight, above the 300s cap. No d13 LER result exists; current screen stops at d11.


**Bias robustness:** at d7 equal-weight separate X/Z task ratios XZZX/CSS were .853 at 2:1, .608 at 5:1, and .279 at 10:1. The gain strengthens with bias, but at 2:1 XZZX-X is worse than CSS-X. Native-gate equivalence remains assumed.


At d7, the 5:1 bias check gave equal-mix XZZX/CSS=.608 (.529–.697); XZZX-X/CSS-X=5.85 and XZZX-Z/CSS-Z=.338. Alongside 2:1=.853 and 10:1=.279, this is workload- and bias-strength dependent.


### Additional decoder feasibility result

Fusion Blossom 0.2.13 serial custom-graph MWPM was added as a classical-decoder candidate. Its custom graph reproduced ordinary PyMatching MWPM predictions on 1,000 d3 development samples after even-integer weight quantization, but achieved only 6.5%–15.3% of PyMatching throughput. Reject this serial path as a d13 acceleration hypothesis; parallel Fusion Blossom remains unassessed and would need a distinct preflight. Correlation-enabled behavior was not tested.

### Sequential calibration result for the profile-inference candidate

A frozen Gaussian SPRT over the existing detector-only LDA score achieved 4.08%/3.84% profile error on an independent 2,500-window/profile validation set at a combined mean 24.83 shots. A fresh d3 end-to-end screen showed LER .001386 vs static Z .004198 for equal separate memory tasks, but per-100-attempt calibration cost erased throughput. A plug-in stable-profile projection at 100k attempts/dwell showed a modest yield interval above static Z; direct 10k dwell remained inconclusive. Promote only as a research lead for long stable jobs, not as a deployment recommendation. Robustness to score-model misspecification and profile changes remains untested.

### Measurement-composition robustness challenge

The nominal Gaussian SPRT failed under a fixed-direction measurement-noise shift (17.6% Z-profile selection errors). A fresh equal-variance SPRT lowered this to 12.0% but still missed the 5% upper-bound gate. This materially downgrades the profile-inference lead: score likelihoods need uncertainty/model-shift handling before long-dwell utility projections can be interpreted operationally.

### CUSUM change detector screen

Class-specific and common-variance likelihood CUSUMs detected all simulated transitions with ~30-shot median delay, but triggered 25–50 false switches/100k nominal shots and up to 271/100k under measurement shift. Periodic 100-shot LDA was less noisy in nominal controls. Reject the tested Gaussian CUSUM; the likelihood model's ideal false-alarm guarantee did not hold empirically.

### Exact physical-pattern lower-bound screen

One shortest graphlike path per d3 aligned X-memory circuit yielded exact circuit-pattern bounds 3.07e-15 (CSS-X) and 3.07e-13 (XZZX-X), far below observed LER. This validates a physical certificate but rejects the single-path method as a useful floor estimator; multiplicity is the open issue.

### Equal-duration syndrome schedule follow-up (independent research v2)

A d3 screen and fresh-seed replication favored three active rounds plus two matched-duration biased data-idle cycles over five active rounds on aligned tasks (mean cell RR .762 and .773). A 2x idle-rate stress retained the Z-aligned benefit (RR .753) but made X alignment near-neutral (RR 1.016), failing the across-cell robustness gate. At d5, five-plus-idle versus nine active rounds showed no gain (RR 1.05, 95% .83–1.33); a single seven-plus-idle point was inconclusive (RR .843, .674–1.056). This is not a general or distance-scaling candidate. Retain only as a workload-specific d3 simulator result; require calibrated idle noise and a concrete application before further work.


### Selective escalation update (independent research v2)

Correlation-vs-ordinary matching disagreement flagged .261% of fresh d3 samples. Routing flagged cases to BP+LSD reduced macro LER by 14.3% in the initial stream, but full decode time was 8.44x baseline; this fails the 2x runtime gate. Keep only as evidence that the flag population is informative. A fresh efficacy replication is pending, but no BP+LSD integration is recommended.


### Fast disagreement-subset supervised selector (independent research v2)

A per-condition L2 logistic model trained on flagged detector syndromes reduced held-out macro d3 LER by 17.2% initially and 16.2% in a fresh train/validation replication, at 1.35x/1.36x inference cost. Same-stream BP+LSD was weaker on five of six replication cells and ~8.3x slower. This is supervised selective decoding, an established family; it is not novel. Main remaining gap is noise-composition robustness; model was trained per known profile and uses simulator labels offline.


### Fast disagreement-subset selector: one frozen measurement-shift replication passed

The nominal selector was applied without retraining at measurement p=.006 after training at p=.003. Two independent d3 six-condition streams gave 13.03% and 13.11% macro LER reduction at 1.35x cost; all per-cell paired intervals favored the selector on both streams. This upgrades the lead beyond nominal-profile evidence for this particular known shift. It remains a per-condition supervised simulator method, with bias/gate shifts, other distances, and hardware untested. Do not generalize this one-dimensional shift to arbitrary noise robustness. Detailed report: `../independent_research_v2/fast_flagged_logistic_measurement_shift_report.md`.


### Flagged logistic method at d5: no useful transfer observed

Six distance-specific d5 fits on 1M training shots each, tested on 1M independent shots/cell, gave macro LER .001959→.0019855 (+1.35%); only two cells improved. The 1.379x inference cost passed, but the fixed accuracy gate failed. No replication or tuning. Limit the positive selector result to d3 and its tested measurement shift; do not claim distance scaling. A distinct d5 algorithm remains possible but is not supported by this screen. Report: `../independent_research_v2/fast_flagged_logistic_d5_transfer_report.md`.


### Fast selector: replicated ratio-10 to ratio-5 bias challenge

Two frozen-model d3 streams showed 17.95% and 17.81% macro LER reduction at ~1.35x cost; all six per-cell paired intervals favored the selector. The X/Z-biased profiles changed anisotropy; balanced profiles were unchanged controls. This strengthens the bounded d3 robustness evidence, alongside the separate measurement-p shift. It does not change the negative d5 transfer result and is not broad or multi-axis robustness. Report: `../independent_research_v2/fast_flagged_logistic_bias_shift_report.md`.


### Fast selector under simultaneous measurement and bias shift

The frozen d3 policy passed a joint shift (measurement p .006, bias ratio 5) on two independent streams: 14.62% and 14.02% macro LER reduction at ~1.35x cost; every per-cell interval favored it. This supports one specific two-axis simulator condition, beyond the separate one-axis challenges. It remains d3-only; the d5 transfer screen failed. Report: `../independent_research_v2/fast_flagged_logistic_combined_shift_report.md`.


### One pooled d3 selector as a compact alternative

Two pooled train/validation streams passed the baseline gate (14.5%/15.1% macro improvement, ~1.36x cost). Every condition improved over correlated matching. Compared on identical held-out streams, the specialized models remained better by ~.00010 absolute macro LER. Consider shared pooling only when a single coefficient set is valuable and that accuracy cost is acceptable; it is not an equivalent replacement or an unknown-profile solution. Report: `../independent_research_v2/fast_flagged_logistic_shared_selector_report.md`.


### Relative matcher-choice model

Two pooled 40-detector-bit relative-choice fits passed the baseline gate (11.96%/12.23% macro reductions, ~1.35x cost). The target is whether correlated matching is wrong on flagged syndromes, then the policy chooses the ordinary output if so. It is simpler to interpret but was measurably less accurate than shared absolute-bit and specialized selectors. Consider only where that tradeoff is acceptable. Full report: `../independent_research_v2/fast_flagged_logistic_relative_choice_report.md`.


### Relative-choice classifier: leave-one-regime-out transfer

Two independent three-fold runs withheld each Pauli regime from training and retained 11.4%/11.5% macro gains at ~1.35x cost, with positive direction in all folds and held-out cells. The decoder graphs were still profile-matched; full-profile and specialized models remained better. Keep this as selector transfer evidence only, not unknown-profile decoding or distance scaling. Report: `../independent_research_v2/fast_flagged_logistic_leave_profile_out_report.md`.


### Basis-agnostic relative-choice transfer rejected

Leave-one-memory-basis-out testing failed (1.54% macro worsening; X-memory holdout -3.72%, one cell >5% harm). The earlier profile transfer required both bases in training. Keep relative-choice claims task/basis-scoped and do not call it basis-agnostic. No replication. Report: `../independent_research_v2/fast_flagged_logistic_leave_basis_out_report.md`.


### Ratio-2 static bias-strength challenge

Two ratio-10 frozen-model streams at physical ratio 2 gave 17.38%/17.90% macro gains at ~1.35x cost with all six cells favorable. This extends stationary bias-strength evidence; the cross-basis and d5 transfer failures remain. Report: `../independent_research_v2/fast_flagged_logistic_bias_ratio2_report.md`.


### Ratio-1 isotropic bias challenge

Two frozen-model d3 streams at physical ratio 1 gave 16.43%/16.77% macro reduction at ~1.33x cost. All points improved; one first-stream cell interval crossed parity. Stationary robustness now includes ratios 1, 2, and 5, but the cross-basis and d5 limitations remain. Report: `../independent_research_v2/fast_flagged_logistic_bias_ratio1_report.md`.


### Doubled gate-noise challenge: borderline, not a pass

The frozen selector reduced macro LER 10.01% in the first stream and 9.95% on replication at gate p=.006; all cells improved and inference cost passed, but the >=10% advancement gate failed on replication. Treat as inconclusive/borderline rather than robustly passing. Report: `../independent_research_v2/fast_flagged_logistic_gate_shift_report.md`.


### Gate-rate stress pair

Halving gate p to .0015 passed twice (24.42%/23.36% macro gains); doubling to .006 narrowly failed the 10% gate on replication (10.01%/9.95%). This is asymmetric rate robustness, not a uniform gate-noise envelope. See both gate-shift reports in v2.


### Measurement-rate stress pair

The ratio-10 frozen selector passed both measurement p=.0015 and .006 on two streams each, with ~18% and ~13% macro reductions respectively and ~1.35x cost. This is a bounded stationary rate range; temporal and graph-mismatch claims remain unsupported. See both measurement-shift reports in v2.


### Alternating temporal gate-rate screen

A frozen stationary selector passed two reversed five-round gate-rate profiles at mean p=.003 on Z-memory/X-bias d3, with 12.47%/11.68% macro reductions at ~1.36x cost. This is a single task/pattern result, not online adaptation. Report: `../independent_research_v2/fast_flagged_logistic_temporal_shift_report.md`.


### Blockwise temporal-rate pattern

A second five-round temporal shape, distinct from the alternating pattern, passed on two streams (12.42%/11.76% macro gain, ~1.36x cost) for Z-memory/X-bias d3. Supports these two maps only; no online adaptation or general temporal robustness claim. Report: `../independent_research_v2/fast_flagged_logistic_temporal_block_shift_report.md`.


### Temporal task-transfer boundary

A blockwise temporal map passed in Z-memory/X-bias but was near-neutral in X-memory/Z-bias; four-cell macro gain was 7.69%, failing the fixed gate. Keep temporal lead scoped to Z-memory/X-bias. Report: `../independent_research_v2/fast_flagged_logistic_temporal_two_task_report.md`.


### Selector training sample efficiency — 100k budget stopped at trainability

A nested 100k-shot-per-condition fit screen found only 93 flagged rows for X-memory/X-biased, below the predeclared minimum of 100. The efficacy gate was not assessed; partial validation output from an interleaved runner is excluded. The validated 1M-shot-per-condition model remains the reference. Do not infer a learning curve. See `../independent_research_v2/fast_flagged_logistic_training_efficiency_report.md`.


### 500k-shot selector training budget — replicated gate pass

A prospective nested 500k fit retained 100.2% of the 1M fit's absolute macro gain initially and 98.4% on fresh replication. Macro reductions were 16.64%/17.11%, every cell improved, and total inference cost was 1.37x/1.35x. This supports halving the d3 simulator training budget from 1M to 500k shots/condition. The 100k screen remains below fit-readiness in one cell; no smaller budget or distance transfer is supported. Full report in v2.


### Empirical histogram CUSUM — rejected on false-switch rate

A frozen 32-bin detector-score likelihood detected all alternating-profile transitions in 19–28 shots but produced 33–41 false switches/100k shots nominal and 46–170 under doubled measurement noise. It failed the 5/25 per-100k limits; periodic 100-shot LDA was quieter. Do not advance this CUSUM or tune on its stream.


### Empirically calibrated histogram CUSUM — initial pass, procedure replication miss

Initial threshold h=8.595 passed independent stable/alternating gates. Fresh calibration selected h=8.327 and narrowly failed shifted-Z false-switch limit (28.9 vs 25/100k); the original h passed a secondary fresh-stream evaluation. Treat as an unresolved simulator lead, not replicated threshold-calibration robustness.


### Small nonlinear flagged-syndrome selector — stopped before validation

A fixed 8-unit tanh MLP hit the 500-iteration L-BFGS-B limit on the first training condition. No validation or accuracy claim. Do not raise iteration count or tune this same candidate on that stream.


### 500k selector training budget under joint noise shift — replicated pass

Fresh 500k/1M nominal fits were tested under measurement p .006 and bias ratio 5, with nominal matcher graphs frozen. The 500k fit reduced macro LER 14.25%/13.19%, retained 98.1%/97.7% of the full-fit gain, and cost 1.34x. All six cells improved; the minimum gains were 4.93%/4.39%. This extends the half-budget evidence to one combined d3 simulator shift only.


### 10,000× claim evidence budget update

The d9 single-cell lower-bound calculation extends to multiplicity: six simultaneous cells need 64.8M zero-failure candidate shots/cell under candidate-only 95% FWER, or 74.2M if half of alpha is reserved for baseline uncertainty. One failure raises these to 92.7M/103.4M. This quantifies inferential cost, not a physical floor.


### Exact planar MPS under biased code-capacity noise — below utility gate

At d3, p=.05 and 10:1 X/Z-biased IID code-capacity noise, exact MPS reduced equal-weight LER 5.55% vs noise-aware MWPM, with 5.15%/5.94% per-axis gains and 37s decode time for 40k shots. It missed the fixed 10% gate; no replication. This is not circuit-level Q-SHIFT evidence.


### Calibrated CUSUM rate precision audit

The frozen h=8.595 point rate passed twice, but episode-cluster 95% intervals for shifted-Z were 20.2–28.9 and 19.3–28.7 false switches/100k, crossing the 25 limit both times. Do not claim 95%-supported false-alarm control for that stratum.
