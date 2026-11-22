# DB6-dev results: the alarm-gated block-lookahead overlay (LA)

**Status: development evidence only, not confirmatory.** It is one pre-registered attempt (PROPOSAL_DB6.md) on fresh
DB6 seeds, frozen at `99aa4a84f` (DB6_FREEZE.json). The LA rule itself was found by replaying the DB2–DB4 development
records (FEASIBILITY.json), so this run is its first test on data it was not chosen on. It is still the designer's own
run, and a separate confirmatory study is needed before any claim is made. CF1 and every sealed dataset were not
used.

**The latency contract.** The LA arms decode block t after seeing block t's own 2,000 detection-only rows. That is
one block of decoding latency, so they are not comparable with W0F's real-time contract. W0F remains the confirmed
real-time result (CF1). The fair comparisons for LA are LA_BANK, LA_DB2 and LA_STATIC, which get the same latency
and the same data.

## Run

| Item | Value |
|---|---|
| Episodes | 27 (AA3 AB3 BA3 BB3 S1 2 S4 2 U2 N_C2 N_OFF3 RX4) |
| Scored blocks | 6–29, 1,000 eval rows each (24,000 rows per episode) |
| Started / finished | 2026-11-22 14:30:03Z / 16:32:47Z (7,363 s, 8 workers) |
| Jobs | 27/27 returncode 0, no reruns, `state: ready_for_analysis` |
| Analysis | run twice into separate directories: ANALYSIS.json and TIMELINE.json byte-identical |
| Archive check | strict (hash, arm set, exact key set, 125-byte width, zero padding, counts): passed |

## Pre-registered decision: ADVANCE

| Criterion | Rule | Result | Pass |
|---|---|---|---|
| E1 | mean(LA_W0F − W0F) ≤ −3 and exact sign test p ≤ 0.05 | mean **−6.48** errors/episode; 18 better, 0 worse, 9 tied; p = 3.8e−6 | yes |
| S1 | no episode worse than W0F by > 24 | max episode harm 0 | yes |
| S2 | no block worse than W0F by > 24 | max block harm 0 | yes |
| S3 | wrong-state LA uses ≤ 5% | 0 of 51 uses (CP upper 5.7%) | yes |
| S4 | RX pooled ≤ 0 and every RX episode ≤ +12 | pooled −44; episodes −8, −11, −13, −12 | yes |
| E2 | arm to confirm (LA_W0F vs LA_BANK, LA_DB2) | LA_W0F: −37.7 vs LA_BANK, −6.9 vs LA_DB2 per episode | **LA_W0F** |
| R | harm rate (episodes with LA_W0F > W0F) | 0 of 27, CP upper 10.5% | reported |

ADVANCE = E1 ∧ S1 ∧ S2 ∧ S3 ∧ S4 = **true**.

S3's Clopper–Pearson upper bound (5.7%) is slightly above the 5% threshold. The pre-registered rule is on the
observed rate (0%), so S3 passes, but 51 uses are too few to bound the wrong-state rate below 5% with 95%
confidence. A confirmatory study should size the number of uses for that.

## Pooled errors (27 episodes, 648,000 eval rows per arm)

| Arm | Errors | | Arm | Errors |
|---|---|---|---|---|
| ORACLE | 574 | | W0F | 959 |
| LA2_W0F (exploratory) | 783 | | W0 | 958 |
| **LA_W0F** | **784** | | DB2_PLAN | 1,031 |
| LA_DB2 | 971 | | DB2 | 1,128 |
| LA_BANK | 1,801 | | STATIC | 2,288 |
| LA_STATIC | 2,070 | | BANK | 2,441 |
| AD3 | 4,314 | | A_nominal | 10,014 |

LA_W0F removes 175 of W0F's 385 errors above ORACLE (**45% of the gap**). The overlay helps every base arm (BANK
−640, DB2 −157, STATIC −218), but LA_W0F is the best of them.

## By panel (errors summed over episodes)

| Panel | n | W0F | LA_W0F | LA2_W0F | LA_DB2 | ORACLE | LA uses (wrong) |
|---|---|---|---|---|---|---|---|
| AA | 3 | 95 | 93 | 85 | 93 | 74 | 7 (0) |
| AB | 3 | 115 | 85 | 80 | 85 | 56 | 6 (0) |
| BA | 3 | 117 | 89 | 84 | 290 | 65 | 5 (0) |
| BB | 3 | 129 | 86 | 67 | 73 | 38 | 5 (0) |
| N_C | 2 | 35 | 35 | 35 | 35 | 35 | 2 (0) |
| N_OFF | 3 | 68 | 67 | 62 | 66 | 51 | 1 (0) |
| RX | 4 | 159 | 115 | 112 | 115 | 102 | 18 (0) |
| S1 | 2 | 93 | 76 | 76 | 76 | 76 | 2 (0) |
| S4 | 2 | 63 | 53 | 33 | 53 | 33 | 5 (0) |
| U | 2 | 85 | 85 | **149** | 85 | 44 | 0 (0) |

What this shows:
- **The gain is at onsets.** LA fired on only 51 of 648 scored blocks, and every gain comes from those blocks:
  the onset cost that M4 identified (431 of W0F's 760 excess errors in the feasibility replay). That matches the
  mechanism the proposal predicted.
- **LA never cost an error.** No episode and no block was worse than W0F. On a block where LA does not fire,
  LA_W0F uses W0F's key, so the two arms are identical there by construction.
- **No effect on N_C or U.** LA never fired on U (an unknown state outside the bank), so it neither helped nor hurt.
  The gap to ORACLE on U (85 vs 44) is untouched; U stays DEFERRED.
- **DB2 stays fragile on BA** (LA_DB2 290 vs LA_W0F 89), as in DB4 and CF1. The overlay doesn't fix destination
  learning.

## Exploratory arm: LA2_W0F (ungated)

LA2 applies the lookahead whenever the single-block fit is a singleton, alarm or not. Its pooled total (783) equals
LA_W0F's, but that hides a trade: it gains on BB, S4 and AA, and it **loses +64 on U** (149 vs 85, both episodes
worse, by +38 and +26). Without the alarm gate, a singleton fit on an out-of-bank state picks a wrong key. This is
evidence for keeping the gate. LA2 was not part of the decision and won't be taken forward.

## What this does and does not support

It supports taking **LA_W0F** to a confirmatory study, under a one-block-latency contract, against LA_BANK,
LA_DB2, LA_STATIC and W0F, with the section 6 baselines in PROPOSAL_DB6.md.

It does not support:
- any claim that LA beats W0F under a real-time contract (it uses data W0F is not allowed to see);
- a confirmed improvement (27 development episodes, one attempt, designer-run);
- any statement about hardware or about d other than 5.

## Files

- `results/dev/ANALYSIS.json`, `results/dev/TIMELINE.json` (from `python db6_run.py analyze`)
- `results/dev/RUN_STATUS.json`
- `results/dev/records/*.json` (27 records; each holds its archive's SHA-256)

The per-block bit archives (`work/dev/archives`, 1.9 MB) are kept locally, not committed, as in DB4.
