# Q-SHIFT Phase 3B — Final Experiment-Readiness Report

**Status: implementation-ready for a separately authorized development study. No sampling authorization is granted here.**

Repository branch: `qshift-advanced-research`

Implementation base: `6070fa875a14fe8e4e9b713607dd0f3a4e6e1c23`

Package: `outputs/qshift_advanced_research_v3a/`

## Scientific integrity

- Candidate A remains the source-faithful **population-limit counterpart**: five burst-probability knots, fixed measurement probability `.003`, piecewise-linear interpolation, the `.00001` burst fit grid, and the equal-weight population-profile scale construction.
- Candidate B remains the joint two-parameter standardized 45-feature objective on the `.0001` by `.0001` fitting lattice over `[0,.020]×[0,.010]`, with row-major tie-breaking (lower burst probability, then lower measurement probability). The 201×101 fit surface has 20,301 candidates. This phase caches its interpolation/scaling and vectorizes score computation; it does not change the objective or grid.
- Exact categorical and approximate DEM templates remain separate. Detector features remain D0–D39 followed by the five existing pair-conjunction features. The deterministic feature-map implementation was changed to allocate/fill one output array; its mapping is unchanged.
- The primary estimand, paired root unit, 1,000-shot primary window, measurement step-up/down strata, root allocations, gate mismatch controls, and analysis rule remain as specified in the prior protocol. The implementation now computes an estimate at boundary `t` from only `[t-N,t)`, then requests the next block from Stim. The first primary post-transition scoring boundary remains `t >= 5,000 + N`.
- The only existing Phase 3A files edited are its README and proposed protocol, with this technical implementation addendum. `finite_history_study_config.json`, the template bank, historical Phase 3A validation report/manifest, all Phase 2C materials, frozen files, other branches, and PR #1 were not changed. The pre-existing Phase 2C preservation hash test passes.
- No protected or Stage 5 outcome data was accessed. No Stim sampling, decoder evaluation, logical-outcome calculation, or production seed generation occurred. Full-run tests used short-lived test-only approvals and mocked deterministic data in temporary directories; they did not call a Stim sampler.

## Computational readiness

### Machine and method

Measured on Windows 11, AMD Ryzen 7 170 with Radeon Graphics (8 physical / 16 logical CPUs), 16,312,205,312 bytes RAM, Python 3.12.10, NumPy 2.5.3, Stim 1.16.0, and psutil 7.2.2. Reproduce with:

```powershell
python outputs/qshift_advanced_research_v3a/benchmark_estimators.py
```

The benchmark warms each function 10 times, then times 200 evaluations using `perf_counter_ns` over 32 fixed feature means derived from deterministic template-bank points. The old implementation is loaded directly from baseline commit `6070fa875a14fe8e4e9b713607dd0f3a4e6e1c23`; both versions use the same inputs and warmup/repetition schedule. Feature extraction and mean computation are timed separately using deterministic modular binary fixtures at the four declared history lengths (30 repetitions each). No detector history is sampled. Detailed output, machine metadata, hashes, median/p95 timings, and projections are in `benchmark_results.json`.

### Measured estimator timings

Median milliseconds per feature-mean fit; p95 follows in parentheses:

| Template family | Candidate | Baseline at 6070fa8 | Phase 3B optimized | Median speedup |
|---|---:|---:|---:|---:|
| Exact categorical | A | 1.035 (1.222) | 0.0722 (0.0905) | 14.34× |
| Exact categorical | B | 5.848 (6.531) | 2.263 (2.754) | 2.58× |
| Approximate DEM | A | 1.056 (1.357) | 0.0728 (0.0928) | 14.52× |
| Approximate DEM | B | 5.900 (6.524) | 2.414 (2.891) | 2.44× |

Candidate B initialization fell from about `.230 s` / `.226 s` per exact/DEM family to `.024 s` / `.023 s`, primarily by replacing Python per-gridpoint interpolation calls with a vectorized cached surface. Candidate A now caches its fixed interpolated profile surface. Feature construction now uses direct binary comparisons and one preallocated 45-column output. Timing varied across benchmark invocations; the table reports the latest recorded run in the JSON artifact.

Numerical comparison against the original grid-scoring formulas covered 16 deterministic targets across both template families: corners, nominal values, measurement mismatch, interior values, and a deterministic non-template vector. No selected A or B estimate changed. The maximum absolute difference in the selected B objective was `3.55×10^-15` from floating-point operation ordering. Existing exact-tie and boundary tests still pass, including the lower-parameter tie rule.

### Workload projection and memory

The proposed allocation has 300 roots across five conditions, 242 update windows per root over the four nested histories, and 72,600 window feature vectors. Each vector is fitted by four family/arm combinations (A/B × exact/DEM), for **290,400 estimator evaluations**. Using latest measured medians, deterministic feature-map medians, and one-time estimator initialization:

- Feature-map and mean work: **8.52 s** projected in the latest run.
- Estimator fitting work: **350.02 s** projected in the latest run.
- One-time estimator initialization: **0.048 s** measured in the latest run.
- Combined measured-core projection: **358.59 s (about 5.98 minutes)** in the latest run. Comparable benchmark invocations ranged from 358.59 to 574.45 s; use the slower result (about 9.57 minutes) for planning because CPU timing varied materially.

