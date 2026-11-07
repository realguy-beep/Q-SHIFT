# Q-SHIFT — Noise Composition Experimental Phase

## Executive result

**The study does not support an adaptive-decoding advantage.** Detector windows distinguished the four trained noise regimes well, but a lookup strategy selected only when independent validation supported it was rejected for every regime in the fresh guarded run. The adaptive stream consequently made zero decoder switches and tied fixed PyMatching exactly. An earlier rate-only selector did switch and performed worse. Composition recognition is therefore not the limiting result by itself: the learned specialist lookup tables did not provide reliable gains over matching.

The prior Q-SHIFT report's negative result is preserved. This phase is a separate directory and does not replace prior datasets, scripts, or reports.

## Phase 1 audit

The original starter circuit is Stim `repetition_code:memory`, distance 3, 3 measurement rounds, 5 qubits, 8 detectors, and 1 logical observable (`L0`, final data parity flip). The original CSV was generated only with `after_clifford_depolarization`; its eight syndrome columns are those eight detector bits. The proper inference target is an estimated observable correction from detector data. Residual error is `sampled L0 XOR estimated correction`; neither the sampled label nor the noise-condition label is available to the decoder.

The audit is in [PHASE1_AUDIT.md](PHASE1_AUDIT.md). It documents the original circuit, target semantics, the channel convention, and limitations before this phase's changes.

## Controlled channel design

All six conditions use the same noiseless Stim circuit skeleton and retain 8 detectors and one observable. Noise is inserted after every CX on its participating qubits using Stim `PAULI_CHANNEL_1`; where measurement noise applies, `X_ERROR(p)` is inserted immediately before the same Z-basis `MR`/`M` locations. No detector or observable annotations are changed.

For data channels, `p_data=0.01` is the total non-identity probability per participating qubit after each CX. Composition is `(pX,pY,pZ)` conditional on a fault: X-dominant `(0.8,0.1,0.1)`, Z-dominant `(0.1,0.1,0.8)`, depolarizing `(1/3,1/3,1/3)`, and held-out mixed X/Z `(0.5,0,0.5)`. Measurement-only uses `p_measure=0.01` per measurement. Held-out data-plus-measurement uses depolarizing `p_data=0.01` and `p_measure=0.01` simultaneously. Thus equal numerical p means equal probability per local channel invocation; it does not mean equal total circuit fault opportunity because data and measurement locations occur different numbers of times.

The controlled data channel is a single-qubit Pauli channel after two-qubit gates, not the original two-qubit depolarizing channel. Stim requires `approximate_disjoint_errors=True` to export some multi-component Pauli channels as a DEM; PyMatching comparisons use this documented approximation. The exact channel operations and probabilities are in [experiment_config.json](experiment_config.json) and [run_composition_experiment.py](run_composition_experiment.py).

## Baselines and separation

The final guarded experiment used 10 new seed families (`20271215` onward). Per seed it generated 30,000 training and 10,000 validation shots for each of four trained regimes: X-dominant, Z-dominant, depolarizing, and measurement-only. Validation was split in half: one half selected lookup correction thresholds; the other half selected lookup versus matching. A specialized table was accepted only if it had fewer paired residuals and an exact McNemar p-value below 0.0125 (0.05 Bonferroni threshold across the four trained regimes). Otherwise the policy retained fixed matching.

It evaluated six conditions on 20,000 fresh shots each per seed (200,000 per condition aggregate). Mixed X/Z and data-plus-measurement were withheld from training. Every compared decoder received identical test detector shots. Noise labels and logical targets were retained only in the audit arrays and scoring code.

- **Fixed PyMatching:** DEM calibrated to the nominal depolarizing composition at p=0.01.
- **Noise-informed PyMatching:** DEM built from the actual test composition; oracle reference with hidden condition knowledge.
- **Pooled lookup:** one fixed Q-SHIFT table trained on pooled known regimes.
- **Per-regime lookup:** known-regime tables; for the four trained conditions the static table result is an oracle selection, while held-out conditions use a preceding 500-shot detector-only pilot to choose a table.
- **Adaptive schedule:** causal 500-shot detector windows, two-window confirmation, posterior at least 0.90, log-likelihood margin at least ln(10), and two-window minimum dwell. It selects a per-regime lookup only when the independent validation gate approved it; otherwise it uses fixed matching.
- **Oracle schedule:** noise-informed PyMatching selected immediately from the true current composition. This is an infeasible upper-reference policy, not a deployable decoder.

## Static held-out results

Residual counts below are out of 200,000 test shots per condition, aggregated across ten independent seeds. The paired Δ is pooled lookup minus fixed matching. Paired 95% intervals use discordant-shot counts; exact two-sided McNemar p-values are provided with a six-condition Bonferroni adjustment. Wilson intervals and all per-seed results are in the JSON.

| Condition | Raw L0 flips | Fixed matching | Noise-informed matching | Pooled lookup | Per-regime lookup | Pooled Δ (paired 95% CI); p (adjusted p) |
|---|---:|---:|---:|---:|---:|---|
| X-dominant | 5,293 | 524 | 524 | 558 | 562 | +34 [+0.6, +49.4]; 0.0126 (0.0759) |
| Z-dominant | 1,199 | 33 | 33 | 32 | 46 | −1 [−8.2, +4.2]; 1.000 (1.000) |
| Depolarizing | 3,943 | 306 | 306 | 329 | 323 | +23 [−6.2, +26.2]; 0.0346 (0.2077) |
| Measurement-only | 2,001 | 54 | 54 | 61 | 100 | +7 [+1.1, +12.9]; 0.0156 (0.0938) |
| Held-out mixed X/Z | 2,931 | 166 | 166 | 183 | 209 | +17 [−7.3, +21.3]; 0.0213 (0.1278) |
| Held-out data + measurement | 5,912 | 550 | 550 | 605 | 612 | +55 [+18.9, +67.1]; 0.000039 (0.000234) |

