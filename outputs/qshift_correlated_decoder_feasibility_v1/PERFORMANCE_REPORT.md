# Correlated decoder feasibility pilot — attempt report

**Decision: INCONCLUSIVE.** The run stopped at the prespecified calibration-order gate. There are no evaluation predictions, logical error counts, LERs, paired efficacy intervals, or evidence of improvement or harm.

## Frozen question and candidate

The candidate was a synthetic per-round common-cause X event on data qubits 8, 12 and 15 after each MR boundary in the distance-3, five-round rotated Z-memory circuit. It models a hypothetical shared control/crosstalk disturbance; it is not hardware calibrated. The noiseless DEM derived five three-detector, zero-observable signatures. The deterministic fixture check found A/B prediction differences on 88 of 600 constructed background-fault-plus-burst syndromes and none on the 32 burst-subset-only patterns. This establishes some decision sensitivity on fixtures, not accuracy.

The frozen pilot compared a globally pooled fixed correlation-aware PyMatching model (A), per-root profile PyMatching (A2), per-root five-factor enumeration with background PyMatching (B), and a true-q privileged B reference (C). A2 and B used identical per-root detector-only estimates; C alone received generating q. The five-factor hybrid is not exact full-circuit maximum-likelihood decoding.

## Execution outcome

- Source/freeze commit: `bfd971d06d0deadaac965086c3a6cbdca58eeb4b`.
- Pretest freeze SHA-256: `5f5111de8bc8fad30e4f2a904c7bb6fad1d43e767deac0d160f4d95d4e50d711`.
- Attempt: `attempt_001`; watchdog lifetime: 5.265 seconds; no timeout.
- 33/33 Stim calls committed: 3 training + 30 calibration.
- Verified generated shots: 18,000 (3,000 training; 15,000 calibration; 0 evaluation).
- Evaluation archives: 0. No evaluation observables were sampled, read, scored, or used.
- The 33 committed training/calibration archives passed SHA-256 verification; their combined size is 45,494 bytes. The complete local run directory held 37 files totaling 75,928 bytes. Raw arrays remain ignored and local.
- Stim sampling time recorded across calls: 0.0357 seconds; sample-archive writes: 0.6285 seconds. The watchdog's 5.265-second lifetime includes process startup, status writes and calibration analysis. Peak RSS was not persisted for this early-gate exit, so no run peak-memory result is claimed.

The run performed no decoder inference. It did not compute an LER, paired difference, confidence interval, or scientific performance comparison. It did not use Stage 5, sealed data, or any other evaluation data.

## Failure diagnosis from training and calibration detectors only

The committed `BurstRateEstimator.fit` contains this coefficient-order error:

```python
self.intercept, self.slope = np.polyfit(probabilities, rates, deg=1)
```

NumPy returns `[slope, intercept]`. The frozen code therefore stored training slope `0.0006667` as the intercept and training intercept `0.88` as the slope. The actual training feature means were 0.0000, 0.0108 and 0.0176 at q=0, 0.01 and 0.02. Calibration detector-only feature means were 0.00020, 0.00980 and 0.01884. With the reversed coefficients, all 30 per-root estimates clipped to zero; the predeclared strict ordering gate failed and the runner correctly stopped before evaluation.

An offline algebra check on the same training/calibration detector arrays, using the correctly ordered fitted line (`slope=0.88`, `intercept=0.0006667`), yields clipped calibration mean q-hats 0.0000, 0.01038 and 0.0200. This is a diagnosis of the implementation defect only. It was not applied to decoder construction, was not used to choose a model, and does not authorize continuation or establish performance.

**Additional data-handling deviation:** the sampling helper stored observable arrays alongside training and calibration detector arrays. The estimator and calibration path use only detector arrays; the observable columns were not passed to the estimator or any decoder and were not scored. Their unnecessary persistence is recorded as a protocol implementation deviation. No evaluation arrays exist. A corrected future runner should not persist training/calibration observables unless a separately justified use is approved.

## Post-freeze diagnostic bookkeeping deviation

After the pilot stopped, the sampler-free deterministic preflight was run again to recheck the fixture sensitivity. That script rewrites its timing JSON, which is part of the pretest freeze. The new JSON was preserved separately as `deterministic_preflight_postfreeze_recheck.json`; the frozen `deterministic_preflight.json` was restored from commit `bfd971d06d0deadaac965086c3a6cbdca58eeb4b` and its SHA-256 returned to the frozen value `112ad549e8470a76190cdd9ac0aafd400e4be4562fcc9aec83f11a42626c74df`. This is disclosed as a local bookkeeping deviation; no source, protocol, seed, model, or sampling changes were made, and the recheck made zero sampler calls.

## Decision and next action

The outcome is **INCONCLUSIVE**, not NO-GO: deterministic decision sensitivity exists, but the efficacy stage never ran. The failure is attributable to a reproducible coefficient assignment defect, while the small ten-root design would in any case support exploratory rather than confirmatory interpretation.

Do not resume or rerun this frozen attempt. The preserved 18,000 shots and all 33 archive hashes are recorded in `FAILED_ATTEMPT_EVIDENCE_MANIFEST.json`; the original source freeze remains unchanged. Any corrected implementation, decision to reuse the detector arrays, revised handling of stored observables, or new evaluation sampling requires a separately versioned protocol and explicit authorization. No automatic follow-up was launched.

## Reproduction and evidence

From the repository root:

```powershell
python outputs/qshift_correlated_decoder_feasibility_v1/verify_failed_attempt.py
python outputs/qshift_correlated_decoder_feasibility_v1/run_deterministic_preflight.py
```

The first command verifies only the preserved training/calibration archive hashes and detector-derived feature diagnostics. It does not call a sampler or read observable arrays. The second command is sampler-free and reconstructs the deterministic model/fixture comparison. The actual local run directory is ignored at `outputs/qshift_correlated_decoder_feasibility_v1/pilot_runs/attempt_001/`.