This is a projection for the deterministic feature/estimator core only. It excludes Stim circuit sampling, sampler startup, checkpoint writes, final JSON output, and analysis. A credible end-to-end wall-time estimate is unavailable without sampling and was not invented. Timing varied between benchmark invocations; the projection is an estimate from measured medians, not a runtime guarantee.

Four optimized estimator objects used about **135.8 MB RSS** after construction in the latest run. The benchmark comparison process, which held both baseline and optimized implementations simultaneously, peaked at about **172.4 MB**. This is approximately 12.4× below the proposed 2 GiB limit. The runner processes one 10,100×40 `uint8` root at a time (404,000 bytes of detector storage), keeps only one root’s compact records in memory, and streams the combined results file. The 2 GiB cap is feasible for the runner on this machine, with substantial headroom. Full-result analyzer peak memory was not measured against a generated study result and remains outside the runner’s enforced cap.

Candidate B remains the dominant measured CPU cost. There is no further optimization applied because the present measured core is a few minutes and the full-run sampler cost is unknown; changing grid resolution or objective was prohibited.

## Execution integrity

### Authorization

The runner requires schema `qshift-finite-history-approval-v2`. It rejects absent, expired, inconsistent, or input-mismatched approvals. The required approval binds SHA-256 hashes for the protocol, configuration, template bank, runner, estimator, analyzer, template generator, circuit-builder source, and a Python/NumPy/Stim runtime fingerprint, plus the seed-manifest SHA-256 and stable ID. It also requires development-only scope, protected access false, exact conditions and split allocation, total/per-condition root and shot limits, explicit positive CPU and memory limits, UTC expiry, approver, and approval reference. The approved memory limit cannot exceed the config’s 2 GiB hard cap. The runner additionally refuses any changed frozen condition schedule or split allocation.

No approval file or production seed manifest was created in the repository. The valid approval files used in integration tests were ephemeral fixtures in temporary directories and carried test-only identity/reference values.

### Checkpoint, resume, and chronology

- The runner estimates from only past detector rows and samples the next block afterward. A and B use identical feature means. Exact and DEM fits are separate and explicitly tagged.
- Each root checkpoint has a canonical-payload checksum, run fingerprint, exact seed-entry hash, and a unique file keyed by the approved root identity. `RUN_MANIFEST.json` is replaced atomically after each completed root. The final results JSON is streamed in deterministic root/boundary/history/family/arm order.
- Resume verifies protocol/config/template/source/authorization/seed hashes and every completed-root file. It skips validated roots, adopts a valid orphan checkpoint left between root-file and manifest replacement, and refuses corrupted or mismatched checkpoints/results. Partial temporary files are preserved in `incomplete_checkpoints/`; incomplete roots may be recomputed with the same already-approved seeds. A stale lock with a confirmed dead PID can be recovered; active or ambiguous locks fail closed.
- Windows same-volume `os.replace` and file `fsync` are used. Python does not provide a portable directory-entry `fsync` guarantee here, so power-loss durability of rename metadata is not claimed; checksums detect incomplete artifacts during recovery.

### Deterministic test results

Command:

```powershell
python -m unittest discover -s outputs/qshift_advanced_research_v3a/tests -v
```

Result: **22 deterministic tests passed** (final run time recorded in `PHASE3B_SOURCE_MANIFEST.json`). Tests cover original A/B population behavior; optimization equivalence; corners and exact ties; malformed inputs; exact/DEM separation; fixed gate assumption; frozen Phase 2C source hashes; frozen configuration rejection; authorization hashes, expiry, scope and seed identity; duplicate seeds/roots; causal history and transition boundaries; mocked end-to-end result compatibility and pairing; deterministic record order; interrupted-root recovery and resume; valid orphan-temp promotion; corrupted checkpoint/result rejection; mismatched fingerprint rejection; lock cleanup; and resource-limit guards. `py_compile` and both CLI help paths passed. CLI help does not sample.

## Recommended bounded pilot (proposal only)

After independent protocol/run approval, begin with **10 development-only roots: two roots per each of the five frozen conditions**, all in the development split. Keep the existing 10,100-shot root schedule, 100-shot updates, four history lengths, both estimators, and both separately tagged template families. Total planned pilot volume is **101,000 shots**. Do not create the roots until approval.

The measured deterministic feature/estimator core projects to about **12–19.2 seconds** for this pilot across the benchmark range (the full 300-root core projection scaled by update count, plus one-time estimator initialization). Sampling, sampler startup, and file I/O are excluded; pilot elapsed time is therefore not yet known. Expected outputs are 10 checksummed root checkpoints, a run manifest, and a streamed results file. Do not use this pilot for statistical power or performance claims and do not inspect it to tune the frozen estimator or scenario values.

Stop on any input-hash mismatch, non-development scope, root/seed duplication, missing or extra roots, chronology/pairing error, checksum error, sample-shape error, memory or approved CPU limit breach, or unanticipated partial output. Preserve the run directory and failure evidence; resolve implementation/integrity faults before any further study.

## Readiness decision

**GO for requesting a separately authorized, bounded development-only execution pilot. NO sampling is authorized by this implementation report.** The runner and analysis path pass deterministic and mocked recovery checks, estimator outputs preserve the declared grid choices, and measured core runtime/memory are practical. The complete study runtime remains unknown until an authorized pilot measures Stim sampling and filesystem costs. No evidence here supports estimator superiority, decoder benefit, or logical-error improvement.
