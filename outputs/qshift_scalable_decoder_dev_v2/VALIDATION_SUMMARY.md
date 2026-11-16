# Validation summary — scalable decoder V2

## Identity and boundary

- Branch: `codex/qshift-correlated-decoder-v1-6`
- Protocol base: `84ff46a4eac4dfc4769521508243065fbfebb7d9`
- V2 protocol commit: `4948bc43b442f651a4d845dd249980a68cbf0bce`
- No V1 or V1.6b frozen file was modified. `git diff --name-only -- outputs/qshift_scalable_decoder_dev_v1` returned no paths.
- Current environment observed: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, psutil 7.2.2. No dependency installation occurred.
- Current module checks: `ldpc` unavailable; `beliefmatching` unavailable.

## Exact commands and outcomes

1. `py -3.12 -m unittest discover -s outputs/qshift_scalable_decoder_dev_v2 -p 'test_*.py' -v` — 12 passed.
2. `py -3.12 -m unittest outputs.qshift_correlated_decoder_v1_4.tests.test_model_v14.D3EquivalenceTests.test_base_circuit_text_identical outputs.qshift_correlated_decoder_v1_4.tests.test_model_v14.D3EquivalenceTests.test_scaled_v1_family_is_exactly_v1_1_burst outputs.qshift_correlated_decoder_v1_4.tests.test_model_v14.D3EquivalenceTests.test_candidate_circuit_text_identical outputs.qshift_correlated_decoder_v1_4.tests.test_model_v14.D3EquivalenceTests.test_events_identical outputs.qshift_correlated_decoder_v1_4.tests.test_model_v14.LargerDistanceTests.test_shapes_events_and_families outputs.qshift_correlated_decoder_v1_4.tests.test_model_v14.LargerDistanceTests.test_d5_burst_only_syndromes_are_removed_exactly -v` — 6 passed in the final rerun. Tests whose fixture helper calls a seeded NumPy RNG were not run under the V2 no-random-generator protocol.
3. `py -3.12 -m py_compile outputs/qshift_scalable_decoder_dev_v2/factor_bp_v2.py outputs/qshift_scalable_decoder_dev_v2/exact_reference.py outputs/qshift_scalable_decoder_dev_v2/run_fixtures_v2.py` — passed.
4. `py -3.12 outputs/qshift_scalable_decoder_dev_v2/run_fixtures_v2.py --output fixture_results_final.json` — six of six cases completed; 33.39 s parent wall, each case below 10 s and the 120 s per-case limit.
5. `py -3.12 outputs/qshift_scalable_decoder_dev_v2/trace_diagnostics_v2.py` — completed; trace reimplementation matched decoder residual/iteration results for each traced fixture.
6. `py -3.12 outputs/qshift_scalable_decoder_dev_v2/period2_diagnostic.py` — completed; no two-step oscillation was identified in the tested toy cycle.
7. `py -3.12 outputs/qshift_scalable_decoder_dev_v2/check_alternatives.py` — `ldpc=False`, `beliefmatching=False`.
8. Exact `fixture_results_post_edge_fix.json` versus `fixture_results_final.json` comparison — 102 prediction/model/convergence fields, zero mismatches.

All verification was deterministic and used analytical/synthetic detector fixtures. No Stim sampler calls, new detector-event draws, training, evaluation labels, saved evaluation arrays, Stage 5 files, or sealed outcome data were accessed. No benchmark is running.

Final bounded rerun after documentation and manifest completion: the 12 V2 tests passed in 0.605 s; the six explicitly listed V1.4 no-RNG regressions passed in 0.157 s; seven V2 modules compiled; the 34-entry explicit source/dependency manifest verified; and Git reported no changes under the V1, V1.6b replay, or V1.6b calibration evidence directories. These durations are individual test process wall times, not a full-workload benchmark.

## Failures and corrections preserved

- The first V2 test pass detected test expectation issues: one DEM's implicitly counted D1 required a two-bit syndrome, and default tolerance 1e-8 was not tight enough for a 1e-10 tree-oracle assertion. Tests were corrected to declare both detector dimensions and request 1e-13 for the exact toy-only check; the production defaults remain frozen.
- A later test found V2's zero-incidence fast path omitted random logical-only mechanisms. The implementation was repaired and the whole six-case fixture set rerun to a new file, preserving prior outputs. Final output is `fixture_results_final.json`.
- An initial trace launch had a wrong local import-root index and stopped before model construction; the path was corrected and the diagnostic then completed. No sampler was involved.

## Decision

**REVISE** — p-boundary and logical-only implementation defects are fixed; tree correctness and finite-output checks pass, and the update is about 7–10× faster on these one-run fixtures. However q=0 nonconvergence persists, d=3 q=0 predictions disagree with exact inference on 4/6 fixed syndromes, and loopy logical-class probability remains approximate. No stochastic experiment or performance superiority claim is authorized.
