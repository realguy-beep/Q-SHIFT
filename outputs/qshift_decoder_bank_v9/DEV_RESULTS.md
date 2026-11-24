# DB8-dev results: no ADVANCE

**Run:** attempt 3, `work/dev_a3`, under `DB8_FREEZE_A3.json` (commit 7ac49b16c, amendment A3).

- It ran from 2026-11-23T19:22:53Z to 2026-11-24T03:09:08Z: 64 of 64 jobs, no reruns.
- Analysed with `db8_analyze.py` after the post-run seed-check fix (`ANALYSIS_FIX.md`, commit e4f9bed49).
- Two analyses gave byte-identical `results/dev/ANALYSIS.json` (sha256 prefix b79fe878447aef6d).

This is development evidence. Under the protocol, a no-ADVANCE result means no CF3 plan is written for these arms. CF2's NOT CONFIRMED verdict is unchanged.

## Decision

| Arm | A1 in-bank retention | A2 wrong actions, U_FAR ∪ U_OUT | A3 harm caps | A4 vs CB and LA_DB2 | ADVANCE |
|---|---|---|---|---|---|
| LA_R2 (cap 180), primary | **pass**: retention 1.00; 19 better, 0 worse, 5 tied; sign p 1.9e−6 | **pass**: 1 of 24 episodes (LA_R1: 9) | **fail** | **pass**: 3,210 vs 10,081 and 3,724 | **no** |
| LA_R2_170, secondary | **pass**: retention 0.974; same sign test | **pass**: 1 of 24 | **fail** | **pass**: 3,167 | **no** |

**A3 fails on U_NEAR only.** It fails on three counts:

- **Pooled harm:** U_NEAR pooled harm against W0F is +375 for LA_R2 and +327 for LA_R2_170. The cap is ≤ 0.
- **Worst episode:** the worst U_NEAR episode is +55. The cap per unknown episode is ≤ 12.
- **Worst block:** that same block is also the worst block overall, at 55. The block cap is ≤ 24.

U_E, U_FAR and U_OUT pass: their pooled harm is 0, 0 and −2, and no episode exceeds 0.

Note: CB does not have fewer errors than LA_R2 (10,081 vs 3,210).

## What happened on U_NEAR (descriptive)

U_NEAR's state is UN = X09, support (7, 14, 42). Its nearest bank state is B, at single-block λ = 28.2.

- In all 8 episodes the lookahead fired exactly once, in the onset block (block 8–12). It switched to `bank:B`, and that one block cost 41–55 errors more than W0F.
- After that it did not fire again, so each episode's total harm equals that one block's harm.
- The fit cap of 180 cannot filter this: UN fits B well (expected g ≈ 120 + 28).

This is the near-neighbour effect from Phase B, now for an out-of-bank state that sits close to B rather than to A.

## Other descriptive numbers

**Pooled errors over 64 episodes:**

| Arm | Errors |
|---|---|
| ORACLE | 1,372 |
| W0F | 3,031 |
| LA_R2_170 | 3,167 |
| LA_R2 | 3,210 |
| LA_R1 | 3,211 |
| LA_W0F | 3,211 |
| LA_DB2 | 3,724 |
| CB | 10,081 |

These pooled totals include the unknown panels. On the 24 in-bank episodes, LA_R2 keeps all of LA_W0F's gain over W0F (retention 1.00).

**Lookahead firings and wrong actions:**

| Arm | Firings | Wrong actions |
|---|---|---|
| LA_W0F | 67 | 20 wrong identifications |
| LA_R1 | 54 | U_FAR 5, U_OUT 4, U_NEAR 8 |
| LA_R2 | 46 | U_OUT 1, U_NEAR 8 |
| LA_R2_170 | 43 | U_OUT 1, U_NEAR 7 |

None of LA_R1, LA_R2 or LA_R2_170 took a wrong action on any in-bank panel or on U_E.

**Single-row harm against W0F:**

| Arm | Rows |
|---|---|
| LA_R2 | 383 |
| LA_R2_170 | 335 |
| LA_R1 | 389 |
| CB | 7,397 |

**The fit cap works on far states, not on near ones.** On U_FAR and U_OUT it cut wrong actions from LA_R1's 9 to 1. On U_NEAR it removed none, because UN is too close to B to separate in one block.

## Evidence

- `results/dev/`: `ANALYSIS.json`, the 64 records, `RUN_STATUS.json` and `journal.jsonl`.
- The archives stay local in `work/dev_a3/archives`. Their hashes are in the records.
- Earlier attempts: `RUN_ATTEMPT1.md` and `RUN_ATTEMPT2.md`. Their outputs were never analysed.
