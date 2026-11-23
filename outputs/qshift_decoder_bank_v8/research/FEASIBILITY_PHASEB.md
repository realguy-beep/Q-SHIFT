# Phase B feasibility: unknown-state rejection for the lookahead overlay (development evidence only)

**Recommendation:**
- **GO** for one bounded *development* experiment (DB8-dev) of a lookahead with a stricter fit cap and
  pre-registered key-change accounting, on fresh seeds and with **new** out-of-bank states.
- **NO-GO** for any confirmatory run now, and for any attempt to recover gains at A onsets.

CF2 stays NOT CONFIRMED and was not used here.

**Inputs.**
- DB1 `TRAINING.json`.
- Development records of DB2 (v2), DB4 (v4) and DB6 (v6). Their U episodes give 7 out-of-bank episodes and 136 E
  blocks.
- DB6 dev error records.
- No CF2, CF1 or seal material. The deny-list is enforced in code, and `SourceTests` checks it.

**Method.**
- Detector-only rows were re-generated from each dev record's own recorded seeds: 2,000 rows per block, with no
  labels, evaluation rows or decoding.
- The DB6 causal chain was recomputed on them. All **648/648** DB6 dev blocks reproduce the stored lookahead
  statistic, alarm and single-block plausible set exactly.
- Detector marginal rates for each state come analytically from the stim detector error model, with no sampling.
- Run with `python research/phaseb.py`. The output is `research/PHASEB.json`, and the script is deterministic: two
  runs gave identical bytes.

## 1. Why E is read as A

The single-block fit is a binomial likelihood ratio over the 120 detectors:

g_s(k) = 2 Σ_d [ k_d ln(q̂_d / p_s,d) + (n − k_d) ln((1 − q̂_d) / (1 − p_s,d)) ],  q̂ = k / n, n = 2,000.

For rows from state X it is approximately noncentral χ² with 120 degrees of freedom, and

λ_X,s ≈ 2n · Σ_d KL(r_X,d ‖ p_s,d).

State s is *plausible* when g_s ≤ τ₁ = 202.4, the DB1 training quantile for L = 1.

**Analytic noncentralities for E rows (n = 2,000):**

| Template | λ | E[g] |
|---|---|---|
| A | **95.5** | 215.5 |
| OFF | 125.4 | 245.4 |
| D | 145.1 | 265.1 |
| C | 162.8 | 282.8 |
| B | 181.6 | 301.6 |

For a block's own state, λ ≈ 6–7, so E[g] ≈ 127. The extra 6–7 comes from error in the training templates.

E's signature sits just above A's plausibility cut. Under the χ² model, **P(g_A ≤ τ₁ | E) = 0.31**. In the dev
data, A is in the single-block plausible set for 40 of 136 E blocks (29%): 28 as the singleton {A} and 12 alongside
OFF. A is the best-fitting template for **119 of 136** E blocks.

So E is not misread because of a bug or a tuning choice. In detector marginals at 2,000 rows, E is a near-neighbour
of A. The plausibility cut was set to accept own-state blocks, with almost none rejected. It cannot separate the
two:
- to push P(E plausible as A) to 5% would take about **2,630 rows**;
- to push it to 1% would take about **3,040 rows**.

Either means more than one block of detector rows, so more latency.

**At E onsets** (7 in the dev data), the change alarm fired every time (7/7). The plausible set was the singleton
{A} at 2 of 7. In CF2, 3 of 5 E onsets triggered `bank:A`; that is the historical record, not used here.

## 2. Can detector-only unknown-state rejection work?

**Partly, with an absolute fit cap below τ₁.** The fit to the best template separates E from genuine states:

| | Best single-block fit: min, 10%, median, 90%, max |
|---|---|
| E blocks (136) | 137, 181, 215, 252, 298 |
| In-bank blocks, own state (632) | 87, 104, 126, 151, 206 |
| E blocks read as singleton {A} (28) | min 148, quartiles 188 / 193 / 198, max 202 |
| DB6 lookahead uses (51) | min 103, quartiles 125 / 138 / 151, max 188 |

| Cap c on best fit | E blocks rejected | In-bank own-fit blocks rejected | E singleton-{A} misreads kept | DB6 lookahead uses kept |
|---|---|---|---|---|
| 160 | 97.1% | 4.4% | 1 / 28 | 43 / 51 |
| 170 | 94.9% | 2.5% | 3 / 28 | 44 / 51 |
| 180 | 90.4% | 0.8% | 4 / 28 | 49 / 51 |
| 202.4 (τ₁, current) | 67.6% | 0.2% | 28 / 28 | 51 / 51 |

The χ² model agrees. At c = 170, P(E fits A ≤ c) = 2.7% and P(an own-state A block ≤ c) = 99.2%. At c = 180 the
figures are 7.1% and 99.8%.

**Limits:**
1. **Rejection power is specific to each unknown state.** It works for E because λ_E,A ≈ 95 sits well above the
   own-state λ ≈ 7. An unknown whose marginal signature is closer to a bank template (λ ≲ 30) cannot be rejected
   by any detector-marginal statistic at 2,000 rows. Only E has been studied. It is in the learner catalog, and its
   dev data were used to choose the caps above. Unknowns not yet seen are untested.
