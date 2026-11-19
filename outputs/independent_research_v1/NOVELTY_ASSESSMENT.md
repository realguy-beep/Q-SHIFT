# Novelty and overlap assessment

## Established directions with direct overlap

- **Per-syndrome ensemble selection:** directly established in peer-reviewed neural ensemble decoding. Q-SHIFT's local selector feasibility was also negative. A general claim of novel decoder routing is unsupported.
- **Confidence-gated selective decoding:** established in selective acceptance, adaptive-window decoders, and recent meta-decoder work. Q-SHIFT would need a materially narrower problem and a useful calibrated signal.
- **Belief-assisted/correlated matching:** established in peer-reviewed work and implemented by PyMatching. Q-SHIFT's 720,000-shot pilot is a context-specific ablation, not an algorithmic invention.
- **Tensor-network ML decoding and noise adaptation:** established under specified surface-code noise models. Full circuit feasibility and equal-resource comparisons remain open for Q-SHIFT.
- **Neural surface-code decoding:** broad family is established, with recent strong hardware-informed evidence. Q-SHIFT's existing CNN is development-only and inferior to PyMatching.
- **Bias-tailored code structures and distance scaling:** established code-design and threshold directions. Any gain requires separate qubit, round, and circuit resource accounting.

## Potentially useful but not yet novel

A native categorical factor graph could preserve mutually exclusive Pauli gate outcomes and avoid the approximate independent DEM representation. This is a methodological direction, not a novelty claim. Exact toy posterior tools already exist locally. The current sum-product prototype's poor one-qubit toy result shows that a naive Bethe approximation is inadequate. A contribution would require a validated, scalable inference method, a literature overlap review using accessible primary sources, and a fair strong-baseline comparison.

The practical use of an independent-root LER gate for correlation-aware decoding may yield an empirical systems result, but a 720,000-shot Q-SHIFT development pilot already exists and failed its practical-effect gate. Repeating it or presenting it as a newly discovered decoder would have no novelty.

Memory-basis alignment under known Pauli bias is established bias-aware code configuration, not a novel decoder. The new distance-3 measurements provide Q-SHIFT-specific matched-resource evidence (5.2×–11.1× lower LER in the aligned biased conditions), but novelty would require a new code/circuit schedule, a robust policy under bias drift, or a resource-aware scaling result. No such claim is supported here.

Detector-only bias estimation by a linear classifier is also an established statistical technique, and noise adaptation is a mature QEC research direction. The current Q-SHIFT-specific result is empirical: one frozen detector-only X/Z classifier trained on synthetic ratio-10 d=3 streams generalized across tested d=3,5,7 and ratios 2,5,10; a direct d=3 selected-basis development run beat static Z under equal profile weights. This is not evidence of a new inference algorithm. Publication value would depend on robust performance under realistic calibration mismatch and time-varying noise at equal total shot/round cost; those tests remain open.

A same-observable follow-up found the profile-selected matching bank statistically indistinguishable from a pooled fixed graph on one d=3 condition. The larger LER effect arises when the measured logical observable/basis is selected according to the known noise profile. Treat that as task-specific memory configuration evidence, not decoder superiority or a general logical-qubit memory improvement.

## Publication boundary

No publication-level novelty claim is justified by this expedition checkpoint. The current supported contribution is a negative feasibility result: the proposed non-approximated DEM follow-up cannot pass Stim conversion for Phase 2B's categorical `PAULI_CHANNEL_2` circuits, and an initial generalized sum-product Bethe approach failed an exact toy topology. External literature retrieval was partially blocked, so the broader novelty assessment remains provisional.


The P(s), Z(s) representation is a standard parity/Fourier identity and is not claimed as a novel decoding algorithm. The development contribution is an independently validated implementation on Q-SHIFT's categorical seven-layer circuit tail, extending exact fragment feasibility beyond the prior joint-state cap. It does not establish novelty or full-circuit scalability.


The native-XCX XZZX experiment is not a new code or decoder. It supplies Q-SHIFT-specific finite-size evidence that a checkerboard XZZX orientation interacts strongly with physical bias under an explicit native entangler noise model. No hardware novelty claim is made because equal CX/XCX/CZ error channels and durations have not been measured.


