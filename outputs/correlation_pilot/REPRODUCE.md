# Reproduce the correlation-aware pilot

The pilot is a development feasibility experiment. It uses Stim 1.16.0 and PyMatching 2.4.0 in the environment recorded in `SMOKE_PREFLIGHT.json` and `RUN_TIMINGS.json`.

## Before execution

1. From this directory, run `python preflight_correlation_pilot.py`. It screens all candidate seeds against recoverable historical records, validates the Phase 2B circuit/DEM files and matching graph fingerprints, tests PyMatching's correlation API, runs a deterministic 4,096-shot-per-stratum smoke, performs statistical-code self-checks, and records storage/runtime estimates.
2. Run `python -m py_compile preflight_correlation_pilot.py run_correlation_pilot.py analyze_correlation_pilot.py freeze_pilot.py smoke_test_correlation_pilot.py`.
3. Run `python smoke_test_correlation_pilot.py` for the actual runner’s decoder-call pattern at 256 diagnostic shots per stratum. This is not part of the 720,000 development shots.
4. Run `python freeze_pilot.py`. It writes `SEED_INVENTORY.json` and a no-overwrite `PRETEST_FREEZE.json`; verify that no test checkpoint exists at this point.
5. Run `python run_correlation_pilot.py`. The runner rejects any changed frozen input, writes one atomic checkpoint per stratum/root and resumes only if an existing checkpoint has the expected root metadata and schema.
6. After all 72 checkpoints exist, run `python analyze_correlation_pilot.py`. It independently unpacks detector arrays, reconstructs all four decoders, exactly re-decodes stored detector data, checks predictions and hashes, recomputes all residual counts and paired statistics, and writes the reports.

## Expected outputs

- `PRETEST_FREEZE.json`, `SEED_INVENTORY.json`, `SMOKE_PREFLIGHT.json`, `SMOKE_TEST.json`, and statistical self-check evidence.
- `checkpoints/stratum_XX_root_YY.npz` for 72 roots, containing packed 40-detector data, one observable bit per shot, four paired predictions and root metadata.
- `RUN_PROGRESS.json` and `RUN_TIMINGS.json`.
- `RESULTS.json`, `RESULTS.md`, `STATISTICAL_ANALYSIS.md`, `LIMITATIONS.md`, `PER_ROOT_RESULTS.csv`, `PER_STRATUM_RESULTS.csv`, `SECONDARY_COMPARISONS.csv`, `DECODER_DISAGREEMENTS.csv`, `INDEPENDENT_EVIDENCE_AUDIT.md`, `CHECKPOINT_HASHES.json`, and `MANIFEST.json`.

The analysis is development-only. Do not reuse these pilot labels to tune a policy and then describe the same data as independent validation. Preserve all failures and the rejected seed namespace records.

