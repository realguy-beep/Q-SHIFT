# Phase 2C Seed Collision Audit

The pre-pilot scan examined **948 files** below `outputs/` outside the new Phase 2C directory, including prior JSON/CSV/Markdown/Python/text records and NPZ seed/metadata fields. It extracted **519 distinct historical seed values** from recoverable records. There were **zero read failures**, **zero collisions**, and all **44 proposed Phase 2C seeds were internally unique**.

The 44 values comprise six diagnostic seeds (89000001–89000006), six development streams (89010001–89010006), six calibration streams (89020001–89020006), 24 pilot-root seeds (`89200001 + 100*cell_index + root_index`, root index 0–3), and two statistical resampling seeds (89300001 and 89300002). Full extracted values, their source files, and the exact examined-file inventory are preserved in `SEED_COLLISION_AUDIT.json`.

Coverage is limited to seed values present in recoverable files. Unrecorded historical RNG use cannot be screened or ruled out. The collision statement therefore applies to the recoverable repository evidence, not to unknown runs that left no seed record.

## Supplemental estimator RNG audit

The frozen runner also sets each sklearn forest `random_state` to its development Stim seed plus 1,000, yielding 89011001–89011006. These six estimator-internal RNG values were omitted from the initial 44-value inventory. A post-sampling supplemental audit in `AUXILIARY_RNG_AUDIT.json` confirms they are unique and disjoint from the 519 recoverable historical values and all 44 listed streams. They did not generate circuit shots and did not overlap any simulator or statistical seed. This is an inventory-documentation omission, not a sample-stream collision; it is retained as a preflight limitation.