The complementary-orientation screen is not a new code family or algorithm. It adds local finite-size evidence that the native XZZX checkerboard's bias orientation changes performance, while showing that one complement does not beat CSS under the tested Z-biased condition.


The biased-noise planar MPS comparison applies an established tensor decoder to an established biased code-capacity model; it is not a new algorithm. Its local empirical contribution is the paired chi=16 vs bias-aware MWPM screen with independent seeds. No novelty or circuit-level gain is claimed.


The tensor-train rank diagnostic uses standard SVD-based ranks and makes no algorithmic novelty claim. Its local value is a reproducible compressibility boundary for one exact Q-SHIFT categorical tail under a fixed detector ordering.


The d3/d5/d7/d9 fixed-bias synthesis adds no algorithmic novelty. It is a descriptive four-point finite-size analysis with sparse aligned counts, not a new threshold or scaling result.


The XZZX finite-size advantage against mismatched CSS does not establish a useful code-design gain against bias-aligned CSS. The new comparison reuses independent development data and is not a novel algorithmic result.

The min-fill TT ordering is a standard graph heuristic, not a new method. The local result is negative: on the exact Q-SHIFT tail it increased rather than reduced the maximum high-accuracy ranks, and it does not establish a global tensor-network complexity bound.

Sequential probability ratio testing is established statistical methodology (Wald, *Sequential Analysis*, 1947); this is not claimed as a new algorithm. The local contribution is a frozen detector-only feature application and a matched Q-SHIFT simulator cost/LER evaluation. Its positive long-dwell result is a stable-profile plug-in projection; novelty and deployment value remain unestablished.

Stim shortest-graphlike-error analysis and the identity-paired lower-bound argument are established tools/logic. The local result is an exact physical certificate for two d3 circuits, but its probability is too small to inform the practical floor; no novel floor method is claimed.


The equal-duration round-count experiments use standard syndrome scheduling and biased surface-code circuits. They make no algorithmic novelty claim. Their local evidence is a d3 simulator tradeoff under an assumed idle Pauli model, a failed across-profile idle robustness gate, and no supported d5 improvement. Neither publication novelty nor hardware relevance is established.


The correlation-disagreement selective escalation experiment combines established correlated matching, ordinary matching, and BP+LSD methods; it is not a novel decoder. Its local result is an accuracy-cost tradeoff on d3 development data (14.3% macro LER reduction at 8.44x cost), pending independent replication and below any practical advancement gate.


The flagged-subset logistic selector is an established supervised meta-decoder/selective-decoding pattern and is not claimed as a novel algorithm. Q-SHIFT-specific evidence is a replicated d3 held-out LER gain at modest inference overhead, against correlation-enabled matching and a stronger BP+LSD escalation comparator. Robustness, distance scaling, and hardware transfer are open.


### Measurement-shift result does not change novelty assessment

The learned disagreement-subset selector has now passed one prespecified twofold measurement-flip shift on two fresh streams. This strengthens its development evidence but does not make the method novel: supervised selective/meta-decoding remains an established approach, and the finding is limited to six fixed d3 simulator conditions and one shift axis. Novelty would require a distinct algorithmic contribution and comparison beyond this bounded robustness result.


### Distance-transfer screen narrows scope

The method-specific d5 test did not show benefit (macro LER worsened 1.35%); this further limits the learned-selector development result to d3 and the tested measurement shift. It does not alter the novelty assessment: the d3 method remains an established supervised selective-decoding pattern, and the d5 screen supplies no positive algorithmic contribution.


### Second bounded robustness result

The frozen selector also survived one ratio-10 to ratio-5 bias shift on two d3 streams. This strengthens empirical robustness for that configuration but is not an algorithmic novelty claim; the method remains established supervised selective decoding. The d5 transfer failure remains and limits scaling claims.


### Joint-shift robustness does not change novelty or scope

The frozen selector passed one simultaneous measurement/bias shift on two d3 streams. This strengthens development evidence but remains an established supervised selective-decoding method, not a novelty claim. Its negative d5 transfer screen still prevents distance-scaling claims.


