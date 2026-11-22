# DB4 development results: W0 + static fallback (W0F)

Development evidence only. No confirmatory sampling, no sealed data (RE1 H2, RE2 H3/H4, V1.6 d=3 seal) opened.
Plan: `PLAN_DB4.md` (commit `dac543067`). Code and seeds: `089a94741`. Fidelity: `6beda2511` (`FIDELITY.json`, all_pass).

## Run

- 21 episodes (AA 4; BB, AB, BA, S1, S4, N_OFF, N_C 2 each; U 3), fresh DB4 seeds screened against every prior
  inventory (`DB4_SEEDS.json`). Single attempt, clean tree, head `6beda2511`, 8 workers.
- Started 2026-11-22T05:59:42Z, finished 08:14:22Z (8,080 s). `results/dev/RUN_STATUS.json`.
- `analyze` run twice into separate directories: `ANALYSIS.json` and `TIMELINE.json` byte-identical.
  SHA-256: ANALYSIS `54791f51…843803d`, TIMELINE `952e205f…37493a`.
- Scored blocks 6–29, 1,000 evaluation rows each: 24 errors per episode = 0.001 LER.

## Criteria (pre-registered in PLAN_DB4.md)

| # | Criterion | Value | Pass |
|---|---|---|---|
| G1 | every panel W0F − W0 ≤ +2 (mean/episode) | max +0.25 (AA); all others 0 | yes |
| G2 | every panel W0F ≤ STATIC + 12 | max 0.0 (AA) | yes |
| G3 | U: W0F − AD3 ≤ +24 | 0.0 | yes |
| G4 | BB, AB, BA, S1, S4, N_C each ≤ −12 vs STATIC; pooled ≤ −24 | −33.5 … −130.5; pooled −71.6 | yes |
| G5 | null panels ≤ 1 switch/episode | N_OFF [1, 1], N_C [0, 0] | yes |
| G6 | AA: W0F − BANK ≤ −24, W0F ≤ BANK every episode | −129.5; 4/4 | yes |

**ADVANCE = true** under the plan's rule. This authorises proposing a confirmatory step; it does not run one.

## Errors by panel (totals)

| Panel | ep | W0F | W0 | DB2_PLAN | DB2 | BANK | AD3 | STATIC | ORACLE |
|---|---|---|---|---|---|---|---|---|---|
| AA | 4 | 126 | 125 | 125 | 125 | 644 | 1322 | 126 | 93 |
| AB | 2 | 70 | 70 | 70 | 70 | 150 | 435 | 137 | 39 |
| BA | 2 | 88 | 88 | 88 | 162 | 156 | 457 | 163 | 61 |
| BB | 2 | 85 | 85 | 85 | 62 | 73 | 183 | 227 | 36 |
| N_C | 2 | 45 | 45 | 89 | 45 | 45 | 44 | 224 | 45 |
| N_OFF | 2 | 43 | 43 | 63 | 43 | 34 | 34 | 63 | 34 |
| S1 | 2 | 69 | 69 | 69 | 69 | 69 | 206 | 330 | 55 |
| S4 | 2 | 55 | 55 | 55 | 55 | 38 | 70 | 190 | 31 |
| U | 3 | 122 | 122 | 122 | 122 | 122 | 122 | 421 | 73 |
| **Total** | 21 | **703** | **702** | 766 | 753 | 1331 | 2873 | 1881 | 467 |

## What the run shows — and what it does not

1. **The fallback did no harm, but it also bought nothing on fresh data.** It fired on 6 of 504 blocks
   (1.2%, matching the ~1% replay rate). In 4 of those W0 already held `bank:A`, so the keys were identical.
   In the other 2 (AA_e3 block 25, BA_e0 block 27) W0 took an unflagged class-less AD key; W0F cost +1 error
   at AA_e3 b25 and tied at BA_e0 b27. Net W0F − W0 = **+1 error over 21 episodes**.
2. **The DB3 failure mode did not recur.** DB3's AA_e1 lost 97 errors by holding a stale key on the unknown
   path (replay 132 → 35). No fresh AA episode reproduced that sequence (AA had 7 empty-P blocks; holding the
   previous key there cost W0 nothing). So the run confirms no-harm, not benefit. The only evidence that the fallback *helps* remains the
   seen-data replay on DB3 AA_e1 — which is development data and was used to design the rule.
3. **G6 and G4 measure the W0 gate, not the fallback.** W0F's −129.5/episode vs BANK on AA and its wins over
   STATIC come from W0's gate (W0 alone scores the same). They are fresh, independent repeats of DB3's
   finding that the worst-case gate beats DB1's bank on burst-order panels.
4. **U (unseen class E): 52 empty-P blocks, 0 triggers.** AD's estimates were accepted and named a class, so
   W0F followed AD exactly (W0F = AD3 = 122). The fallback correctly stayed out of the way.
5. **Where W0/W0F is not best.** BANK beats it on N_OFF (34 vs 43), S4 (38 vs 55) and BB (73 vs 85); DB2
   (hybrid) beats it on BB (62 vs 85) while losing badly on BA (162 vs 88). The gap to ORACLE is 236 errors
   in total (703 vs 467). These are small panels (2 episodes); none is a criterion failure.

## Deviations from the plan

- None in procedure. The trigger count (6) is below the replay's 10 because the fresh episodes differ; the plan
  set no minimum trigger count.

## Limitations

- 2–4 episodes per panel; differences of a few errors per episode are within episode-to-episode spread.
- Simulated d=5 surface-code noise only; no hardware integration is claimed.
- The fallback's benefit is not independently confirmed (point 2). A confirmatory test of the benefit would need
  episodes in which the unknown path is reached repeatedly, which this panel design rarely produces.
- Nothing here is a claim of decoder superiority beyond these development panels.

## Files

`results/dev/ANALYSIS.json`, `TIMELINE.json`, `RUN_STATUS.json`, `records/*.json` (21). NumPy archives stay in
`work/dev/archives` (ignored, local).
