# Q-SHIFT Phase 3B — Independent Replication

This directory contains the pre-registered independent replication of the Phase 3A X-specialist result. It preserves all earlier phase directories.

## Reproduction

Requires the sibling Phase 3A project at `../phase3_geometry_investigation` plus Python with Stim, PyMatching, NumPy, and Matplotlib. The runner pins the Phase 3A source and v4 result hashes and refuses silent drift. Run from this directory in a clean copy of the Phase 3B directory:

```powershell
python run_phase3b_replication.py
```

The runner refuses to overwrite any existing result/raw artifacts. The frozen run uses 20 independent seed roots, 30,000 shots per seed and each of four conditions (2.4 million total test shots). Raw arrays are checkpointed after each seed. Exact inputs and protocol hash are in `CONFIG.json` and `PRE_REGISTERED_PROTOCOL.md`.

## Files

- `PRE_REGISTERED_PROTOCOL.md` — frozen primary endpoint, seeds, shot count, and analysis.
- `CONFIG.json` — configuration plus protocol and source hashes.
- `run_phase3b_replication.py` — reproducible runner; imports the exact Phase 3A circuit/noise and decoder definitions.
- `RESULTS.json` — aggregate, per-seed, model, runtime, and integrity results.
- `per_seed_results.csv` — decoder outcomes and paired differences for each seed and condition.
- `statistical_analysis.json` — primary seed-level inference and Holm-adjusted exploratory tests.
- `raw_data/` — compressed detectors and observable labels for all 20 seeds.
- `SHA256_MANIFEST.json` — checksums for protocol, code, input source, results, plots, and raw data.
- `plots/` — primary seed differences and decoder error-rate figures.
- `REPORT.md` — full scientific interpretation and limitations.

This phase ends with the replication report. It does not implement adaptive selection or start Phase 3C.
