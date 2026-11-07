# Phase 3B experiment log

## Audit completed before replication

- Reviewed Phase 3A `REPORT.md`, `EXPERIMENT_LOG.md`, `config.json`, `run_phase3_pilot.py`, all v1–v4 result JSONs, and v4 raw files.
- v1 is excluded: it passed conditional composition fractions directly as channel probabilities, creating approximately 50% residual rates and invalid noise strength.
- v2, v3, and v4 are not replications. All use seed roots 31503001, 31503002, and 31503003. Their corresponding raw NPZ files have identical SHA-256 hashes across versions, so they are successive corrected checkpoints over the same samples. v4 added structure checks and analysis metadata.
- The exact corrected Phase 3A runner SHA-256 is pinned in `CONFIG.json` and the Phase 3B runner imports its `make_circuit`, `decoder_for`, `sample`, and `structure_signature` definitions. The v4 result checksum is also pinned. This preserves circuit, channel conversion, and matcher definitions.
- Scientific limitation retained: each `DEPOLARIZE1/2(0.01)` is replaced with independent one-qubit Pauli channels on each participating qubit, including ancilla participants. It is not a correlated two-qubit gate-noise model. Measurement noise is zero. DEM conversion uses `approximate_disjoint_errors=True`.

## Protocol freeze and feasibility

The pre-registered protocol was saved and SHA-256 hashed before final test generation. The hash is `eb052d2679937a8a9b2e291f03af1347ceb46e4a6acbcaf8f3526b47b52517a0`. The Phase 3B runner has its own frozen SHA-256 in configuration and refuses to run if it changes. Final seed roots are 31604001 through 31794001 in increments of 10,000; condition seeds are root + 101, 201, 301, and 401. These do not overlap Phase 3A or development seed 31999001.

A separate, non-test timing check used seed 31999001 and 30,000 X-biased shots. Fixed and X-specialist batched decoding together took 0.0287 seconds. This data was not saved or included in Phase 3B. With Phase 3A's 12 disagreements per 36,000 shots, 30,000 shots per seed was expected to yield about 10 informative disagreements per seed if the pilot rate held. The final design fixed 20 seeds and 30,000 shots per seed for each of four conditions (2.4 million total shots) before outcomes were examined.

## Final run

The ideal circuit check passed (256/256 all-zero detector and observable samples). All four conditions passed circuit-schema and common-structure checks. Twenty seed bundles were generated; each holds 30,000 detector rows and observable targets for each of four conditions. Identical detector arrays were passed directly to all five decoder roles (fixed, three specialists, and condition-informed oracle). Observable labels were used after decoding for residual scoring only.

Primary result: X-specialist had 43,675 residual errors vs fixed's 43,673 across 600,000 X-biased shots. It won on 6 seeds, lost on 11, and tied on 3. There were 162 changed corrections, with 82 X-specialist-only failures and 80 fixed-only failures. Mean seed difference was +0.00000333 rate (candidate minus fixed), exact sign-test p=.332, and the seed-bootstrap 95% interval crossed zero. The Phase 3A reduction did not reproduce.

Integrity check: aggregate counts equal the sum of all per-seed results; all 20 raw file hashes match; detector matrices have 24 columns; protocol, Phase 3A runner, Phase 3A v4 result, Phase 3B runner, and output checksums are retained in `SHA256_MANIFEST.json`.
