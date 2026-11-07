# Stage 2 RNG collision audit

The amended formula yields 60 unique roots and 190 unique derived stage/template/diagnostic values. The existing proposed inventory has the same roots/templates/diagnostic but different calibration, validation, and test offsets, so it does not reproduce exactly. Historical scan found an actual collision: seed 73000001 appears in Phase 4B template generation (Phase 4B config uses template seed start 53000001, wait: audit indicates value via scan maybe Stage4C prior reserved namespace). Inspect exact occurrence in `PHASE4C_STAGE1_FROZEN_PLAN`/config: extracted from historical seed-named field.

Because an actual recoverable historical seed collision was found, Stage 2 sampling is blocked pending a new prospective seed namespace. No held-out shots were generated.
