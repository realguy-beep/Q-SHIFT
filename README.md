# Q-SHIFT

**Q-SHIFT is a simulation-based research prototype for studying quantum error-correction decoding under changing and structured noise.** It uses Stim to generate circuit-level detector data, PyMatching for conventional decoding, and small neural models for controlled comparisons. It has not been connected to quantum hardware.

## Current status

The project demonstrates a working local simulator, decoder and training dashboard, reproducible paired-evaluation workflows, and extensive audit tooling. It has **not established a practically meaningful, confirmatory adaptive or neural-decoder improvement over a strong fixed PyMatching baseline**. A new development comparison found adaptive and pooled detector-calibrated fixed decoding were very close on nonzero synthetic-burst conditions. The original pooled calibration call had a confirmed protocol deviation; a separately frozen reconstruction passed saved-array verification, but this is not a clean confirmatory execution. The geometry-preserving CNN improved on an earlier pooled CNN in a small development study, but remained worse than PyMatching.

See [RESEARCH_STATUS.md](RESEARCH_STATUS.md) for the current evidence summary and [EXPERIMENT_INDEX.md](EXPERIMENT_INDEX.md) for study locations, audit state, seed records and reproduction references.

## Prototype architecture

```text
Stim circuit and configured noise
              │
              ▼
Detector samples + logical-observable labels
              │
      ┌───────┴────────┐
      ▼                ▼
PyMatching bank    Neural candidates
      └───────┬────────┘
              ▼
Paired evaluation, audits and saved reports
```

The local dashboard in `dashboard/` offers bounded simulation/training workflows, status and GPU telemetry. A *decoder* is a method that infers a logical correction from detector outcomes. Adaptive selection and online-weight approaches have been investigated, but the tested versions did not show reliable gains over fixed decoding. The dashboard and all results are software/simulation work, not a hardware interface.

## Installation

Use Python 3.12 in a virtual environment. Install the package requirements, then install a PyTorch build appropriate to the local CPU/CUDA driver. PyTorch is deliberately not pinned in `dashboard/requirements.txt` because CPU and CUDA wheels differ.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r dashboard\requirements.txt
# Install the suitable PyTorch wheel separately using the official PyTorch instructions.
```

Start the dashboard from the repository root:

```powershell
python dashboard\run_local.py
```

Open `http://127.0.0.1:8765`. The server is configured for local use. CUDA readiness is based on PyTorch's CUDA availability; GPU telemetry is a separate reading. Without a CUDA-enabled PyTorch installation, supported training runs use CPU.

## Tests and bounded diagnostics

From the repository root:

```powershell
python -m unittest discover -s dashboard\tests -v
python -m unittest discover -s outputs\phase3a_controller_repair\tests -v
python -m unittest discover -s outputs\phase3a_correlated_noise_preflight -p "test_*.py" -v
python outputs\phase3a_correlated_noise_preflight\run_preflight.py
python outputs\phase3a_correlated_noise_preflight\dem_pair_screen.py
python outputs\phase3a_correlated_noise_preflight\verify_phase3a_manifest.py
```

The Phase 3A commands above are small diagnostic checks. Other reproduction instructions live with each frozen study. Do not rerun a frozen experiment in its existing output directory; use its documented procedure and a new, screened output allocation when a new run is explicitly authorized.

## Research record and data policy

`outputs/` contains historical protocols, negative findings, reports, code, manifests and local raw evidence. The `.gitignore` intentionally excludes raw shot archives, checkpoints, local runtime state, logs and known multi-megabyte per-sample JSON payloads without ignoring the whole `outputs/` tree. Ignoring a file does not delete it; the local research evidence stays in place. Small reports, configurations, source, tests, manifests and result summaries remain eligible for version control.

The independent-test allocation must remain sealed unless a specific frozen protocol authorizes its evaluation. Never commit test samples, labels, predictions or credentials. Do not describe simulated measurements as hardware results.

## Milestones

- **Phase 1–3:** lookup, regime-specialist and noise-composition studies found that classification or specialization alone did not reliably improve decoding; several initial positive-looking results did not replicate or failed multiplicity controls.
- **Phase 4A/4B:** detector-calibrated matching improved the measurement-heavy test condition in two related studies, with Phase 4B carrying a documented template-generation deviation. The effect did not generalize across all conditions in the later Phase 4C study.
- **Phase 4C / Phase 5:** pooled fixed decoding remained competitive; the equal-regime recovered Stage 2 primary comparison was near zero. Adaptive selection, online reweighting and the tested neural models have not shown a reliable gain over the strong fixed baseline.
- **Current Phase 3A preflight (controller/noise work):** future-run finalization repair and a small synthetic cross-location burst preflight passed. It is separate from the earlier surface-code Phase 3A studies; numbering is retained as found in historical files. No Phase 3B production sampling has begun.
- **Strong fixed-baseline burst comparison:** a separate paired 3.66-million-shot development study compared nominal fixed, pooled detector-calibrated fixed, a safety-constrained fixed fallback, detector-profile adaptation and a privileged true-noise reference. A confirmed deviation in the original pooled-calibration call led to a separately frozen reconstruction. Saved-array verification passed, but the result is not a clean confirmatory execution; see the final interpretation report.

See [the strong-baseline interpretation](outputs/strong_fixed_baselines_v1/FINAL_RESULTS_AND_INTERPRETATION.md) and [the experiment index](EXPERIMENT_INDEX.md) for counts, uncertainty and audit limits. The corrected adaptive-versus-pooled-fixed difference is small relative to the stated practical benchmark; the safety-constrained fixed rule fell back to nominal after validation. Stage 5 evidence remains unchanged, and no sealed Stage 5 outcomes were accessed by this study. This project does not claim novelty or superiority merely from having implemented candidate architectures.
