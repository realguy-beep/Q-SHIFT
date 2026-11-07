# Current Project Status

**Status:** exploratory software research; no validated adaptive advantage; no hardware integration.

## What is established

- Legacy starter data are highly repetitive and suitable only for prototype exploration without stronger split controls.
- Repetition-code matching remains the strongest validated baseline among the approaches tested.
- Detector-only regime classification can recognize some trained regimes in the small Phase 1 setting, but recognition did not yield improved residual logical performance.
- Specialist DEM/PyMatching models did not pass the Phase 2 usefulness gate.
- The Phase 3A surface-code specialist signal did not replicate in the independent Phase 3B study.
- Research history, key structured results, negative findings, and artifact inventory are consolidated under this directory.

## What is not established

- A reproducible gain over fixed PyMatching.
- Robust detection of unseen mixtures.
- Useful switching between specialist decoders.
- Scalability to large detector counts/distances.
- Hardware runtime, integration, or compatibility.

## Source issues to keep visible

1. Phase 1 report vs structured JSON per-regime totals differ. JSON totals are used for machine-readable master tables; raw replay is needed to resolve.
2. Phase 2 report prose conflates 2,401 condition-specific oracle errors with 2,402 validation-selected strategy errors; JSON/table definitions are clear.
3. Phase 3A corrected versions v2/v3/v4 are checkpoints on identical sample hashes, not replications.
4. Starter conversation metrics do not map to the local saved model or a preserved raw test artifact.

## Recommended next action

Review the Phase 4A proposal and authorize or revise it explicitly before any compute. The proposed first experiment tests model adequacy and calibration before any adaptive selector. If the user does not authorize Phase 4A, preserve this package as a complete handoff; do not infer authorization from the presence of the proposal.
