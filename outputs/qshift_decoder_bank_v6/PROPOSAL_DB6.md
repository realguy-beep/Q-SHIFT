# DB6 proposal: block-lookahead state identification (proposal only, not built, not run)

**Status: proposal for owner review.** Nothing here has been built, sampled or tuned. The investigation used
development records only:

| Study | Episodes |
|---|---|
| DB2 | 23 |
| DB3 | 18 |
| DB4 | 21 |
| **Total** | **62** |

All numbers come from `feasibility.py`, which writes `FEASIBILITY.json` deterministically. The replay logic is
in `devdata.py` and `la_replay.py`.

**Not used:**
- CF1 records, which are confirmatory evidence;
- any sealed data;
- any frozen file, which was not modified.

**Disclosure.** The author has seen CF1's aggregate tables, which are reported in `CF1_RESULTS.md` and
`CF1_ERRATUM.md`. No mechanism, threshold or panel choice below was taken from CF1. Any new evaluation must use
fresh seeds.

## 1. Failure mechanisms supported by the development records

**M1. W0F pays a premium for "A insurance" on blocks whose state is already identified.** This is why BANK
beats W0F on BB, S4 and N_OFF.
- **The cost.** W0F's worst-case gate keeps key A while the identified state is OFF or D. Key A costs
  R[OFF][A] = 0.0012 against 0.0002 for the state key, which is about one extra error per 1,000-row block. On
  identified blocks this cost **197 errors in OFF and 36 in D**, over all 62 episodes.
- **It explains the BANK losses.** On identified blocks, W0F − BANK is BB +34, S4 +36 and N_OFF +19. The losses
  sit almost entirely there.
- **What the premium buys.** Against BANK, W0F wins −1,824 errors at onset blocks and −1,277 during detection
  lag. Most of that comes on A-burst panels (AA, AB, BA, R, RX).

**M2. The insurance is justified because A is hard to see but catastrophic to miss.**
- **Hard to see.** The same-block change alarm catches OFF→A only 26 of 41 times and A→OFF 27 of 39 times.
  It catches B transitions 30 of 31 times each way.
- **Ambiguous when fitted alone.** A single-block fit of an A block gives a multi-state set in 18 of 35 cases.
- **Catastrophic to miss.** The wrong key in state A costs about 0.049 LER.
- **Naive lookahead fails for this reason.** A lookahead using the pooled-segment fit loses +940 errors on
  missed A onsets. Those blocks are pooled with the earlier OFF blocks, so the fit says OFF.

**M3. The BB-vs-BA trade-off cannot be identified causally.**
- **Why.** BB and BA have the same distribution up to the second burst's onset. Any rule that anticipates "B
  again" from the past will gain on BB and lose on BA.
- **DB2 is that rule.** In DB3 and DB4, DB2 gains −80 errors against W0F on BB and loses +440 on BA.
- **Consequence.** No destination-learning rule that only looks at past blocks can win both panels.

**M4. Most of the remaining gap is onset blocks.** W0F's dev gap to ORACLE is 760 errors in total:

| Block type | Errors | Share |
|---|---|---|
| Onset | 431 | 57% |
| Identified (the M1 premium) | 233 | 31% |
| Detection lag | 96 | 13% |

Before an onset block is decoded, only that block's own detector data can reveal the onset.

## 2. Candidate algorithms and their causal inputs

