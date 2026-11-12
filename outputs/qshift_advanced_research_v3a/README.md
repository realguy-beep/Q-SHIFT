# Q-SHIFT Phase 3A joint estimator

This package implements detector-only Candidate B and a source-faithful **population-limit counterpart** of Candidate A. It does not sample detector histories, evaluate a decoder, or estimate logical error.

## Reproduce templates and deterministic checks

From repository root:

```powershell
python outputs/qshift_advanced_research_v3a/generate_templates.py
python -m unittest discover -s outputs/qshift_advanced_research_v3a/tests -v
python outputs/qshift_advanced_research_v3a/benchmark_estimators.py
```

`generate_templates.py` uses deterministic single-fault signatures and parity algebra to build the 21×11×45 exact-categorical template surface and the separate approximate-DEM surface. It never invokes a Stim sampler. It writes the versioned `template_bank_v1.json`.

## Estimate from detector observations

```python
from outputs.qshift_advanced_research_v3a.qshift_estimators import (
    CandidateA, CandidateB, TemplateBank,
)

bank = TemplateBank.load(
    "outputs/qshift_advanced_research_v3a/template_bank_v1.json"
)
detector_history = ...  # binary array shaped (shots, 40), detector bits only
baseline = CandidateA(bank, "exact_categorical").estimate(detector_history)
joint = CandidateB(bank, "exact_categorical").estimate(detector_history)
print(baseline.to_dict())
print(joint.to_dict())
```

To compare the DEM approximation, select `"approximate_dem"` explicitly. The two families have distinct template means and scale vectors. The bank records Stim version, gate p, circuit, DEM conversion flags, detector-pair map, reviewed source checkpoint and template grids. Gate p is fixed to `.003`; the estimator does not estimate gate noise.

## Objective and limits

Candidate A uses five burst knots, fixed measurement p `.003`, piecewise-linear interpolation and the source `GRID_STEP=.00001`. Its templates and pooled feature scales are deterministic population values, so it is not a sampled calibration run. Pooled population scales assume equal weighting of the five template batches, matching equal-sized calibration batches. Candidate B bilinearly interpolates the established `.001` two-parameter template lattice, searches both parameters at `.0001`, minimizes the 45-feature mean standardized squared residual and clips to the declared rectangle. Exact floating-point score ties choose lower burst p, then lower measurement p, matching the published row-major `argmin` behavior.

Population-vector recovery verifies implementation and objective wiring only. Finite-history bias/variance, calibration uncertainty, temporal drift, gate mismatch, out-of-model behavior and decoder consequences remain unvalidated. The future finite-history protocol is in `DEVELOPMENT_STUDY_PROTOCOL.md`; no sampling is authorized by this package.

The guarded study executor is `run_finite_history_study.py`. It samples in chronological 100-shot blocks. At each eligible boundary, it computes all arms from the same trailing detector-only window before asking Stim for the next block. Only detector bits are returned; observables are not requested.

The runner requires a separately prepared approval record with schema `qshift-finite-history-approval-v2`. It binds SHA-256 values for the protocol, configuration, template bank, runner, estimator, analysis script, template generator, circuit builder, runtime fingerprint (Python/NumPy/Stim versions), and seed manifest; it also binds the seed manifest ID, development-only scope, exact approved condition/split allocation, root/shot/memory/CPU limits, expiry, approver, and approval reference. Missing or mismatched fields fail closed. No approval record or production seed manifest is included in this package.

The output directory is a resumable run directory. Each completed root is atomically written with a payload checksum and seed-entry hash, then indexed in `RUN_MANIFEST.json`. Valid orphan root checkpoints are adopted after interruption. Partial temporary checkpoint files are retained under `incomplete_checkpoints/` for audit and the uncompleted root is rerun. Corrupt or mismatched completed checkpoints, completed results, and manifests are rejected. Resume by rerunning the same command with the same approved inputs and output directory; existing completed roots are verified and skipped.

Example invocation after separate protocol and run approval:

```powershell
python outputs/qshift_advanced_research_v3a/run_finite_history_study.py `
  --config outputs/qshift_advanced_research_v3a/finite_history_study_config.json `
  --templates outputs/qshift_advanced_research_v3a/template_bank_v1.json `
  --seed-manifest outputs/qshift_advanced_research_v3a/approved_development_seed_manifest.json `
  --authorization-record outputs/qshift_advanced_research_v3a/approved_run_record.json `
  --output-dir outputs/qshift_advanced_research_v3a/runs/approved_run_001
```

Neither authorization nor seed file is included. The approval record must be created only after the exact development-only seed manifest exists, so its identity and SHA-256 can be checked. Do not run this command until the current protocol and run have separate explicit approval. Unit tests construct short-lived test-only approval and seed fixtures in temporary directories and use mocked detector blocks; those fixtures are not experiment authorizations.

`finite_history_pilot_config.json` is a separate, unauthorized pipeline-pilot proposal with two development roots per frozen condition (10 roots total). It preserves the conditions, windows, estimators, and shot schedule but omits the held-out split and is not for primary inference. Its own config hash and a separately approved 10-root seed manifest must be bound into a fresh approval record before use. No pilot seed manifest is included.

After an authorized run, the deterministic root-level Welch analysis is:

```powershell
python outputs/qshift_advanced_research_v3a/analyze_finite_history_study.py `
  --results outputs/qshift_advanced_research_v3a/runs/approved_run_001/finite_history_results.json `
  --output outputs/qshift_advanced_research_v3a/runs/approved_run_001/analysis_summary.json
```
