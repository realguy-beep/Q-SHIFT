# Q-SHIFT adaptive decoding research report

**Status: simulation research prototype; adaptive superiority not demonstrated.** The original lookup experiments are preserved. This report records the corrected ten-seed evaluation and exploratory circuit/noise checks.

## Research question and result

Can detector-only regime estimation select or adjust a decoder to beat fixed decoding as noise changes? In the tested Stim repetition-memory circuits, **no**. A mixed-regime table, specialized tables, and the detector-window hybrid all had more residual errors than fixed PyMatching in the aggregate. The hybrid's detector-frequency regime classifier was sometimes useful for identifying a regime, but choosing the corresponding learned table did not improve decoding. Correct-noise PyMatching had the same residual outcomes as nominal PyMatching on these test samples.

This rejects these implementations for this circuit/noise family. It does not prove that adaptation is impossible in settings where noise changes the relative likelihoods of fault mechanisms or where independently available hardware telemetry contains useful information.

## Reproducible primary experiment

Runner: `qshift_research.py`; complete seed-level and aggregate data: `qshift_research_results.json`.

- 10 independent replicate seeds.
- For each seed and each training regime (0.001, 0.003, 0.006): 100,000 training shots and 30,000 validation shots. Mixed and per-regime tables use distinct training batches. Validation is separate from training and test.
- 100,000 shared test shots per condition per replicate, pooled to 1,000,000 test shots per condition. All decoders receive the same detector samples and observable labels for scoring.
- Test settings: 0.001, 0.002, 0.003, 0.0045, 0.006, and 0.008. The last is outside the training range; 0.0045 is an explicitly requested intermediate.
- Q-SHIFT sees detector bits only. Nominal PyMatching uses p=0.003; noise-specific matching and nearest-regime lookup are explicitly oracle/informed references.
- Residual is sampled observable XOR decoder correction. Thresholds and lookup-versus-matching choices use validation only.

### Aggregate results

Counts are residual logical-observable errors over 1,000,000 paired test shots. Paired Δ is decoder errors minus fixed matching errors. The paired interval is an approximate 95% interval from discordant pairs; p is the exact two-sided McNemar test. P values are unadjusted across exploratory conditions.

| Test noise | Raw observable flips | Fixed matching | Correct-noise matching | Mixed lookup | Per-regime lookup* | Adaptive hybrid | Mixed Δ vs fixed (95% CI; p) |
|---:|---:|---:|---:|---:|---:|---:|---|
| 0.001 | 1,577 | 6 | 6 | 7 | 12 | 12 | +1 [−4.2, +6.2] per million; 1.000 |
| 0.002 | 3,247 | 39 | 39 | 47 | 71 | 62 | +8 [−4.4, +20.4]; 0.268 |
| 0.003 | 4,840 | 97 | 97 | 101 | 127 | 101 | +4 [−14.0, +22.0]; 0.744 |
| 0.0045 | 7,130 | 208 | 208 | 231 | 326 | 251 | +23 [−3.8, +49.8]; 0.107 |
| 0.006 | 9,635 | 374 | 374 | 413 | 427 | 418 | +39 [+3.9, +74.1]; 0.0338 |
| 0.008 | 12,700 | 663 | 663 | 741 | 694 | 700 | +78 [+30.6, +125.4]; 0.00142 |

*Per-regime lookup uses the nearest trained regime's table and threshold; the true test regime is used to choose it, so this is an informed oracle reference. It is not a deployable detector-only result.

All paired differences for the learned mixed table are nonnegative. The 0.006 result is nominally significant before accounting for six comparisons; it does not survive a Bonferroni correction. At the unseen 0.008 regime, mixed lookup is clearly worse than fixed matching in this run. Every decoder's residual-rate Wilson interval is included in the JSON. For the fixed decoder the intervals are 2.75–13.09, 28.53–53.31, 79.52–118.32, 181.59–238.25, 337.97–413.86, and 614.43–715.40 errors per million, respectively.

The adaptive hybrid estimates a regime from detector-pattern frequencies in windows of 1,000 shots, then uses a per-regime lookup or nominal matching according to its validation comparison. Its errors exceed fixed matching at 0.001, 0.002, 0.0045, 0.006, and 0.008, and tie at 0.003. It is rejected as a performance improvement. At 0.0045 it split windows between the 0.003 and 0.006 regimes; at 0.008 it selected the 0.006 table. Selection does not guarantee the selected table is a better decoder.

