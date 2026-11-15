# Q-SHIFT correlated decoder feasibility V1.1

This version repairs the V1 affine-estimator coefficient order and evaluates the same four decoder arms on 60,000 fresh paired development shots, reusing only hash-verified V1 training/calibration detector arrays. It is exploratory, not confirmatory.

## Sampler-free verification

From the repository root using Python 3.12.10 with the versions in `config.json`:

```powershell
py -3.12 outputs/qshift_correlated_decoder_feasibility_v1_1/prepare_seeds.py
py -3.12 outputs/qshift_correlated_decoder_feasibility_v1_1/verify_reuse.py --v1-repo C:\Users\LENOVO\Documents\Codex\2026-11-15\qshift-correlated-decoder-feasibility-v1
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_feasibility_v1_1/tests -v
py -3.12 outputs/qshift_correlated_decoder_feasibility_v1_1/preflight.py --v1-repo C:\Users\LENOVO\Documents\Codex\2026-11-15\qshift-correlated-decoder-feasibility-v1
py -3.12 outputs/qshift_correlated_decoder_feasibility_v1_1/freeze_pretest.py
```

The preflight builds circuits/DEMs and decoder objects, loads only the `detectors` member of V1 archives, tests deterministic synthetic fixtures, and records resource/runtime estimates. It does not call a Stim sampler.

## Single evaluation execution

Sampling is disabled in the ordinary runner. After all source, seed, archive and resource checks pass and the pretest freeze is committed, the only authorized launch path is:

```powershell
py -3.12 outputs/qshift_correlated_decoder_feasibility_v1_1/run_watchdog.py --execute --expected-head <FROZEN_COMMIT_SHA> --v1-repo <EXACT_V1_WORKTREE_PATH>
```

This command performs the one bounded V1.1 evaluation. It refuses an existing attempt and does not resume or retry. Do not invoke it if any gate fails. Raw archives and per-shot arrays are local and ignored; lightweight reports and reproducibility metadata are version controlled.

See `EXPERIMENT_PROTOCOL.md` for the scientific design, exact limits, interpretation and evidence boundaries.
