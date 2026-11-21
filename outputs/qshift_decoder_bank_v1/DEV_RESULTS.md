# DB1 development results

**Verdict: `ADVANCE = false`.** Five of the six pre-declared criteria pass. **D2 fails clearly:** on the primary R panel the training-selected static decoder beats the bank. Nothing here is confirmatory, and no confirmatory proposal is made from this run.

## Run

| Item | Value |
|---|---|
| Code | commit `b4b1abc27`; clean tree checked by `db_run.py dev` before launch |
| Run | 16 episodes, 8 workers, 2026-11-21 08:51–10:24 UTC (5,566 s); all 16 jobs return code 0 |
| Seeds | fresh DB1 validation seeds, disjoint from training and from 18,964 prior seed values (`DB1_SEEDS.json`, test `test_seeds`) |
| Analysis | run twice into separate folders; `ANALYSIS.json` and `TIMELINE.json` byte-identical (`cmp`) |
| Stored | `results/dev/` holds ANALYSIS, TIMELINE, RUN_STATUS and the 16 episode records. Decoded-bit archives stay in the ignored `work/dev/` |
| Nothing changed afterwards | No threshold, template, risk entry, κ or criterion was changed after the run |

Panels: 24 scored blocks × 1,000 evaluation rows per episode, so each episode is 24,000 rows.

## Errors per panel (all arms on the same rows)

| Panel (episodes) | BANK | BANK_ID | AD3 | AD | STATIC | ORACLE | A_nominal |
|---|---|---|---|---|---|---|---|
| C0 (2) | 82 | 82 | 82 | 82 | 82 | 82 | 2,232 |
| N (2: OFF, C) | 39 | 39 | 39 | 39 | 149 | 39 | 139 |
| **R (4), primary** | **565** | 565 | 1,306 | 1,366 | **129** | 105 | 1,741 |
| S1 (3) | **115** | 115 | 211 | 211 | 521 | 85 | 2,828 |
| S4 (3) | **66** | 74 | 123 | 123 | 318 | 56 | 662 |
| U (2) | 84 | 84 | 84 | 84 | 311 | 47 | 436 |

