# Correlated decoder V1.3: design plan (DRAFT, not frozen)

**Status:** planning draft for owner review. No V1.3 code, seeds, freeze or sampling. Nothing here authorizes execution.

## What V1.2 left open

V1.2 reached GO_DEVELOPMENT_ONLY. B beat static matching A\* by 0.27 pp and per-root matching A2 by 0.35 pp. Two anomalies remained:

1. The true-q arm C was not the best prior; a smaller-than-true prior (Bstatic q=0.0025) did better.
2. Per-root adaptation added nothing at nonzero q.

## Planning diagnostics (exploratory; already-exposed V1.1 selection set only)

`diag_prior_calibration.py` and `diag_matching_correlations.py` sweep priors and PyMatching's `enable_correlations` flag on the 60,000 V1.1 evaluation shots. These shots were already analyzed twice. There is no sampling, and V1.2 evaluation data were not used. Numbers below are errors per 20,000 shots for each condition.

| Decoder | q=0 | q=0.01 | q=0.02 |
|---|---:|---:|---:|
| Plain matching, correlations ON, static q=0.005 (V1.2 A\*) | 184 | 245 | 331 |
| Plain matching, correlations ON, q=0 / per-root (≈A2) | 142 | 265 | 349 |
| Plain matching, correlations OFF, any q | 102–104 | ≈975 | ≈1,880 |
| Five-factor, residual correlations ON (frozen B), best prior | 156 | 201 | 224 |
| Five-factor, residual correlations OFF, best prior | 109 | 125 | 148 |

What these suggest. They are not claims, because these data shaped the plan:

- **Correlated matching helps with the burst but hurts background decoding** on this circuit: 142 vs 104 errors at q=0. Neither mode dominates.
- **The frozen five-factor decoder has a cost mismatch (H1).** It picks residual edges with `decode_to_edges_array(..., enable_correlations=True)` but scores them with *static* edge weights. With correlations OFF, the selection and the scoring agree. Errors then fall by roughly a third, and the best prior moves near the true q (q=0.01: best 125 at q≥0.0125 vs 131 at true q; q=0.02: flat at 148 for q≥0.0125). That largely explains V1.2's "smaller prior wins" anomaly.
- **V1.2's matching family missed a mode-switching option.** A matching decoder that switches mode on the detector-only q̂ (OFF near q=0, ON otherwise) is a stronger adaptive baseline than V1.2's A2.

## V1.3 question

On fresh data: does a cost-consistent five-factor decoder (residual correlations OFF) beat the **strongest matching family**, including a mode-switching adaptive matcher? And does the repair restore a calibrated prior, with the true q near best?

The burst support stays given, as in V1.1 and V1.2. Learning the support is deferred to V1.4 (see "Deferred").

## What stays fixed

- The V1.1 circuit, q ∈ {0, 0.01, 0.02}, the estimator (refit check unchanged), and V1.1 `model.py` imported unchanged.
- V1.2's machinery: shared contract, run_pipeline/rehearsal design, watchdog, the freeze pattern including `.gitattributes`, and the analyzer validating before writing.

## Arms

| Arm | Definition | Role |
|---|---|---|
| A\*on | Matching, correlations ON, static q selected | Strong static matching (V1.2 A\* family) |
| A\*off | Matching, correlations OFF, static q selected | Reported; expected weak at nonzero q |
| **A2sw** | Matching per root: OFF at q=0 if q̂ < τ, else ON at q̂; τ selected | **Strongest adaptive matching** |
| B | Frozen V1.2 B (five-factor, residual ON, per-root q̂) | Continuity; size of the repair |
| Bstatic | Frozen V1.2 Bstatic (residual ON, q=0.0025) | Continuity |
| **Boff** | Five-factor, residual OFF, per-root q̂ | **Candidate** |
| Boff_static | Five-factor, residual OFF, static q selected | Representation without adaptation |
| Coff | Five-factor, residual OFF, true q | Calibration check (privileged) |

Boff uses uncorrelated matching on its q=0 path too, so it is consistent throughout. A new `multi_prior` variant with a `correlations` flag gets the same bit-identity tests as V1.2. The reference is an explicit per-mask, per-prior implementation, not the frozen class.

## Selection (before any V1.3 sampling)

- **Selection set:** the 288,000 V1.2 evaluation shots. They are now already-exposed development data, read-only and hash-verified. They are larger and fresher than V1.1's 60,000.
- **Selected values:** A\*on q, A\*off q and Boff_static q on a grid of {0, 0.00125, …, 0.02}; τ for A2sw on a grid of q̂ thresholds. The criterion is the minimum equal-weight LER, with ties going to the smaller value. The rule is committed before it runs, as in V1.2.

## Allocation

The same as V1.2, so effect sizes are comparable: 24 roots per q, 4,000 evaluation shots and 500 detector-only calibration shots per root. That is 324,000 new shots in 144 calls, on a fresh V1.3 seed namespace screened against V1, V1.1, V1.2 and the performance sprint.

**Runtime:** two five-factor families (residual ON for B/Bstatic, OFF for Boff/Boff_static/Coff) double the matching calls, to roughly 1,000 s projected. The proposal is a 3,000 s cap, with the preflight projection required to stay at or below 60% of it.

## Endpoints

**Co-primary** (intersection-union; equal-weight over q ∈ {0.01, 0.02}; root-stratified paired bootstrap, 20,000 replicates):

1. Boff − best of {A\*on, A\*off}, fixed at selection: beats the strongest static matcher.
2. Boff − A2sw: beats the strongest adaptive matcher.

**Safety:** at q=0, the 95th percentile of Boff − A2sw must be below +0.0005. A2sw is the toughest q=0 comparator, since it reaches uncorrelated matching there.

GO, NO-GO and INCONCLUSIVE follow the same structure as V1.2, with these comparators substituted.

**Secondary (descriptive):**
- Boff − B (value of the cost repair);
- Boff − Boff_static (value of adaptation once costs are consistent);
- Coff − Boff (is the true prior now near-optimal? This is a direct H1 check);
- A2sw − A\*on.

## Engineering safeguards carried over and added

- All of V1.2's safeguards: contract constants, fake-sampler rehearsal through `run_pipeline`, non-mutating re-analysis, an LF freeze, gated dry-run, and a single attempt with no retry.
- **New:** a test that each decoder's edge-selection mode matches its cost model, using the explicit mismatch fixture that motivated V1.3.
- **New:** the post-run from-scratch recount script is committed with the frozen package, rather than written afterwards.

## Deferred to V1.4: learned burst support

All five burst signatures here are logically trivial (`observable_flip=0`). Detector data alone can locate co-firing triples but cannot identify their logical effect. A learned-support decoder must therefore either assume the effect or estimate it with labeled calibration data. That design choice needs its own plan. V1.3 first establishes the strongest *oracle-support* decoder, so V1.4 has a clean ceiling to compare against.

## Decisions for the owner

1. **Scope:** cost repair and the stronger matching family now, with learned support deferred to V1.4.
2. **Selection set:** use the V1.2 evaluation arrays (288,000 already-exposed shots).
3. **Allocation and runtime:** keep V1.2's allocation of 324,000 new shots and raise the cap to 3,000 s.
