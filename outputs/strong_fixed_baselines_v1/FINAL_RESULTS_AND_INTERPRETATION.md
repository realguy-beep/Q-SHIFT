# Strong fixed baselines and detector-profile adaptation: final development report

**Classification:** development feasibility study with a declared runner deviation; not confirmatory.

**Final reconstruction freeze:** `POSTRUN_RECONSTRUCTION_FREEZE_V1.json` (SHA-256 `7d8b50218118ec0c56f3930efe3804d6cf1fb1669f720353620d06e910fe9aaf`).

**Independent numerical verification:** `POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json` (`audit_status: PASS`; not an independent institution or external replication).

**Stage 5:** no Stage 5 samples or sealed outcomes were accessed by this study.

## Question and design

The study asked whether detector-profile adaptation adds value after comparison with stronger fixed matching methods. It reused the audited distance-3, five-round rotated Z-memory Stim circuit with 40 detectors, one logical observable, balanced gate/measurement noise at 0.003, and a synthetic paired-X burst `CORRELATED_ERROR(p) X8 X10` inserted after the five measurement boundaries. Burst probabilities were 0, 0.004, 0.008, 0.012 and 0.016. The burst is a controlled simulator mechanism, not a hardware-calibrated crosstalk model.

The five arms used identical paired evaluation detector and observable arrays: nominal fixed PyMatching (`p=0`); one pooled detector-calibrated fixed matcher; a safety-constrained fixed candidate with a nominal fallback; per-root detector-profile adaptive matching; and a privileged matcher given the true simulated burst probability. The privileged reference is not deployable. The safety candidate was selected with a separate development partition and checked against an independent validation partition. Calibration data and evaluation data were separate. The adaptive arm used per-root detector-only calibration; pooled static used the aggregate calibration detector rows.

The study generated 3,660,000 unique shots: 60,000 template; 450,000 selection; 450,000 validation; 1,200,000 final calibration; and 1,500,000 paired final-development evaluation shots. The 600 evaluation roots comprise 120 roots per burst probability and 2,500 evaluation shots per root.

## Material implementation deviation and reconstruction

The first runner's pooled-estimator call used final-calibration batches tagged with their generating probabilities when fitting detector profiles. The frozen protocol required profile fitting from independent template batches at `p={0,0.01,0.02}`, followed by estimating one pooled probability from final-calibration detector rows only. This is a confirmed implementation deviation. The original `p=0.00831` estimate and predictions remain preserved as legacy outputs and are excluded from corrected comparisons.

Before final evaluation labels were used in the reconstruction, a separate reconstruction protocol and hash freeze were written. The reconstruction refit profiles using only independent template detectors, estimated a pooled `p=0.00804` using the pooled calibration detectors, and independently rebuilt and re-decoded the saved evaluation detector arrays. Both pooled probabilities happened to produce identical decoder predictions on all 1.5 million saved evaluation shots. That agreement does not undo the deviation or make the original runner compliant. The result is a protocol-consistent reconstruction from already sampled development arrays with a disclosed deviation, not a clean run or independent confirmation.

## Reconstructed final-development results

Every condition has 300,000 paired evaluation shots. LER is errors divided by shots.

| Burst p | Nominal fixed errors (LER) | Pooled static errors (LER) | Safety static errors (LER) | Adaptive errors (LER) | Privileged reference errors (LER) |
|---:|---:|---:|---:|---:|---:|
| 0.000 | 1,444 (0.481333%) | 1,581 (0.527000%) | 1,444 (0.481333%) | 1,446 (0.482000%) | 1,444 (0.481333%) |
| 0.004 | 1,719 (0.573000%) | 1,598 (0.532667%) | 1,719 (0.573000%) | 1,594 (0.531333%) | 1,596 (0.532000%) |
| 0.008 | 2,122 (0.707333%) | 1,771 (0.590333%) | 2,122 (0.707333%) | 1,773 (0.591000%) | 1,771 (0.590333%) |
| 0.012 | 2,344 (0.781333%) | 1,746 (0.582000%) | 2,344 (0.781333%) | 1,740 (0.580000%) | 1,740 (0.580000%) |
| 0.016 | 2,523 (0.841000%) | 1,692 (0.564000%) | 2,523 (0.841000%) | 1,665 (0.555000%) | 1,666 (0.555333%) |
| **All five conditions** | **10,152 / 1,500,000** | **8,388 / 1,500,000** | **10,152 / 1,500,000** | **8,218 / 1,500,000** | **8,217 / 1,500,000** |

