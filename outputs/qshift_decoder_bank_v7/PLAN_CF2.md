# CF2 plan: confirmatory run of LA_W0F (plan only; not built, not run)

**Status: plan for review.** It needs two separate approvals:
1. **"build and freeze":** write the code, tests and seeds, run the fidelity gate, and commit the freeze. No CF2
   episode is sampled at this step.
2. **"run CF2":** one sampling attempt against the frozen commit.

These stay closed: RE1 H2, RE2 H3/H4, the V1.6 d=3 seal and `results/re1/records/R6_*.json`. CF1 is used only to
screen seeds; its results are never read for design. Nothing in `qshift_decoder_bank_v1`–`v6` is modified.

This plan applies every item in CF1_ERRATUM.md's "Before any further frozen run" list (§4 below says how).

## 1. What is being confirmed, and under which contract

**The rule.** LA_W0F, exactly as run in DB6-dev (frozen `99aa4a84f`, results `e7094d3b8`):
- the base key is W0F's (`db2_core.gate(mode="worst", kappa=0)` plus `db4_core.fallback_key`, static key A);
- if AD3's change test fires on block t's own detection counts and DB1's single-block plausible set is a
  singleton {s}, block t is decoded with `bank:s` (`db6_core.lookahead`, `la_key`);
- otherwise W0F's key is used.

Nothing is re-fitted. No parameter is chosen from CF2 data.

**The contract: one block of decoding latency.** Block t's evaluation rows are decoded after block t's 2,000
detection-only rows have been seen. No labels, evaluation rows or truth are used. Every claim from CF2 is made
under this contract only. W0F (CF1) stays the confirmed **real-time** result. CF2 doesn't compare the two as
equals. It tests whether one block of lookahead, added to W0F, reduces errors **without measurable harm**.

**Comparators.** All are decoded on the same rows in the same loop. This is DB6's arm list, unchanged:
- **W0F:** the same rule without lookahead; this is the primary comparison;
- **LA_STATIC, LA_BANK, LA_DB2:** fair-information baselines, with the same overlay, latency and data;
- **reported only:** W0, BANK, DB2, DB2_PLAN, STATIC, AD3, ORACLE, A_nominal, and LA2_W0F (ungated, dropped after
  DB6 but kept so the job code is unchanged).

## 2. What the development evidence supports (DB6-dev, 27 episodes)

Per-episode paired differences, LA_W0F minus the comparator, in errors per episode:

| vs | mean | sd | better / worse / tied |
|---|---|---|---|
| W0F | −6.5 | 6.1 | 18 / 0 / 9 |
| LA_STATIC, changing panels (AB BA BB S1 S4 N_C U) | −67.7 | 37 | 17 / 0 / 0 |
| LA_BANK, AA AB BA RX | −82.2 | 70 | 12 / 1 / 0 |
| LA_DB2, all panels | −6.9 | 26 | 3 / 4 / 20 |

**LA_DB2 is not tested.** LA_W0F wins big on BA (−31, −127, −43) and loses a little on BB (+3 to +6). The sign
test has nothing to work with there, so no claim is made against DB2; that comparison is reported only. BANK
reliably beats LA_W0F on BB, S4 and N_OFF (+2 to +13), so those panels are left out of the LA_BANK test, as in
CF1's H2.

## 3. Pre-registered hypotheses and safety gates

The unit is the episode. d is the error count over scored blocks 6–29, LA_W0F minus the comparator (24 errors =
0.001 LER).

**Test.** A one-sided **exact sign test** on the nonzero d values (ties dropped). It assumes no symmetry, so a
rare skewed harm cannot hide behind it (erratum §1). There are no non-inferiority tests based on sign flips.

