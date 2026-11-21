# DB3 plan: tiebreak between the DB2 risk-gate rules (development only)

**Status: plan only, not built.** Nothing in DB1 or DB2 is changed. Seals stay closed. No confirmatory sampling.

## Why

DB2's development run (`../qshift_decoder_bank_v2/DEV_RESULTS.md`) passed F1–F6 for both candidate rules and could not separate them. The two rules made 938 and 928 errors, and they differed in only 3 of 23 episodes. The run also had two design gaps:

1. **It never sampled burst-free OFF.** The null panel draws its state at random and drew A, A and B. OFF is the null case where the rules are predicted to differ.
2. **Its recurrence panels favour one rule.** RB (B after B) suits learning the destination. RX visits A, then B, then A, which is neutral. No panel has B followed by A, the order where learning is predicted to cost most. One real block of that kind (RX_e0, block 25) cost DB2 43 errors.

So the DB2 result says nothing about which rule is better. The answer depends on whether bursts tend to repeat the previous type, which DB2's panels decided by construction.

## What the training table predicts (before any DB3 data)

`design_feasibility.py` uses DB1's TRAINING.json risk table only and assumes perfect identification with one block of lag. Values are errors per episode, then key switches.

| Panel | ORACLE | STATIC | BANK | DB2_PLAN (worst, κ .0005) | **W0 (worst, κ 0)** | DB2 (hybrid, κ 0) |
|---|---|---|---|---|---|---|
| N_OFF | 4.8 | 28.8 | 4.8 / 0 | 28.8 / 0 | 12.8 / 1 | 12.8 / 1 |
| N_C | 24.0 | 62.4 | 24.0 / 0 | 33.6 / 1 | 24.0 / 0 | 24.0 / 0 |
| AA (A, then A) | 12.8 | 28.8 | 111.2 / 4 | 28.8 / 0 | 28.8 / 0 | 28.8 / 0 |
| BB (B, then B) | 14.4 | 112.0 | 14.4 / 0 | 48.8 / 4 | 48.8 / 4 | **24.6 / 1** |
| AB (A, then B) | 13.6 | 70.4 | 62.8 / 2 | 38.8 / 2 | 38.8 / 2 | 38.8 / 2 |
| BA (B, then A) | 13.6 | 70.4 | 62.8 / 2 | 38.8 / 2 | 38.8 / 2 | **83.0 / 2** |
| **Family score** | | | 280.0 | 217.6 | **192.0** | 212.0 |

Two predictions follow:

- **Hysteresis.** κ = 0 instead of 0.0005 gains 16 errors on N_OFF and 9.6 on N_C, and loses nothing on any panel in the table.
- **Learning the destination.** It gains 24.2 on BB and loses 44.2 on BA. In a family where repeat and change are equally likely it is a net loss.

**W0 is a third candidate.** It is the worst-case rule with κ = 0, the "worst κ=0" column of DB2's own design table, and was fixed from training data before any DB2 sample. It was set aside in A1 because its predicted RB cost (48.8) would exceed BANK's predicted 14.4 by more than F4 allows. In the DB2 run BANK actually made 35.0 on RB.

**Disclosure:** the decision to bring W0 back was made after seeing the DB2 development results. That is why the choice is made on fresh seeds and not on DB2's data.

## Candidates

| Arm | Rule | Parameters | Simplicity rank |
|---|---|---|---|
| W0 | worst case over next states, no learning | κ = 0, hazard prior 1/30 | 1 (fewest moving parts) |
| DB2_PLAN | the rule approved for DB2 | κ = 0.0005 | 2 |
| DB2 | hybrid (learned destination after the first observed change) | κ = 0, DEST_ALPHA = 0.25 | 3 |

**Reference arms:** BANK (DB1), STATIC, ORACLE, AD3 and A_nominal are kept exactly as in DB2, so the code paths that passed fidelity stay unchanged.

No new parameter values are introduced. DEST_ALPHA, the hazard prior (A0 = 1, B0 = 29) and κ keep their DB2 values.

## Panels (fresh DB3 seeds)

Every panel starts in OFF. Bursts begin at block 6 or 7 and last 4–5 blocks, with OFF gaps of 4–5 blocks, as in DB2.

