# Reproduction guide

Run from the repository root in an environment with Python 3.12, Stim 1.16, PyMatching 2.4, and NumPy 2.5 (tested versions are recorded in `RESULTS.json`). No network access or new data download is needed once dependencies are installed.

```powershell
python -B -m unittest discover -s outputs/matching_representation_investigation -v
python -B outputs/matching_representation_investigation/matching_investigation.py
python -B outputs/matching_representation_investigation/verify_results.py
python -B outputs/matching_representation_investigation/verify_inputs.py
python -B outputs/matching_representation_investigation/verify_manifest.py
```

`matching_investigation.py` recreates only this investigation's deterministic outputs (`RESULTS.json`, `SEPARATOR_GRID.csv`, and `SURFACE_FRAGMENT_SUMMARY.csv`). `verify_results.py` independently rescales the stored exact references and predictions; `verify_inputs.py` checks historical hashes and writes only `PHASE0_VERIFICATION.json`; `verify_manifest.py` reads the local manifest and checks the covered local files. The 5.9 MB result JSON contains the bounded predictions and exact distributions needed for rescoring. No simulator shots or historical files are generated or changed.

`CASE_PLAN.json` was created before the analysis run and contains the fixed case/seed plan. The preserved `*_BEFORE_FIXTURE_CORRECTION` files are a diagnostic record of an initial fixture with unequal anchor distributions; they are excluded from the final planned comparison. `REPRESENTATION_RULE_CLARIFICATION.md` records the added logical-only-event rejection discovered during validation.

All reported risks are exact probability sums for the specific model named in each row. No Monte Carlo uncertainty estimates are applicable. Do not compare native categorical risk and independent-DEM risk as if they were the same noise law.
