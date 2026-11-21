# DB3 tiebreak results (development only)

**Verdict: no candidate is selected (`chosen = null`).** All three candidates fail eligibility condition E2 on the same panel (AA) for the same reason:
- **What happened.** On one AA episode, every bank-family arm took DB1's shared unknown path during an undetected A burst. Two blocks of that path cost 99 errors.
- **Why that excludes all three.** The path is identical in W0, DB2_PLAN, DB2 and DB1's BANK, so it is not a difference between the rules.
- **Following the rule anyway.** The pre-declared rule says no eligible candidate means no selection. It is not overridden here.

**What the run does show** (descriptive only, not a selection):
- **W0 ranks first** on the pre-declared score: 255.0, against DB2_PLAN's 284.8 and DB2's 330.9.
- **W0 has the smallest worst-panel regret:** 14.3, against 20.0 and 91.5.
- **Learning the next state lost.** DB2 versus DB2_PLAN, the original question, comes out +46.1 errors summed over panels, so DB2 is worse. DB2 gained on BB, N_OFF and N_C (by κ alone on the null panels) and lost 91.5 errors per episode on BA.

## Run

| Item | Value |
|---|---|
| Code | Commit `e6600fca0`. `db3_run.py dev` checked that the tree was clean, that `FIDELITY.json` passed and that `W0_REPLAY.json` was present before launch. |
| Run | 18 episodes on 8 workers, 2026-11-21 15:30–17:09 UTC (5,945 s). All 18 jobs finished. |
| Fidelity | The DB3 code re-ran DB2 development episode RB_e1 and matched DB2's record on every block, for every DB2 arm (DB2, DB2_PLAN, BANK, AD3, STATIC, ORACLE, A_nominal). It compared keys, errors, decoded bits, plausible sets, estimates, the tracker, alarms and template fits (`FIDELITY.json`). |
| E3 replay | W0 was replayed on DB2's 23 records (`W0_REPLAY.json`). The replay first reproduced DB2's and DB2_PLAN's recorded keys on every block. W0 then matched DB2_PLAN on every block, with 0 unknown blocks, and passed F1–F6. All three candidates pass E3. |
| Seeds | 1,638 fresh seeds, disjoint from 23,218 earlier values, which include all DB1 and DB2 seeds (`DB3_SEEDS.json`, test `test_seeds`). |
| Analysis | Run twice into separate folders. `ANALYSIS.json` and `TIMELINE.json` are byte-identical (`cmp`). |
| Stored | `results/dev/` holds ANALYSIS, TIMELINE, RUN_STATUS and the 18 records. The decoded-bit archives stay in the ignored `work/dev/`. |
| Changed after the run | Nothing: no rule, margin, panel or parameter. |
| Seals | Not opened. No held-out or sealed data was read. |

## Mean errors per episode (all arms decode the same rows)

| Panel (episodes) | W0 | DB2_PLAN | DB2 | BANK | AD3 | STATIC | ORACLE | W0 / PLAN / DB2 predicted |
|---|---|---|---|---|---|---|---|---|
| N_OFF (3) | 21.3 | 30.7 | 21.3 | 18.0 | 17.7 | 30.7 | 18.0 | 12.8 / 28.8 / 12.8 |
| N_C (2) | **22.0** | 42.0 | **22.0** | 22.0 | 22.0 | 114.5 | 22.0 | 24.0 / 33.6 / 24.0 |
| AA (2) | 86.0 | 86.5 | 86.0 | 299.5 | 368.0 | **38.0** | 28.5 | 28.8 / 28.8 / 28.8 |
| BB (4) | 45.8 | 45.8 | **31.5** | 38.5 | 92.2 | 115.5 | 18.0 | 48.8 / 48.8 / 24.6 |
| AB (3) | 43.7 | 43.7 | 42.3 | 130.7 | 214.3 | 75.7 | 25.0 | 38.8 / 38.8 / 38.8 |
| BA (4) | **36.2** | **36.2** | 127.8 | 124.5 | 224.0 | 77.2 | 22.8 | 38.8 / 38.8 / 83.0 |
| **Score S** (sum of panel means) | **255.0** | 284.8 | 330.9 | 633.2 | 938.2 | 451.6 | 134.3 | 192.0 / 217.6 / 212.0 |
| Total errors (18 episodes) | **739** | 808 | 1,044 | 1,741 | 2,741 | 1,395 | 393 | |

Per-episode values, switches, held-A counts and sources are in `results/dev/ANALYSIS.json`.

## Selection rule (fixed in `PLAN_DB3.md` before the run)