| Panel | Schedule | Episodes | Purpose |
|---|---|---|---|
| N_OFF | OFF throughout (fixed, not drawn) | 3 | DB2's coverage gap; hysteresis effect |
| N_C | C throughout (fixed) | 2 | hysteresis effect when stationary |
| AA | OFF, A, OFF, A, OFF | 2 | same as DB2's R; all candidates predicted equal |
| BB | OFF, B, OFF, B, OFF | 4 | where learning should help |
| AB | OFF, A, OFF, B, OFF | 3 | change of type, A first |
| BA | OFF, B, OFF, A, OFF | 4 | where learning should hurt |
| **Total** | | **18** | |

More episodes go to BB and BA, the panels where the candidates are predicted to differ.

**Runtime.** DB2 ran at 3,120 CPU s per episode, plus about 10% for the extra arm. With 8 workers that is about 2–2.5 h.

## Pre-declared selection rule

**Score.** S(c) = the sum over the 6 panels of candidate c's mean errors per episode. Each panel has equal weight, whatever its episode count. Lower is better.

**Eligibility.** A candidate is eligible only if all three of these hold:

| # | Condition |
|---|---|
| E1 | On N_OFF and N_C, at most 1 key switch per episode. |
| E2 | On every panel, the mean is no more than 12 errors per episode above STATIC's (an LER difference of 0.0005). |
| E3 | It passes DB2's F1–F6 on DB2's development records. DB2 and DB2_PLAN already do. W0 is checked by the replay below. |

**Choice.**
- Take the eligible candidate with the lowest S.
- If an eligible candidate ranked simpler is within 12 errors of that lowest S, choose the simpler one instead.
- Simplicity order: W0, then DB2_PLAN, then DB2.

**Reported regardless of the choice:**
- the pairwise DB2 − DB2_PLAN result per panel, which is the question as originally asked;
- every per-panel paired difference with its per-episode values;
- each candidate's worst-panel regret against the best candidate on that panel.

**Predicted outcome:** W0, with S = 192 against DB2's 212 and DB2_PLAN's 217.6.

**How this could come out differently.** Real identification lags more than the idealisation assumes, as both DB1 and DB2 showed. A lag on the BB panel helps DB2, because it holds B during the lag. A lag on N_OFF delays leaving A by the same amount for every candidate with κ = 0.

## The W0 replay on DB2's records (E3; no sampling)

The gate is a pure function of the plausible set P, the tracker and the previous key. The DB2 records store P and the tracker for every block, and the tracker does not depend on the arm. So W0's keys can be recomputed exactly for all 23 DB2 development episodes.

A block's errors are known when another arm used the same key in that block. If W0 chooses a key no arm used, that block is marked unknown, and W0 fails E3 only if a criterion fails even with the unknown blocks counted favourably.

The replay runs and is committed before the DB3 run starts. Its only role is to decide E3.

## Build steps (after approval)

1. **Setup.**
   - Create `outputs/qshift_decoder_bank_v3/` on the branch `claude/qshift-decoder-bank-v3`, cut from `claude/qshift-decoder-bank-v2`.
   - The v3 code imports the DB2 modules, just as DB2 imported DB1.
   - New code: `db3_config.py` (panels, the W0 arm, the seed namespace `qshift-decoder-bank-v3:db3`) and `db3_run.py` (the arms, analysis and selection rule).
2. **Seeds.** Write `DB3_SEEDS.json`, screened against every prior inventory including `DB2_SEEDS.json`.
3. **Tests.**
   - W0 is the DB2 gate in "worst" mode with κ = 0.
   - The selection rule, on synthetic inputs, including the simplicity tie-break.
   - The panel schedules.
   - The table above, against `design_feasibility`.
   - No seal is touched, and all files are LF-only.
4. **Replay.** Run the W0 replay and commit `W0_REPLAY.json`.
5. **Fidelity.** Re-run DB2 development episode RB_e1, where DB2 and DB2_PLAN differ, through the v3 code. It must match DB2's stored record on every block for every DB2 arm. This takes about 50 min.
6. **Commit, then run.** Commit with a clean tree, then run the 18 episodes. Run the analysis twice and check the outputs are byte-identical.
7. **Write up.** Write `DEV_RESULTS.md`, then commit and push `claude/qshift-decoder-bank-v3`. Nothing is merged.

**Total time:** about 1 h to build, 1 h for fidelity and 2–2.5 h for the run.

## Claim boundary

DB3 picks one rule for a later confirmatory proposal. It is a development selection on fresh simulated seeds and is not confirmation. A confirmatory frozen run of the chosen rule needs separate authorization. The study stays at d = 5 with the simulated templates A–D, and makes no hardware claim.
