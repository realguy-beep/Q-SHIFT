# CF2 results: confirmatory run of LA_W0F

**Pre-registered decision: NOT CONFIRMED.** C1 and the safety gates G1, G2, G3, G5 and G6 pass. **G4 fails**:
3 of 96 lookahead uses were wrong-state, which puts the Clopper–Pearson 95% upper bound at 7.9%, above the 5% limit.
Under PLAN_CF2.md §3, CONFIRMED needs every gate, so CF2 does not confirm LA_W0F. C2 and C3 count only when CONFIRMED
holds, so they are not claimed either. The DB6 result stays development evidence.

This is a simulation study: a d=5 surface code, these noise panels, and one block of decoding latency. It was run
by the same team, from frozen commit `9b41acfac` (CF2_FREEZE.json).

## Run

| Item | Value |
|---|---|
| Episodes | 48 (AA4 AB6 BA6 BB5 S1 3 S4 4 U5 N_C3 N_OFF4 RX8), fresh `cf2:` seeds |
| Started / finished | 2026-11-23 05:08:26Z / 09:32:55Z (15,869 s, 8 workers) |
| Jobs | 48/48 returncode 0, no reruns, `state: ready_for_analysis` |
| Pre-run guards | head = freeze commit, clean tree, 85 frozen hashes (working copy and HEAD blobs), fidelity pass |
| Analysis | run twice: ANALYSIS.json and TIMELINE.json byte-identical |
| Archive check | strict (hash, arm list, exact key set, 125-byte width, zero padding, counts): passed |

**Deviations:** one, before any CF2 seed was used. The first fidelity attempt (FIDELITY_ATTEMPT1.json) matched DB6
on every field and bit, but reported `all_pass: false`. The cause was a rule I had added that the plan did not
contain: it required lookahead uses on U_e0, which had none in DB6. The rule was narrowed to BB_e0 (commit
`a083f3832`) and fidelity was re-run and passed. Both files are frozen. The run itself was the single planned attempt.

## Hypotheses (exact one-sided sign tests on nonzero episodes, Holm at α = 0.05)

| # | LA_W0F vs | Panels | n | mean d | median | better / worse / tied | p | Holm | bootstrap 95% mean |
|---|---|---|---|---|---|---|---|---|---|
| C1 | W0F | all | 48 | **−6.06** | −7 | 30 / 0 / 18 | 9.3e−10 | reject | [−7.7, −4.5] |
| C2 | LA_STATIC | AB BA BB S1 S4 N_C U | 32 | −65.3 | −62 | 32 / 0 / 0 | 2.3e−10 | reject | [−76.8, −54.3] |
| C3 | LA_BANK | AA AB BA RX | 24 | −43.6 | −37.5 | 17 / 6 / 1 | 0.017 | reject | [−62.0, −26.6] |

C1 also meets its effect rule (mean ≤ −3), so **C1 passes**. C2 and C3 reject H0, but they are **not claimed**,
because each counts only when CONFIRMED holds. The bootstrap intervals are descriptive only.

## Safety gates (LA_W0F vs W0F)

| Gate | Rule | Result | Pass |
|---|---|---|---|
| G1 | no episode d > +24 | max episode harm 0 | yes |
| G2 | no block > +24 | max block harm 0 | yes |
| G3 | ≤ 2 of 48 episodes with d > 0 | 0 of 48 (CP upper 6.1%) | yes |
| G4 | wrong-state CP upper ≤ 5% | **3 of 96 uses wrong, CP upper 7.9%** | **no** |
| G5 | RX pooled ≤ 0, every episode ≤ +12 | −90 pooled; −7 to −16 | yes |
| G6 | U pooled ≤ 0, every episode ≤ +12 | 0 pooled; all five 0 | yes |

**Where G4 failed.** All three wrong uses were on U, the out-of-bank panel. There the plan counts every
lookahead use as wrong, because the true state E has no bank key.

| Episode | Block | True state | LA key | W0F key | Errors (LA / W0F / ORACLE) |
|---|---|---|---|---|---|
| U_e1 | 8 | E | bank:A | bank:A | 7 / 7 / 0 |
| U_e2 | 10 | E | bank:A | bank:A | 6 / 6 / 0 |
| U_e3 | 11 | E | bank:A | bank:A | 5 / 5 / 0 |

