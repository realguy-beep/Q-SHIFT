# Strong-baseline development v1 — execution preflight

**Recorded before study sampling.** Controlling source/configuration/seed freeze: `PRETEST_FREEZE_V6.json` (SHA-256 `e63dbc5806e8dff08b8729a2b425c3ac0870ecb5e44e526ace061e2a0bd87357`).

- Branch: `codex/research-strong-baselines-v1`; base checkout at `ae5ad5bc9ff90db15a1a77b64bf68e9a2b1b4971` before new work.
- Frozen files verified: 23 SHA-256 entries; all matched at preflight.
- Independent seed screen: 25 historical source records, 11,464 recoverable large-integer values; 1,625 total stream IDs (1,603 study streams, two bootstrap streams, 20 non-study benchmark streams); zero collisions; study stream shot sum exactly 3,660,000.
- Tests: `python -B outputs/strong_fixed_baselines_v1/test_experiment.py` — **10 passed**. These tests use synthetic arrays and structural DEM checks; they do not generate study samples.
- Pipeline benchmark: `BENCHMARK_RESULTS_V4.json`; 3,500 benchmark-only shots, excluded from study allocation. Conservative runtime projection 133.33 s; peak observed RSS 708,390,912 bytes; projected archive storage 11,281,679 bytes plus small report/status files; disk reserve requirement 5 GiB.
- Environment: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, SciPy 1.18.1. Immediately before launch: available RAM 5,913,452,544 bytes; free C: disk 263,969,456,128 bytes.
- The new `outputs/strong_fixed_baselines_v1/run/` directory was absent before launch. No study or Stage 5 samples were generated at preflight. No Stage 5 raw arrays or sealed-test artifacts were opened.
- One Python process was visible during the resource-check command itself; this was the preflight command process. No separate experiment worker was running.

Preflight outcome: **PASS to start the bounded development study**. This is not an inference about performance and is not a confirmatory study authorization.
