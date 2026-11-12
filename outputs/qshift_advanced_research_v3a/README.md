# Q-SHIFT Phase 3A joint estimator

This package implements detector-only Candidate B and a source-faithful **population-limit counterpart** of Candidate A. It does not sample detector histories, evaluate a decoder, or estimate logical error.

## Reproduce templates and deterministic checks

From repository root:

```powershell
python outputs/qshift_advanced_research_v3a/generate_templates.py
python -m unittest discover -s outputs/qshift_advanced_research_v3a/tests -v
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

The guarded study executor is `run_finite_history_study.py`. It requires a separate authorization record whose protocol SHA-256 matches the final protocol and a pre-created development-only seed manifest. Example invocation after separate approval:

```powershell
python outputs/qshift_advanced_research_v3a/run_finite_history_study.py `
  --config outputs/qshift_advanced_research_v3a/finite_history_study_config.json `
  --templates outputs/qshift_advanced_research_v3a/template_bank_v1.json `
  --seed-manifest outputs/qshift_advanced_research_v3a/approved_development_seed_manifest.json `
  --authorization-record outputs/qshift_advanced_research_v3a/sampling_authorization.json `
  --output-dir outputs/qshift_advanced_research_v3a/runs/approved_run_001
```

Neither authorization nor seed file is included. Do not run this command until both are supplied under a separately approved protocol.

After an authorized run, the deterministic root-level Welch analysis is:

```powershell
python outputs/qshift_advanced_research_v3a/analyze_finite_history_study.py `
  --results outputs/qshift_advanced_research_v3a/runs/approved_run_001/finite_history_results.json `
  --output outputs/qshift_advanced_research_v3a/runs/approved_run_001/analysis_summary.json
```
