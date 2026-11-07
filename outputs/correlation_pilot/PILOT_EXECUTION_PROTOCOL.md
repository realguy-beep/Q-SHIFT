# Correlation-aware PyMatching pilot — execution freeze protocol

**Status:** Prospective execution record, created after the direction-selection protocol and before full-pilot sampling. This document clarifies seed collisions and unambiguous analysis details; it does not alter any prior experimental artifact.

## Research question and scope

Test whether PyMatching’s correlated matching option changes logical decoding utility when applied to the same frozen detector error model (DEM), graph weights and paired samples as ordinary matching. This is a development feasibility study, not a confirmatory experiment and not an adaptive controller test.

## Circuit and six conditions

Use the verified Phase 2B Stim generator for rotated surface-code X- and Z-memory, distance 3, five rounds. Strata, in frozen order, are X-memory/X-biased, X-memory/balanced, X-memory/Z-biased, Z-memory/X-biased, Z-memory/balanced, Z-memory/Z-biased. Preserve the existing generated detector and `OBSERVABLE_INCLUDE(0,...)` definitions. For each condition, total 1Q and 2Q categorical gate-fault probability is 0.003, measurement-flip probability is 0.003, and the X/Y/Z weight ratio is 10:1:1, 1:1:1, or 1:1:10. Preserve Phase 2B post-Clifford injection locations and the ordered fifteen two-qubit Pauli outcomes.

Build DEMs with the exact Phase 2B flags `decompose_errors=True` and `approximate_disjoint_errors=True`. The latter approximates mutually exclusive categorical channels as independent DEM mechanisms; both decoder arms use the same approximation.

## Four decoder arms

1. **Pooled fixed, uncorrelated:** Phase 2B calibration-selected fixed model, X-memory index 0 / Z-memory index 2, correlation support disabled both at matcher construction and decode call.
2. **Pooled fixed, correlated:** identical fixed-model DEM and weights, correlation support enabled at construction and decode call.
3. **Regime-informed, uncorrelated:** DEM indexed to the known generating regime; privileged evaluation diagnostic only.
4. **Regime-informed, correlated:** same regime DEM with correlation use enabled; privileged diagnostic only.

The primary comparison is arm 2 minus arm 1. The regime-informed results are secondary references and are never described as deployable.

## Seed amendment and allocation

Two candidate namespaces were rejected before test sampling. `93000001` collided with prior Phase 5 adaptive-development blocks. `97000001–97000012` collided with Phase 4C headroom template-generation seeds. A literal `100000000` in `run_phase5d.py` was reviewed as a threshold assertion (`roots > 100000000`), not an RNG seed; the diagnostic stream was moved to `100000999` to avoid ambiguous textual matching.

The accepted prospective allocation, subject to the saved full collision scan, is:

- Root seed for stratum `s` and root `r`: `100000001 + 100*s + r`, where `s=0..5`, `r=0..11`.
- Diagnostic seed: `100000999`.
- Root-stratified bootstrap seed: `100010001`.
- Primary sign-flip seed: `100010002`.
- All 72 root seeds and three auxiliary seeds are distinct. The inventory records every value and scanned source file.

Before freeze, scan the proposed exact seeds against recoverable files under `outputs/`, excluding this new output directory and the originating direction-selection plan. Scan text/JSON/CSV/Python/YAML/log artifacts and numeric NPZ fields whose key names identify seed/RNG data. A negative scan means only “no collision among recoverable records”; it cannot establish absence of unrecorded RNG use or unavailable history.

## Sampling plan

For each of six strata, use 12 new independent roots and 10,000 shots/root. Total **720,000** fresh development shots. Each root’s Stim detector samples and logical observable labels are stored once; all four arms decode those same values. Store detectors packed little-endian as `(10000,5)` uint8, labels `(10000,)` binary uint8, and predictions `(4,10000)` binary uint8. Write each NPZ atomically and never overwrite a valid checkpoint. No training or calibration is conducted on pilot test labels; the pooled indices are inherited from the Phase 2B calibration-only selection.

## Statistical decisions frozen before sampling

- Endpoint: equal-weight mean across the six strata of pooled-fixed correlated LER minus pooled-fixed uncorrelated LER. Negative favors correlated matching.
- Primary root-cluster test: two-sided Monte Carlo sign-flip, 100,000 assignments, PCG64 seed 100010002, signs applied to paired per-root differences within their original stratum, equal-weight aggregation across strata, add-one p-value.
- Primary interval: regime/stratum-stratified percentile bootstrap, 20,000 resamples, PCG64 seed 100010001; independently resample 12 roots within each stratum while applying the same root indices to both paired arms. Report 95% interval.
- Shot-level exact McNemar counts and p-value are descriptive, not a replacement for root-cluster inference.
- Secondary family: 12 exact root-level paired sign-flip tests (regime-informed minus corresponding pooled-fixed result; correlation off and on in each of six strata), exhaustive over `2^12` signs per test and Holm-adjusted as one family.
- Practical margin: **0.0002 absolute LER**, exactly. Feasibility gate requires primary point estimate ≤−0.0002, upper 95% bound ≤−0.0002, at least four favorable strata, and a favorable aggregate after deleting any single stratum.
- No per-cell p-values are used to select models; no test outcome changes the analysis.

## Resource preflight

The deterministic smoke was run at 4,096 shots per condition. A two-times extrapolation gave a bounded full-run estimate in `SMOKE_PREFLIGHT.json`; actual runtime is recorded after execution. Storage is estimated from compressed smoke NPZs with a 50% margin and checked against free space before freeze. Measured values and the system versions are preserved in the preflight JSON.

## Execution gate and reproducibility

Freeze this document, configuration, seed inventory, preflight, runner, independent analysis code, statistical self-check, Phase 2B source/configuration/selection, and saved generator artifacts by SHA-256 before any full-pilot test shot. The runner verifies this freeze before sampling. If any hash differs, stop and create a new pre-sampling freeze before starting. Full sampling proceeds only if the smoke, seed scan, DEM/graph identity, circuit/noiseless/noise checks, statistical self-check, storage estimate, and exact margin check all pass.

The data are a simulation under one specified stochastic Pauli model. They do not establish hardware performance, general superiority of correlated matching, exactness of the DEM, or an adaptive-decoding benefit.

