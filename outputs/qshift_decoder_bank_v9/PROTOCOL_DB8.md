# DB8-dev protocol: fit-capped lookahead with unknown-state panels (protocol only; not built, not run)

**Status: draft for approval. This is a development study, not a confirmatory one.** It needs two separate
approvals:
1. **"build and freeze":** code, tests, seeds, fidelity, freeze. Nothing is sampled for the study at this step.
2. **"run DB8":** one attempt from the frozen commit.

If DB8 advances, the most it allows is *writing* a confirmatory plan (CF3), which would need its own approvals.

**Evidence base.** Phase B (`outputs/qshift_decoder_bank_v8/research/FEASIBILITY_PHASEB.md`, commit `d7dc1b107`)
used development evidence only. CF2 stays NOT CONFIRMED and is not used for any design choice here. Its seeds are
used only for screening. These stay closed: RE1 H2, RE2 H3/H4, the V1.6 d=3 seal and `results/re1/records/R6_*.json`.
Nothing in v1–v8 is modified.

## 1. Questions

| Q | Question | Why it matters |
|---|---|---|
| Q1 | Does a stricter fit cap keep the lookahead's in-bank gain? | Phase B predicts it keeps 174 of 175 dev errors saved at c = 180 |
| Q2 | Does it stop wrong-state actions on unknown states the cap was not chosen on? | The cap was chosen on dev data that include E. Generalisation is the open question |
| Q3 | What happens on an unknown state that is detector-indistinguishable from a bank state? | Phase B's analysis says some unknowns cannot be rejected. Their harm has never been measured |
| Q4 | Is the method better than simpler same-latency baselines? | Two baselines could not be scored from stored records |

## 2. Rules under test (all causal; one block of decoding latency)

All rules use the same inputs as DB6's LA: block t's 2,000 detector-only rows, the preceding segment, and W0F's
base key. No labels, evaluation rows or truth. P₁ is DB1's single-block plausible set (τ₁ = 202.42), and g_s is
the single-block fit to state s's template.

