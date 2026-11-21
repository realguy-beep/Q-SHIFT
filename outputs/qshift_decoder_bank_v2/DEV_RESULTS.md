# DB2 development results

**Verdict: `ADVANCE = true`.** All six criteria fixed in `PLAN_DB2.md` (F1–F6, amendment A1) pass for the amended rule DB2.

Three qualifications come with this verdict:

- **The run cannot separate DB2 from the approved rule.** The approved rule, kept as the arm DB2_PLAN, would also pass all six criteria on this run. Over all 23 episodes it made slightly fewer errors (928 against DB2's 938).
- **The predicted weak case was never sampled.** The null panel N drew states A, A and B. Burst-free OFF, the case where DB2 was predicted to lose (+8 errors and one switch per episode), did not come up.
- **This is development evidence only.** There are 2–4 episodes per panel, and nothing here is confirmatory.

## Run

| Item | Value |
|---|---|
| Code | Commit `d4e2f6057`. `db2_run.py dev` checked that the tree was clean and that `FIDELITY.json` passed before launch. |
| Run | 23 episodes on 8 workers, 2026-11-21 12:11–14:40 UTC (8,973 s). All 23 jobs finished. |
| Fidelity | DB2's code re-ran DB1's dev episode R_e0 and matched DB1's stored record on every block: BANK, STATIC, AD3, ORACLE and A_nominal keys, errors and decoded bits, plus plausible sets and estimates (`FIDELITY.json`). |
| Seeds | 2,093 fresh seeds, disjoint from 21,125 earlier values, which include every DB1 seed (`DB2_SEEDS.json`, test `test_seeds`). |
| Analysis | Run twice into separate folders. `ANALYSIS.json` and `TIMELINE.json` are byte-identical (`cmp`). |
| Stored | `results/dev/` holds ANALYSIS, TIMELINE, RUN_STATUS and the 23 episode records. The decoded-bit archives stay in the ignored `work/dev/`. |
| Changed after the run | Nothing: no rule, prior, κ, criterion or arm. |
| Seals | Not opened. No held-out or sealed data was read. |

Each episode has 24 scored blocks of 1,000 evaluation rows, so 24,000 rows per episode. A difference of 0.001 in LER is therefore 24 errors per episode.

## Errors per episode (mean; all arms decode the same rows)

| Panel (episodes) | DB2 | DB2_PLAN | BANK (DB1) | AD3 | STATIC | ORACLE | DB2 predicted |
|---|---|---|---|---|---|---|---|
| C0 (2) | 39.5 | 39.5 | 39.5 | 40.5 | 39.5 | 39.5 | 28.8 |
| N (3: A, A, B) | 41.3 | 41.3 | 41.3 | 41.7 | 114.7 | 41.3 | — (OFF/C not drawn) |
| **R (4)** | **33.5** | 33.5 | 139.2 | 287.5 | 33.5 | 26.8 | 28.8 |
| R_long (2) | 28.0 | 28.0 | 82.0 | 152.5 | 28.0 | 16.5 | 28.8 |
| RB (2) | **29.5** | 46.0 | 35.0 | 94.5 | 119.5 | 15.5 | 24.6 |
| RX (4) | 56.0 | **45.2** | 208.2 | 370.0 | 74.5 | 30.2 | 38.8 |
| S1 (2) | 48.5 | 48.5 | 48.5 | 89.0 | 193.0 | 36.0 | 42.0 |
| S4 (2) | 39.5 | 39.5 | 29.0 | 45.0 | 106.5 | 21.5 | 35.6 |
| U (2) | 43.0 | 43.0 | 43.0 | 42.0 | 133.5 | 21.5 | — |
| **Total (23)** | **938** | **928** | 2,068 | 3,682 | 2,016 | 653 | |

The predictions assumed perfect identification and the training risk table. As with DB1, the observed values run higher because identification lags, and C0's real error rate on key A was 1.6 per block rather than the 1.2 in the training table.

## Criteria (fixed before the run; values are DB2 differences in LER)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| F1 | R: DB2 − BANK ≤ −0.001, all episodes ≤ 0 | **pass** | −0.0044. Per episode −0.0035, −0.0043, −0.0066, −0.0033 (4/4). |
| F2 | R and R_long: DB2 − STATIC ≤ +0.0005 | **pass** | 0.0000 on both. DB2 makes exactly STATIC's errors on these panels. |
| F3 | RX: DB2 − min(STATIC, BANK) ≤ −0.0005 | **pass** | −0.0008 against STATIC. Per episode 0.0000, −0.0010, −0.0009, −0.0012. |
| F4 | RB, S1, S4: DB2 − BANK ≤ +0.001 and DB2 − STATIC ≤ −0.001 | **pass** | Against BANK: RB −0.0002, S1 0.0000, S4 +0.0004. Against STATIC: −0.0038, −0.0060, −0.0028. |
| F5 | Null (C0 + N): DB2 − BANK ≤ +0.0005, ≤ 1 switch per episode | **pass** | 0.0000 and 0 switches in all 5 episodes. Burst-free OFF was not drawn, so this is weaker evidence than planned. |
| F6 | U: DB2 − AD3 ≤ +0.001 | **pass** | +0.00004 (one error per episode). |

**The approved rule scored the same way.** DB2_PLAN gets:

| # | DB2_PLAN result |
|---|---|
| F1 | −0.0044, 4/4 episodes ≤ 0 |
| F2 | 0 and 0 |
| F3 | −0.0012 |
| F4 | RB +0.00046 against BANK, so it passes |
| F5 | 0, with 0 switches |
| F6 | +0.00004 |

So DB2_PLAN also passes every criterion. Amendment A1 predicted that it would fail two of them:

- **F4.** A1 predicted RB 48.8 for DB2_PLAN against BANK's 14.4. In the run DB2_PLAN made 46.0 on RB, close to its prediction, but BANK made 35.0, far above its prediction, so the gap shrank to 11 errors.
- **F5.** This failure depended on a burst-free OFF episode, and none was drawn.

## What genuinely improved, and the evidence

1. **DB1's main failure is fixed.** On R, DB1's bank lost to STATIC in 4/4 episodes, at +0.0045 LER. DB2 ties STATIC exactly and beats BANK by 0.0044 in 4/4 episodes, with the same result on R_long. The mechanism matches the plan:
   - The hazard term keeps key A while the stream is in OFF, at a cost of 57 blocks and 26 errors on R.
   - It never decodes a first or recurrent A onset with the wrong key.
   - For first onsets, DB2 had 16/16 timely (by c + 1), against BANK's 13/16 and AD3's 0/16.
   - For recurrent onsets, DB2 had 10/10 timely, against BANK's 8/10.
2. **It keeps the bank's gains over STATIC and AD3 where the noise really moves.** S1, S4, RB, U and the N state-B episode are 0.0028–0.0092 LER better than STATIC. Total errors are 938, against BANK's 2,068, STATIC's 2,016 and AD3's 3,682.
3. **On mixed recurrence (RX), DB2 is the only arm below both STATIC and BANK.** It beats STATIC in 3/4 episodes and ties it in the fourth.
4. **The learned destination helps when it is right.** On RB, after seeing one change into B, DB2 holds B rather than A through OFF. That made it 15 and 18 errors better than DB2_PLAN on the two RB episodes.

## What did not improve, or got worse

- **The learned destination hurts when it is wrong.** On RX_e0 DB2 saw one OFF→B change, then held B through OFF. When A returned at block 25, that one block cost 48 errors against DB2_PLAN's 5. With DEST_ALPHA = 0.25, a single observation moves 62% of the destination weight to the state it saw, which is overconfident for one data point. This one block decides the DB2 versus DB2_PLAN totals.
- **S4 is still worse than BANK** (+10.5 errors per episode, inside the F4 margin). In D, with no change seen out of D, the worst-case next state includes A, so DB2 holds key A instead of D for 9 blocks.
- **On R and R_long, DB2 behaves like STATIC rather than adapting.** It holds A almost throughout: R_long holds A for 39 blocks and costs 23 errors against ORACLE. On R, the remaining gap to ORACLE is 6.7 errors per episode. The first-onset limit in the plan says any causal policy pays some of this; the rest is the price of holding A through OFF.
- **The OFF transition is never followed** (0/24 OFF events timely, by design). The breakeven hazard is 2.6%, and the prior hazard of 1/30 sits above it for the whole episode.
- **Unknown onsets in U are no faster** (3–4 blocks for every adaptive arm). DB2 adds nothing here; it falls back to AD3's estimate like DB1.

## Remaining limitations

- **Too few episodes.** With 2–4 episodes per panel, the bootstrap bounds in `ANALYSIS.json` are descriptive only. The DB2 versus DB2_PLAN difference rests on three episodes.
- **Coverage gap.** A burst-free OFF null episode, the case predicted to cost DB2 and break DB2_PLAN, was not sampled. Any next step should fix that panel's draw rather than rely on random state choice.
- **Fixed design.** All results come from the fixed simulated templates A–D, q = 0.01, p = 0.003, d = 5. There is no hardware data and no claim of decoder superiority beyond this simulation.
- **Not tuned, but now seen.** DEST_ALPHA and the hazard prior were set before the run and not tuned on it. Any change made now, for example a stronger destination prior, would be tuned on this data. It would need a fresh development run before any confirmatory step.
- **Fidelity episode is not evidence.** On DB1's R_e0, DB2 made 34 errors against BANK's 132. That episode was seen before DB2 was designed, so it is not counted as evidence.

## Deviations

- **Amendment A1** (documented at the top of `PLAN_DB2.md`, before any DB2 data existed) replaced the approved rule with the hybrid rule at κ = 0 and kept the approved rule as the DB2_PLAN arm. This run shows the motivating prediction (that DB2_PLAN would fail F4 and F5) did not hold. The two rules are statistically indistinguishable here.
- **No other deviations** from `PLAN_DB2.md`.

## Not done (needs authorization)

No confirmatory frozen sampling, sealed evaluation or held-out data was run or opened. Natural next steps, none started:
- a fixed-draw null panel including burst-free OFF;
- a pre-registered choice between DB2 and DB2_PLAN;
- a confirmatory run.
