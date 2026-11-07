# Q-SHIFT Reproducibility Guide

## Scope

This is an evidence-synthesis and documentation pass. No simulations were run and historical data were not changed. Phase reports, runner source, structured results, previous audits, and the 208-file handoff inventory were consulted. This package does not claim a new replay of every historic shot array.

## Artifact map

- `outputs/phase4a_model_adequacy/`: five-round circuit, calibration, validation/test runner, results, audit.
- `outputs/phase4b_replication/`: independent measurement-heavy repeat and raw test checkpoints. Fresh templates were used despite a written reuse protocol.
- `outputs/phase4c_strong_baselines/`: Stage 1 frozen baseline selection; `stage2/` contains plan, bundles, recovery analysis, and results.
- `outputs/phase4c_strong_baselines/adaptive/`: controller, decoder bank, evaluation, schedules, tests, v2/v3 and Phase 5D/5E evidence.
- `outputs/master_project_handoff/`: file inventory, experiment registry, consolidated report, negative findings, and methodology notes.

## Existing reproduction commands (not run for this package)

Run only after reading the matching frozen config and use a new output location; do not write into historical result folders.

```powershell
python outputs/phase4a_model_adequacy/run_phase4a.py
python outputs/phase4b_replication/run_phase4b.py
python outputs/phase4c_strong_baselines/run_stage1.py
python outputs/phase4c_strong_baselines/adaptive/run_phase5e.py
```

Stage 2 `stage2/analyze_saved_checkpoints.py` analyzes saved test bundles. It cannot recreate calibration arrays that were not stored.

## Method and software

The primary circuit is Stim `surface_code:rotated_memory_z`, distance 3, five rounds. Gate/measurement probability candidates are the 3x3 grid over 0.001, 0.003, and 0.006. Stim samples detector data and one logical observable; PyMatching decodes from decomposed DEMs. Detector-only fitting uses smoothed template marginal profiles, a composite Bernoulli score, and deterministic grid-order tie-breaking. Labels are reserved for validation/test residual scoring. Residual error is sampled observable XOR predicted correction. Paired comparisons share identical detector shots.

Phase 5E reports Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3. Stage 2 primary analysis uses equal regime weighting, 100,000 paired root-cluster sign-flip assignments (seed 74000001), and 100,000 regime-stratified bootstrap draws for its 95% interval.

## Unresolved gaps and inconsistencies

- Stage 2 has 60 roots and 1.8M held-out shots; saved predictions and counts were independently checked. Calibration arrays are absent, so calibration selection cannot be regenerated end-to-end.
- Phase 4B fresh-template generation deviated from its frozen reuse protocol.
- Phase 1 report/JSON per-regime totals disagree. Phase 2 report prose says 2,402 noise-informed errors while table and JSON sum to 2,401; disputed totals are not headline claims.
- Phase 3A corrected revisions share seed bundles; Phase 3B is the independent replication.
- Phase 5E prose counts disagree with executable source/JSON; this package uses 4x3 dynamic accounting.
- There are no hardware results, integration measurements, or end-to-end latency data.

## Verified references

1. C. Gidney, "Stim: a fast stabilizer circuit simulator," *Quantum* 5, 497 (2021). DOI 10.22331/Q-2021-07-06-497. https://arxiv.org/abs/2103.02202
2. O. Higgott, "PyMatching: A Python Package for Decoding Quantum Codes with Minimum-Weight Perfect Matching," *ACM Transactions on Quantum Computing* 3(3), Article 16 (2022). DOI 10.1145/3505637. https://doi.org/10.1145/3505637
3. A. G. Fowler, M. Mariantoni, J. M. Martinis, and A. N. Cleland, "Surface codes: Towards practical large-scale quantum computation," *Physical Review A* 86, 032324 (2012). DOI 10.1103/PhysRevA.86.032324. https://arxiv.org/abs/1208.0928
