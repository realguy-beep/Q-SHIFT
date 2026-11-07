# Reproducing Phase 2B

## Recorded environment

The run used Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, and NumPy 2.5.3. SciPy is used for exact McNemar tests. `PRETEST_FREEZE.json` revision 2 freezes source/configuration, generated circuits and DEMs, seed allocation, development/validation data, calibration data, model selection, and the statistical plan before held-out sampling. Revision 1 is preserved as `PRETEST_FREEZE_SUPERSEDED_1.json`; it was superseded before any test shot after fixing a runtime metadata label.

## Main execution commands

The original experiment was run in two stages:

```powershell
python -m unittest -v test_phase2b.py
python run_phase2b.py prepare
python run_phase2b.py heldout
```

`prepare` screens historical seed records, validates circuit/noise/DEM behavior, generates six independent development/validation batches and six calibration batches, selects global/per-regime models from calibration only, and writes the pretest freeze. `heldout` validates every frozen hash before sampling and atomically saves 120 root files (20 per basis/regime cell, 10,000 shots each). It resumes only an existing root that matches its frozen seed/metadata and independently re-decodes correctly.

The current directory is a completed evidence archive: `prepare` intentionally refuses to replace its freeze. To reproduce the complete run from scratch, use a clean copy of the source package and the recorded seed allocation, keeping this original archive unchanged. The stored streams are deterministic; a same-seed reproduction is a computational replay, not an independent replication.

## Analysis and evidence verification

```powershell
python -m unittest -v test_phase2b.py
python analyze_phase2b_verified.py
python verify_phase2b.py
python verify_manifest.py
```

The first frozen analyzer attempt failed on a NumPy 2.5 signed/unsigned accumulator cast, then a reporting key mismatch. It is preserved unchanged as `analyze_phase2b.py`. `analyze_phase2b_verified.py` is a documented reporting-only copy with an explicit integer cast and the correct `primary_signflip` schema key; it re-decodes all test arrays and verifies the freeze. `ANALYSIS_CORRECTION.md` records the exact failures and confirms that the statistical procedure did not change. `verify_phase2b.py` is a separate audit that independently re-decodes every saved test bundle, checks seed/filename/schema mappings, recalculates calibration selection, and reconciles per-root, per-cell, and overall totals.

## Evidence layout

- `data/development_validation/`: 6 independent 5,000-shot batches.
- `data/calibration/`: 6 independent 20,000-shot batches used for selection.
- `data/heldout/`: 120 compressed test bundles, each containing detectors `(10000,40)`, observables `(10000,)`, and three predictions `(3,10000)`.
- `dems/`: six circuit and six detector-error-model text files.
- `CALIBRATION_RESULTS.csv`, `PER_ROOT_RESULTS.csv`, `PER_REGIME_RESULTS.csv`, `DECODER_DISAGREEMENT.csv`, and `PAIRED_COMPARISONS.csv`: machine-readable results.
- `STATISTICAL_RESULTS.json`, `ORACLE_HEADROOM.json`, `PHASE2B_ANALYSIS_AUDIT.json`: primary inference, oracle diagnostics, and raw-evidence audit.
- `SHA256_MANIFEST.json`: hash and byte-length inventory for all delivered files except the manifest itself.

The regime-informed comparator uses the known simulated regime identity and is not an adaptive controller. Test labels are used only for scoring and explicitly labeled retrospective oracle diagnostics.
