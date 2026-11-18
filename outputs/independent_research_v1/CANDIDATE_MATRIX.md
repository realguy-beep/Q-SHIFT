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

The matrix is therefore a landscape of distinct approaches, not a claim that every row is an untested Q-SHIFT candidate. The next genuinely open implementation gap is structured native-categorical inference, but the first loopy Bethe prototype failed a small exact fixture and needs algorithm redesign before any circuit evaluation.


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
