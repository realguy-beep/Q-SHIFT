# DB1: a causal decoder bank with separate change, identity and risk checks (development)

**Status:** development study. The training outputs are fixed in `TRAINING.json`, and this plan, the code and the criteria are committed before the validation run. **Nothing here is confirmatory.** Any frozen confirmatory sampling needs the owner's separate authorisation.

**No historical evidence is changed.** DB1 lives in its own directory. It imports AD2/AD3 code read-only from `outputs/qshift_adaptive_robust_v1` and writes nothing there. No seal is read.

## Why

The review on `codex/qshift-response-gap-research-v1` (`cdaf6a618`) was verified claim by claim (`VERIFICATION.md`). On our own data:
- AD3's S2 gain came almost entirely from recognising a returning burst (523 of 528 errors);
- first appearances are limited by the estimator, not by detection;
- AD2/AD3 had no strong static comparator;
- one false flag decoded with the nominal model can cost about 96 errors.

DB1 tests whether separating the decision into three checks, over a small prebuilt decoder bank with a robust static fallback, improves on AD3 where the review says it should, without harm where AD3 is already good.

## Method (`db_core.py`, `db_run.py`)

| Check | Rule |
|---|---|
| **1. Change detection** | AD3's frozen two-sample G (`ad3.g_stat`, τ = 163.13): block u against its segment; above τ, the segment restarts at u |
| **2. State identification** | The segment's pooled detector counts (at most the last 6 blocks) are tested against each bank state's fixed per-detector rate template with a goodness-of-fit G. Plausible set P = {s : G_fit_s ≤ τ_fit[L]}, L = segment blocks |
| **3. Logical risk** | Act with the bank key that minimises the **worst development LER over P** (risk table R[state][key]). Keep the current key unless another lowers that worst case by more than κ = 0.0005 |
| **Unknown state (P empty)** | Use AD's own accepted 6-block estimate (open-set learning). If it is flagged, hold the current key, never the nominal fallback |
| **Robust static fallback** | The single bank key with the lowest equal-weight mean training LER; it is also the initial key |

- **The bank:** 5 BP+OSD decoders (OFF = burst-free at p = 0.003, and the four public bursts A–D at p = 0.003), the same engine and model construction as AD3's oracle.
- **Advance information:** the bank is a **closed bank of characterised states**. It uses advance knowledge that these five states exist and what their detector templates look like, which AD and AD3 do not have. This is disclosed, and the U panel tests a state outside the bank.

## Training (`db_train.py`; training seeds only)

| Output | Data | Rule |
|---|---|---|
| Templates | 20 blocks × 2,000 detector rows per state | rate = (k + ½) / (n + 1) |
| τ_fit[L], L = 1..6 | 4 static streams × 30 blocks per state; all windows of L consecutive blocks | max over states of the 99.5% quantile of own-state G_fit |
| Risk table | 5,000 labelled rows per state, decoded by all 5 keys on the same rows | LER |
| Static key | the risk table | argmin of the equal-weight mean LER |

**Training results** (`TRAINING.json`, 418 s; written before the plan was committed and before any validation sample):

- **τ_fit:** 202, 201, 198, 207, 213 and 227 for L = 1–6. It rises with L because the 40,000-row templates have their own sampling noise.
- **Identification:**
  - **Single block (L = 1):** the true state was in the plausible set in 99–100% of windows, and the best-fitting template was correct in 99–100%.
  - **The ambiguity is OFF versus A:** A was plausible in 61% of OFF windows and OFF in 61% of A windows, with a mean set size of 1.8.
  - **From L = 2,** the set is essentially a singleton.
- **Risk table** (errors in 5,000 rows; rows = true state, columns = key):

  | true \ key | OFF | A | B | C | D |
  |---|---|---|---|---|---|
  | OFF | 1 | 6 | 1 | 1 | 1 |
  | A | 247 | **6** | 247 | 247 | 242 |
  | B | 57 | 58 | **7** | 56 | 57 |
  | C | 11 | 13 | 11 | **5** | 12 |
  | D | 13 | 9 | 13 | 13 | **5** |