### Pooled selector alternative

Pooling the flagged examples into one logistic model is a compact implementation variant, not a novel method. It passed the baseline development gate but was measurably weaker than six specialized models. No algorithmic novelty or unknown-profile generalization is established.


### Relative-choice variant

Recasting the label as which matcher is wrong is a useful representation but remains conventional supervised meta-decoding, not a novelty claim. It passed a bounded d3 gate but was weaker than the absolute-bit selector.


### Leave-one-regime-out evidence is bounded transfer, not novelty

The relative-choice classifier transferred to one withheld d3 Pauli regime when the matcher graph remained profile-matched. This is a robustness result for supervised selective decoding, not a new algorithm or unknown-profile decoder. The d5 method-transfer result remains negative.


### Basis holdout failure further limits transfer claims

The relative-choice model failed when one memory basis was excluded from training. The positive held-out-regime result is therefore basis-conditional and should not be described as a universal decoder or general transfer algorithm.


### Ratio-2 shift strengthens evidence, not novelty

The frozen selector passed one more stationary bias-strength shift at ratio 2. This adds empirical scope for the established supervised selector but is not an algorithmic novelty claim and does not address temporal or hardware robustness.


### Isotropic shift is a robustness result only

Passing the ratio-1 stationary channel challenge increases empirical scope but does not introduce a new algorithmic contribution or establish broad noise robustness.


### Gate-noise robustness is unresolved

The gate-p shift's fresh stream fell just below the fixed utility threshold, despite favorable paired errors. Do not fold it into the positive robustness claims or characterize the selector as robust to arbitrary gate-rate mismatch.


### Gate-noise axis is not uniformly robust

The half-rate gate shift passed strongly, while the double-rate shift narrowly failed its utility gate on replication. Robustness claims must preserve this directional boundary.


### Measurement-rate robustness scope

The frozen selector passed half- and double-measurement-rate shifts at d3, strengthening stationary development evidence. This remains a robustness result, not a novel algorithm or temporal-noise guarantee.


### Temporal shift adds bounded robustness evidence

One alternating gate-rate pattern transferred on a single d3 task. This is a robustness finding for an existing selector family, not an online adaptation algorithm or novelty claim.


### Second temporal pattern remains bounded evidence

The frozen selector passed a second imposed temporal-rate shape, which strengthens robustness evidence but does not make it an online adaptation method or novel decoder.


### Temporal task dependence

The blockwise temporal result is task-specific: it held for Z-memory/X-bias but not the complementary X-memory/Z-bias task. Do not imply general temporal robustness or a universal adaptation method.


The 100k-shot training-efficiency screen did not produce efficacy evidence: one of six cells fell below the frozen minimum flagged-row count and partial validation was excluded after a runner-order defect. It does not add a novelty claim or alter the established d3 selector result.


### Half-budget training result is empirical efficiency, not algorithmic novelty

The fixed 500k-shot training budget retained the 1M model's d3 selector gains on nominal and one replicated combined shift. This is a reproducible sample-efficiency result for an established supervised selector, not a new decoder architecture or generalization theorem. The 100k prefix was not fit-ready in one condition.

### Nonparametric sequential likelihood remains conventional and unvalidated

A histogram score likelihood with empirical CUSUM boundaries is a standard statistical construction. Its recalibration procedure missed one shifted false-alarm gate on fresh data, so it supports neither a new change-detection method nor robust online adaptation.

### MPS efficacy is a known-family benchmark

The qecsim exact planar MPS improvement over MWPM in a d3 biased code-capacity surrogate is an application benchmark for established degeneracy-aware maximum-likelihood decoding. It missed the frozen practical-effect gate and does not establish a circuit-level Q-SHIFT contribution.

### Neural selector result is a feasibility stop

The single 8-unit tanh prototype failed its fixed optimizer iteration budget before validation. There is no neural efficacy or novelty evidence from that run.

A same-seed cluster-bootstrap audit found that both frozen-threshold shifted-Z validation intervals cross the 25/100k false-switch limit. The histogram CUSUM remains an established statistical construction with unresolved calibration guarantees, not a novel online adaptation result.