The pooled table had more errors than fixed matching in five of six conditions. Its only lower count was one error on Z-dominant noise, with no evidence of a difference. After correcting for six comparisons, the clearest result is that pooled lookup is worse on the held-out data-plus-measurement mixture. No composition shows a corrected-significant Q-SHIFT gain. Noise-informed PyMatching had the same residual outcomes as nominal matching on these test shots; the correct model did not change matching decisions in this particular small circuit and probability range.

The detector-frequency estimator's preceding-pilot top class was correct on all 10 Z-dominant, depolarizing, and measurement-only pilots; on 8/10 X-dominant pilots it chose X-dominant and on 2/10 it chose depolarizing. All 10 held-out mixed-X/Z pilots mapped to depolarizing; all 10 held-out data-plus-measurement pilots mapped to X-dominant. Thus it detects trained compositions well, but these held-out mixtures collapse to nearest known patterns rather than being identified as novel mixtures.

## Causal time-varying experiment

Each seed used a 12-block schedule with 4,000 shots per block: X-dominant stable period, Z-dominant, depolarizing, return to X-dominant, measurement-only, then return to Z-dominant. There were 480,000 paired stream shots total. The adaptive code received only detector windows; schedule labels were used by separate evaluation/oracle code.

The detector classifier was correct on **94.4%** of 500-shot windows. It recognized a changed trained regime in a mean of about **530 shots** (usually one 500-shot window; some changes took 1,000 shots). Those are regime-recognition delays, not decoder adaptation: the guarded validation gate rejected every lookup strategy, so the deployable policy made **zero switches**. Its decoder adaptation delay is therefore not applicable; it remained fixed by design.

| Stream decoder | Residual errors / 480,000 | Rate | Paired difference vs fixed |
|---|---:|---:|---|
| Fixed PyMatching | 622 | 0.1296% | — |
| Guarded detector-adaptive policy | 622 | 0.1296% | 0; exact paired p=1 |
| True-composition oracle PyMatching | 622 | 0.1296% | 0; exact paired p=1 |

An earlier **rate-only** selector, preserved in `results/composition_results_v3.json`, switched 29 times over the ten seeds and made 589 errors versus fixed matching's 558 on its separate 480,000-shot stream. Its paired test had 58 adaptive-only failures versus 27 fixed-only failures (exact p=0.00102). The new independent-seed guarded experiment shows why the additional validation gate matters: it avoids unsupported switching, but then produces no adaptive benefit.

## Runtime and memory

Local batched decoder calls on Python 3.12 / Stim 1.16 / PyMatching 2.4 / NumPy 2.5 measured about 0.11 microseconds per shot for fixed matching and 0.13 microseconds per shot for lookup at the representative depolarizing condition. Adaptive estimation and switch bookkeeping averaged about 0.32 milliseconds per 500-shot window, or 0.64 microseconds per shot, in addition to decoding. These are local batched software throughput measurements, not single-shot or hardware latency. The guarded selector performed no switches, so measured switching-event cost was zero; regime estimation still ran.

At that condition, approximate Python object storage was 6.1 KB for the pooled table and 15.1 KB for four specialized tables. PyMatching's Python wrapper was 48 bytes, which excludes native graph storage and is not a fair total-memory estimate. Memory fields and per-seed timings are recorded in the results JSON.

## Statistical interpretation and limitations

- Shot-level paired tests compare identical detector shots for two decoders. Seed-level bootstrap intervals resample ten seed-level differences; both appear separately in the result JSON.
- Pooled lookup's paired error differences were +34, −1, +23, +7, +17, and +55 for the six conditions. The latter held-out mixed data/measurement condition remains worse after the six-way Bonferroni adjustment.
- Rare logical failures are still estimated from 200,000 samples per condition. These experiments do not establish low logical-error tails at larger distances.
- The code is distance 3 with 3 rounds and 8 detectors. The regime classifier uses empirical detector-pattern frequencies; it may not scale to larger detector spaces or nonstationary windows shorter than the 500-shot estimator window.
- The current time-varying schedule uses stable blocks with sudden transitions and returns; it does not model gradual drift, correlated bursts, leakage, calibration error, or hardware data.
- All time and memory numbers are software approximations. No hardware compatibility or integration is claimed.
- Earlier simple-selector results, smoke runs, and the initial rate-only pilot are preserved; see [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

## Decision and ranked next experiments

1. **Highest scientific value / moderate feasibility / moderate cost:** train composition-conditioned DEM/PyMatching weight models from calibration circuits, then test detector-only selection among them on fresh seeds. The current lookup fails, but PyMatching itself is the better decoder; adapting its calibrated weights is the most direct test of the hypothesis.
2. **High value / moderate feasibility / higher cost:** increase distance and rounds, and include asymmetric measurement channels plus correlated/time-bursty faults. This checks whether composition inference and matching choices remain distinguishable beyond eight detectors.
3. **Moderate value / high feasibility / low-to-moderate cost:** improve regime inference with a calibrated sequential likelihood-ratio/change detector and tune window length only on development schedules, then test on new randomized schedules. The current 500-shot classifier is accurate on these stable blocks, but the guarded decoder had no specialist worth selecting.

The first best-justified experiment—an independent-seed conservative paired validation gate—was run. It prevented harmful switching but did not produce adaptation. The next phase should focus on alternative PyMatching weight models rather than further tuning the current lookup threshold. The run configuration, raw data, plots, and failed pilots are preserved in this directory.
