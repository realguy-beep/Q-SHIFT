# Phase 3A Deterministic Preflight Results

**Status: PASS for the small simulator/decoder preflight only. Phase 3B remains an unexecuted draft.** No production training or feasibility sampling was run.

## Validation results

| Check | Result |
|---|---|
| Frozen Phase 2B circuit base | Z-memory, distance 3, five rounds; 40 detectors, one observable |
| Burst target validation | Data qubits 8 and 10; Stim coordinates `(1,3)` and `(3,3)` |
| Burst insertion | Five `CORRELATED_ERROR` events, one after each `MR` round boundary; serialized Stim mnemonic is `E` |
| Zero-noise behavior | 32 shots; zero nonzero detector bits and zero observable flips |
| Zero-correlation limit | `p_burst=0` reproduces the same noiseless detector and observable arrays |
| Isolated common-cause demonstration | 2,048 shots at `p=0.1`: joint rate 0.09814, both marginals 0.09814, 0 discordant pairs, sample correlation 1.0 |
| Surface burst response | 256 shots at `p_burst=0.02`, otherwise noiseless: 25 shots had a nonzero detector vector; no observable flip in this small sample |
| DEM structure | 40 detectors and one observable with/without burst; 586 no-burst vs 591 burst-inclusive error mechanisms; 444 separator-bearing records in the burst-inclusive DEM |
| Matching graph construction | PyMatching 2.4.0 accepted frozen no-burst and burst-inclusive DEMs; 142 vs 147 edges |
| Paired decoder sample | 256 same detector/observable shots; all outputs `(256,1)`; same seed reproduced exactly |
| Correlation option check | `enable_correlations=False/True` used identical burst-inclusive DEM; zero prediction disagreements in the 256-shot smoke sample |
| Seed collision audit | 6,520 unique values extracted from 31 historical seed-metadata files; 0 collision with four formal preflight seeds, four unit-test seeds, or the one recorded preliminary smoke seed |
| Independent test isolation | No independent-test sample/label files were opened; 0 test access is recorded |

The paired smoke sample produced 2 errors for the frozen no-burst PyMatching model and 1 each for the burst-inclusive matcher with correlation handling off or on. The burst-inclusive model differed from the frozen decoder on 3/256 shots; the correlation switch changed 0/256 predictions. These counts only validate the sample-to-decoder path. They are far too small and were not designed for a performance claim.

## DEM approximation and graph compatibility

The frozen Phase 2B generator uses categorical `PAULI_CHANNEL_2` instructions. Stim's conversion with `approximate_disjoint_errors=False` failed exactly because the `PAULI_CHANNEL_2` operation requires the option to be enabled. Both matching arms therefore use the same Phase 2B-compatible conversion: `decompose_errors=True, approximate_disjoint_errors=True`. This remains an approximation for the categorical two-qubit channels; it is not a claim of exact full-circuit likelihood modeling.

A separate **no-shot** screen tested all 36 data-qubit pairs. The selected pair `(8,10)` passed graphlike DEM conversion and matching construction, adding five per-round records `D8 D10`, `D16 D18`, `D24 D26`, `D32 D34`, and `D36 D38`. A total of 27 pairs passed and 9 failed graphlike decomposition. The failure records and complete pair inventory are in `DEM_PAIR_SCREEN.json`. Failed pairs were not altered or sampled.

## Seeds and sample accounting

Formal preflight streams: `2503001001–2503001004`. Regression-fixture streams: `2503002001–2503002004`. The preliminary code/API smoke checks before the formal config used `2500000001`; that seed is recorded separately and is not reused in the formal allocation. The seed scanner read only files with seed metadata in their names, skipped sealed-test path segments, and did not inspect sample arrays from those historical studies. Exact files, extracted value counts, and collision checks are in `PREFLIGHT_RESULTS.json`.

The formal runner generated 2,880 sample draws, including a 256-shot same-seed replay and a 32-shot same-seed zero-correlation replay. Those replay arrays duplicate prior deterministic draws, so the formal run contains **2,592 distinct diagnostic shot records**. The small automated unit tests used a separate four-seed fixture namespace and generated 2,304 draws, including a 128-shot reproducibility replay. The no-shot pair screen generated zero samples. No Phase 3B production shots were generated.

## Historical preservation audit

- The 750K autonomous development run remains `completed`, 50/50 jobs and five roots, with `independent_test_access=0`. Of its 377 run-manifest entries, the only hash mismatch is `controller.stdout.log`: the manifest recorded the empty file, while the current 2,745-byte status stdout was written after the manifest and matches the completed status record. All other listed artifacts match. This is recorded as a post-manifest log artifact, not silently counted as a perfect manifest pass.
- The 1.665M hybrid residual sprint remains `failed`, with 30/30 jobs; all 292 entries in its separate post-run audit manifest still match. Its independent read-only audit and raw evidence remain intact. The historical controller failure is not repaired in place.

## Commands and execution notes

Final passing commands:

```powershell
python -m unittest discover -s outputs/phase3a_controller_repair/tests -v
python -m unittest discover -s outputs/phase3a_correlated_noise_preflight -p 'test_*.py' -v
python outputs/phase3a_correlated_noise_preflight/run_preflight.py
python outputs/phase3a_correlated_noise_preflight/dem_pair_screen.py
```

The final runs passed 6 controller-finalization tests and 5 correlated-noise tests; the deterministic preflight and 36-pair DEM screen both completed successfully. During implementation, one test initially assumed Stim would preserve the long `CORRELATED_ERROR` mnemonic; Stim canonicalizes it to `E`, so the assertion was corrected. An initial read-only audit lookup also used `progress_status` instead of the saved record's `progress_status_preserved`; the lookup was corrected. Neither issue affected historical artifacts or scientific samples. The preflight also exposed the preexisting 750K post-manifest stdout discrepancy described above.

Configuration, simulator, runner, and diagnostic hashes are collected in `PHASE3A_MANIFEST.json`. The exact software packages are recorded there and in the JSON results.