| # | Claim | Comparator | Panels pooled | Pass rule |
|---|---|---|---|---|
| C1 (primary) | lookahead reduces W0F's errors | W0F | all 10 | Holm-rejected **and** mean d ≤ −3 |
| C2 | LA_W0F beats the pre-selected fixed key with the same information | LA_STATIC | AB BA BB S1 S4 N_C U | Holm-rejected |
| C3 | LA_W0F beats DB1's bank with the same information on burst-order panels | LA_BANK | AA AB BA RX | Holm-rejected |

**Multiplicity.** Holm across C1–C3 at a family-wise α = 0.05.

**Safety gates for LA_W0F against W0F.** All must pass. They are reported whatever the outcome.

| Gate | Rule |
|---|---|
| G1 | no episode with d > +24 |
| G2 | no scored block where LA_W0F has more than 24 errors above W0F |
| G3 | at most 2 of 48 episodes with d > 0; the Clopper–Pearson upper bound is reported (0 → 6.1%, 2 → 12.6%) |
| G4 | wrong-state uses: one-sided 95% CP upper bound ≤ 5%. A use is wrong when the chosen key ≠ the block's true state; any use on U counts as wrong. With the expected ~93 uses, 0 wrong uses pass; 1 wrong use passes only with ≥ 95 uses. |
| G5 | RX: pooled d ≤ 0 and every RX episode d ≤ +12 |
| G6 | U (out-of-bank): pooled d ≤ 0 and every U episode d ≤ +12 |

**CONFIRMED = C1 ∧ G1 ∧ G2 ∧ G3 ∧ G4 ∧ G5 ∧ G6.** C2 and C3 are separate claims, each valid only when CONFIRMED
also holds.

**Reported for every hypothesis:**
- mean d, median d, counts better/worse/tied;
- the sign-test p value and the Holm decision;
- a percentile bootstrap 95% interval for mean d (20,000 resamples, seed recorded in the freeze), as a
  description, not a test.

**Reported, not tested (no claim from any of these):**
- per-panel tables; LA_W0F vs LA_DB2, W0, BANK, DB2, STATIC, AD3 and ORACLE;
- the share of the W0F−ORACLE gap closed (DB6-dev: 45%);
- LA2_W0F (expected to lose on U, as in DB6);
- the **onset table**. An opportunity is a scored block whose true state differs from block t−1's. Truth is used
  in scoring only. For each destination state the table gives the number of opportunities, LA triggers, correct
  triggers, and errors saved against W0F. It also gives LA triggers on blocks that are not opportunities.

**What CF2 cannot show:**
- that LA beats W0F under a real-time contract;
- open-set generalization: U's class E is outside the bank but inside the learner catalog (erratum §3);
- anything about a *best* fixed decoder: LA_STATIC uses key A, pre-selected by training risk.

## 4. Panels, size and power

**Panels.** These are DB6's generators, unchanged (`db6_config.episode_params`, `block_state`, `changes`; RX
through C2). Only the counts change. They are weighted toward the panels where LA acts (RX, AB, BA, BB), and U
and the null panels are kept for G6 and harm.

| Panel | AA | AB | BA | BB | S1 | S4 | U | N_C | N_OFF | RX | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Episodes | 4 | 6 | 6 | 5 | 3 | 4 | 5 | 3 | 4 | 8 | **48** |

**Power, if the DB6-dev effects hold:**
- **C1:** about 32 of 48 episodes nonzero, all negative in dev, so p ≈ 2⁻³² ≈ 2e−10. Even 26 of 32 negative
  still gives p < 0.001. Expected mean d ≈ −7.
- **C2:** 32 episodes; all 17 were negative in dev.
- **C3:** 24 episodes; in dev, 12 of 13 were negative.
- **G4:** expected LA uses ≈ 93 (dev rate per panel). With 0 wrong uses the bound is 3.2%; with 1 wrong use it is 5.0%, a fail at 93 uses.

The main risk to C1 is harm on panels where dev had none, which G1–G3 would catch. The main risk to G4 is too
few uses; if the expected count is not reached, G4 fails rather than passing on a weak bound.

