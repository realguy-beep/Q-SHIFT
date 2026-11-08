# Q-SHIFT v2 bounded development pilot

Status: exploratory development only; not independent confirmation
Branch/worktree: `qshift-v2-dev` at `C:\Users\LENOVO\Documents\Codex\2026-11-08\qshift-v2-dev`
Base commit: `0146f756d5d419b0f5afa6d99c7a3dfac38361eb`
Research input: `Q-SHIFT_research_report_2026-11-08.md`

## Decision

**Do not launch the 11.736M-shot study yet.** The small pilot confirms that ordinary and explicitly correlation-aware PyMatching are distinct, reproducible modes on this DEM, and that the causal controller runs on chronological detector-only blocks. It does not show that change-triggering improves on batch calibration or the EWMA arm. The pilot is severely underpowered: 10 streams, only two per schedule, 300 scored shots each. Its apparent LER differences are a few logical failures. No confidence interval or superiority claim is warranted.

Repair the event controller and evaluate false alarms/delay/cost on a somewhat larger bounded development pilot first. The current controller's GLR alarms were frequent and only four alarms led to accepted graph switches. The chosen threshold was uncalibrated. The EWMA profile arm made fewer errors in ordinary mode and tied the event arm in explicit correlation mode. This argues for refinement and measurement of cost before committing to the full study.

## Source and decoder-mode audit

The inspected Stage 4 graph builder creates a DEM with `decompose_errors=True` and `approximate_disjoint_errors=True`, then constructs PyMatching using `enable_correlations=True`. The shared `decode_prediction` calls `matcher.decode_batch(d)` with no keyword; the installed PyMatching 2.4.0 signature defaults its own decoding flag to `False`. The saved Stage 4 runners and recovery auditors use the same omitted decode flag. Historical records remain unchanged.

The DEM contains higher-order detector mechanisms that have decomposition separators. On the current distance-3, five-round circuit, the flattened DEM has 586 errors at burst p=0 and 591 at p=.01; each has 317 mechanisms with more than two detector targets and 444 decomposed mechanisms. Thus correlation-aware decoding is applicable: both flags are accepted and the model carries decompositions. The injected XX burst itself is graphlike. This does not imply the two modes must differ on every syndrome.

The v2 pilot constructs and decodes with the same explicit flag per arm. It generated identical syndrome streams for ordinary and correlation-aware arms. Across all seven decoder policies (21,000 scored predictions per mode), correlation-aware mode had 115 logical errors versus 99 in ordinary mode, a descriptive increase of 16 errors. This tiny, heterogeneous sample is not evidence that ordinary decoding is generally better; it shows the flags matter and the comparison needs more roots and a prespecified hypothesis.

## Pilot protocol and reproducibility

The run used Stim 1.16.0 and PyMatching 2.4.0. One fixed development profile was generated at p={0,.005,.01,.015,.02}, 300 detector-only shots per knot. Separately, 300 labeled shots at each knot selected a static p by total development logical errors; p=.005 was selected (counts: p=0: 8; .005: 4; .01: 4; .015: 4; .02: 5). This static-selection set is tiny, so the “strong static” comparator is only a feasibility baseline, not reliably optimized.

Ten chronological streams were generated: two replicates each of stationary p=.01, step up .002→.018, step down .018→.002, smooth sinusoidal drift .01±.008, and a one-block transient .018 on a .002 background. Each stream had 100 initial detector shots used as detector-only calibration and 300 scored shots. The same stream went to all methods. Total was 7,000 unique generated shots (1,500 profiles, 1,500 static-selection, 4,000 streams); no held-out labels entered estimator/controller decisions. Scored outcomes exclude calibration shots.

The event arm used the current 45-feature profile estimator over a 0.02 probability range, cached graphs at p={0,.005,.01,.015,.02}, a six-bin count of co-firing nominated detector pairs, GLR threshold 8, 4-block maximum history, 2-block minimum dwell, and 0.001 p hysteresis. Its estimate callback fit the profile estimator on the latest 100 past detector shots. Updates occur after decoding the current 50-shot block and affect later blocks. The block summary and profile objective differ; the summary is a lightweight change statistic only.

Other arms: fixed p=0; development-selected static p=.005; one-time profile estimate from the 100-shot warm-up; privileged exact block-mean true p; trailing 100-shot profile estimate; EWMA-weighted profile estimate (alpha=.08); and periodic profile refit every 100 shots. All use the same cached grid for non-oracle decoders, the same detector data, and the same explicit correlation flag. The oracle builds exact p graphs lazily. Oracle p, labels and schedule are used only outside the adaptive control path.

Run command from repository root: `python -m outputs.qshift_v2_dev_v1.run_pilot`

Correctness test command: `python -m unittest discover -s outputs/qshift_v2_dev_v1 -p 'test_*.py' -v`

Both completed successfully. Three deterministic unit tests cover detector-only pair summaries, invalid category rejection, and future-block update/dwell behavior. The pilot took 6.97 seconds. CSV SHA-256: `3adb7932f14d0336c37be37c970640c72efc9a07ce0826a995e585259c9c2bb0`.

Seed namespace starts at 20,771,108, with deterministic offsets coded in `run_pilot.py`. No Stage 5 paths, data, outcomes or frozen evaluation seeds were opened by this run. A collision check against the complete historical development-seed inventory was not performed, so this allocation needs a preflight before any follow-up. The code reports `independent_test_access=0`; that is a run configuration assertion, not an external audit.