| Id | Mechanism | Inputs (detector-only unless stated) | Dev evidence | Verdict |
|---|---|---|---|---|
| **LA** | **Alarm-gated lookahead overlay** on W0F | the same-block change test, then DB1's plausible set refitted on block t's own 2,000 detection rows (L = 1, DB1's τ_fit[1]); no labels, no eval rows | exact replay: **2,273 → 1,925 (−348, −15%)**; 33 episodes better, **0 worse**, max episode harm 0; used on 99 blocks, 2 wrong-state (harmless) | **GO (development)** |
| LA2 | lookahead on *every* block (single-block fit, no alarm needed), to remove the M1 premium | same as LA | not replayable: single-block fits exist in the records only on alarm blocks (0 wrong singletons in 98 bank-state cases, but that sample is selected) | exploratory arm only |
| H | learned destinations / hazard tuning (the DB2 family) | past blocks | M3: wins BB, loses BA | NO-GO |
| K | switching penalty / hysteresis κ | past blocks | the model has no intrinsic switching cost; DB2_PLAN (κ > 0) was worse on nulls (DB4 N_C 89 vs 45) | NO-GO |
| Q | arm selection from labelled calibration rows | 250 labels per block (past) | the premium difference is about 0.25 errors per 250 rows, so it cannot be seen within an episode | NO-GO |
| U | better unknown-state policy | past or same-block AD estimate | U headroom is 92 errors over 5 dev episodes (36 onset, 56 lag); LA gives 0 (E is not in the bank) | DEFER |

**LA changes the operating contract.** To decode block t's evaluation shots, it waits for block t's own
detection-only shots. That is **one block of decoding latency**: suitable for batch or delayed decoding, not
for real-time feed-forward. It must be reported as a separate operating mode, not as a drop-in W0F upgrade.

**The information, not W0F's gate, drives the gain.** The same overlay improves every base arm in the dev
replay. W0F remains the best base once the overlay is applied to all of them.

| Base arm | Without LA | With LA | Change |
|---|---|---|---|
| W0F | 2,273 | **1,925** | −348 |
| BANK | 5,140 | 4,155 | −985 |
| DB2 | 2,735 | 2,308 | −427 |
| STATIC | 5,292 | 4,888 | −404 |

So any LA claim must be made against LA-baselines, which get the same latency and the same information.

## 3. Feasibility and identifiability risks

1. **Selection and forking.** LA was found by examining these same dev records. Two lookahead variants were
   looked at (pooled and alarm-gated), and the records also shaped W0F. The −348 is hypothesis-generating, and
   fresh development seeds must reproduce it.
2. **Missed-A risk.** LA keeps W0F's key whenever the alarm doesn't fire, so missed A onsets cost the same as
   now. That is why the harm in the replay was 0. LA2 would remove this protection and is the risky arm.
3. **The premium stays.** LA does not fix M1 on steady blocks. BANK-family arms may still beat LA-W0F on BB, S4
   and N_OFF.
4. **Stale contract tests.** The DB4 causality test forbids using block t's data at block t. LA needs a new,
   explicit contract and a truth-invariance test, as the independent review asked.
5. **The state E (unknown) path is unchanged**, and its gap remains.

## 4. Pre-registered development experiment (DB6-dev)

**Arms.** All arms run in one loop and decode the same rows.

| Group | Arms |
|---|---|
| Existing arms (unchanged) | W0F, W0, BANK, DB2, STATIC, AD3, ORACLE, A_nominal |
| New arms | **LA-W0F** (candidate), **LA-BANK**, **LA-DB2**, **LA-STATIC** (fair-information baselines), **LA2-W0F** (exploratory, descriptive only) |

**Panels and seeds.** Fresh development seeds, screened against every inventory including `CF1_SEEDS.json`.
The panels use DB4's generators plus DB2's RX generator as an A-onset challenge.

| Panel | AA | AB | BA | BB | S1 | S4 | U | N_C | N_OFF | RX | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Episodes | 3 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 3 | 4 | **27** |

**Paired comparisons.** d = arm errors − comparator errors per episode over scored blocks 6–29. Every test is
valid without symmetry, as the erratum requires.

| # | Comparison | Criterion |
|---|---|---|
| E1 | LA-W0F vs W0F | pooled exact sign test on episodes with d ≠ 0, one-sided p ≤ 0.05, **and** mean d ≤ −3 errors per episode |
| E2 | LA-W0F vs LA-BANK, and LA-W0F vs LA-DB2 | pooled mean d ≤ 0; per-panel results reported, BB, S4 and N_OFF expected positive |
| S1 | Safety | no episode with LA-W0F − W0F > +24 (0.001 LER) |
| S2 | Safety | no block where LA's key costs more than +24 errors over W0F's key |
| S3 | Safety | wrong-state lookahead uses ≤ 5% of LA uses, with the Clopper–Pearson 95% bound reported |
| S4 | Safety | RX challenge: pooled LA-W0F − W0F ≤ 0 and no RX episode > +12 |
| R | Report only | the harm rate P(d > 0) with its Clopper–Pearson bound; all LA2-W0F results |

**Required tests before the run:**
- the existing arms reproduce DB4 dev AA_e3 and BA_e0 bit for bit (fidelity);
- the LA input is exactly block t's detection counts, and never labels, eval rows or truth. This is a mocked
  truth-invariance test: perturbing truth, labels and evaluation rows must leave the LA keys unchanged;
- the overlay leaves the base arm's state unchanged;
- strict archive width and key checks;
- typed retries: an infrastructure failure gets a retry, and a code error stops the run;
- the freeze hashes LF-normalized committed blobs plus all lazy imports and data files, and is tested on a
  fresh checkout.

**Decision.**
- **ADVANCE** to a separately approved confirmatory plan only if E1, S1, S2, S3 and S4 all hold.
- E2 decides which LA base would be confirmed. If LA-BANK or LA-DB2 beats LA-W0F pooled, the confirmatory plan
  names that arm instead, and says so.
- Otherwise the result is NO-GO for LA. There is no re-tuning on these data, and any second attempt needs a new
  plan.

## 5. Compute estimate and stopping criteria

**Compute.**

| Step | Time |
|---|---|
| Build, tests and freeze | about 3 h |
| Fidelity | about 45 min (2 episodes) |
| DB6-dev | about 2.9 h ±20 min (27 episodes, DB4's measured throughput of about 385 s per episode with 8 workers) |

LA adds only a single-block fit, plus at most one extra decoder key per block, which is usually already
decoded. In total that is about 7 h, within one day.

**Stopping rules:**
- stop before sampling if fidelity or any pre-run test fails;
- one attempt only;
- no records are inspected before all 27 have finished;
- a code error voids the run.

## 6. Independent baselines and safety criteria needed later (for a confirmatory study)

**Fair-information baselines.** LA-BANK, LA-DB2 and LA-STATIC get the same latency and the same data.

**A static comparator chosen independently.** The current STATIC uses key A, the lowest training risk among
the bank keys. A confirmatory study should also add the best fixed key for each panel as a descriptive upper
bound on fixed decoders.

**A same-hysteresis gate ablation.** This isolates the W0 gate's contribution.

**Inference that stays valid under rare, skewed harms:**
- an exact sign test for superiority;
- a pre-specified per-episode and per-block harm cap;
- Clopper–Pearson harm rates;
- no symmetric-null non-inferiority tests.

**A dedicated A-onset challenge panel**, with trigger and opportunity counts defined before scoring.

## 7. Recommendation

**GO for a bounded DB6-dev experiment, LA only**, under an explicit one-block-latency contract. **NO-GO** for
H, K and Q, on the M3 identifiability argument and the absent mechanism. **DEFER** U.

For the competition, W0F remains the confirmed, real-time-contract result. LA is development evidence only
until it is confirmed on fresh seeds.
