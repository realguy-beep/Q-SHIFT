# CF1 results: confirmatory run of W0F

A single confirmatory attempt, run as planned in `PLAN_CF1.md` from the frozen commit `d50d522df`
(`CF1_FREEZE.json`, 54 files). The owner authorized it with "Run CF1".

No sealed data was opened (RE1 H2, RE2 H3/H4, the V1.6 d=3 seal). Nothing in `v1`–`v4` was modified.

## Run

- **Episodes:** 48, from fresh seeds (`CF1_SEEDS.json`). None of the 4,368 seeds overlaps any of the 26,767
  values in earlier inventories.
- **Timing:** started 2026-11-22T09:15:46Z and finished 12:47:08Z (12,683 s), using 8 workers.
- **Re-runs:** none (`results/cf1/RUN_STATUS.json`).
- **Pre-run guard:** the head commit, a clean working tree and all 54 frozen hashes were checked before any
  sampling. Records were not opened until all 48 jobs had finished.
- **Analysis:** `cf1_analyze.py` was run twice into separate directories, and the two `CF1_ANALYSIS.json` files
  are byte-identical (SHA-256 `19c1cf4d…e25017a5`).

## Pre-registered hypotheses

All four are rejected at a family-wise α = 0.05 after Holm adjustment.

d is W0F errors minus comparator errors per episode, over scored blocks 6–29 (24,000 rows; 24 errors = 0.001 LER).

| # | Claim | Panels | n | mean d | 95% bound | p | Holm |
|---|---|---|---|---|---|---|---|
| H1 | W0F beats STATIC | AB, BA, BB, S1, S4, N_C, U | 37 | −74.7 | ≤ −64.9 | 5.0e−6 | **confirmed** |
| H2 | W0F beats BANK | AA, AB, BA | 18 | −110.5 | ≤ −86.6 | 1.0e−5 | **confirmed** |
| H3 | W0F within +24 of AD3 | U | 6 | +2.0 | ≤ +3.7 | 0.0156 | **confirmed** |
| H4 | W0F within +2 of W0 | all | 48 | +0.04 | ≤ +0.13 | 5.0e−6 | **confirmed** |

**Notes on the tests:**
- For H1, H2 and H4, the p values come from 200,000 random sign flips with a fixed seed. These p values sit at
  or near the smallest value the method can give: every H1 and H2 episode has d < 0.
- H3 uses exact enumeration over n = 6, and p = 1/64 is the smallest p possible at that n.
- H3's d values are [4, 0, 0, 2, 0, 6]. H4's are all 0 except one +2.

## Errors by panel (totals)

| Panel | ep | W0F | W0 | DB2_PLAN | DB2 | BANK | AD3 | STATIC | ORACLE |
|---|---|---|---|---|---|---|---|---|---|
| AA | 6 | 207 | 207 | 207 | 207 | 929 | 1920 | 207 | 170 |
| AB | 6 | 233 | 233 | 233 | 234 | 732 | 1259 | 446 | 133 |
| BA | 6 | 223 | 223 | 223 | 1000 | 991 | 1337 | 428 | 133 |
| BB | 6 | 228 | 228 | 228 | **148** | **179** | 500 | 616 | 92 |
| N_C | 5 | 92 | 92 | 198 | 92 | 92 | 92 | 544 | 92 |
| N_OFF | 5 | 102 | 102 | 129 | 102 | **82** | **81** | 129 | 82 |
| S1 | 4 | 141 | 141 | 141 | 141 | 141 | 255 | 723 | 111 |
| S4 | 4 | 127 | 127 | 127 | 127 | **92** | 170 | 424 | 73 |
| U | 6 | 276 | 274 | 274 | 274 | 274 | **264** | 902 | 147 |
| **Total** | 48 | **1629** | 1627 | 1760 | 2325 | 3512 | 5878 | 4419 | 1033 |

Bold marks a comparator that beats W0F on that panel.

## What is confirmed, and what is not

1. **Confirmed (H1).** W0F's adaptive decoding beats the best fixed key on every changing-noise panel, and in
   every one of those 37 episodes.
2. **Confirmed (H2).** On the burst-order panels, the worst-case gate beats DB1's bank in all 18 episodes, by
   about 0.0046 LER per episode on average. DB2 (hybrid) fails BA again: 1,000 errors against W0F's 223. That
   is consistent with DB3, and it shows why the worst-case gate was kept.
3. **Confirmed (H3).** On the unseen class U, W0F stays within 2 errors per episode of AD3, far inside the +24
   margin. Two caveats:
   - W0F is still slightly worse than AD3 there (276 vs 264).
   - It switches keys about 19 times per episode, because it follows AD's changing estimates.
4. **Confirmed (H4), meaning no harm only.** The static fallback fired on 11 of 1,152 blocks (1.0%). On 10 of
   them it tied W0, and on 1 (U_e2, block 18) it cost +2 errors. **It never helped.** So there is still no
   fresh-data evidence that the fallback has a benefit, as `PLAN_CF1.md` §2 anticipated. Its only demonstrated
   benefit remains the replay of the development episode DB3 AA_e1.
5. **Expected losses, as predicted.** BANK beats W0F on BB (+8.2 errors per episode), S4 (+8.8) and N_OFF
   (+4.0). These match the sign and size seen in development. DB2 beats W0F on BB by 13.3 per episode, more
   than in development. W0F is within 0.001 LER of ORACLE overall but not at it: 1,629 vs 1,033 errors in total.

## What may be claimed

**The claim CF1 supports:**

> In a pre-registered confirmation in simulation (a d=5 surface code under these correlated-noise panels), run
> on fresh seeds by the same team, the W0F decoder bank beat a fixed decoder and DB1's bank on changing-noise
> and burst-order panels. It was non-inferior to AD3 on an unseen noise class and to W0 without the fallback.

**Claims CF1 does not support:**
- independent confirmation, or hardware evidence;
- decoder superiority in general (BANK and DB2 each beat W0F on some panels);
- any benefit from the static fallback.

## Deviations

- None in procedure.
- The freeze hashed more files than the plan listed: it also covered the repo modules the episode loop
  imports. This only makes the freeze stricter.

## Files

- `results/cf1/CF1_ANALYSIS.json` and `RUN_STATUS.json`.
- `results/cf1/records/*.json` (48 files).
- The NumPy error-bit archives stay in `work/cf1/archives`. That folder is git-ignored and local.