## Criteria (fixed in `PLAN_DB1.md` before the run)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| D1 | R: BANK − AD3 ≤ −0.001, BANK ≤ AD3 in every episode | **pass** | −0.0077 LER; episodes −0.0088, −0.0105, −0.0077, −0.0039 (4/4 ≤ 0) |
| D2 | R: BANK − STATIC ≤ −0.001 | **fail** | **+0.0045**; episodes +0.0041, +0.0035, +0.0043, +0.0063 (STATIC better in 4/4) |
| D3 | Null: BANK − STATIC ≤ +0.0005, zero BANK switches | pass | −0.0011 (C0 equal; N's state-C episode STATIC +103 errors); 0 switches in 4/4 null episodes |
| D4 | Recurrent ON timely (by c + 1): BANK − AD3 ≥ 0.20 | pass | BANK 3/4, AD3 0/4 |
| D5 | U: BANK − AD3 ≤ +0.001 | pass | 0.0000 (identical errors, 84 = 84) |
| D6 | S1, S4: BANK − AD3 ≤ 0 | pass | S1 −0.0013 (3/3), S4 −0.0008 (3/3) |

With 2–4 episodes per panel, the bootstrap bounds in `ANALYSIS.json` are descriptive only.

## What genuinely improved, and the evidence

1. **Versus AD3, the bank responds much faster to known states.**
   - **Known relocations:** reached the acceptable key in 1 block in 9/9 relocations, against 3–5 blocks for AD3 and AD.
   - **Recurrent ON:** delays 1, 1, 1, 2 for BANK, against 3, 4, 3, 2 for AD3.
   - **First ON:** delays 1, 1, 1, 1 for BANK, against null, 4, 3, 3 for AD3.
   - This cut errors by 57% on R (1,306 → 565), 45% on S1 (211 → 115) and 46% on S4 (123 → 66). BANK was better in every one of those 10 episodes.
   - The one-block delay is the causal floor established in `VERIFICATION.md` (claim 7).
2. **The null panels are stable.** BANK made zero key switches on the four static episodes, matching ORACLE's errors exactly. AD and AD3 change key 21–23 times on the same episodes; on these episodes that cost nothing, but it is not stable.
3. **There is no harm outside the bank.** On U (an unseen burst W06), the plausible set emptied and BANK fell back to AD's estimate (39 of 48 blocks). It made exactly AD3's errors, and it never decoded with the nominal model.
4. **The static comparator matters, and it was missing from AD2/AD3.** On R, the single static key A (129 errors) beats AD3 (1,306) by 90% in every episode. The adaptive claims in AD2/AD3 were never tested against this baseline. On S1, S4, N and U, STATIC is far worse (for example 521 vs 115 on S1), so neither arm dominates.

## What did not improve: why D2 fails

The R errors split by true state and BANK's key, summed over the 4 episodes:

| R blocks | Blocks | BANK | STATIC | ORACLE |
|---|---|---|---|---|
| A state, BANK on key A | 25 | 58 | 58 | 58 |
| **A state, BANK on another key** | **9** | **463** | 11 | 11 |
| OFF state, BANK on key A | 13 | 11 | 11 | 7 |
| OFF state, BANK on another key | 49 | 33 | 49 | 29 |

- **Where the cost comes from:** BANK's whole deficit comes from 9 blocks. Burst A was present, but BANK was still on the OFF key, at about 51 errors per block. These are the unavoidable reactive blocks: each of the 8 ON changes costs at least one block, and one recurrent ON cost two.
- **What switching OFF saves:** on 49 OFF blocks, about 0.3 errors per block (49 → 33 in total).
- **The cause is a design flaw in DB1, not a tuning issue.** The risk gate picks the key with the lowest worst-case LER over the plausible set **for the current block only**. It does not price the chance that the burst returns before the next detection.
  - Key A costs about 0.3 errors per OFF block, while a missed A block costs about 50.
  - So switching OFF only pays if the burst stays away for about 150 blocks per return. R's dwells are 4–5 blocks.
- **BANK_ID behaves the same.** It had identical errors on R (565), so the gate's worst-case over the plausible set adds nothing on R. The only difference between the two arms is 8 errors on S4.
- **The general limit:** under the causal floor, any purely reactive policy is beaten by a robust static key whenever a costly state recurs faster than its cost asymmetry can repay. This is the review's robust-fallback argument, confirmed on our data.

## Remaining limitations

- **Small sample:** 2–4 episodes per panel. The large effects (R, S1, S4 against AD3; R against STATIC) are consistent in every episode. Small ones, such as BANK − BANK_ID on S4, are not resolved.
- **A closed, pre-characterised bank** (5 states, all at p = 0.003). It is given advance knowledge that AD/AD3 lack, which is disclosed. Background shifts and S3 are not covered.
- **The U panel is limited:** the open-set path only reproduces AD (3-block delay on unknown onset). The bank does not learn new states.
- **The correctness metric overstates STATIC's misses:** "acceptable key" marks STATIC as never correct on OFF blocks, although it costs only about 0.3 errors per block there. The OFF-event delays for STATIC (all null) should be read with that in mind.
- **Single code distance** (d = 5), weight-3 public bursts, simulation only. Nothing here concerns hardware or decoder superiority.

## Next step (not run; needs a new plan and fresh seeds)

The failure points to a **transition-aware risk gate**. It would leave a costly-state key only when the expected saving over the expected dwell exceeds the expected cost of a late return, with the return rate estimated from training schedules. This must be specified before any new data is generated, and tested on fresh development seeds (a DB2). It **cannot be evaluated on this run**, because the idea came from these results. No confirmatory frozen sampling has been done or started.

AD2's and AD3's results, freezes and verdicts are unchanged by DB1.