| Step | W0 | DB2_PLAN | DB2 |
|---|---|---|---|
| E1: null panels, ≤ 1 switch per episode | pass (1, 1, 1 / 0, 0) | pass (0, 0, 0 / 1, 1) | pass (1, 1, 1 / 0, 0) |
| E2: every panel ≤ STATIC + 12 | **fail** (AA +48.0) | **fail** (AA +48.5) | **fail** (AA +48.0, BA +50.6) |
| E3: F1–F6 on DB2's records | pass | pass | pass |
| Eligible | no | no | no |
| Worst-panel regret against the best candidate | **14.3** (BB) | 20.0 (N_C) | 91.5 (BA) |
| **Chosen** | | **none** | |

## Why every candidate failed E2

AA_e1 has bursts of A at blocks 6–9 and 14–18. Its change test alarmed falsely at block 3, then missed both real onsets until block 19. The current segment therefore pooled OFF and A data:

- **Blocks 8 and 9.** No template fitted, so the plausible set was empty and the arms took DB1's unknown path. At block 8 that meant AD's estimate, costing 45 errors; at block 9 it held that key, costing 54. STATIC made 2 and 0 errors on those blocks.
- **Who was affected.** W0, DB2_PLAN, DB2 and BANK all made these errors, because the unknown path is shared code inherited unchanged from DB1.
- **The other AA episode.** AA_e0 has 40 errors for each candidate and for STATIC.

**Across all 18 episodes** the unknown path ran on 15 blocks. Only these two caused large losses. The one other notable block was BA_e1 block 18, where DB2 lost 50 errors because it held a learned key B while A was active.

**A lesson about the rule, not a change to it.** E2 measures each candidate against STATIC, so it can exclude all candidates at once for a failure they share. A tiebreak rule should rank candidates on their paired differences and apply absolute guards separately. This is recorded as a design flaw of DB3's rule. The rule is not re-scored, because that would mean changing it after seeing the results.

## Findings, and the evidence for each

1. **Learning the next state is the losing component, as predicted.** Against DB2_PLAN, DB2 gains 14.3 per episode on BB but loses 91.5 on BA. BA was predicted at +44.2 and came out at twice that, losing in 4/4 episodes (+94, +173, +52, +47).
   - **Why it loses.** After one B burst, DB2 holds B through OFF, so the A onset is decoded with B's key until it is identified.
   - **How badly.** On BA, DB2 is worse than DB1's BANK (127.8 against 124.5) and worse than STATIC (77.2).
2. **Removing the hysteresis (κ = 0) helps on the null panels, as predicted.** W0 against DB2_PLAN is −20.0 on N_C (2/2 episodes) and −9.3 on N_OFF (3/3), with at most one switch.
   - **Where else it differs.** On all four burst panels W0 and DB2_PLAN are identical or within 0.5 errors. On DB2's 23 episodes they were identical on every block.
   - **What it means.** W0 is DB2_PLAN with a free improvement on stationary streams.
3. **N_OFF was predicted 12.8 for W0 and came out 21.3.** The step from A to the OFF key happened one block later than predicted (held A 24 blocks out of 72). And unlike BANK (18.0), W0 never takes the OFF key immediately: the hazard term makes it wait.
4. **The bank family still beats STATIC broadly.** W0 is below STATIC on 5 of 6 panels: −9.3 on N_OFF, −92.5 on N_C, −69.8 on BB, −32.0 on AB and −41.0 on BA. Its total is 739 errors, against STATIC's 1,395, BANK's 1,741 and AD3's 2,741. The exception is AA: on burst-free OFF and on A-only bursts, STATIC (key A) is already near-optimal, and the shared unknown path makes the bank family worse than that.

## Remaining limitations

- **No selection was made**, so no rule is ready for a confirmatory proposal from this run.
- **Few episodes.** With 2–4 episodes per panel, every value here is descriptive. AA's E2 failure rests on one episode. It is still a real failure mode, not noise: a false alarm followed by missed onsets sends the arms down the unknown path.
- **The unknown path is now the dominant weakness.** It is inherited from DB1 and is the same for all candidates. DB1's task listed "robust static fallback" as a priority, and this run is direct evidence for it. Falling back to the static key when P is empty would have avoided both large losses. That change has not been made or tested; it would need its own plan and fresh development seeds.
- **Fixed simulation only.** The study uses d = 5 with the simulated templates A–D. There is no hardware claim and no claim of decoder superiority.

## Deviations

None from `PLAN_DB3.md`. The only post-run steps were the analysis and this write-up.

## Not done (needs authorization)

No confirmatory sampling and no sealed or held-out data. Possible next steps, none started:
- a plan for a static fallback on the unknown path;
- a corrected selection rule that ranks paired differences, run on fresh seeds;
- then a confirmatory proposal.
