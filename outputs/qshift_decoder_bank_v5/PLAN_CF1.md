# CF1 plan: confirmatory run of W0F (plan only — not built, not run)

Status: **plan for review.** Two separate approvals are needed:
1. **"build and freeze"**: write the code, the tests and the seeds, run the fidelity gate, and commit the freeze.
   No confirmatory episodes are sampled at this step.
2. **"run CF1"**: one sampling attempt against the frozen commit.

Sealed material (RE1 H2, RE2 H3/H4, the V1.6 d=3 seal, `results/re1/records/R6_*.json`) stays closed. Nothing in
`qshift_decoder_bank_v1`–`v4` is modified.

## 1. What is being confirmed

**Rule under test.** W0F, which is DB4's advanced candidate, frozen exactly as at `780d1c9f0`:
- `db2_core.gate(mode="worst", kappa=0)`;
- on the unknown path, `db4_core.fallback_key` with static key `A`;
- DB1's plausible set and estimator, using DB1's `TRAINING.json` risk.

Nothing is re-fitted. No parameter is chosen from CF1 data.

**Comparators**, all decoded on the same rows in the same loop:
- STATIC (`bank:A` always);
- BANK (DB1);
- AD3;
- W0 (the same gate without the fallback);
- DB2 and DB2_PLAN, reported only;
- ORACLE and A_nominal, reported only.

**What the development evidence supports.** These are paired W0 − comparator differences, in errors per
episode, over the 41 stored DB3 and DB4 episodes. Here sd is the spread between episodes.

| Panel | vs STATIC | vs BANK | vs AD3 |
|---|---|---|---|
| AA | +15.8 (sd 39) * | −157.7 (71) | −293.5 (28) |
| AB | −32.6 (9) | −68.2 (48) | −175.4 (15) |
| BA | −39.8 (5) | −70.2 (55) | −186.7 (28) |
| BB | −70.2 (13) | **+6.8 (1.8)** | −47.3 (9) |
| S1 | −130.5 (5) | 0.0 | −68.5 (45) |
| S4 | −67.5 (13) | **+8.5 (2.1)** | −7.5 (0.7) |
| N_C | −91.0 (4) | 0.0 | +0.2 |
| N_OFF | −9.6 (2) | **+3.8 (1.8)** | +4.0 (2.1) |
| U | −99.7 (9) | 0.0 | 0.0 |

\* The AA figure comes from DB3's AA_e1, the stale-key failure that W0F's fallback was built to remove. On AA,
STATIC's key is the true key, so no adaptive rule can beat it there.

These numbers set the hypotheses below. **BANK reliably beats W0 on BB, S4 and N_OFF**, so the plan does not
claim W0F beats BANK everywhere.

## 2. Pre-registered hypotheses

The unit of analysis is the episode. d is the per-episode error count over scored blocks 6–29, W0F minus the
comparator. 24 errors equals 0.001 LER.

| # | Type | Panels pooled | Claim if it passes |
|---|---|---|---|
| H1 | superiority vs STATIC | AB, BA, BB, S1, S4, N_C, U | adapting beats the best fixed key when the noise changes |
| H2 | superiority vs BANK | AA, AB, BA (burst order) | the worst-case gate beats DB1's bank on burst-order panels |
| H3 | non-inferiority vs AD3, margin +24 (0.001 LER) | U (an unseen class) | the bank does not degrade AD on a class it does not contain |
| H4 | non-inferiority vs W0, margin +2 | all panels | the static fallback does no measurable harm |

**Test.** Each hypothesis uses a one-sided paired sign-flip permutation test on the episode d values:
- superiority: H0 is mean d ≥ 0;
- non-inferiority: the test is applied to d − margin, and H0 is mean d ≥ margin.

The flip distribution uses 200,000 random flips from a fixed seed recorded in the freeze. It is exact when
n ≤ 16.

**Multiplicity.** Holm–Bonferroni across H1–H4 at a family-wise α = 0.05.

**Reporting.** Each hypothesis is reported with:
- the mean d;
- a 95% one-sided bound, from the percentile bootstrap over episodes with 20,000 resamples and a fixed seed;
- the p value and the Holm decision.

**Reported but not tested** (no claim is made from any of these):
- per-panel results;
- W0F vs BANK on BB, S4 and N_OFF, which are expected to be losses of a few errors per episode;
- switches on the null panels;
- the fallback trigger rate;
- W0F vs DB2, DB2_PLAN and ORACLE.