In each case the single-block fit read E as A, the alarm fired, and LA chose `bank:A`. W0F was already using that
key, so these three uses changed no decoding and cost no errors. That observation came after the data were seen,
and it doesn't change the decision. The pre-registered gate measures whether the lookahead *identifies* the state
correctly, not what a wrong identification costs. On the in-bank panels, 0 of 93 uses were wrong.

The plan also flagged this risk ahead of time: with about 93 expected uses, a single wrong use would already fail
G4.

## What CF2 does show (reported; no claim beyond the decision above)

**Pooled errors (1,152,000 eval rows per arm):**

| Arm | Errors | Arm | Errors |
|---|---|---|---|
| ORACLE | 1,073 | W0F | 1,744 |
| LA2_W0F (ungated) | 1,441 | W0 | 1,733 |
| **LA_W0F** | **1,453** | DB2_PLAN | 1,834 |
| LA_DB2 | 1,730 | DB2 | 2,116 |
| LA_BANK | 2,421 | BANK | 3,492 |
| LA_STATIC | 3,827 | STATIC | 4,158 |
| AD3 | 7,618 | A_nominal | 18,344 |

LA_W0F removes 291 of W0F's 671 errors above ORACLE, or **43% of the gap**; DB6-dev showed 45%. No episode and no
block got worse.

**By panel (errors summed over episodes):**

| Panel | n | W0F | LA_W0F | LA_DB2 | ORACLE | LA uses |
|---|---|---|---|---|---|---|
| AA | 4 | 163 | 163 | 163 | 128 | 6 |
| AB | 6 | 235 | 186 | 175 | 144 | 16 |
| BA | 6 | 224 | 162 | 465 | 113 | 17 |
| BB | 5 | 204 | 134 | 119 | 103 | 15 |
| N_C | 3 | 66 | 66 | 66 | 66 | 1 |
| N_OFF | 4 | 77 | 77 | 77 | 58 | 0 |
| RX | 8 | 306 | 216 | 216 | 186 | 29 |
| S1 | 3 | 146 | 134 | 134 | 98 | 2 |
| S4 | 4 | 122 | 114 | 114 | 66 | 7 |
| U | 5 | 201 | 201 | 201 | 111 | 3 |

**Onset table.** An opportunity is a scored block whose true state differs from the previous block's.

| Destination | Opportunities | LA triggers | Correct | Errors saved vs W0F |
|---|---|---|---|---|
| A | 36 | 15 | 15 | 0 |
| B | 33 | 29 | 29 | 267 |
| C | 4 | 3 | 3 | 6 |
| D | 4 | 4 | 4 | 2 |
| E (out of bank) | 5 | 3 | 0 | 0 |
| OFF | 64 | 23 | 23 | 7 |
| Not an opportunity | — | 19 | 19 | 9 |

Almost all of the gain (267 of 291) comes at **B onsets**. At A onsets LA fired 15 times, always correctly, and
saved nothing: W0F's minimax key is already A. That matches the feasibility finding that A is the hard state to
see and the cheap one to insure.

**Other observations:**
- **LA_DB2.** It is still fragile on BA (465 against LA_W0F's 162) and better on AB and BB, as in DB6. No claim.
- **LA2_W0F (ungated).** Its pooled total is close to LA_W0F's (1,441 vs 1,453), and it did better in 31 of 48
  episodes. On U it tied this time (201), where in DB6 it lost 64. It remains exploratory: it was dropped after DB6,
  and CF2 can't support claims about it.

## What may be said

- **Not:** "LA_W0F is confirmed." The pre-registered criterion failed on G4.
- **Supported**, as a conditional statement under the frozen procedure: "In a pre-registered simulation run on
  fresh seeds, adding one block of lookahead to W0F lowered errors in 30 of 48 episodes and raised them in none (C1,
  p = 9e−10). The study's state-identification safety gate failed: 3 of 96 lookahead decisions on an out-of-bank
  state were wrong, although none changed the decoder used."
- **Unchanged:** W0F remains the confirmed real-time result (CF1). LA requires one block of latency.
- **Any further claim** needs a new plan. For example, it could re-specify G4 to count only uses that change the
  key, but it would have to be pre-registered on fresh seeds, and CF2's data could not be used to choose it.

## Files

- `results/cf2/ANALYSIS.json`, `results/cf2/TIMELINE.json` (from `python cf2_analyze.py`)
- `results/cf2/RUN_STATUS.json`
- `results/cf2/records/*.json` (48 records; each holds its archive's SHA-256)

The per-block bit archives (`work/cf2/archives`) are kept locally, not committed, as in DB4 and DB6.