| Arm | Fires on block t when | Key when it fires (otherwise W0F's key) |
|---|---|---|
| W0F | never (base, real-time) | — |
| LA_W0F | alarm and P₁ = {s} | bank:s (DB6/CF2 rule, unchanged) |
| **LA_R1** | alarm, P₁ = {s}, and bank:s ≠ W0F key | bank:s |
| **LA_R2** (primary) | LA_R1 and g_s ≤ **180** | bank:s |
| LA_R2_170 (secondary) | LA_R1 and g_s ≤ 170 | bank:s |
| **CB** (baseline) | every block: DB1 `bank_decide` on the single-block fit (L = 1, κ = 0.0005, its own previous key); if P₁ is empty, W0F's key | minimax key over P₁ |
| FIX_OFF … FIX_D (baselines) | never | the fixed bank key |

DB6's other arms (W0, BANK, DB2, DB2_PLAN, STATIC, AD3, ORACLE, A_nominal, LA_BANK, LA_DB2, LA_STATIC, LA2_W0F) are
kept, so the DB6 loop runs unchanged.

**All five bank keys are decoded on every block.** That allows exact scoring of the CB and FIX arms and of any
future key rule, and it gives the best fixed key per panel as a *descriptive* reference. It is chosen on outcomes,
so it is never a test. ORACLE decodes each block's true support, including the new unknown states.

The caps 180 and 170 are fixed here from Phase B. They are not tuned on DB8.

## 3. Panels (64 episodes, fresh `db8:` seeds)

**In-bank panels** use DB6's generators, unchanged. They are weighted toward B onsets, where the gain sits:

| AA | AB | BA | BB | S1 | S4 | N_C | N_OFF | RX | In-bank total |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 5 | **24** |

**Unknown-state panels** use DB1's U schedule: state A until onset o ~ U{8, …, 12}, then the unknown state X until
block 29. Background noise is p₀ throughout. Each X was selected *before any DB8 sample*, by the rules below. The
selection used analytic detector rates from the stim detector error model (no sampling) and the noncentrality λ
against DB1's templates at n = 2,000. Labels used before (A–D = W01, W05, W09, W14; E = W06; W13; X13) are
excluded.

| Panel | X | Support | Selection rule | Nearest template, λ | In learner catalog | Episodes |
|---|---|---|---|---|---|---|
| U_E | W06 (E) | 9, 25, 53 | continuity with DB1–CF2 | A, 95.5 | yes | 8 |
| **U_FAR** | X03 | 3, 25, 34 | the public burst whose λ_min is closest to E's, nearest template ≠ A | OFF, 96.7 | yes | 12 |
| **U_OUT** | V01 + qubit 3 | 1, 3, 12, 38 | the first public burst in label order, plus the lowest qubit that takes it outside the catalog, with λ_min in [60, 140] and nearest ≠ A | C, 90.5 | **no** (4-qubit) | 12 |
| **U_NEAR** | X09 | 7, 14, 42 | the public burst with the smallest λ_min | B, **28.2** | yes | 8 |

At build time, the selection script must reproduce this table exactly from the committed burst files. If it does
not, stop and report.

**What each panel can show:**
- **U_FAR and U_OUT** test whether the cap generalises beyond E, to a different nearest template (OFF, C) and to a
  support outside the learner catalog.
- **U_E** is continuity only. Its dev data helped choose the cap, so it is not a fresh test.
- **U_NEAR** is expected to be *undetectable*: E[g_B] ≈ 148, below both caps. It measures what any detector-only
  lookahead does when an unknown state looks like a bank state.

**Total: 24 in-bank + 40 unknown = 64 episodes.**

## 4. Outcomes, defined before sampling

The unit of analysis is the episode. "Wrong-state" means the fired key is not the block's true state's key. Every
firing on an unknown panel is wrong-state by definition.

| Outcome | Definition |
|---|---|
| **Wrong action** | a firing that changes the key (≠ W0F's key) on a wrong state |
| Wrong identification | any firing on a wrong state, whether or not the key changed (reported) |
| Wrong-action episode | an episode with ≥ 1 wrong action |
| Net error d | arm minus W0F errors over blocks 6–29, per episode |
| Shot harm | evaluation shots the arm got wrong and W0F got right (from the error bits) |
| Retention | (W0F − LA_R2) / (W0F − LA_W0F), pooled errors over the in-bank panels |

## 5. Advance criteria (all must pass; every value is reported whatever the outcome)

| # | Criterion | Rule |
|---|---|---|
| A1 | in-bank gain kept | retention ≥ **0.90**, **and** the exact sign test of LA_R2 against W0F on in-bank non-tied episodes has p ≤ 0.05 |
| A2 | wrong actions stopped on fresh unknowns | on U_FAR ∪ U_OUT (24 episodes): LA_R2's wrong-action episodes ≤ **2**, **and** ≤ LA_R1's |
| A3 | harm caps | every episode: LA_R2 − W0F ≤ +24; every block ≤ +24; each unknown panel (including U_NEAR): pooled LA_R2 − W0F ≤ 0 and every episode ≤ +12 |
| A4 | beats simpler same-latency baselines | pooled errors over all 64 episodes: LA_R2 ≤ CB **and** LA_R2 ≤ LA_DB2 |

**ADVANCE = A1 ∧ A2 ∧ A3 ∧ A4.** It permits writing a CF3 plan, with LA_R2 at c = 180.

The secondary arm LA_R2_170 is reported only. It can be proposed for CF3 only if it passes A1–A4 *and* LA_R2 fails
**only** A2.

If CB beats LA_R2 in pooled errors, the recommendation switches to CB, which is simpler. That choice is still
subject to its own A1–A3 evaluation.

**Reported but not tested:**
- per-panel tables, shot harms, wrong identifications;
- the onset table (as in CF2) with key-changing and non-changing firings shown separately;
- the best fixed key per panel;
- U_E results, and the U_NEAR identification rate;
- LA_W0F's G4-style rate for continuity.

Episode-cluster bootstrap intervals are descriptive only. Descriptive contrasts carry no p values (`runkit.describe`).

**Inference limits, stated in advance:**
- A1's sign test is a statement about how often LA_R2 wins under this panel mix, not about a mean (CF2 addendum §1).
- A2 and A3 are counts against fixed caps, not population coverage claims.
- DB8 is development evidence, and it cannot confirm anything.

## 6. Size and power (assumptions from Phase B and DB6 dev; no CF2 input)

**A1.**
- DB6 dev had about 0.67 non-tied episodes per in-bank episode. Over 24 episodes that gives about 16 non-ties.
- In dev, R2(180) kept 37 of 38 key-changing firings, so it would give about 15–16 wins and 0 losses.
- That makes p ≈ 2⁻¹⁵ ≈ 3e−5. Even 4 losses out of 16 still gives p = 0.038.
- Retention under the dev numbers is about 0.99.

**A2.**
- Per-episode wrong-action probability at the cap, from the χ² model: 3–7% at c = 180 (§2 of Phase B), assuming
  U_FAR/U_OUT's λ ≈ 90–97 behaves like E's.
- Over 24 episodes, the expected number of wrong-action episodes is 0.7–1.7. P(≤ 2) is 0.97 at 3% and 0.77 at 7%.
- If the cap does *not* generalise (LA's rate, about 30–40% per episode), the expected count is about 8, and A2
  fails with probability above 0.99 (P(≤ 2) = 0.003 at 35%).
- So A2 separates the two cases.

**A3, U_NEAR.** There is no prior evidence on U_NEAR. It is included as a safety gate because a fast advance must
not hide harm on undetectable unknowns.

**Compute.**
- DB6/CF2 ran at about 275–330 s of wall time per episode with 8 workers.
- Decoding all five bank keys adds about 30–40%. The other new parts (four rule arms and CB) are bookkeeping and
  one more key choice.
- Estimate: about 420 s per episode, so **64 episodes take about 7.5 h** (±45 min).
- A smaller option is 48 episodes (in-bank 18, U_FAR 10, U_OUT 10, U_NEAR 6, U_E 4), about 5.6 h. With it, A2 has
  20 episodes, and the A1 sign test has about 12 non-ties.

## 7. Build and freeze (approval 1)

1. **New package** `outputs/qshift_decoder_bank_v9/`, on branch `claude/qshift-decoder-bank-v9-db8` from
   `claude/qshift-cf2-remediation-v8`.
   - `db8_config.py` imports `db6_config`. It adds the arms, the unknown states (from §3's rules) and the episodes.
   - `db8_run.py` = DB6's `episode_job` plus overlay lines only (source-identity tested, as DB6 was against DB4).
     The added lines are the LA_R1/LA_R2 rules, CB, the FIX arms, all-key decoding and models for the new supports.
   - Runner protections come from v8 `runkit`:
     - the exact approved freeze commit (`check_revision`);
     - full runtime identity, including scipy and ldpc;
     - `Reservation`, `Journal` and fail-closed `run_jobs`;
     - `load_strict` with exact episode, archive and seed identity, and 1,000 evaluation rows.
2. **Tests:**
   - loop identity with DB6;
   - the rule truth table (R1/R2/CB edge cases);
   - the sampler-free synthetic truth invariance (v8 pattern), extended to the new arms;
   - §3's unknown-state selection reproduces exactly;
   - the new supports have ORACLE models;
   - criteria A1–A4 on hand-built records;
   - `load_strict` mutation tests;
   - no seal; LF only;
   - seeds screened against every inventory through `CF2_SEEDS.json`.
3. **Fidelity gate**, before any DB8 seed is used. Re-run DB6 dev BB_e0 and U_e0 with their DB6 seeds. Every DB6
   field and every DB6-arm bit must match the DB6 records exactly. BB_e0 must show at least one LA_R2 firing. If not,
   stop and report.
4. **Freeze:** a portable manifest (LF-normalised committed blobs, traced inputs, burst files, seeds, this protocol,
   fidelity), the runtime identity, the selection table and the decision constants. Check it on a fresh LF checkout.
   It is committed locally and pushed only on your say-so.

## 8. Run rules (approval 2)

- **A single attempt** via `runkit`: HEAD must be exactly the freeze commit (parent = code commit, only the freeze
  file changed), the runtime identity must match, and the run directory takes an exclusive reservation.
- **No records are opened until all 64 are done.** Progress is read from the journal and file counts only.
- **Failures:** a pre-write infrastructure error gets one bounded retry. Anything else stops the run, keeps the
  partial outputs, and makes DB8 void. There is no fix-and-rerun without a new protocol.
- **The analysis** is run twice and must be byte-identical. Results go to `results/dev/` and `DB8_RESULTS.md`.
  They are committed, and pushed only on your say-so. Nothing is merged.

## 9. What DB8 can and cannot support

- **ADVANCE:** "In development simulation, a fit-capped lookahead kept the in-bank gain and avoided wrong actions
  on two fresh unknown states, one outside the learner catalog, without harm above the caps." That justifies
  *planning* CF3, nothing more.
- **NO-ADVANCE:** reported as a negative result. The Phase B mechanism analysis stands. W0F remains the confirmed
  real-time result.
- **Either way, DB8 cannot support:**
  - confirmation;
  - real-time claims;
  - claims about unknowns other than these four;
  - hardware, drift within a block, or other code distances.
