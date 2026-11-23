# DB8-dev run, attempt 2: stopped at the first U_FAR episode (design defect)

**Freeze:** `DB8_FREEZE_A2c.json` (freeze commit 48161c830).
**Run folder:** `work/dev_a2`, reserved 2026-11-23T15:34:27Z. It was run with 8 workers and all 64 jobs were queued.
**Stopped:** 2026-11-23T19:09:35Z, with state `failed`, while the runner waited on `U_FAR_e0`.

The error was `ValueError('Encountered a decomposed error instruction with an undetectable component (0 detectors). This is not supported.')`.

## Cause

The U_FAR state chosen under PROTOCOL_DB8 section 3 was `X03`, support (3, 25, 34). For that support the correlated-matching decoder cannot be built: `re1.decoders` → `model_v14.build_matching` → `pymatching.Matching.from_detector_error_model` rejects the decomposed error model.

Only the ORACLE arm decodes with the true unknown state's key. It needed this decoder in the first U_FAR block that was decoded.

The DB8 tests built the circuit for each new support but not its decoders, so the defect was not caught before the freeze. The code error is not an infrastructure error, so `runkit.run_jobs` stopped the run fail-closed.

Checked without sampling afterwards: decoders for UO (1, 3, 12, 38) and UN (7, 14, 42) build.

## What attempt 2 left

- **28 episode records and their 28 archives,** for AA (2), AB (3), BA (3), BB (3), S1 (2), S4 (2), RX (5) and U_E (8). There is no output for the null panels N_C and N_OFF (queued last) or for U_FAR, U_OUT and U_NEAR.
  - Their byte sizes and SHA-256 hashes are in `RUN_ATTEMPT2/OUTPUTS.json`.
  - They were not parsed, decoded, summarised or analysed, and they will not be.
- **`RUN_ATTEMPT2/journal.jsonl`** and **`RUN_ATTEMPT2/RUN_STATUS.json`**, copied byte for byte.
- `work/dev_a2` stays reserved and is not reused.

## Change for attempt 3

- **Amendment A3** (`AMENDMENT_A3.md`, approved by the project owner) replaces U_FAR's state with `V06`, support (1, 42, 47).
- **New test:** every state any arm can decode with, the bank, E and the three new states, must build decoders.
- **New folder and freeze:** run folder `work/dev_a3`, freeze `DB8_FREEZE_A3.json`.
- **Unchanged:** all other code, rules, seeds and episodes, and `FIDELITY.json`. Fidelity runs DB6 episodes, which never build a decoder for an unknown state.