2. **The cap costs some genuine identifications.** See §4.
3. **Only marginal detector counts are used.** Pairwise detector co-occurrence statistics carry more information
   about the support, and might separate states more strongly. They are not explored here. They would need a new
   estimator and its own dev validation.

## 3. Why the gains sit at B onsets

The overlay's benefit at an onset into state s, against W0F's key b, is 1,000 · (risk[s][b] − risk[s][s]) errors
per block. W0F's minimax choice in an ambiguous segment is A, and A is costly only in B:

| True state | Excess over own key when decoding with A (errors / 1,000 rows) |
|---|---|
| A | 0.0 |
| **B** | **10.2** |
| C | 1.6 |
| OFF | 1.0 |
| D | 0.8 |

On DB6 dev onsets this predicts savings almost exactly:

| Onset into | Opportunities | Triggers | Predicted saving | Observed saving |
|---|---|---|---|---|
| A | 20 | 6 | 0 | 0 |
| B | 18 | 15 | 153 | 147 |
| C | 2 | 2 | 2.4 | 5 |
| D | 2 | 2 | 3.2 | 5 |
| OFF | 35 | 10 | 6.0 | 4 |

So the concentration at B is structural, not chance. The lookahead earns what W0F's insurance leaves on the table,
and W0F already insures A. **No controller can gain at A onsets** relative to W0F (headroom 0). Its total gain is
bounded by about 10 errors per B onset, plus at most about 1.6 per other onset.

## 4. A causal controller that keeps the gain with fewer inappropriate triggers

Candidate rules fire on a *subset* of LA's own firings. On those blocks both LA_W0F's and W0F's errors are
recorded, so the effect on DB6 dev is **exact**, not modelled.

| Rule | Uses | Key-changing | Wrong-state | Errors saved vs W0F (LA: 175) |
|---|---|---|---|---|
| R0: LA as frozen | 51 | 38 | 0 | 175 |
| R1: fire only if the key changes | 38 | 38 | 0 | 175 |
| R2(160): R1 + best fit ≤ 160 | 33 | 33 | 0 | 149 |
| R2(180): R1 + best fit ≤ 180 | 37 | 37 | 0 | 174 |
| R3(50): R1 + fit margin ≥ 50 | 37 | 37 | 0 | 175 |

**On the 136 dev E blocks**, taking W0F's base key as A (the minimax key, as in CF2), R0 would trigger on 2.
R1 and R2(160) would trigger on 0.

**Interpretation:**
- **R1 is accounting, not identification.** It removes exactly the no-op firings, including every kind CF2 saw, at
  zero error cost. On its own it does **not** improve the ability to recognise unknown states. It would make a G4
  defined on key-changing actions meaningful.
- **R2 is a real identification change.** With c ≈ 170–180 it removes 86–89% of E-as-A misreads, at a cost of
  about 1 genuine identification and 0–1 error per 175 saved (c = 180) in DB6 dev. The cap was chosen on dev data
  that include E, so it **must** be tested on new unknown states before anyone relies on it.

## 5. Is the method competitive with same-latency baselines? (DB6 dev, 27 episodes)

| Arm | Errors |
|---|---|
| ORACLE (has the true state) | 574 |
| LA2_W0F (ungated) | 783 |
| **LA_W0F** | **784** |
| LA_DB2 | 971 |
| W0F (real-time) | 959 |
| LA_BANK | 1,801 |
| LA_STATIC | 2,070 |

LA_W0F is the best of the gated same-latency arms in dev and ties the ungated LA2 (which lost on U in DB6). Two
stronger same-latency baselines have **not** been evaluated:
- a *current-block bank decision*: DB1's minimax over the single-block plausible set, used every block;
- the best fixed key per panel, given the same lookahead.

Neither can be scored from the stored records, because the keys they would choose were not always decoded. A
future protocol must include them as arms.

## 6. GO / NO-GO

**NO-GO:**
- A confirmatory rerun of LA_W0F (CF2's question is closed).
- Any redefinition of G4 applied to CF2.
- Any attempt to gain at A onsets (zero headroom against W0F).
- Any claim about unknown-state rejection beyond E.

**GO for one bounded development experiment, DB8-dev, under a new protocol to be approved before anything is
built:**
1. **Arms:** W0F, LA_W0F (frozen), LA-R1, LA-R2(c) with c fixed at **180** from this report (with 170 as a
   pre-declared secondary), plus the two same-latency baselines in §5.
2. **Panels:** the DB6 mix plus **at least two new out-of-bank states**, with supports not in the bank and not in
   the learner catalog, defined before seeds are drawn. Plus a dedicated E panel for continuity.
3. **Outcomes defined separately and in advance:** identification (wrong-state rate among all triggers),
   inappropriate action (key-changing triggers on wrong states), net errors and per-shot harm. Analysis by episode
   cluster, with fixed strata.
4. **Run protections:** the v8 `runkit` protections (exact freeze commit, full runtime identity including ldpc and
   SciPy, strict identity binding, exclusive reservation, fail-closed interruption).
5. **Size:** set by pre-registered power under clustered, heterogeneous scenarios, not by CF2.
6. **Bound:** development evidence only. A confirmatory study would need a further plan and approval.

What DB8-dev cannot answer: hardware, drift within a block, other code distances, or noise outside the declared
models.
