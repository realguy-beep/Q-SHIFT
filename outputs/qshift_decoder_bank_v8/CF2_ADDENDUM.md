# CF2 addendum: statistical assumptions, G4 clustering and corrected interpretation

**The CF2 decision stands, permanently: NOT CONFIRMED.** This addendum responds to the independent audit
(`outputs/qshift_decoder_bank_v7/CODEX_INDEPENDENT_AUDIT.md`, commit `63306649d`, PASS WITH CONCERNS). It changes no
CF2 file. The plan, code, seeds, freeze, both fidelity attempts, records, analysis and `CF2_RESULTS.md` at
`6bd35b752` stay as they are. Where this addendum and `CF2_RESULTS.md` disagree, the addendum wins on
interpretation. It never changes the decision.

No new CF2 analysis was run beyond reproducing the audit's numbers. The audit's script
(`audit_cf2_saved_evidence.py`) gave every count, p value, interval and gate quoted below, unchanged.

## 1. What the sign test establishes (F1)

C1–C3 use an exact one-sided sign test on the nonzero episode differences. It assumes no **symmetric magnitudes**,
which was CF1's error. It still rests on assumptions, and it answers a narrower question than "the mean improved".

- **Estimand.** The test concerns *how often* LA_W0F beats its comparator in an episode (the median sign), among
  episodes where they differ. It does **not** test the mean difference, and it does not bound rare large harm.
- **Null model.** The reference distribution is Binomial(n, ½) over independent episodes. CF2's episodes come from
  fixed panel quotas (for example RX 8, AA 4) with different distributions. Pooled across those strata, the
  binomial reference is exact only under a per-episode sign null in which each episode independently favours
  either arm with probability ½. It is not exact for a mixture-average null over a population of panels.
- **The tail is invisible.** Suppose d = −6 with probability 0.99 and d = +594 otherwise. The mean is 0, yet with
  probability 0.99⁴⁸ ≈ 0.617 all 48 episodes show −6, and C1, its mean rule and G1–G3 would all pass. The
  bootstrap interval in `CF2_RESULTS.md` resamples observed episodes, so it cannot see such a tail either. It also
  varies the fixed panel quotas. It stays **descriptive only**.

**Corrected reading of C1:** "In 48 fresh episodes under the frozen panel mix, LA_W0F made fewer errors than W0F in
30 episodes and more in none (exact sign test on the 30 non-ties, p = 9.3e−10, Holm-adjusted 1.9e−9)." That is a
statement about *frequency of improvement* under that mix. It is not a population mean margin, and not a safety
bound on rare large harm.

## 2. What the harm and wrong-state bounds establish (F2)

G3 and G4 use one-sided exact Clopper–Pearson bounds, which assume independent, identically distributed Bernoulli
trials. CF2's data are not like that:

- **Clustering.** The 96 lookahead uses fall in 39 of the 48 episodes, with up to 7 in one episode. Uses within an
  episode share a schedule, its parameters and the segment history.
- **Heterogeneity.** The wrong-state rate differs sharply by stratum. In-bank panels had **0 wrong of 93 uses**. The
  out-of-bank panel U had **3 wrong of 3 uses**, because the plan counts every U use as wrong.
- **G3 counts episodes**, under a fixed panel mix.

So neither bound has demonstrated coverage for a population of heterogeneous, clustered episodes. **G4's 7.8787% is
still the correctly computed frozen score, and G4 fails.** Nothing here makes the rule stricter or looser after the
fact. The point is that a future study needs episode- or cluster-level intervals and fixed strata, chosen before
sampling.

## 3. The three wrong-state uses (F9, with the audit's figures)

| Episode | Block | True state | Lookahead key | W0F key | Errors (LA / W0F) |
|---|---|---|---|---|---|
| U_e1 | 8 | E | bank:A | bank:A | 7 / 7 |
| U_e2 | 10 | E | bank:A | bank:A | 6 / 6 |
| U_e3 | 11 | E | bank:A | bank:A | 5 / 5 |

