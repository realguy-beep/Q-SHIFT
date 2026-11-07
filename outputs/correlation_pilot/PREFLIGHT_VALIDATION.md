# Correlation-aware pilot — preflight and execution validation

**Decision: PASS.** All mandatory pre-sampling checks passed before the 720,000-shot run. The run and saved-array audit have since completed. This is a bounded development pilot, not a confirmatory experiment.

## Mandatory checks

| Check | Result | Evidence and interpretation |
|---|---|---|
| PyMatching version and correlation API | PASS | PyMatching 2.4.0. The correlation-enabled matcher is constructed with `enable_correlations=True` and decoded with the same option. A negative control—constructing with correlation disabled, then requesting correlated decode—raises `ValueError`. See `SMOKE_PREFLIGHT.json`. |
| Correlation metadata is usable | PASS | The six DEMs contain decomposition separators (564 in X-memory and 572 in Z-memory in the frozen diagnostic). Correlation-enabled calls are accepted, the negative control is rejected, and the deterministic smoke observed prediction differences in the conditions where sampled cases exercised them. |
| Paired decoder graph/DEM identity | PASS | Each on/off pair is built from the same DEM object. Preflight and runner compare detector/observable/fault identifiers, sorted graph edges, weights, and fault IDs; all match between the option settings. Only the decoder algorithm's use of correlation metadata changes. |
| Six circuits/noise conditions | PASS | X- and Z-memory × X-biased, balanced, and Z-biased conditions are built with the frozen Phase 2B generator. Distance 3, five rounds, one logical observable, 40 detectors, 0.003 single- and two-qubit categorical gate-fault probability, 0.003 measurement-flip probability, and X:Y:Z ratios 10:1:1, 1:1:1, and 1:1:10 were checked against Phase 2B source and generated circuit/DEM records. |
| Noiseless behavior and detector/observable shape | PASS | The frozen generator's noiseless and normalized circuit checks passed for both memory bases. Sample arrays have 40 detector bits and one logical-observable bit; packed storage is five bytes per shot. |
| Seed uniqueness and collision screen | PASS, bounded by recoverable history | Final allocation has 72 root seeds plus diagnostic, bootstrap, and sign-flip streams (75 total), all distinct. The preflight scanned 425 text/config/source files and 1,141 NPZ files for recorded seed values. Two proposed namespaces were rejected for historical collisions before the final allocation. This cannot rule out undocumented RNG use or unavailable historical records. Exact inventories and rejected-candidate audits are retained in `SEED_INVENTORY.json`, `SEED_COLLISION_PRECHECK.json`, `SEED_COLLISION_970_AUDIT.json`, and `SEED_TEXT_MATCH_REVIEW.json`. |
| Root-cluster statistical code | PASS | Self-checks cover paired root differences within six fixed strata, equal-stratum aggregation, independent sign assignments, add-one Monte Carlo p-values, shared within-stratum root indices for paired bootstrap arms, exhaustive secondary sign flips, and reproducible RNG streams. See `STATISTICAL_SELF_CHECK.json`. |
| Practical margin | PASS | Configuration and pre-test freeze record exactly **0.0002 absolute LER**. Primary success additionally required point and upper 95% CI at or below -0.0002, at least four favorable strata, and favorable leave-one-stratum-out effects. |
| Deterministic smoke | PASS | `python smoke_test_correlation_pilot.py`: 1,536 total deterministic diagnostic shots (256 per stratum), valid sample/prediction schemas, paired arm calls, and correlation-on/off behavior. It did not contribute to the full-pilot dataset. |
| Runtime/storage preflight | PASS | Smoke-based estimate with 2× runtime margin: 191.84 s. Estimated compressed evidence with 50% margin: 1,748,627 bytes. Available disk at preflight: 280,736,010,240 bytes. Full execution completed within the estimate. |
| Freeze before full sampling | PASS | `PRETEST_FREEZE.json` status is `FROZEN_BEFORE_FULL_SAMPLING`; it records the source, config, runner, analysis, statistics, seed inventory, Phase 2B references, and protocol hashes. The runner checked these hashes before sampling. |

## Execution and audit checks

- `python preflight_correlation_pilot.py` — exit 0; PASS.
- `python -m py_compile preflight_correlation_pilot.py run_correlation_pilot.py analyze_correlation_pilot.py freeze_pilot.py smoke_test_correlation_pilot.py` — exit 0.
- `python smoke_test_correlation_pilot.py` — exit 0; PASS.
- `python freeze_pilot.py` — exit 0; 72 roots and 3 auxiliary seeds frozen before test sampling.
- `python run_correlation_pilot.py` — exit 0; 72/72 roots and 720,000/720,000 paired shots saved.
- `python analyze_correlation_pilot.py` — exit 0; all stored predictions re-decoded and aggregate analysis written.
- `python independent_recompute.py` — exit 0; rebuilt models, re-decoded 2,880,000 prediction bits, and independently reproduced per-root, per-stratum, aggregate, CI, and primary test values.
- `python -m py_compile independent_recompute.py` — exit 0.

## Bounded claims and caveats

`approximate_disjoint_errors=True` is inherited from the Phase 2B DEM conversion. The original Stim categorical Pauli channels are sampled, while the DEM decomposition approximates mutually exclusive events; correlation-aware matching only uses correlation metadata retained in this approximate DEM. The experiment isolates the effect of the PyMatching correlation option under that shared DEM approximation. It does not establish exact decoding of the native categorical model.

The timing file could not collect process RSS because `psutil` was unavailable. Runtime and storage were measured/estimated; peak process memory is therefore **not measured**. The experiment is simulation-only, distance 3/five rounds, and development-only. No adaptive controller or hardware integration was tested.