- **Static key: A** (mean LER 0.37%, against 1.1–1.3% for the others).
  - **Why A:** an undecoded burst A is the costliest mistake, and A's key costs little on OFF data.
  - **What it implies:** STATIC is the oracle on C0, and is close to it on every block of R, since R only toggles A. **D2 is therefore a demanding test.** This is noted before the validation run; the criterion is not changed.

## Validation run (`db_run.py dev`; fresh DB1 seeds, disjoint from training and all prior inventories)

Per block: 2,000 unlabelled + 250 labelled + 1,000 evaluation rows; 30 blocks; blocks 6–29 scored; q = 0.01; p = 0.003.

| Panel | Schedule (generator and scorer only; never shown to a policy) | Episodes |
|---|---|---|
| C0 | A static | 2 |
| N | one static state drawn per episode from OFF, A–D | 2 |
| S1 | A → B at 15 (a known relocation) | 3 |
| S4 | B → C at 10, C → D at 20 | 3 |
| **R (primary)** | OFF; A on at block 6 or 7; three dwells drawn from {4, 5}: first ON, first OFF, recurrent ON, final OFF | 4 |
| U | A → E at a random block in 8–12; E = W06 (20 detectors), by a fixed rule, outside the bank and the training | 2 |

**Arms, all on the same evaluation rows:**

| Arm | Role |
|---|---|
| **BANK** | candidate |
| BANK_ID | ablation: best-fitting plausible state, with no risk gate |
| AD3 | AD3's frozen rule, re-implemented through `ad3.py`'s own functions and checked bit-for-bit against the committed AD3 rehearsal (`FIDELITY.json`) |
| AD | AD2's method |
| STATIC | the training-selected static key |
| ORACLE | BP+OSD with the true model |
| A_nominal | burst-free matching |

## Pre-declared development criteria (fixed before the validation run)

Promotion to a confirmatory proposal (`ADVANCE`) needs all of D1–D6:

| # | Criterion |
|---|---|
| D1 | **R:** BANK − AD3 LER ≤ −0.001, and BANK ≤ AD3 in every R episode |
| D2 | **R:** BANK − STATIC LER ≤ −0.001 |
| D3 | **Null (C0 + N):** BANK − STATIC ≤ +0.0005, and zero BANK key switches |
| D4 | **Recurrent ON:** the timely fraction (correct key by c + 1) for BANK minus AD3 ≥ 0.20 |
| D5 | **U:** BANK − AD3 ≤ +0.001 (no material harm on a state outside the bank) |
| D6 | **S1, S4:** BANK − AD3 ≤ 0 |

**Always reported:**
- per-arm errors and LER;
- the paired episode differences and their bootstrap upper bounds (6 or fewer episodes per panel, so these are descriptive);
- event delays by type (first ON, recurrent ON, OFF, relocation, unknown onset);
- key switches on static panels;
- wrong-burst actions;
- the BANK − BANK_ID ablation.

## Deviations from the review's proposal

1. **The identification statistic:** a template goodness-of-fit with a plausible set, instead of discriminants on parity/cofire features with Page accumulation. It is simpler and auditable, and it uses the same detector marginals as AD3.
2. **Static selection:** an equal-weight mean over the five bank states from the training risk table, instead of a pooled argmin over its design panels.
3. **Scale:** 16 validation episodes and a single training stage, instead of 60–72 held-out roots and a separate tuning split. The thresholds are set by fixed rules on training data, and nothing is tuned on validation episodes.
4. **No background grid:** the bank holds p = 0.003 states only. A background shift leads to the unknown path (AD's estimate), and S3 is not run.
5. **Timing at block cadence only:** no sub-block prefix control, and no wall-clock alarm-to-ready measurement beyond per-episode timings.
6. **The bank is closed and pre-characterised** (disclosed above). A cold-start bank is AD3 itself, which serves as the comparator.

## Claim boundary

Development evidence at d=5, with public weight-3 bursts at p = 0.003 and simulation only. With 2–4 episodes per panel, DB1 can show a large effect or a clear failure mode; it cannot confirm a small one. AD2's and AD3's results and verdicts are unchanged by anything here.
