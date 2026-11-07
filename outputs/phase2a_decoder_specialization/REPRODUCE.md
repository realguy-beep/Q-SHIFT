# Reproducing Phase 2A

## Scope and status

Phase 2A is a development-only, simulation study. It does not reuse the already-inspected prototype evaluation samples, does not test within-circuit noise changes, and does not demonstrate a hardware decoder. The evaluation consists of 20 independent roots in each of three fixed noise regimes, with 10,000 paired shots per root (600,000 total). All nine decoders see the same detector shots and observable labels within each root.

The pretest source, configuration, selection, and audit-input hashes are recorded in `FREEZE.json`. The freeze was written before sampling according to runner order and filesystem timestamps. Later reporting-only additions (`supplement_phase2a.py`, `verify_phase2a.py`, and this document) did not alter the frozen runner or experimental data. `PHASE2A_AUDIT_RESULTS.json` records the independent verification.

## Environment

The recorded run used Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, and NumPy 2.5.3. It also uses SciPy and Matplotlib for the analysis outputs. Install compatible versions in an isolated Python environment using the repository's existing dependency guidance, then run the commands below from this directory.

## Commands

The following commands operate on saved data and do not generate new Stim shots:

```powershell
python -m unittest -v test_phase2a.py
python analyze_phase2a.py
python supplement_phase2a.py
python verify_phase2a.py
```

`analyze_phase2a.py` independently decodes every saved detector array, rebuilds per-root and per-regime tables, paired comparisons, multiple-comparison adjustment, uncertainty outputs, and plots. `supplement_phase2a.py` rechecks calibration selections against saved calibration arrays and adds descriptive hindsight-headroom and observed-equivalence summaries. `verify_phase2a.py` checks every pretest frozen hash, re-decodes all 60 raw evaluation bundles, verifies metadata and binary array schemas, and reconciles the per-root/per-regime CSV totals.

The sampling command, if a new reproduction is intentionally authorized, is:

```powershell
python run_phase2a.py
```

It is not needed to reproduce the present analysis. A new run would create new evaluation files and must use a newly reviewed seed allocation; do not run it over this evidence directory.

## Outputs

- `data/`: 60 compressed root files, each holding 10,000 x 40 detector bits, 10,000 observable labels, and 9 x 10,000 decoder predictions.
- `SEED_MANIFEST.csv`: root/regime/seed/file mapping.
- `PHASE2A_RESULTS.json`, `PER_SEED_RESULTS.csv`, `PER_REGIME_DECODER_RESULTS.csv`: raw-array-derived numerical results.
- `STATISTICAL_ANALYSIS.md`: paired root-level inference and Holm-adjusted family.
- `DECODER_DISAGREEMENT.csv`, `SYNDROME_DISAGREEMENT_PATTERNS.json`: disagreement statistics and observed syndrome patterns.
- `ORACLE_HEADROOM.json`: deployable calibration-selected comparisons plus explicitly unattainable hindsight diagnostics.
- `DECODER_BANK_AUDIT.json`: DEM/matching graph configuration and hashes.
- `PHASE2A_AUDIT_RESULTS.json`: independent final integrity and count reconciliation.
- `PHASE2A_MANIFEST.json`: hashes and byte lengths for all delivered Phase 2A files except the manifest itself.

## Interpretation limits

The calibration data contain one 20,000-shot batch per regime. The supplementary paired intervals characterize shot-level variation within those batches; they do not establish seed-to-seed calibration-selection stability. The retrospective evaluation-label oracles use the evaluation labels to select and score models and are optimistic diagnostics only. A matching prediction gives the predicted logical-observable flip; these arrays do not store physical correction chains.