**What CF1 cannot show.** It cannot show that the fallback *helps*. The stale-key situation it guards against
appeared once in 41 development episodes, so H4 tests no harm only. Any claim of benefit stays at "seen-data
replay, development only".

## 3. Panels and size

**Panels.** These are the DB4 generators, unchanged (`db4_config.episode_params`, `block_state` and
`changes`), with new episode counts.

| Panel | AA | AB | BA | BB | S1 | S4 | U | N_C | N_OFF | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| Episodes | 6 | 6 | 6 | 6 | 4 | 4 | 6 | 5 | 5 | **48** |

**Power**, from the development spread and assuming effects at the development size:
- H2 pools 18 episodes. The expected mean d is about −98, with SE about 16, so the test is roughly 6 standard
  errors from zero.
- H1 pools 37 episodes, with an expected mean d below −60 and a small spread.
- H3 and H4 have development differences of 0 and +0.05 against margins of +24 and +2.

So every hypothesis has very high power if the development effects are real. Their main risk is that the
development effects do not hold up.

**Compute.** DB4 processed about 385 s of wall time per episode with 8 workers. 48 episodes is about 5.1 h,
±30 min. A smaller option is 32 episodes (4/4/4/4/3/3/4/3/3), about 3.4 h. That keeps H1 and H2 well powered
but leaves only 4 episodes in U for H3.

## 4. Freeze procedure (approval 1)

1. **New package** `outputs/qshift_decoder_bank_v5/` on branch `claude/qshift-decoder-bank-v5`:
   - `cf1_config.py` imports `db4_config` and changes only `EPISODES` and the seed namespace (`cf1:`);
   - `cf1_run.py` imports DB4's `episode_job` and does not copy it;
   - `cf1_analyze.py` holds the H1–H4 tests above.
2. **Tests:**
   - the episode loop is identical to DB4's;
   - the permutation test is exact on small hand-checked cases;
   - Holm ordering is correct;
   - the non-inferiority shift is applied correctly;
   - `cf1_analyze.py` run on DB4's 21 dev records reproduces the DB4 per-panel numbers;
   - no seal names appear in the code;
   - files use LF line endings only;
   - the seeds are screened against every prior inventory through `DB4_SEEDS.json`.
3. **Fidelity gate**, run before any CF1 seed is used. Re-run DB4 dev episodes AA_e3 and BA_e0 with their DB4
   seeds; these are the two where W0F and W0 took different keys. Every per-block key and error for every arm
   must match the DB4 records exactly. If they don't, stop and report.
4. **`FREEZE.json`** records:
   - SHA-256 of every `.py` file in `v1`–`v5`;
   - SHA-256 of `DB1/TRAINING.json`, `CF1_SEEDS.json`, `PLAN_CF1.md` and `FIDELITY.json`;
   - the permutation and bootstrap seeds;
   - the git head.

   It is committed, and the branch is pushed only if you say so.

## 5. Run rules (approval 2)

- **Single attempt.** It runs only from the freeze commit with a clean tree, and `cf1_run.py` checks every hash
  in `FREEZE.json` before it samples anything.
- **No looking during the run.** Only the count of finished jobs is read; no record is opened until all 48 are
  done.
- **A crashed job** (an infrastructure failure, not a result) is re-run once with the same seeds. The run is
  deterministic, so this cannot change any result, and the re-run is logged as a deviation.
- **A code bug found after sampling starts** stops the run. The bug is reported, CF1 is declared void, and no
  fix-and-rerun happens without a new plan and your approval.
- **The analysis** is run twice and must be byte-identical. All four hypotheses are reported whatever the
  outcome, and a failed hypothesis is written up as a failure.
- **Results** are written to `results/cf1/` and `CF1_RESULTS.md`, then committed. Nothing is merged.

## 6. What may be claimed afterwards

- **If a hypothesis passes:** "pre-registered confirmation **in simulation** (d=5 surface code, these noise
  panels), on fresh seeds, by the same team." It is not independent confirmation and not hardware evidence.
- **If one fails:** that claim is withdrawn and the development result is reported as not confirmed.
- **Either way:** no claim of general decoder superiority, and no claim of a fallback benefit (§2).

## 7. Timeline (competition in ~7 days)

| Step | Duration |
|---|---|
| Build, tests and fidelity gate | about 2–3 h |
| CF1 run | about 5 h (48 episodes) |
| Analysis and write-up | about 1 h |

That fits in one day after approval 1, which leaves time for the competition pack.