## Actual results

Pooled paired counts across the five scenarios (3,000 scored shots per mode):

| Decoder | Ordinary decode | Explicit correlation-aware decode |
|---|---:|---:|
| Fixed nominal p=0 | 19 / 3,000 (0.633%) | 23 / 3,000 (0.767%) |
| Development-selected static p=.005 | 11 / 3,000 (0.367%) | 16 / 3,000 (0.533%) |
| Batch profile estimate | 16 / 3,000 (0.533%) | 21 / 3,000 (0.700%) |
| Privileged exact true-p | 10 / 3,000 (0.333%) | 14 / 3,000 (0.467%) |
| Trailing-window 100 | 16 / 3,000 (0.533%) | 19 / 3,000 (0.633%) |
| EWMA profile, alpha=.08 | 13 / 3,000 (0.433%) | 20 / 3,000 (0.667%) |
| Event-triggered GLR | 16 / 3,000 (0.533%) | 20 / 3,000 (0.667%) |
| Periodic recalibration | 16 / 3,000 (0.533%) | 19 / 3,000 (0.633%) |

These are descriptive shot aggregates over only two streams per scenario; shots within an adaptive stream are dependent. Do not calculate shot-level inferential p-values from them. The oracle is privileged and not a deployable performance floor. The tiny development-selected static sample makes p=.005 vulnerable to selection noise.

The CSV stores arm-level counts, not per-shot paired logical outcomes. Therefore paired logical-error differences between policies were not computed; shared shot streams make such an analysis possible only after adding paired outcome logging. The ordinary-versus-correlation-aware aggregate also compares matched stream inputs, but its reported difference is a marginal count difference rather than a paired discordance statistic.\n\nThe event controller recorded 12 threshold alarms and 4 accepted switches across 10 streams and both decoding modes; the mode replays use the same observations, so these are duplicate algorithmic exposures, not 20 independent streams. Trailing-window updates counted 32 switches, EWMA .08 counted 51, and periodic updates counted 16. Stationary scenario event switch count was zero in this pilot, but two streams cannot bound false-alarm probability. Response delay, calibration interruption and per-policy CPU/memory were not instrumented in this pilot; the aggregate wall runtime is not a fair per-decoder cost comparison.

Scenario-level summaries and every stream's error, policy and switch counts are in `pilot_results.csv`. These results do not support an improvement claim. In ordinary mode, the event policy tied batch calibration and trailing/periodic methods in total errors; EWMA was 13 versus 16 event errors. In explicit correlation-aware mode event had 20 versus 21 batch and 20 EWMA; this one-error difference is noise at this sample size. The static arm had the fewest errors among deployable methods, but it was selected on only 1,500 development shots.

## Correctness and integrity limitations found

- The first pilot draft incorrectly included calibration data in the LER and let a trailing estimate see its current block. Those outputs were overwritten by a corrected replay before reporting. The final metrics exclude the first 100 calibration shots; the trailing estimator now uses only completed prior blocks.
- The controller's alarm threshold h=8 was selected heuristically, not calibrated for any false-alarm target. It cannot support a false-alarm claim.
- There are two independent streams per schedule. Smooth drift has only 400 total scored time steps per stream, and the transient lasts one 50-shot block. This cannot resolve adaptation delay robustly.
- The baseline profile training set is small and static p selection used the same narrow five-point synthetic family. It is a development-selected comparison, not a strong frozen baseline.
- The pilot changes one simulator seed per newly encountered p segment and samples sequentially within each segment. This is valid for the specified synthetic process but does not model drift within a shot.
- Correlation-aware decoding uses Stim's decomposed DEM and the documented categorical-noise approximation. This is not an exact circuit-level maximum-likelihood decoder.
- Runtime/memory were recorded only at whole-run level, not by policy. The proposed CPU savings criterion remains unevaluated.
- A seed-collision inventory check and independent source replay have not been completed.

## Recommendation

Retain v2 as a separate research branch, but do not yet freeze or run the 11.736M-shot proposal. First fix the GLR alarm calibration and diagnostics, instrument latency and memory by arm, enlarge static-selection data, and add enough independent stationary streams to estimate false alarms. Then run a fresh, preregistered pilot with stream-level uncertainty and held-out drift schedules. If the event method does not beat EWMA/trailing methods in either unconditional LER or a prespecified cost/accuracy tradeoff, stop this controller line. Any later independent confirmation needs a new protocol and new development-disjoint allocation; this pilot is not confirmation.

## Source hashes

SHA-256 at commit preparation:

- `controller.py`: `3CE77C3DA7437D360115CDAA3CA73ADB323E82C8779E905D022997AF684B5020`
- `run_pilot.py`: `859EB3E36ECF23B95CDDD551FAB69CF540E33803C185804C51B29706956F2466`
- `test_controller.py`: `E89AE72B9C16929C3F4A19ABA63F23BD9B844BE701F75224AA8F0BEC41F2F38B`
- `pilot_config.json`: `2FBEF2F5198AE00BB78D879AD0481CC4BBC53C77284D4A5BBA2DB7FC6CA0005F`
- `pilot_results.csv`: `3ADB7932F14D0336C37BE37C970640C72EFC9A07CE0826A995E585259C9C2BB0`
- `pilot_summary.json` (current run; runtime field varies on rerun): `F1B77BE444E708343A335BE3A6FD39C2A4F99A39E11190AC2F9E227F03F7AA3C`
