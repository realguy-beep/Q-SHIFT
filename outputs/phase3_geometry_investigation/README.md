# Q-SHIFT Phase 3A — Surface-Code Pilot

This is a separate, bounded pilot directory. Phase 1 and Phase 2 files and results are unchanged. The pilot asks whether a new code geometry causes composition-specialized PyMatching models to change logical-observable corrections.

## Reproduce

Use Python with Stim, PyMatching, NumPy, and Matplotlib installed. From this directory run:

```powershell
python run_phase3_pilot.py --output phase3a_surface_pilot_new.json
```

The script refuses to overwrite an existing result name or associated raw files. The committed pilot used three seeds and 12,000 shots per condition per seed (144,000 test shots total). To rerun the exact pilot, use `--output phase3a_surface_pilot_v4.json` only in a fresh copy of this directory; this directory already contains that run.

## Contents

- `config.json`: geometry, noise convention, compositions, and seeds.
- `run_phase3_pilot.py`: circuit transformation, DEM construction, paired evaluation, and graph generation.
- `results/phase3a_surface_pilot_v4.json`: validation, decoder metadata, aggregate and per-seed data.
- `raw/phase3a_surface_pilot_v4_seed_*.npz`: paired test detectors and observable labels for audit only.
- `raw/manifest_phase3a_surface_pilot_v4.json`: raw file sizes and SHA-256 hashes.
- `figures/phase3a_surface_pilot_v4_residual_rates_with_intervals.png`: residual rates with Wilson 95% intervals.
- `REPORT.md`: methods, results, interpretation, and Phase 3B recommendation.

The `v1` result files are intentionally retained as a failed development attempt. They used composition fractions as unconditional channel probabilities, producing invalidly high noise; they are excluded from the report's findings. `v2` and `v3` are corrected checkpoints. `v4` adds the cross-condition circuit-structure hash assertion and is the reported run.
