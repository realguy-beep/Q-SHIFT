# Reproducing Phase 2C

Run commands from the repository root with the recorded Python environment and package versions in `PILOT_FREEZE.json`.

1. Run correctness tests: `python -m unittest discover -s outputs/phase2c_decoder_fidelity -p test_phase2c.py -v`.
2. Freeze and prepare development/calibration artifacts: `python outputs/phase2c_decoder_fidelity/run_phase2c.py prepare`.
3. Inspect `PILOT_FREEZE.json`; it must declare zero pilot shots at freeze. The runner verifies every frozen SHA-256 before sampling.
4. Run the independent pilot: `python outputs/phase2c_decoder_fidelity/run_phase2c.py pilot`.
5. Recompute reports and independently re-decode every saved pilot bundle: `python outputs/phase2c_decoder_fidelity/analyze_phase2c.py`.
6. Verify final file inventory and hashes: `python outputs/phase2c_decoder_fidelity/build_manifest.py`, then `python outputs/phase2c_decoder_fidelity/verify_manifest.py`.

The first command regenerates all development and calibration inputs, fits the frozen forest bank and writes the pre-pilot freeze. Do not edit source/configuration after the freeze. The second runner command refuses to proceed if frozen hashes differ. Each pilot NPZ is written atomically and contains paired detector shots, observable labels, six decoder predictions, reference probabilities, identity metadata, and its Stim RNG seed. The analyzer rebuilds the PyMatching models from frozen DEMs, loads the frozen forests, and requires byte-for-byte prediction/probability equality before aggregating results.

Phase 2C seed namespaces: diagnostic 89000001–89000006; development 89010001–89010006; calibration 89020001–89020006; pilot `89200001+100*cell_index+root_index`; bootstrap 89300001; sign-flip 89300002. `SEED_COLLISION_AUDIT.json` documents the exact scanned file set and any historical coverage gaps.

This is an exploratory feasibility pilot with four independent pilot roots per cell. Its confidence intervals and p-values do not support a confirmatory claim. `exact_toy.py` is an exhaustive exact calculator only for the finite toy channel tests; the surface-code reference remains an empirical posterior approximation.