The fixed and correct-noise PyMatching results have zero discordant residual outcomes in these tests. Under this uniform channel, changing p changed edge weights without changing the observed matching decisions. This should not be generalized to heterogeneous or drifting channels.

## Time-varying pilot

`qshift_time_varying.py` and `qshift_time_varying_results.json` evaluate six 100,000-shot stationary segments: 0.001, 0.006, 0.003, 0.008, 0.0045, and 0.002. A 1,000-shot detector window estimates the regime without receiving p. Validation-selected lookup/matching choices are 0.001→lookup, 0.003→matching, 0.006→lookup. The regime estimator agreed with the nearest trained regime on 77.5% of shots. Fixed matching and the adaptive policy both had 120 residual errors across 600,000 shots; nearest-regime lookup had 155. This is one pilot sequence, not a replicated test, and it provides no adaptive gain.

## Runtime, memory, and scaling

The primary harness times batched decoder calls on this local Python 3.12.10 / Stim 1.16.0 / PyMatching 2.4.0 / NumPy 2.5.3 environment. At one representative condition, measured batch-average decode costs were about 33 ns/shot for matching, 64 ns/shot for mixed lookup, and 580 ns/shot for windowed adaptive estimation plus selection. These are throughput measurements for batches of 100,000, not per-shot hardware latency. Adaptive bookkeeping is materially more expensive than either base decoder in this Python implementation.

Detector encoding now packs arbitrary-width detector rows into Python integer keys; it does not truncate at eight bits. Lookup storage is a sparse dictionary of patterns observed in training. The primary run used roughly 13.6 KB for the probability maps across the mixed and three specialized tables (Python object-size approximation; it excludes counts, allocator overhead, and runtime state). The exploratory distance-5 / five-round circuit had 24 detectors and 419 observed training patterns; the representation handled all 24 bits. Yet with only 100,000 shots in that exploratory run, lookup made 48 test errors while matching made 2. At distance 3/five rounds the counts were 42 vs 19. Sparse encoding scales correctly as a representation, but lookup accuracy and storage growth still need study; it is not a scalable decoder result.

## Noise and circuit checks

`qshift_design_sweep.py` and `qshift_design_sweep_results.json` preserve single-seed exploratory runs (100k train, 30k validation, 100k test at p=0.003):

| Circuit/channel | Detectors | Lookup errors | Matching errors |
|---|---:|---:|---:|
| distance 3, rounds 3, depolarizing | 8 | 9 | 7 |
| distance 5, rounds 5, depolarizing | 24 | 48 | 2 |
| distance 3, rounds 5, depolarizing | 12 | 42 | 19 |
| distance 3, rounds 3, X faults | 8 | 43 | 34 |
| distance 3, rounds 3, Z faults | 8 | 0 | 0 |
| distance 3, rounds 3, measurement flips | 8 | 18 | 3 |

These runs are not replicated or powered for claims. The Z-fault case is uninformative for this Z-basis repetition-memory observable: the chosen phase faults produced no sampled observable failures. The measurement-flip case confirms that the current lookup does not handle a changed mechanism better than matching in this small run. A dedicated study should compare codes/bases appropriate to each Pauli channel rather than interpret the zero-error negative control as success.

## Statistical and implementation notes

- Paired confidence intervals use a normal approximation based on discordant shots; exact McNemar p values use a two-sided binomial test. The JSON stores both discordant counts for audit.
- P values in the six-condition table are exploratory and unadjusted; the isolated p=0.0338 at 0.006 is not evidence after multiplicity correction. The out-of-range condition indicates harm, not robustness.
- The experiment runner uses seeds derived from the replicate seed and distinct offsets for training, validation, and test. Noise labels are used only to generate datasets, choose oracle references, and summarize test conditions; the adaptive decoder receives detector bits and shot-window boundaries only.
- A previous draft of `qshift_research.py` compared different validation batches for lookup and matching policy selection. That report was overwritten and is superseded by the current corrected 10-seed results. The final policy compares both decoders on the same validation samples.
- Existing baseline artifacts and prior successful/unsuccessful runs remain in this `outputs` directory. The original project under Downloads was not modified.

## Decision and next work

Keep PyMatching as the operational baseline and retain lookup as a research baseline only. Do not claim adaptive advantage. The most defensible next experiment is a replicated, paired study with heterogeneous mechanisms or controlled temporal drift where detector-pattern frequencies can identify a *change in relative fault mechanisms*, using validation-only policy selection and a locked, independently generated stream test. Include code-basis-matched bit/phase experiments and distance scaling. Hardware telemetry, compilation, latency, and integration remain untested.
