# DB2: a transition-aware risk gate for the decoder bank (development plan)

**Status:** plan only. Nothing has been built or sampled for DB2. Building and running it need the owner's approval of this plan. **Nothing here is confirmatory.** No seal is read, and AD2/AD3/DB1 evidence is read-only.

## Why

DB1 (`outputs/qshift_decoder_bank_v1/DEV_RESULTS.md`) beat AD3 on R, S1 and S4, but the static key A beat it on R (129 vs 565 errors).
- **Where the deficit came from:** 9 blocks where burst A returned while the bank held the OFF key, at about 51 errors per block.
- **What switching OFF saved:** about 0.3 errors per OFF block.
- **The cause:** DB1's risk gate judged only the current block. It never priced a change before the next check, which is the earliest any causal policy can react.

**An error in DB1's criteria, found while writing this plan.** D2 asked BANK to beat STATIC by 0.001 LER on R. But the training risk table predicts that even ORACLE beats STATIC there by only about 0.0007 (`design_feasibility.py`), and the run gave 0.00025. **D2 could not have passed for any policy.** DB1's conclusion stands, since BANK was 0.0045 *worse* than STATIC. But DB2's criteria are each checked against this kind of prediction before they are fixed (below).

## The idea, and why one step ahead is enough

The choice of decoder key does not change what the policy observes later. The change test, identification and estimation all use detector data and labelled rows, which are the same whichever key decodes them. So the cost of each block can be minimised separately: a per-block Bayes choice against the *predicted* state of the block about to be decoded is optimal, and no multi-step planning is needed.

DB1 used the state of the last observed segment. DB2 also allows for the chance that the state changes before the next block.

## Method (changes to DB1 only)

Everything in DB1 is kept: AD3's change test, the template fit, the plausible set P, the unknown path, κ = 0.0005, the 5-key bank, and `TRAINING.json` (read-only, no retraining).

**The risk of key k at block t:**

  risk(k) = max over s ∈ P of [ (1 − h_s) · R[s][k] + h_s · max over d ≠ s of R[d][k] ]

- **R:** DB1's training risk table.
- **h_s:** the learned hazard of leaving state s. It is the posterior mean of a Beta(1, 29) prior, updated causally inside the episode:

  h_s = (1 + number of changes out of s) / (30 + number of blocks identified as s)

- **What counts as a change:** an AD3 alarm whose old and new segments are identified as different states. False alarms raise h, which errs towards the safer key.
- **What counts as a block identified as s:** a block whose segment had P = {s} when it was scored. Blocks with |P| > 1 or P empty count for no state.
- **The prior** is a fixed rule, "one expected change per 30-block episode". It is not tuned.
- **Worst case over the next state d:** the bank cannot know which burst comes next. This matches DB1's worst case over the current plausible set.
- **The rule reduces exactly to DB1 when h = 0** (unit test).

**Why it helps on R.** In an OFF state, holding key A costs 0.0012 − 0.0002 = 0.0010 per row. The worst next state costs key A 0.0116 (burst B) and the OFF key 0.0494 (burst A). So holding A is worth it once h > 0.0010 / (0.0010 + 0.0494 − 0.0116) = 2.58%.
- **Before any change**, the prior gives 3.3%, falling below 2.6% after about 9 quiet OFF blocks.
- **After one A → OFF change**, h_OFF stays above 2.6% for at least 40 OFF blocks.
- **For the other bursts there is no penalty:** keys B, C and D cost OFF data no more than the OFF key (R[OFF][·] = 0.0002), so DB2 keeps them freely.

## Design selection (training table only, before any DB2 data)

`design_feasibility.py` computes the expected errors for each rule from `TRAINING.json`'s risk table. It assumes identification is correct one block after each change. It uses the panel schedules below, with dwells fixed at 4, and no validation data.

Expected errors per episode (24,000 scored rows):

| Panel | ORACLE | STATIC | DB1 BANK | Mixture, α = 0.25 | **DB2 (worst-case next state)** |
|---|---|---|---|---|---|
| C0 | 28.8 | 28.8 | 28.8 | 28.8 | 28.8 |
| N (OFF) | 4.8 | 28.8 | 4.8 | 4.8 | 7.8 |
| N (C) | 24.0 | 62.4 | 24.0 | 24.0 | 24.0 |
| R | 12.8 | 28.8 | 111.2 | 77.0 | **28.8** |
| R_long | 9.8 | 28.8 | 59.0 | 77.0 | **28.8** |
| RB | 14.4 | 112.0 | 34.4 | 14.4 | 48.8 |
| **RX** | 17.6 | 70.4 | 126.0 | 87.0 | **38.8** |
| S1 | 31.8 | 184.8 | 42.0 | 42.0 | 42.0 |
| S4 | 25.6 | 90.4 | 28.4 | 28.4 | 35.6 |

