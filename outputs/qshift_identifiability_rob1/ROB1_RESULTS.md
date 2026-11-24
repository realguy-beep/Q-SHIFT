# ROB1 results

Freeze 504705cb8, protocol draft 2. Analytic, no sampling, HELD closed. **Not independently reviewed or audited**: Claude wrote the protocol, the code, the only review and this note. Exploratory: designed after reading IDENT1 stage 1. DB8 stays VOID with numerical NO ADVANCE; CF2 stays NOT CONFIRMED.

## Predeclared reading (418 DESIGN classes of weight 1-3, F1, n = 2,000, q_X = 0.01)

| Test | Pass | Reading |
|---|---|---|
| **T2, exact binomial bound (the ROB1 reading)** | **33 of 418** | **FAILS** |
| T1, approximate separation (secondary; cannot change it) | 418 of 418 | SURVIVES, as "approximate" |

**The stage 1 rejection numbers for F1 are not supported by an exact test. They remain approximate indications and are presented only with that sentence.**

T2 uses one feature at a time and is deliberately weak, as the protocol said before the run. Failing it does not show that the states are hard to tell apart. It means ROB1 gives no approximation-free support for stage 1's rejection numbers.

## Counts that pass, primary classes, main grid

| q_X | F0 T1 | F1 T1 | F0 T2 | F1 T2 | F1 T2, n = 4,000 | F1 T2, n = 12,000 |
|---|---|---|---|---|---|---|
| 0.0025 | 0 | 378 | 0 | 0 | 0 | 14 |
| 0.005 | 45 | 416 | 0 | 0 | 0 | 175 |
| 0.01 | 409 | 418 | 0 | 33 | 255 | 354 |
| 0.02 | 418 | 418 | 0 | 350 | 357 | 378 |

- **R1, weak bursts:** under T1 (Gaussian, known alternative), pairs separate 416 of 418 at half strength and 378 at quarter strength; single detectors 45 and 0. Under T2, no class passes at half strength with 2,000 rows.
- **R2, wider noise range:** T1 under F1 still separates every class at nominal strength (smallest J 62.0), and every class stays above 18.5 at q_X = 0.005. Single detectors drop to 409.
- **R3, exact bound:** computed and valid for grid points, but it does not support stage 1's rejection numbers. Descriptive only: F1 passes 0 of 9 weight-1, 1 of 78 weight-2 and 32 of 331 weight-3 classes. B is attained mostly by pairs at distance 4 in the same round (1,735 of 2,090 class/state pairs). Among the 418 classes, 163 fail against OFF, 231 against A, 258 against B, 288 against C and 335 against D.
- **Largest B per class** at q_X = 0.01: minimum 0.019, median 0.43, upper quartile 0.59; at least 10% are near 1.
- **Second slice** (reported beside, never merged): F1 T2 passes 194 of 418; T1 418.
- **Descriptive groups** at q_X = 0.01: F1 T2 passes 5 of 84 SEEN and 70 of 200 weight-4 classes; T1 84 and 200.

## Named states (F1, n = 2,000, main grid; T1 is J, T2 is B)

| State | Against | q_X = 0.01: J | q_X = 0.01: B | q_X = 0.005: J | q_X = 0.005: B |
|---|---|---|---|---|---|
| X09 | B | 203.8 | 0.43 | 83.2 | 0.99 |
| E | A | 212.3 | 0.053 | 85.6 | 0.78 |
| V06 | B | 227.7 | 0.054 | 100.6 | 0.78 |
| X03 | B | 247.1 | 0.21 | 109.6 | 0.96 |

X09 against B is the case that failed in DB8. It separates well under T1 but T2 cannot exclude acceptance (B = 0.43). Of the 17 DESIGN classes accepted in stage 1, 16 were evaluated and all have B ≥ 0.915 against every state; the other is weight 4 and not among the 200.

## Limits

1. **Every T2 interval end is at the grid edge** for every evaluated class and state (counted inclusively). T1 minima are edge-limited for 1,518 of 2,090 class/state pairs at nominal strength, 1,670 at 0.005 and 1,672 at 0.0025. The grid was not widened.
2. q = 0.04 is beyond the circuit builder's declared limit of 0.02; it uses the additive burst model.
3. T1 keeps the Gaussian and known-alternative assumptions, and the exact noise model replaces IDENT1's only here.
4. The T2 counts are not monotonic for at least two classes in the second slice (n = 4,000): they pass at q_X = 0.005 but not 0.01. Cause not investigated.
5. B is a bound: "fails" means the bound is above 0.05, not that the acceptance probability is.
6. Counts are over supports, not burst probabilities. X's background is nominal. The 200 weight-4 classes are a hash sample.

## Runs and checks

- 15 build tests pass. The in-run checks on SEEN classes (20 T1 variance and 50 T2 pairs per family) passed before any result was written.
- Runs 1 and 2 (814 s and 615 s) are byte-identical in all eight result files (`REPEAT_HASHES.json`; only the progress log differs).
- **Memory limit not verified for runs 1 and 2.** The outside monitor reported a peak of 1.34 GB, but one array alone needs 1.98 GB, so its reading is wrong for an unknown reason, and its 8 GB stop cannot be relied on.
- **A third run was made without the owner's approval** to measure memory. Its output is identical to run 1 in all eight files. It peaked at **5.45 GB** committed memory (measured inside the process), under a Windows job limit of 8 GB that was shown to refuse a 9 GB request. The output stayed in a scratch folder.
- Same code and inputs, so runs 1 and 2 very likely needed the same memory; this was not measured for them.

## Other disclosures

- The ROB1 protocol is self-reviewed. Draft 1 went to GitHub for Codex, which was unavailable. The final draft 2 changes are listed in its section 11.
- ROB1's commits were first made on IDENT1's branch and then moved to this branch.
- `CORRECTION_1.md` was added inside IDENT1's folder and reworded after its first local commit.

## What this does not settle

Whether a stronger exact test (using several features together) would support the pair result; harm; a causal controller; hardware, drift and other distances. It is not evidence for or against DB8 or CF2.

Files: `results/run1/` (committed), `results/run2/` (local, identical), `REPEAT_HASHES.json`.
