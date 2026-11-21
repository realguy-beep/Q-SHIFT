# Verification of the response-gap review (`codex/qshift-response-gap-research-v1`, `cdaf6a618`)

Each claim was checked against the committed AD2/AD3 code, records (`outputs/qshift_adaptive_robust_v1/results/`), the AD3 screen and the local decoded-bit archives. No sampling was needed for any check.

## Verified

| # | Claim (report) | Check | Result |
|---|---|---|---|
| 1 | S2 alarms: 14/24 on the change index, 17/24 by the next, 7 unmatched in their own segment (ROOT_CAUSE) | Recounted from `results/ad3/records/S2_e*.json`, matching each alarm only inside its own segment | **Confirmed.** AD3_RESULTS.md had 15/18/2; corrected by erratum `04c166886` |
| 2 | 523 of the 528 errors AD3 saved on S2 came from the recurrent ON; first ON unchanged | Summed AD − AD3 per segment | **Confirmed:** 0 / 2 / 523 / 3 for changes 6 / 12 / 18 / 24 |
| 3 | `AD3_FREEZE.json` hashes a CRLF copy of `ad3.py`; the LF blob differs (REPRODUCIBILITY) | SHA-256 of `git show HEAD:…/ad3.py` (`febfd055…`) and of its CRLF re-encoding (`98f5a62b…` = frozen) | **Confirmed.** Only that entry: AD3's other 77 and AD2's 65 entries match the committed blobs |
| 4 | On S1/S3/S4, AD3 used keys different from AD's on 4/6/1 blocks; equal error counts do not prove equal predictions | Compared decoded error bits in `work/ad3/eval/archives` | **Confirmed 4/6/1**, and further: the predictions were **bit-identical** on all 11 blocks |
| 5 | Screen: exact-and-unflagged recovery 1/80, 20/80, 48/80 for 1/2/3 blocks; flags 55/80, 54/80, 29/80 | `AD3_SCREEN.json` per-burst counts | **Confirmed** |
| 6 | C0: AD = AD3 = 346 vs ONCE 250; two flagged blocks in one root cost the 96 | `results/ad3/records/C0_e4.json` | **Confirmed** (blocks 14, 15; class 747 correct but flagged) |
| 7 | Causal floor: the earliest reactive action is the block after the first changed block | `ad3.py`: the change test for block u runs at the start of iteration u + 1 | **Confirmed** (by construction of the interface) |
| 8 | Recall reuses the alarm threshold, so non-rejection is weak evidence of a match | `ad3.recall(library, k, n, tau)` with the same τ | **Confirmed** |
| 9 | F3 compared AD3 with AD, not with a strong static decoder | `AD3_PROTOCOL.md` F3 | **Confirmed.** No strong static comparator existed in AD2/AD3 |
| 10 | Finite-row bounds: ON ≥ 46 (β .90) / 60 (β .95); OFF ≥ 90 / 91, with w = 0.99⁵ (FEASIBILITY) | Recomputed `ceil(log((1−β)/(1−α))/log w)` and `ceil(log(α/β)/log w)` | **Arithmetic confirmed.** These are loose necessary conditions, far below the 2,000 rows per block, so they do not bind here |

## Not verified, or not adopted

- **Literature claims** (`LITERATURE_REVIEW.md`, `REFERENCES.md`): not checked. They are treated as unverified background and nothing in DB1 depends on them.
- **The validation scale** (up to about 7 million rows over three authorisation stages): not adopted as a first step. DB1 is a bounded development run: 16 validation episodes (1.56 million generated rows), plus 1.43 million training rows, and anything confirmatory is left for the owner to authorise.
- **The state-identification method** (regularised common-covariance discriminants over parity/cofire features with Page accumulation): replaced by a simpler, auditable rule. Each state's per-detector rate template from separate training rows is tested with a goodness-of-fit G, which gives an explicit plausible set. This is the "directional" element in a minimal form; the discriminant is untested here.
- **The strong static definition** (a pooled argmin across the null/R/K/T design panels): simplified to an equal-weight mean over the five bank states, from a training risk table. See `PLAN_DB1.md`, deviations.
- **Prefix (sub-block) control and HMM/BOCPD** (matrix priorities 5–8): out of scope for DB1.

## Conclusion of the check

The review's factual statements about AD2/AD3 are correct, and two exposed real errors in our reporting, now corrected by erratum. Its central diagnosis also holds on our data:
- AD3's gain came from recognising a returning state;
- the first appearance of a burst is limited by the estimator, not by detection;
- AD and AD3 had no strong static baseline, and no protection against an expensive nominal fallback.

DB1 tests the parts of its recommendation that follow from that diagnosis: separate checks, a prebuilt bank, a risk gate and a strong static fallback.