The safety rule selected `p=0.004` in development selection, but its validation one-sided 95% upper bound for zero-burst excess was `+0.00056`, exceeding the frozen `+0.0002` limit. It therefore correctly fell back to `p=0`; the final safety-static results equal nominal fixed. Pooled fixed captured most of the nonzero-burst benefit but had a zero-burst excess of `+0.0004567` (one-sided 95% root-bootstrap upper `+0.0005233`), above that same practical harm limit.

## Adaptive comparison and uncertainty

The prespecified equal-weight mean over the four nonzero burst conditions for **adaptive minus pooled static** was `−0.00002917` absolute LER (about `−0.00292` percentage points). The 100,000-resample, condition-stratified root-cluster percentile interval was `[−0.00005167, −0.00000750]`. Per-condition effects were −0.00001333, +0.00000667, −0.00002000 and −0.00009000 at p=0.004, 0.008, 0.012 and 0.016, respectively. This descriptive interval is conditional on these selected/calibrated models and this simulated development sample; there are no confirmatory p-values. The point estimate is much smaller than the stated 0.0002 absolute-LER practical-benefit benchmark.

Adaptive versus pooled fixed produced the following paired error discordances (adaptive-only failures / pooled-only failures): p=0: `6/141`; .004: `60/64`; .008: `4/2`; .012: `1/7`; .016: `16/43`. Across nonzero conditions this is 81 adaptive-only and 116 pooled-only failures, a net 35 fewer adaptive errors across 1.2 million shots. At p=0 adaptive had two more errors than nominal (`+0.00000667`); its descriptive one-sided 95% root-bootstrap upper bound was `+0.0000200`, below the 0.0002 benchmark.

For context, adaptive minus the safety-static fallback averaged `−0.00161333` over nonzero conditions (95% descriptive root-bootstrap interval `[−0.00170250, −0.00152417]`). This large contrast is mostly the consequence of the safety rule reverting to burst-blind nominal matching; it is not evidence that adaptation beats the stronger pooled decoder. The pooled and adaptive arms had nearly identical nonzero-condition LERs, while the pooled arm failed the zero-burst safety benchmark.

## Interpretation, limitations and decision

This run shows a real tradeoff within one narrow synthetic burst model: one pooled fixed matcher performs much better than nominal under bursts but incurs measured harm when bursts are absent; a conservative static rule avoids that harm by reverting to nominal; detector-profile adaptation tracks the changing settings and is close to pooled fixed on nonzero conditions. The study does **not** establish a practically meaningful adaptive advantage over the pooled fixed arm, generalization to other noise families or code distances, or performance on hardware.

The primary protocol limitation is the confirmed pooled-calibration implementation deviation. The corrected pooled value and predictions were reconstructed after the run from saved development calibration/evaluation arrays under a separate freeze; this is transparent but not equivalent to a clean prospective execution. Bootstrap intervals do not repair that limitation or establish external validity. The privileged reference uses hidden generating p and is only a diagnostic. The injected pair error is synthetic, and DEM decomposition approximations remain part of the modeling stack. Stage 5 evidence remains separate and unchanged.

**Decision:** retain the implementation as reproducible development evidence and preserve the negative/ambiguous conclusions. Do not claim Q-SHIFT superiority or proceed directly to confirmatory sampling. Any next study should first correct the pooled-calibration path, freeze it prospectively, keep a strong pooled fixed arm and a zero-burst no-harm gate, and evaluate on fresh independent roots.

## Reproduction and audit pointers

- Protocol/config/freeze: `STRONG_BASELINE_PROTOCOL.md`, `experiment_config.json`, `PRETEST_FREEZE_V14.json`.
- Sampling history and failure preservation: `STUDY_FAILURE_V1.md`, `run_recovery_v5/status.json` (local ignored run record).
- Deviation/reconstruction rules: `POSTRUN_AUDIT_ATTEMPT_V1.md`, `POSTRUN_RECONSTRUCTION_PROTOCOL_V1.md`, `POSTRUN_RECONSTRUCTION_FREEZE_V1.json`.
- Independent saved-array verification: `verify_reconstruction_outputs_v1.py`, `POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json`.
- Detailed tabulations: `report_reconstruction_v1/RESULTS.md`, `PER_CONDITION.csv`, `PER_ROOT.csv`, and `RESULTS.json`.
- Tests: `python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v`.

The archive data and corrected per-shot prediction files are local and Git-ignored. The report summarizes saved evidence; it does not replace the raw archives or their audit manifests.
