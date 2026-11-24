# DB8-dev post-run analyser fix: seed identity check

**When:** after attempt 3 finished (`work/dev_a3`, freeze commit 7ac49b16c, 64 of 64 jobs, no reruns) and before any result was read. Approved by the project owner.

## Defect

`db8_analyze.seeds_for` expected an evaluation seed (`bNN:eval`) for all 30 blocks. The episode job draws evaluation rows, and records their seed, only in scored blocks 6–29. So `runkit.load_strict` rejected the first record with `ValueError: seed identity AA_e0`, before anything was analysed.

The tests used synthetic seeds and did not compare `seeds_for` with what the job records.

## Check before the fix

This compared only the seed fields of all 64 records:

- every recorded seed equals the frozen `DB8_SEEDS.json` value;
- no record has an extra seed;
- the only keys missing are the evaluation seeds of blocks 0–5.

## Fix

`seeds_for` now expects evaluation seeds only for blocks in `C.SCORED`. A new test checks this key set against the episode job.

Nothing else changed:

- the loader's other identity checks (episode set, job status, archive paths and hashes, archive keys, row counts and padding);
- the criteria A1–A4 and the decision;
- the reported values.

The run remains bound to `DB8_FREEZE_A3.json` at commit 7ac49b16c. This fix is a later commit, and the frozen analyser can be compared with it by `git diff 7ac49b16c -- db8_analyze.py`.
