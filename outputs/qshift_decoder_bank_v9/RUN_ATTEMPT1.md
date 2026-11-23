# DB8-dev run, attempt 1: stopped before any result (infrastructure)

**Freeze:** `DB8_FREEZE.json` (freeze commit 7d2aec31a, code_head 4e217ee09).
**Run folder:** `work/dev`, reserved 2026-11-23T13:41:02Z. It was run with 8 workers and all 64 jobs were queued.
**Stopped:** 2026-11-23T15:14:12Z, with state `failed`. The runner raised `RunStop('AA_e0: infrastructure error after output was written')`.

## Cause

The episode job writes `archives/<job>.npz` and then `records/<job>.json`. It creates `archives/` itself but not `records/`. The fidelity command creates `records/` before it starts its jobs, and so did DB6's own run. `cmd_run` in DB8 did not.

So when AA_e0 finished, it saved its archive and then failed to open its record file (`FileNotFoundError`). An output had already been written, so `runkit.run_jobs` did not retry the job. It stopped the run fail-closed, terminated the pool, and moved the outputs of every in-flight episode to `partial/<job>/attempt1/`.

No record file exists. None of the decoding code, the decision rules, the seeds or the analysis code was involved.

## What attempt 1 left

- **7 episode archives** (AA_e0, AB_e0–e2, BA_e0–e2). Their byte sizes and SHA-256 hashes are in `RUN_ATTEMPT1/PARTIALS.json`. They were not loaded, decoded, summarised or analysed, and they will not be.
- **`RUN_ATTEMPT1/journal.jsonl`** and **`RUN_ATTEMPT1/RUN_STATUS.json`**, copied byte for byte from `work/dev`.
- The `work/dev` folder stays reserved (its `RUN.lock` is never released). It is not reused.

## Change for attempt 2

- **Fix:** `db8_run._prepare_run(run)` creates the parent folder of every output path. `cmd_run` calls it right after reserving the run folder and before any job starts.
- **Tests:** a regression test reserves a fresh folder, runs `_prepare_run`, and writes both output paths. The wiring test checks that `_prepare_run(run)` comes before `RK.run_jobs(`.
- **Unchanged:** the episode job, the decision rules, the seeds, the episodes, the protocol and `FIDELITY.json`.
  - Fidelity is not repeated, because the gate runs only the episode job (unchanged).
  - `cmd_run` and the folder setup are not part of what the fidelity gate tests.
- **New run folder** `work/dev_a2` and **new freeze file** `DB8_FREEZE_A2.json`. `DB8_FREEZE.json` is kept unchanged as historical evidence and is itself hashed into the new freeze.
- `db8_analyze.py` now reads `work/dev_a2`.

Attempt 2 re-runs all 64 episodes from the same DB8 seeds. Only attempt 2's records and archives are analysed.

## Freeze addendum: `DB8_FREEZE_A2.json` superseded before use

`DB8_FREEZE_A2.json` (freeze commit 6931cb43d) failed the fresh-checkout check on Windows, on one file only: `RUN_ATTEMPT1/journal.jsonl`.

- **Cause:** the repository rule `* text=auto` checks `.jsonl` out with CRLF on Windows, and the freeze hashes `.jsonl` bytes without normalising line endings. This checkout and Linux checkouts are LF and pass.
- **Fix:** a v9-scoped `.gitattributes` pins `*.jsonl` to LF. The freeze moves to `DB8_FREEZE_A2b.json`.
- **Status:** no run used `DB8_FREEZE_A2.json`. It is kept unchanged and hashed into the new freeze.

`DB8_FREEZE_A2b.json` (freeze commit 7680b3e5d) then failed the same check on `.gitattributes` itself, which has no suffix and also fell under `text=auto`.

- **Fix:** `.gitattributes` now pins itself to LF. Every frozen file was then checked: each is either normalised by the hash rule or pinned to LF.
- **New freeze:** `DB8_FREEZE_A2c.json`.
- **Status:** no run used `DB8_FREEZE_A2b.json`. It is kept and hashed into the new freeze.