**Compute.** DB6-dev ran at 273 s of wall time per episode with 8 workers, so 48 episodes take about
3.6 h ±20 min.

## 5. Build and freeze (approval 1)

1. **New package** `outputs/qshift_decoder_bank_v7/` on branch `claude/qshift-decoder-bank-v7`, which this plan
   opens from `e7094d3b8`:
   - `cf2_config.py` imports `db6_config` and changes only `EPISODES` and the seed namespace (`cf2:`);
   - `cf2_run.py` imports DB6's job and does not copy it. It adds only a `cf2` setup mode and reuses DB6's
     portable freeze, typed retries and strict archive checks;
   - `cf2_analyze.py` holds C1–C3, G1–G6 and the onset table.
2. **Tests:**
   - the job is DB6's (source identity);
   - **mocked truth invariance** (erratum item 4): perturbing truth metadata, current-block labels and
     evaluation labels leaves every LA and base key unchanged;
   - the sign test, CP bound and Holm order on hand-checked cases;
   - `cf2_analyze.py` on the 27 DB6-dev records reproduces DB6's E1 values exactly;
   - the strict-archive mutations (key set, width, padding, counts) are rejected;
   - no seal names; LF only;
   - seeds screened against every inventory through `DB6_SEEDS.json` (and CF1_SEEDS).
3. **Fidelity gate**, before any CF2 seed is used. Re-run DB6-dev episodes **BB_e0** (the largest LA gain) and
   **U_e0** (the out-of-bank panel, where LA2 harms) with their DB6 seeds. Every per-block key, error and
   lookahead field, for every arm, must match the DB6 records bit for bit. If not, stop and report.
4. **`CF2_FREEZE.json`**, the portable manifest (erratum item 1):
   - LF-normalized SHA-256 of every tracked `.py` in v1–v7;
   - every traced input, lazy imports and data files included;
   - DB1 `TRAINING.json`, the burst assets, `CF2_SEEDS.json`, `PLAN_CF2.md` and `FIDELITY.json`;
   - the bootstrap seed, the Python and numpy versions, and the git head.

   It is verified against the working copy, against the committed blobs, and on a fresh LF worktree checkout. It
   is committed locally, and the branch is pushed only on your say-so.

## 6. Run rules (approval 2)

- **Single attempt,** from the freeze commit with a clean tree. The run checks every freeze hash and the fidelity
  result before it samples.
- **No looking during the run.** Only the count of finished record files is read; no record is opened until all
  48 are done.
- **Typed retries** (erratum item 3). An infrastructure failure (OSError, MemoryError, EOFError, ConnectionError,
  timeout) gets one retry with the same seeds, logged as a deviation. Any other exception stops the run, and CF2
  is void; there is no fix-and-rerun without a new plan and your approval.
- **The analysis** is run twice and must be byte-identical. Every hypothesis and gate is reported whatever the
  outcome, and a failure is written up as a failure.
- **Results** go to `results/cf2/` and `CF2_RESULTS.md`, and are committed. Nothing is merged.

## 7. What may be claimed afterwards

- **If CONFIRMED:** "pre-registered confirmation **in simulation** (d=5 surface code, these panels, one-block
  decoding latency), on fresh seeds, by the same team: adding the lookahead overlay to W0F reduced logical errors
  with no episode or block harm above the caps." C2 and C3 add their fair-information statements if they pass.
- **If C1 or any gate fails:** LA is reported as not confirmed, and the DB6 result stays development evidence.
- **Either way:**
  - not independent confirmation;
  - not hardware evidence;
  - no real-time claim;
  - no claim against DB2 or against a best fixed decoder.

## 8. Timeline

| Step | Time |
|---|---|
| Build, tests, fidelity (2 episodes, about 45 min) and freeze | about 2–3 h |
| CF2 run | about 3.6 h (48 episodes) |
| Analysis and write-up | about 1 h |

That is within one day of approval 1, which leaves time for the competition pack.