**The alternatives:**
- **A learned-destination mixture** (Dirichlet α per destination) was considered. It still pays for A's first appearance, so on R it ends up between BANK and STATIC (77). With α = 1 it is no better than BANK (122). It is kept as an ablation arm with α = 0.25.
- **The worst-case rule** costs at most 14 expected errors per episode over the better of BANK and STATIC, on RB. It matches STATIC on R and R_long, and it is the only rule expected to beat both baselines on RX.

**Disclosure:** the DB2 rule was chosen from this table. The table uses training-derived risks and panel schedules I wrote myself. It is a development design choice, made before any DB2 data exist. The predictions assume perfect identification. DB1's real BANK on R made 141 per episode against 111 predicted, so real numbers will be higher.

## Development run (fresh DB2 seeds; disjoint from DB1 training, DB1 validation and all prior inventories)

Per block: 2,000 unlabelled + 250 labelled + 1,000 evaluation rows; 30 blocks; blocks 6–29 scored; q = 0.01; p = 0.003.

| Panel | Schedule (generator and scorer only) | Episodes |
|---|---|---|
| C0 | A static | 2 |
| N | one static state per episode from OFF, A–D | 3 |
| R | as DB1: A on at 6 or 7; three dwells from {4, 5} | 4 |
| R_long | A on at 6 or 7 for 4–5 blocks, then OFF to the end | 2 |
| RB | as R, with burst B | 2 |
| **RX (primary)** | OFF; A on at 6 or 7; then OFF, B, OFF, A, OFF, each dwell from {4, 5}; truncated at block 29 | 4 |
| S1 | A → B at 15 | 2 |
| S4 | B → C at 10, C → D at 20 | 2 |
| U | A → E (W06, outside the bank) at a random block in 8–12 | 2 |

That is 23 episodes, about 2.2 million generated rows, estimated at 2.5–3 hours on 8 workers.

**Arms (same evaluation rows):**

| Arm | Role |
|---|---|
| **DB2** | candidate |
| DB2_MIX | ablation: learned-destination mixture, α = 0.25 |
| BANK | DB1's rule, unchanged |
| STATIC | key A |
| AD3 | comparator; needed for U |
| ORACLE | true model |
| A_nominal | burst-free |

AD and BANK_ID are dropped to save decoding time; DB1 already reports them.

**Fidelity check before the run:** DB1's development episode R_e0 is re-run through the DB2 code. BANK, STATIC and AD3 must reproduce the committed `results/dev/records/R_e0.json` block keys and errors exactly. This reuses a seen DB1 episode for code identity only, and no claim is drawn from it.

## Pre-declared criteria (checked against the predicted values above)

Promotion to a confirmatory proposal (`ADVANCE`) needs all of F1–F6.

| # | Criterion | Predicted |
|---|---|---|
| F1 | R: DB2 − BANK ≤ −0.001, and DB2 ≤ BANK in every episode | −0.0034 |
| F2 | R and R_long, each: DB2 − STATIC ≤ +0.0005 | 0.0000 |
| F3 | **RX: DB2 − min(STATIC, BANK) ≤ −0.0005**, computed per arm over the panel | −0.0013 |
| F4 | RB, S1 and S4, each: DB2 − BANK ≤ +0.001 and DB2 − STATIC ≤ −0.001 | +0.0006 at most / −0.0026 or lower |
| F5 | Null (C0 + N): DB2 − BANK ≤ +0.0005, and at most 1 DB2 key switch per episode | +0.0001 / 0–1 |
| F6 | U: DB2 − AD3 ≤ +0.001 | 0 |

**Always reported:**
- per-arm errors and LER;
- paired episode differences, which are descriptive at 2–4 episodes;
- event delays by type;
- the h_s trajectories;
- the blocks where DB2 held a burst key on OFF data, and what that cost;
- the DB2 − DB2_MIX ablation;
- wrong-burst blocks;
- a comparison of the observed errors with the predictions in this table.

## Build steps (after approval)

1. `outputs/qshift_decoder_bank_v2/`: new code, which imports DB1's modules read-only.
2. Tests, including:
   - h = 0 reduces to DB1;
   - the break-even values above;
   - hazard updates only from past blocks;
   - the RX/R_long/RB schedules;
   - LF-only files;
   - no seal;
   - disjoint seeds.
3. Seeds `db2:…`, screened against every earlier inventory, DB1's included.
4. Fidelity re-run, then commit and freeze **before** the development run.
5. The development run, two identical analyses, then `DEV_RESULTS.md`, commit and push to `claude/qshift-decoder-bank-v2`. Nothing is merged.

## Claim boundary

This is development evidence at d = 5, with public weight-3 bursts at p = 0.003, in simulation, over a closed bank. A first appearance of the costliest burst still costs one block for any causal policy that ever leaves its key. DB2 can at best match the static key on A-only schedules; its possible gain is on mixed schedules (RX, RB, S1, S4), where no static key is good. AD2, AD3 and DB1 results are unchanged by anything here.
