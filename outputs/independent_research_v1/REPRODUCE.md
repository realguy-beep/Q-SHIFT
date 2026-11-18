# Reproduce the isolated research checkpoint

## Environment

Use Python 3.12.14. In `/workspace/qshift-independent-research-v1`, create the worktree-local environment and install the pinned research packages:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-input -r outputs/independent_research_v1/requirements-research.txt
```

Observed versions at checkpoint: NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, PyMatching 2.4.0, LDPC 2.4.1, NetworkX 3.7. Python package builds were installed from PyPI with TLS verification enabled. PyTorch was not installed because the screened prototype does not use it and the environment has no visible GPU. `MPLCONFIGDIR=/tmp/qshift-mpl` avoids matplotlib attempting to create a cache beneath the read-only home path.

## Checks and calculations

From the worktree root:

```bash
python3.12 outputs/independent_research_v1/zero_failure_bounds.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python -m unittest discover -s outputs/independent_research_v1 -p 'test_categorical_bp.py' -v
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/dem_preflight.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/dem_threshold_scan.py
```

The toy tests load analytically defined categorical circuits and exact-posterior code from the tracked `outputs/categorical_decoder_feasibility/` directory. The DEM preflight imports the read-only tracked Phase 2B builder. It generates circuits in memory and does not sample shots or write under historical output paths.

## Experiment provenance

- Branch: `codex/qshift-independent-research-v1`.
- Main base: `7cbc2e791a854e40ed4e840393fc8b4368d95ac2`.
- Phase 2B circuit builder SHA-256: `256826516353c5d3effb6a0b85969934ac2b61edc2848148d935087e54dffcbd`.
- Phase 2B decoder bank SHA-256: `ea88bbd9c60b027b7525d330db39df5c48fc3495a6644a9b991fa70ac2161080`.
- `research_direction_selection/PILOT_PROTOCOL.md` SHA-256: `96a08320b8f01a42f6be7b6526c8092e12e9202d0a0b2bf9738c24b8579c797a`.
- `research_direction_selection/SELECTED_DIRECTION.md` SHA-256: `6655a6f0aa28380f7145b4531eaa49af634c9e97d30815fd89a0c3cbb3e1b98f`.
- No confirmatory data or independent-test material was accessed. Development-only source-circuit shots and separate ideal-syndrome qecsim code-capacity shots are recorded in `RESULTS.json` with their scopes.

## Continuation

Continue in this same worktree and branch. Read `WORK_LOG.md`, `RESEARCH_LOG.md`, and `CLAUDE_HANDOFF.md` first. Do not repeat the existing correlation pilot. The next potentially useful step is an exactness-controlled redesign of native categorical inference on small cyclic factor graphs; the current Bethe prototype is a negative screen and must not be used on the distance-3 circuit without a revised exact-toy validation gate.

- Reproduce the bounded MPS validity/runtime preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_screen.py --preflight`. This does not launch the full screen.

- Reproduce BP+LSD setup/runtime validity preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bplsd_feasibility.py --preflight`. Reproduce the fixed development run with the same command without `--preflight`; it writes to this research directory only.

- Reproduce the rare-event estimator preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/rare_event_is.py --preflight`; reproduce the main and 8-replicate development runs with the same script and respectively no flag or `--replicates 8 --shots 5000`. These runs sample approximate DEMs only.

- Reproduce exact-channel instrumentation validity/timing with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_importance_sampler.py --preflight`; reproduce the fixed main sample without `--preflight`; reproduce the two independent stability blocks using `--replicates 8 --shots 5000` and `--replicates 8 --replicate-start 8 --shots 5000`. Validate against raw Stim circuit sampling with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_sampler_crosscheck.py`.

- Reproduce the cross-entropy training/validation run with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/categorical_cross_entropy.py`; it writes its learned proposal and independent validation metrics to `categorical_cross_entropy_results.json`.

- Reproduce the memory-basis analysis from the saved independent direct-arm aggregates with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_orientation_analysis.py`. It samples no new shots.

- Reproduce the distance-5 timing/shape preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/code_distance_scaling.py --preflight`; the fixed development screen runs without `--preflight`.

- Reproduce the bias-strength preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/bias_crossover.py --preflight`; rerun the fixed development screen without `--preflight`.

- Reproduce the distance-7 known-profile extension preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/basis_alignment_distance7.py --preflight`; the fixed 500,000-shot-per-cell run uses the same command without `--preflight`.

- Reproduce the fixed-bond qecsim MPS 100-shot preflight with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/tensor_mps_truncated.py --preflight`; reproduce the fixed χ=16 development screen without `--preflight`.

- Reproduce detector-only binary identification with `bias_identification.py --preflight` and then without the flag; reproduce the three-class strength stress test with `bias_strength_identification.py --preflight` and then without the flag. `bias_binary_cross_strength.py` re-scores those exact seeded streams using the earlier frozen two-class model; it does not fit a model or add independent sample streams.

- Reproduce the cross-sample LER projection with `python outputs/independent_research_v1/basis_decision_projection.py` only if needed; the saved projection is `bias_decision_projection.json`.

- Reproduce direct, independent calibration-to-memory policy validation with `MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v1/adaptive_basis_end_to_end.py --preflight`, then run without the flag. `adaptive_basis_end_to_end_first_pass_reversed.json` is an invalid implementation pass retained for audit; use only `adaptive_basis_end_to_end_results.json`.
