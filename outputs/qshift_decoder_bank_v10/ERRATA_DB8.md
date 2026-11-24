# DB8 errata and disclosures

**DB8's outcome is unchanged: NO ADVANCE for both arms.** CF2 remains NOT CONFIRMED. The v9 files stay as they are; this file corrects how to read them. It responds to Codex's independent audit (`outputs/qshift_decoder_bank_v9/CODEX_INDEPENDENT_AUDIT.md`, commit 426afe894).

Everything here is Claude's own follow-up work. It is not an independent audit.

## C1. Deviation from protocol section 8 (not ranked in the audit)

`PROTOCOL_DB8.md:183-189` requires a single attempt. Apart from one retry of an infrastructure error before any output, a failure "makes DB8 void. There is no fix-and-rerun without a new protocol."

- Attempt 1 failed after writing output. It was fixed and rerun as attempt 2 with no new protocol and no amendment.
- Attempt 2 failed on a code error. Attempt 3 followed amendment A3, which overrides section 3 for U_FAR only and does not mention section 8.
- `RUN_ATTEMPT1.md`, `RUN_ATTEMPT2.md` and the freezes disclose the attempts. No v9 document other than the protocol mentions the void rule or calls the reruns a deviation.
- The documents record the owner's approval of A3. They do not record a decision to waive section 8.

**Proposed reading, pending the owner's decision and Codex's review:** "NO ADVANCE, from a development run that deviated from protocol section 8." Read strictly, section 8 makes DB8 void. Neither reading permits an advance or a CF3 plan.

Two smaller departures: section 8 names the results file `DB8_RESULTS.md`, but it is `DEV_RESULTS.md`; and the analyser was changed after the run (`ANALYSIS_FIX.md`).

## F2. Near-unknown wording

- Protocol line 77 calls U_NEAR "undetectable", and line 78 says it measures "what any detector-only lookahead does". Neither is supported. DB8 tested one marginal-fit rule.
- `DEV_RESULTS.md:75` says UN is "too close to B to separate in one block". Read it as: this rule, with these caps, did not separate them.
- Codex's model-based calculation finds different D117/D119 rates for X09 and B. It was made after the study and is conditional on the model. It shows no working classifier, and Claude has not recomputed it.

## F1 and F3. Attempt 2 and amendment A3

- The failing component was correlated matching, which DB8's bank-key scoring never uses. ORACLE decodes with BP+OSD, and BP+OSD builds for X03 (tested here without sampling). `RUN_ATTEMPT2.md:13` and `AMENDMENT_A3.md:7` ("The ORACLE arm needs that decoder") are wrong on this point.
- So A3's filter "`re1.decoders` must build" excluded X03 because of a decoder the study did not need. A3 changed the question from X03 (nearest OFF) to V06 (nearest B). DB8 says nothing about X03.
- "Before any U_FAR data existed" should read **"before any U_FAR output was persisted"**. The job draws detection, label and evaluation rows before building the failing decoder (`db8_run.py:108-117,185-192`), so X03 rows were generated in the worker and lost with it. The same correction applies to `select_unknowns.py`'s docstring.
- All attempts used the same seeds. Earlier attempts add no independent evidence.

## F6. CB's memory

"Its own previous key" has two readings. Frozen DB8 keeps the last *bank* choice through a W0F fallback. Under the "last emitted key" reading, 16 keys change and CB's pooled errors go from 10,081 to 10,069. A4 passes either way. The frozen CB stands; the other number is a sensitivity check.

## F8. Limits on inference

- A1's sign test concerns non-tied episode signs under this fixed panel mix, not a mean or a population.
- A2 counts 24 episodes from only two fixed unknown supports. LA_R2's firings are a subset of LA_R1's, so "≤ LA_R1" adds nothing on its own.
- A3 and A4 are fixed gates on this sample. There is no bound on rare harm and no multiplicity adjustment.
- Retention is relative to a 194-error gain on 24 in-bank episodes.

## F10. Definitions and the cap's effect

- Protocol lines 84-85 count every firing on an unknown *panel* as wrong. The analyser uses the *block's* true state. They differ for one firing: LA_W0F before a U_OUT onset, correctly matching A. LA_W0F's wrong identifications are 20 by block truth and 21 by panel wording. No gate changes.
- `DEV_RESULTS.md:32` ("in all 8 episodes") and line 75 ("removed none") hold for LA_R2 (cap 180). LA_R2_170 blocked one of the eight (episode 2, fit 177.8) and still added 327 errors.

## F11. Missing summaries

- The onset table, split into key-changing and no-op firings, is in `DB8_ADDENDUM.json`, computed from the committed records.
- The protocol mentions descriptive episode-cluster bootstrap intervals without defining them, and DB8 reported none. None is computed here: choosing a method now would be choosing it after seeing the results. A future protocol should fix the resampling unit, number of resamples, seed and interval type first.

## Corrections to `QSHIFT_HANDOFF.md`

- "Every U_NEAR episode fired once at onset" holds for LA_R2 only. LA_R2_170 fired in seven.
- "The X03 decoder can't be built ... and ORACLE needs it": see F1 above.
- "Codex's independent DB8 audit has not started": it was committed two minutes after the handoff.
