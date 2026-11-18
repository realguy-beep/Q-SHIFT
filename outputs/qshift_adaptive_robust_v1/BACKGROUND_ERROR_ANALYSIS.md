# Background-error floor analysis (development data only)

**Question.** In the d=5 low-p regime, L2 BP+OSD's errors with the burst present equal its burst-free floor, and that floor is what blocked 95% at Stage E. What kind of failures make up the floor?

**Data.**
- **Used:** Stage S development arrays only, from `outputs/qshift_d5_lowp_regime_v1/work/dev/`: 200,000 shots per (condition, q), at L10 (p = 0.001) and L15 (p = 0.0015), q ∈ {0, 0.01, 0.02}.
- **Not used:** Stage E rows (`work/eval_v1`) were **not read**. The script refuses that path. No new Stim samples were generated.
- **Labels:** observable labels are used offline as a diagnostic only. No deployable component sees them.

**Code, output and runtime:**
- Script: `floor_diagnostic.py`.
- Output: `results/floor_diagnostic/FLOOR_DIAG.json` (summary) and `floor_rows.json` (per shot).
- Runtime: 167 s, single process.

## Method

The sample is every shot that the Stage-S-selected L2 failed (prior 0.001 at L10, 0.0025 at L15): **56 failures**, all reproduced deterministically. A fixed control sample of 600 L2 successes (100 per file, seed 20261118) was added. Each shot was checked as follows.

1. **BP convergence** of the L2 BP stage (`converge` flag, and whether the BP-only estimate satisfies the syndrome).
2. **Cost of L2's estimate**, written C_wrong. This is the negative log-likelihood ratio, the sum over e_j = 1 of log((1−p_j)/p_j). That estimate lies in the wrong logical class.
3. **Best correct-class estimate.** BP+OSD (OSD_CS order 40) was run on the parity-check matrix with the logical row appended, with the target logical bit set to the observed label. This gives a valid correct-class error with cost C_correct, which is an *upper bound* on the correct-class minimum.
   - If C_correct < C_wrong, a more likely error exists in the correct class, so L2 is not the most-likely-error decoder on that shot. This is labelled **search-limited** (certain).
   - Otherwise the failure is labelled **MLE-consistent** (conservative: a better correct-class error might exist that the constrained search missed).
4. **Variant re-decodes:** OSD_CS order 40, OSD_E order 8, 500 BP iterations, and min-sum with scaling 0.9.

## Results

| Quantity | Value |
|---|---|
| Failures (L10 / L15) | 56 (12 / 44) |
| BP converged: failures vs controls | **11/56 (20%)** vs **596/600 (99.3%)** |
| Correct-class estimate found | 56/56 |
| **Search-limited** (C_correct < C_wrong) | **10/56 (18%)**; L10 2/12, L15 8/44 |
| **MLE-consistent** (C_correct ≥ C_wrong) | **46/56 (82%)** |
| Near-ties, abs(C_wrong − C_correct) < 0.25 | 9/56 |
| Fixed by OSD_CS-40 / OSD_E-8 / BP-500 / min-sum-0.9 | 3 / 8 / 4 / 12 |
| Fixed by any variant | 17/56 (30%), including 8 of the 10 search-limited failures |
| Variant broke a control success | 0/600 for every variant |
| Error weights (mechanisms), wrong / correct-class | 2–6 / 3–6 |

**How the fixes break down:**
- OSD_CS-40 and BP-500 fixes all lowered the cost below L2's. These are genuine search improvements.
- 6 of min-sum's 12 fixes lowered the cost. The other 6 fixes, and all 8 OSD_E fixes, returned a *more costly* estimate that happens to lie in the correct class. Under a minimum-weight criterion these are not principled improvements. They may reflect degeneracy (more total probability in the correct class) or luck, and this data cannot tell which.

## Interpretation, by candidate cause

| Candidate cause | Evidence here | Assessment |
|---|---|---|
| BP convergence failure | BP fails on 80% of failures and on 0.7% of successes | Strongly associated. On failure shots, OSD does the work, and OSD_CS-10's search is the limit on about 18% of them |
| OSD order and search limits | 10 failures certainly search-limited; higher order or BP-500 fixes 3–4 at lower cost | **Real but small:** at most about 18% of the floor |
| Degenerate logical classes / syndrome ambiguity | 82% MLE-consistent, 9 near-ties, error weights about d/2 | **Dominant.** Most of the floor consists of syndromes whose most likely error lies in the wrong class: a minimum-weight decoder *must* fail on them. Only coset-probability (degenerate, maximum-likelihood) decoding, or a more accurate model, can recover some of them |
| Incorrect likelihood modelling | Not tested here: the decoder used the true base p and true support (oracle) | Not a cause in this oracle setting. It becomes one under mismatch (`DIAG_RESULTS.md`) |
| DEM approximation (`approximate_disjoint_errors=True`) | Not tested | Open. It needs an exact-vs-approximate DEM comparison at d=5 |
| Trapping sets / short cycles | Indirect: non-convergence concentrates on failures | Consistent with it, but no trapping-set enumeration was done |
| Implementation error | 56/56 deterministic reproductions; every correct-class estimate valid | No evidence of an implementation error |
| Graph matching vs hypergraph | Not in scope | Matching is the comparator, so its floor sets the denominator, not the numerator |

## What this implies for 95%

- **A projection, not tuning.** It uses Stage S counts plus published Stage E summaries, and no decoder was selected on Stage E.
  - If a better search removed every search-limited failure (−18%), Stage E's L10 numerator of 56 would fall to about 46, against Astar's 928, giving **R ≈ 95.0%**: right at the boundary.
  - If the variants' "any fix" rate (30%) were achieved with no breakage, R would be ≈ 95.8%.
- **The breakage check is far too weak.** Zero breaks in 600 controls only bounds the break rate below about 0.5% (rule of three). The failure rate is about 8e-5 per shot, so a variant that broke 1 success in 10,000 would cancel the gain.
- **The net effect therefore requires full-pool re-decoding** of the 1.2 M Stage S dev shots (§Next).
- **At p = 0.003 the same reasoning gives no route to 95%.** There the floor is a large fraction of Astar's errors (cap about 65%). Removing 18–30% of the floor moves R by only a few points.

## Next (smallest discriminating experiment; needs owner OK)

**What to run:**
- Re-decode all 1.2 M Stage S dev shots (existing arrays; no new sampling) with two pre-declared variants: **min-sum 0.9** and **OSD_CS-40 + BP-200**.
- Report the net error change per (condition, q) against L2, with discordant counts and paired root-cluster CIs.

**Cost:** about 2 × 1.2 M decodes at 5–8 ms/shot, roughly 30–45 min on 8 workers.

**Decision rule, fixed before running:**
- A variant advances to a fresh-seed validation screen only if its net change is negative with a 95% upper bound < 0 in pooled dev data, and q=0 harm is ≤ 0.
- Otherwise the conclusion is "the floor is degeneracy-dominated". That redirects effort to degeneracy-aware decoding: belief-matching, which needs an approved dependency, or ensembles.

## Outcome of the next step (added after the run)

The full re-decode (`REDECODE_RESULTS.md`) did not confirm the projection above. Min-sum creates 27 new failures among L2's successes (net +15 [+3, +27]), and OSD_CS-40 + BP-200 is neutral (net −1 [−9, +7]). Verdict: H-F2.
