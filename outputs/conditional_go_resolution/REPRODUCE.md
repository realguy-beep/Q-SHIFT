# Reproduce this feasibility package

All commands are run from `outputs/conditional_go_resolution/` in the existing repository. They create only development-feasibility evidence in this new directory; they do not edit or rerun historical phases.

```powershell
python decoder_rebuild_fixture.py
python -m unittest -v test_decoder_rebuild_fixture.py
python run_small_development_checks.py
python verify_development_evidence.py
python write_manifest.py
```

Expected test result: **5 tests pass**. Expected independent audit status: `PASS` in `INDEPENDENT_VERIFICATION.json`. The development runner regenerates 456,704 Stim shots from the seeds listed in `SEED_SCREEN.json`; it writes `DEVELOPMENT_CHECKS.json`, `DEVELOPMENT_RAW_EVIDENCE.npz`, `UTILITY_PER_ROOT.csv`, and `TRIGGER_SCHEDULE_MAXIMA.csv`. The independent verifier reads those saved artifacts and does not import the runner’s aggregation/reporting functions.

The data arrays are compressed in NPZ. `FEASIBILITY_CONFIG.json` records the frozen small-pilot settings; `MANIFEST.json` records SHA-256 hashes of the resulting files. This is development feasibility evidence only, not a confirmatory adaptive evaluation.
