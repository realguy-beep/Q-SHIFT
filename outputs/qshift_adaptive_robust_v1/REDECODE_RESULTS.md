# Roadmap step 1 results: full re-decode of Stage S development shots

**Verdict, under the rule pre-registered in `REDECODE_PROTOCOL.md` (commit `600551456`): H-F2_FLOOR_DEGENERACY_DOMINATED.** Neither variant advances. Cheap search changes do not lower L2's net background floor. Min-sum is significantly *worse*.

This is development data. The result is a screening decision, not a confirmatory claim.

## Run

- **Authorization:** owner, 2026-11-18 ("Run floor re-decode").
- **Code and protocol:** committed in `600551456` before any output existed.
- **Command:** `python redecode.py run --workers 8`.
  - 102/102 write-once tasks.
  - Wall time 3,033 s (50.5 min).
  - CPU time: V1 1,555 s, V2 22,026 s, identity checks 115 s.
- **Data:** 1,200,000 Stage S development shots. No sampling, and Stage E was not read.
- **Identity check:** baseline L2 re-decoded on the first 2,000 shots of all 6 files was bit-equal to the saved Stage S error bits.
- **Analysis:** `python redecode.py analyze`, run twice; `REDECODE.json` was byte-identical.

## Pooled results (6 files, 1.2 M shots)

| Variant | Variant-only failures | L2-only failures | Net | Net 95% interval | One-sided McNemar p (variant better) | q=0 net | Decision |
|---|---|---|---|---|---|---|---|
| V1 min-sum 0.9 | 27 | 12 | **+15** | **[+3, +27]** | 0.995 | +5 [−2, +12] | DO_NOT_ADVANCE (significantly worse) |
| V2 OSD_CS-40 + BP-200 | 7 | 8 | −1 | [−9, +7] | 0.50 | +1 [−3, +6] | DO_NOT_ADVANCE (no detectable effect) |

## Per file (errors; variant-only / L2-only)

| File | L2 | V1 | V2 |
|---|---|---|---|
| L10 q0 | 4 | 5 (1/0) | 3 (0/1) |
| L10 q1 | 4 | 7 (3/0) | 4 (1/1) |
| L10 q2 | 4 | 5 (2/1) | 3 (0/1) |
| L15 q0 | 16 | 20 (8/4) | 18 (3/1) |
| L15 q1 | 12 | 18 (9/3) | 11 (1/2) |
| L15 q2 | 16 | 16 (4/4) | 16 (2/2) |

## Interpretation

1. **The floor diagnostic's "fixes" do not survive full decoding.** The diagnostic found min-sum fixing 12 of 56 failures with 0 breaks in 600 controls. On all 1.2 M shots it fixes those same 12 but creates 27 new failures among L2's successes: a break rate of about 2.3e-5 per success. The 600-control check could not have detected that rate (risk R8, predicted in `RISK_REGISTER.md`).
2. **Better search is roughly neutral.** V2 (higher OSD order, more BP iterations) fixes 8 failures and creates 7. This agrees with the diagnostic: about 18% of failures are search-limited, and wider search also moves some borderline successes into the wrong class.
3. **The remaining floor is consistent with most-likely-error decoding.** Most of it cannot be removed by any decoder that returns a single most-likely error. Reducing it requires degeneracy-aware decoding, which compares the total probability of each logical class (ensembles, belief-matching, tensor-network maximum likelihood), or a better noise model.

## Consequences for the program

- **95% at p = 0.001:** the cheap route through search variants is closed. The near-boundary projection in `BACKGROUND_ERROR_ANALYSIS.md` (about 95.0–95.8%) is **not supported**. The figure stays at Stage E's 94.0%.
- **Broad-benchmark 95%:** this remains implausible (`DECISION_REPORT.md` §5). The result removes one of the few candidate levers.
- **Remaining floor lever:** degeneracy-aware decoding (H-F2). The concrete options are:
  - a matching or BP+OSD ensemble that compares class probabilities (no new dependency);
  - belief-matching (needs an approved `beliefmatching` install);
  - small-region tensor-network maximum-likelihood decoding at d=5 (cost unknown).

  Any of these must first be screened on development data, with full-pool net discordance, before any fresh-seed validation.
- **Recommendation:** the next decision-relevant step is roadmap step 2 (H-E1: the mismatch-robust learner on the existing mismatch development arrays). It targets *robustness*, the program's main deployable gain, rather than the 95% headline.
