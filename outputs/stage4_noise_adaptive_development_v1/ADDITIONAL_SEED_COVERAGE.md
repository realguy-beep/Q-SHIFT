# Additional Development Seed Coverage

Result: **PASS_RECOVERABLE_DEVELOPMENT_METADATA**.
Stage 4 candidate seeds: 82 unique; recoverable historical values in union: 2994; collisions: 0.

Files examined:
- `outputs/cnn_architecture_stage2_v1/seed_inventory.json` — 95 values; SHA-256 `1f8493b0aed1d06f2ed0fa4ba420b2263007c5844b4d1c15dd396f906f5cb020`
- `outputs/cnn_architecture_stage2_v1/seed_audit.json` — 13 values; SHA-256 `fe205e33f6f3ab369b88bf4fc71c4ebd32a122630ad2673ae52ff07fcef93f21`
- `outputs/cnn_stage3_residual_gate_v1/seed_inventory.json` — 46 values; SHA-256 `07cab005a1ba5df2ddb26ad664f79c3a878d09622cf965e287f220f35db6b675`
- `outputs/cnn_stage3_residual_gate_v1/seed_audit.json` — 2191 values; SHA-256 `8fbd57f5a65145ff0078abcd48f643f66be0427038ac9c416d2b79f4182420aa`
- `outputs/phase3a_correlated_noise_preflight/config.json` — 0 values; SHA-256 `1a4bbcc2657af7b1a5e36d6898bf4fbc8a6823aeefcfe16ebc7b0fe4a72a6651`
- `outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json` — 8 values; SHA-256 `9083e0f3901ffabbb1f8d04cf9e0fb056e3a72b2d080322b13814562b472806d`
- `outputs/stage4_noise_adaptive_feasibility_v1/seed_inventory.json` — 19 values; SHA-256 `4fab12469a82d51ce502d8477d00e47c0905f16eadf7f46bafe6bd32bf7ba751`
- `outputs/stage4_noise_adaptive_feasibility_v1/seed_audit.json` — 0 values; SHA-256 `572c1b3c2fcbedda81cf42c0a0b18d26380600784de73c4487058d8dc908f1c1`
- `outputs/cnn_architecture_stage1_v1/seed_inventory.json` — 0 values; SHA-256 `f5ab1f123f2a10555411e9d7ea7fd4b8f79e10927833f464eebf20b9aeccd44a`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/seed_inventory.json` — 54 values; SHA-256 `2a3223a7444e4b176048590958c252be85d1b681150d844888605a445d8adbd3`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/seed_inventory.json` — 216 values; SHA-256 `d6065c7c2aa52bd1d9d85e3b9aa31c7ece232eb2f7610c1202dd59e96ef859a8`
- `outputs/neural_decoder_diagnostic/structured_seed_inventory.json` — 396 values; SHA-256 `ce044c465f9dea959f4b5c34f92fc256433b224d2bfc3f76f9a2e040a7eaec7d`
- `outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000/structured_seed_inventory.json` — 72 values; SHA-256 `1ead75aa13fcf5637ab41479c9f2d0e203df952a87641a4e23ea527e55203263`

No independent-test, sealed-test, final-test, held-out sample arrays, or labels were opened, read, hashed, summarized, or used.

An initial broad filename-only search unintentionally displayed filenames under a historical independent-replication raw-data directory. No listed artifact was opened or used; subsequent seed screening read only the development metadata listed above.

The audit can verify only seed values recorded in the listed development metadata. Unrecorded RNG use cannot be ruled out.