All three read E as A and kept W0F's existing key, so they changed no decoding. Overall, 3 of 96 uses were wrong,
and 3 of 3 U uses were wrong. Only 70 of the 96 uses changed the key, and 0 of those 70 were wrong. That figure is
descriptive. **It cannot replace G4's pre-registered denominator**, which counts identifications, not key changes.
The error-bit archives show 294 W0F-only errors and 3 LA_W0F-only errors, a net gain of 291 errors. The net block
counts in `CF2_RESULTS.md` are not individual-shot harms: LA_W0F was worse on 3 individual shots.

## 4. Corrected G4 threshold (F7)

`PLAN_CF2.md` §3 and `CF2_RESULTS.md` say that one wrong use passes "only with ≥ 95 uses". **The correct figure is
93.** The bound for 1 wrong in 93 uses is 4.99940%, which passes; 1 in 92 gives 5.0526%. The smallest numbers of uses
at which 0, 1, 2 and 3 wrong uses pass are **59, 93, 124 and 153**. CF2's observed 3 of 96 fails under either
statement (`runkit.cp_min_n`, test `BoundTests.test_g4_boundary`).

## 5. Unadjusted descriptive p values (F8)

`cf2_analyze.py` puts a `sign_p` field on eight descriptive contrasts under `reported.vs`: LA_DB2, W0, BANK, DB2,
STATIC, AD3, ORACLE and LA2_W0F. They are **not** part of the Holm family of three (C1–C3), are not adjusted, and
support no claim. Read them as counts only. The v8 analyzer helper (`runkit.describe`) gives no p value for
descriptive contrasts.

## 6. Scope and wording corrections (F9)

- **Information used.** The lookahead uses block t's **detector-only** counts, plus the preceding segment. The
  combined policy LA_W0F also uses W0F's base decision, which depends on **past labelled calibration rows**.
  "Detector-only" describes the overlay, not the whole controller.
- **C2's comparator** is LA_STATIC, the overlay on training-selected key A. It can switch keys. So C2 does not
  establish superiority over the strongest fixed or delayed decoder. C2's panels include the constant-noise panel
  N_C. In any case C2 is not claimed.
- **LA_DB2** had fewer errors than LA_W0F on AB and BB in CF2. No claim is made against DB2.
- **ORACLE** receives the block's true state. It is a reference with extra information, not a decoder limit.
- **LA2_W0F's "31 wins"** in `CF2_RESULTS.md` means episodes where LA2_W0F had fewer errors than **LA_W0F**, not
  fewer than W0F.
- **"Outside the bank" is not "outside the learner catalog."** E has no bank key but is in AD's class catalog. CF2
  gives no evidence about open-set generalization.
- **CF1's "real-time" claim** for W0F stands with the qualifications in `CF1_ERRATUM.md` (H3/H4 are conditional
  decisions, and the fallback's benefit is unproven). CF2 added one new descriptive figure here: W0F against W0 gave
  1 W0-only error and 12 W0F-only errors, a net +11. That is further evidence against claiming a net benefit from
  the fallback.

## 7. Process findings (F3–F6) and the truth test

These findings concern safeguards. None of them changed a CF2 number. The recorded run status shows the freeze head,
48 successful jobs and zero retries, and the audit confirmed every saved identity.

- **F3:** the run guard accepted any HEAD the caller supplied, and the freeze omitted scipy and ldpc.
- **F4:** the archive loader did not bind episode, archive and seed identity, or the exact row count.
- **F5:** run reservation was check-then-write, and the retry had no timeout.
- **F6:** the truth-invariance test labelled "mocked" called the real sampler.

The v7 commit `0e2a00147` said "no sampling". That was wrong about the test: its fixture drew about 80,000
synthetic-namespace rows, though no CF2 study seeds. All four are reproduced against the original code in
`REPRODUCTION.json` and fixed for future runs in `runkit.py` (see `FINDINGS_CLOSURE.md`).

## 8. What may be said, now

- **Not:** "LA_W0F is confirmed", "LA_W0F is safe", or "LA_W0F lowers mean error by 6 per episode".
- **Allowed**, as a conditional statement under the frozen procedure: "In a pre-registered simulation (d=5 surface
  code, the CF2 panel mix, one-block decoding latency), LA_W0F beat W0F in 30 of 48 fresh episodes and lost in none
  (exact sign test on non-ties). The pre-registered state-identification gate failed: 3 of 96 lookahead
  identifications were wrong, all on the out-of-bank panel, though none changed the decoder used. CF2 is NOT
  CONFIRMED."
