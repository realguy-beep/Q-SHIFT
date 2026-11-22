# DB4 plan: static fallback on the unknown path (development only)

**Status: plan only, not built.** DB1–DB3 are not changed. Seals stay closed. No confirmatory sampling.

## Why

DB3 selected no rule (`../qshift_decoder_bank_v3/DEV_RESULTS.md`). All three candidates failed E2 on AA_e1 through the same code: DB1's unknown path.

**What happened on AA_e1:**
1. A false alarm at block 3, followed by two missed A onsets, left a segment of mixed OFF and A data.
2. No template fitted it, so the plausible set P was empty.
3. At block 8 the arms took AD's estimate, which named **no burst class**. That cost 45 errors against STATIC's 2. At block 9 they held it, costing 54 against 0.

DB1's original task named a "robust static fallback" as a priority. It was never built: DB1–DB3 all kept the unknown path unchanged.

## The rule (one change, to the unknown path only)

When P is empty:

| AD's estimate | Key used |
|---|---|
| **Accepted** (not flagged) **and names a burst class** | AD's key (unchanged) |
| Anything else: flagged, or no burst class | **the static key A** (was: AD's key, or hold) |

When P is not empty, nothing changes: the W0 gate (worst case over next states, κ = 0) decides.

### Why this rule, and not a pure static fallback

- **An estimate with no burst class contradicts the bank's own test.** Such an estimate decodes as nominal noise, which is what the OFF key does. But an empty P means the OFF template was rejected too, so decoding as OFF goes against the evidence.
- **When the bank's evidence excludes every template, key A is the safe default.** Its worst-case risk over the five templates is 0.0116, against 0.0494 for the OFF key.
- **A flagged estimate is the estimator saying it is unreliable.** Holding a key that came from that path can carry an earlier error forward, which is what happened at block 9.
- **An estimate that names a class is how the bank handles a burst outside its templates (panel U).** Removing it would cost U about 90 errors per episode (DB2: STATIC 133.5 against BANK 43.0). So it stays.

### Disclosure

The rule was designed after seeing DB3's AA_e1, and the trigger condition was chosen by looking at all 55 unknown-path blocks in DB2's and DB3's records. That is why the evidence below is labelled as seen-data replay. It is also why a fresh development run is required before any confirmatory proposal.

## Evidence before any DB4 sample: exact replay on DB2 and DB3 (41 episodes, seen data)

**Why the replay is exact:**
- The gate is a pure function of P, the tracker and the previous key.
- The new fallback always picks key A, and the STATIC arm decoded every block with key A.
- So every counterfactual block's errors are known. There were 0 unknown blocks, and the unchanged rules reproduce every recorded total.

| Panel (source) | W0 | **W0F** (W0 + fallback) | STATIC | BANK → BANK + fallback |
|---|---|---|---|---|
| C0, N, RB, R, R_long, S1, S4 (DB2) | — | identical to W0 on every block | — | unchanged except RX |
| RX (DB2) | 45.2 | 45.2 | 74.5 | 208.2 → 198.2 |
| U (DB2) | 43.0 | 43.0 | 133.5 | 43.0 → 43.0 |
| **AA (DB3)** | 86.0 | **37.5** | 38.0 | 299.5 → 229.5 |
| AB, BB, N_C, N_OFF (DB3) | 43.7, 45.8, 22.0, 21.3 | identical | 75.7, 115.5, 114.5, 30.7 | AB 130.7 → 131.0; others unchanged |
| BA (DB3) | 36.2 | 36.2 | 77.2 | 124.5 → 113.2 (DB2 rule: 127.8 → 116.5) |
| **Total, 41 episodes** | 1,667 | **1,570** | 3,411 | 3,809 → 3,585 |

**How often the fallback acts.** It triggered on 10 of 984 replayed blocks (1%):
- **One large saving:** AA_e1, where blocks 8–9 cost 99 errors before and 2 after. That episode drops from 132 to 35 errors.
- **The other nine triggered blocks** gained or lost at most one error each.
- **On U it triggered once** (U_e1 block 14, flagged), with no change in errors.

**What a fresh run can test.** The failure it fixes is rare. A fresh run of about 20 episodes may not reproduce it. So DB4's run is mainly a **no-harm and full-criteria check** of a single candidate, plus an observed trigger rate. The benefit claim rests on the mechanism and on the replay, and both are stated as such.

## Arms

| Arm | Role |
|---|---|
| **W0F** | the candidate: W0 gate plus the static fallback |
| W0 | paired no-harm reference (the same gate without the fallback) |
| DB2_PLAN, DB2, BANK, AD3, STATIC, ORACLE, A_nominal | as in DB3, so DB3's fidelity check carries over |

No other parameter changes. Hazard prior, κ, templates, τ values and AD3 all keep their DB3 values.

## Panels (fresh DB4 seeds)

Every regime that DB2 and DB3 tested gets at least two episodes:

| Panel | Schedule | Episodes |
|---|---|---|
| N_OFF | OFF throughout | 2 |
| N_C | C throughout | 2 |
| AA | OFF, A, OFF, A, OFF (as DB3) | 4 |
| BB, AB, BA | as DB3 | 2 each |
| S1 | A, then B at block 15 (as DB2) | 2 |
| S4 | B, then C at 10, then D at 20 (as DB2) | 2 |
| U | A, then an unknown burst E at block 8–12 (as DB2) | 3 |
| **Total** | | **21** |

AA and U get extra episodes: they are where the fallback can help (AA) or hurt (U).

**Runtime:** 3 waves of 8 workers at about 45 minutes each, so about 2.3 h.

## Pre-declared criteria (W0F only; paired, on the same rows)

Errors are per episode. 24 errors per episode equals an LER difference of 0.001.

| # | Criterion | Seen-data replay value |
|---|---|---|
| G1 | No harm: on every panel, mean W0F − W0 ≤ +2 | 0 everywhere except AA −48.5 |
| G2 | On every panel, W0F ≤ STATIC + 12 (DB3's E2) | AA −0.5, N_OFF −9.4; others ≤ −32 |
| G3 | U: W0F − AD3 ≤ +24 | +1.0 |
| G4 | BB, AB, BA, S1, S4 and N_C: each panel W0F − STATIC ≤ −12, and pooled over the six ≤ −24 | each between −32 and −145 |
| G5 | N_OFF and N_C: ≤ 1 key switch per W0F episode | 1, 1 / 0, 0 |
| G6 | AA: W0F − BANK ≤ −24, and W0F ≤ BANK in every AA episode | −192 |

**ADVANCE requires G1–G6.** ADVANCE would mean W0F is ready to be proposed for a confirmatory frozen run. Proposing that run, and running it, needs your separate authorization.

**This fixes DB3's design flaw.** G1 is a paired comparison against the same rule without the change, so a failure shared by both arms cannot sink the comparison. G2 stays as an absolute guard, reported separately.

**Reported regardless of the verdict:**
- every trigger: block, true state, AD estimate, and both keys' errors;
- W0F − W0 per episode;
- the trigger rate.

## Build steps (after approval)

1. **Setup.** Create `outputs/qshift_decoder_bank_v4/` on the branch `claude/qshift-decoder-bank-v4`, cut from v3. The v4 code imports DB3, and the loop is DB3's with one extra arm. The only new logic is the fallback branch for W0F.
2. **Seeds.** Write `DB4_SEEDS.json`, screened against every prior inventory including `DB3_SEEDS.json`.
3. **Tests.**
   - The fallback's truth table: accepted with a class, accepted without a class, and flagged.
   - W0F equals W0 whenever P is not empty.
   - The replay table above is reproduced from the stored records, so the replay is committed and tested.
   - The loop matches DB3's apart from the extra arm.
   - Panels, causality, no seal, LF-only files and seeds.
4. **Fidelity.** Re-run DB3 development episode **AA_e1**, the motivating episode, through the v4 code.
   - All DB3 arms must match DB3's stored record on every block: keys, errors, decoded bits, plausible sets, tracker and alarms.
   - W0F must reproduce the replay exactly: 35 errors, with fallback triggers at blocks 8, 9, 12 and 17.
   - This takes about 30 min.
5. **Commit, then run.** Commit with a clean tree, then run the 21 episodes. Run the analysis twice and check the outputs are byte-identical.
6. **Write up.** Write `DEV_RESULTS.md`, then commit and push `claude/qshift-decoder-bank-v4`. Nothing is merged.

**Total time:** about 1 h to build, 30 min for fidelity and about 2.3 h for the run.

## Claim boundary

A DB4 pass shows that W0F does no harm across every regime tested so far and meets every guard. It does not show a measured benefit on fresh data unless triggers occur. Any benefit claim beyond that rests on the seen-data replay, and is labelled as such. The study stays at d = 5 with simulated templates and makes no hardware claim.
