# Stage 4 Full Development Preflight

**Status before sampling:** PASS. No Stage 4 full-study samples were generated during this preflight.

## Frozen pilot and historical evidence

The previous 48,000-shot feasibility pilot remains in `outputs/stage4_noise_adaptive_feasibility_v1/`; no files in that directory were edited. The Stage 2, Stage 3 and Phase 3A evidence was read only for allocation screening. No independent-test samples or labels were opened or accessed.

## Seed screen

`prepare_seeds.py` reproduced the prior 79 sample seeds exactly (4,200,000,001–4,200,000,079) and added three analysis-only seeds (4,200,000,080–4,200,000,082). All 82 candidate values are distinct and within the supported 32-bit range. The initial screen found no overlap with 2,256 recoverable values. A supplemental screen added five development-only seed inventories and found no collision with the expanded 2,994-value historical union:

- `outputs/cnn_architecture_stage2_v1/seed_inventory.json`
- `outputs/cnn_architecture_stage2_v1/seed_audit.json`
- `outputs/cnn_stage3_residual_gate_v1/seed_inventory.json`
- `outputs/cnn_stage3_residual_gate_v1/seed_audit.json`
- `outputs/phase3a_correlated_noise_preflight/config.json`
- `outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json`
- `outputs/stage4_noise_adaptive_feasibility_v1/seed_inventory.json`
- `outputs/stage4_noise_adaptive_feasibility_v1/seed_audit.json`
- `outputs/cnn_architecture_stage1_v1/seed_inventory.json`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/seed_inventory.json`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/seed_inventory.json`
- `outputs/neural_decoder_diagnostic/structured_seed_inventory.json`
- `outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000/structured_seed_inventory.json`

Exact file hashes and extracted counts are in `seed_audit.json` and `additional_development_seed_audit.json`. This covers recoverable development metadata only; unrecorded historical RNG use cannot be ruled out. No sealed-test allocation was checked. An initial broad filename-only search unintentionally displayed filenames under a historical independent-replication raw-data directory. No listed artifact was opened, read, hashed, summarized or used; subsequent seed screening read only the development metadata above.

## Circuit, DEM and decoder checks

Installed versions: Stim 1.16.0, PyMatching 2.4.0. The deterministic check built three circuits/DEMs/matchers at burst probabilities 0, 0.00637 and 0.012. All circuit and DEM definitions had 40 detectors and one observable; matching exposed 40 detector nodes and one fault ID. The p=0 and p=0.012 DEM text differed, confirming burst probability changed the reconstructed model. All three matchers decoded the same 2,500-row all-zero synthetic detector matrix to the same logical prediction. The noiseless p=0 circuit produced eight all-zero detector and observable records.

Synthetic, non-sampled benchmark: median construction was approximately 0.0073 seconds per decoder; decoding 2,500 all-zero rows took approximately 0.0006–0.0010 seconds per decoder. Process RSS after the diagnostic was approximately 82 MB. A deterministic benchmark of 500 profile-conditional bootstrap estimates took 1.14 seconds; a linear projection for 35 calibration roots is about 40 seconds. Full execution remains bounded by the frozen 1,800-second wall-clock and 2 GiB RSS limits. Free disk at preflight was about 273 GB.

## Gate clarification

The old gate counted four of five probabilities, including p=0. The revised protocol does not let a no-burst control count as an improvement condition: it requires improvement at all four nonzero p strata and separately requires the one-sided 95% root-cluster upper bound at p=0 to be no greater than +0.0002 LER harm. The 0.0002 margin is carried forward from prior Stage 2/3 development gates; it was not selected using the Stage 4 pilot's evaluation labels. This is a conservative translation, not an attempt to relax the prior condition count.

## Commands and test outcomes

- `python -m outputs.stage4_noise_adaptive_development_v1.prepare_seeds` — PASS; 79 sample seeds, 3 analysis seeds, 2,256 values in the initial screen, zero collisions.
- `python -m outputs.stage4_noise_adaptive_development_v1.audit_additional_development_seeds` — PASS; 2,994 values in the expanded development-metadata union, zero collisions.
- `python -m compileall -q outputs/stage4_noise_adaptive_development_v1` — PASS.
- `python -m unittest outputs.stage4_noise_adaptive_development_v1.tests.test_stage4 -v` — PASS, 6 tests.
- `python -c "import json; from outputs.stage4_noise_adaptive_development_v1.run_stage4 import diagnostic; print(json.dumps(diagnostic(),indent=2))"` — PASS; no stochastic diagnostic samples.
- `python -m outputs.stage4_noise_adaptive_development_v1.run_stage4 --validate-only` — required after freeze; expected to repeat the same deterministic check and verify the freeze.

During implementation, an initial check incorrectly expected a `Matching.num_observables` property. PyMatching 2.4.0 exposes `num_fault_ids`; the check now uses this actual API and passes. This was resolved before freeze and before Stage 4 sampling.
