# Correlated decoder V1.3 protocol

**Status:** prospective, single bounded development-only evaluation. It is not independent confirmation. It does not authorize Stage 5 access, sealed-data access or follow-up sampling. The evaluation runs only after the owner gives separate sign-off on the frozen commit.

This protocol implements the approved `DESIGN_PLAN_DRAFT.md`. Deviations are listed at the end.

## Question

On fresh data: does a **cost-consistent** five-factor decoder (residual matching with correlations OFF) beat the strongest static matching decoder and a mode-switching adaptive matcher? And does the repair restore a calibrated prior, with the true q near best?

## Lineage and motivation

V1.2 (`b95687ccb451896dcb9963e4e2b261de97572204`, results `e20ac9e71`) reached GO_DEVELOPMENT_ONLY for B over A\* and A2. Two anomalies remained: a smaller-than-true prior won, and adaptation added nothing.

The planning diagnostics (`diag_*.py/json`, V1.1 selection set only) traced both anomalies to a cost mismatch. The frozen five-factor decoder chooses residual edges with correlation-reweighted matching but scores them with static weights. The diagnostics also showed that correlated PyMatching hurts background-only decoding on this circuit (142 vs 104 errors at q=0 per 20,000 shots), so neither matching mode dominates.

`tests/test_mode_aware_decoder.py` pins the facts the design relies on:
- With correlations ON, the mode-aware decoder is bit-identical to the frozen V1.1 decoder.
- With correlations OFF, it equals an independent reference built on PyMatching's own `return_weight`.
- Its OFF-mode background cost equals the PyMatching solution weight, within PyMatching's weight discretization.
- The ON-mode mismatch exists: cost exceeds the minimum weight by more than 1e-3 on the fixtures.

## Fixed elements

- **Circuit:** rotated distance-3 Z-memory, five rounds, p_gate = p_meas = 0.003. A synthetic `CORRELATED_ERROR(q) X8 X12 X15` follows each MR boundary. q ∈ {0, 0.01, 0.02}. V1.1 `model.py` is imported unchanged and hash-checked against the V1.1 freeze.
- **Estimator:** the frozen V1.1 affine estimator, refit from 3,000 V1 training detector rows. Execution stops unless slope = 0.88 and intercept = 0.000667 within 1e-12.
- **Burst support:** the five exact signatures are given to every five-factor arm, as in V1.1 and V1.2. All five are logically trivial (`observable_flip = 0`).

## Arms

All eight arms decode identical detector rows per root. Observables are inspected only after every prediction exists.

| Arm | Definition |
|---|---|
| **Astar** | Static PyMatching, correlations **ON**, q = **0.00375** (best over mode × q) |
| AstarAlt | Static PyMatching, correlations OFF, q = 0 (best in the other mode) |
| **A2sw** | Per root: uncorrelated matching on the base DEM if q̂ < τ = **0.0005**, else correlated matching at q̂ |
| B | Frozen V1.2 B: five-factor, residual ON, per-root q̂ |
| Bstatic | Frozen V1.2 Bstatic: five-factor, residual ON, q = 0.0025 |
| **Boff** | Five-factor, residual OFF, per-root q̂ (candidate) |
| BoffStatic | Five-factor, residual OFF, static q = **0.01125** |
| Coff | Five-factor, residual OFF, true q (privileged) |

## Selection (completed before any V1.3 sampling)

The selection set is the 288,000 V1.2 evaluation shots: already-exposed development data, hash-verified, unchanged before and after. Per-root q̂ comes from V1.2's detector-only calibration record.

- **Grids:** q from 0 to 0.02 in steps of 0.00125; τ ∈ {0, 0.0005, 0.001, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01}.
- **Criterion:** minimum equal-weight LER. Ties go to the smaller value, and to ON before OFF.
- **Pre-registration:** the rule was committed (`e161ce1e9e160986e1b7bb203bef5973f5fe85c5`) before it ran.
- **Consistency checks:** recomputed correlated matching at q̂ equals V1.2's saved A2 predictions on all 288,000 shots, and static ON matching at q=0.005 reproduces V1.2's Astar counts (835 / 1,186 / 1,543).

Results are in `STATIC_SELECTION.json` (committed at `fb433ecc7`, after the rule). Errors out of 288,000 (q=0 / 0.01 / 0.02):

| Selected | Errors | Total |
|---|---|---:|
| Astar: ON, q=0.00375 | 777 / 1,122 / 1,493 | 3,392 |
| AstarAlt: OFF, q=0 | 460 / 4,892 / 8,790 | 14,142 |
| A2sw: τ=0.0005 | 460 / 1,289 / 1,597 | 3,346 |
| BoffStatic: q=0.01125 | 552 / 634 / 719 | 1,905 |

Astar's q equals the V1.2 post-hoc oracle (0.00375). All values were chosen in-sample on the selection set, which makes the baselines optimistic on that set. BoffStatic's static optimum sits between the nonzero true q values, consistent with H1. Since these data shaped the choices, this is not evidence.

## Allocation

The same as V1.2: 3 × 24 roots; 500 detector-only calibration shots per root (observables discarded unread) and 4,000 paired evaluation shots per root. That is 324,000 new shots in 144 sampler calls. There are 146 seeds in the V1.3 namespace, screened against V1, V1.1, V1.2 and the performance sprint (351 values, 0 collisions). The calibration-order gate is as in V1.2: stop before any evaluation sample if it fails.

## Endpoints and decision rule

Statistics are root-paired differences, equal-weight over q ∈ {0.01, 0.02}. The bootstrap uses 20,000 root-stratified paired percentile replicates, with shared indices across contrasts and NumPy `linear` quantiles.

**Co-primary** (intersection-union): (1) Boff − Astar and (2) Boff − A2sw.

**Safety:** at q=0, Boff − A2sw from an independent bootstrap stream, against a tolerance of +0.0005.

- **GO (development only):** both co-primary 95% intervals lie entirely below 0; Astar has at least 100 nonzero errors; Boff's point LER is below Astar's at both nonzero q; and the q=0 95th percentile is below +0.0005.
- **NO-GO:** the Boff − Astar interval is entirely at or above 0, or the q=0 5th percentile is above +0.0005.
- **INCONCLUSIVE:** everything else, including a gate, resource or finalization failure.

**Secondary (descriptive):**
- Boff − B (value of the cost repair);
- Boff − BoffStatic (value of adaptation once costs are consistent);
- Coff − Boff (calibration check: under H1, the true prior should be near-optimal);
- A2sw − Astar;
- Boff − AstarAlt;
- B − Astar (V1.2 replication on fresh data).

**Interpretation boundary:** even a GO is development evidence for one synthetic mechanism at d=3, with oracle burst support. It is not hardware, scaling, latency or independent-test evidence.

## Execution controls

- The V1.2 machinery is unchanged, except for the arms:
  - a hash freeze, non-circular and LF-pinned;
  - an exact `--expected-head` on a clean `codex/qshift-correlated-decoder-v1-3`;
  - the pinned environment, V1 reuse verification and estimator refit;
  - a PASS preflight, the Windows watchdog, and a single attempt with no resume, retry or seed substitution.
- **Limits:** 3,000 s wall time (watchdog process-tree kill plus in-process guard), 2 GiB sampled RSS, at least 1 GiB free disk, 256 MiB of artifacts. The preflight projection must be at or below 60% of the cap.
- **Rehearsal:** `rehearsal.py` drives the same `run_pipeline` through runner, analyzer and manifest with a fake sampler.
- **Recount:** `recount_from_scratch.py` (NumPy only, no package imports) is frozen with the package and tested on the rehearsal run. It is the planned post-run independent recount.

## Deviations from the draft

1. **Matching-arm list:** the draft listed A\*on and A\*off. They are implemented as Astar (the selected best over both modes) and AstarAlt (best in the other mode), so the co-primary comparator is fixed by selection. The two arms cover the same models.
2. **Recount script:** the frozen recount reads the shot count from the archives, rather than hard-coding 4,000, so it can be tested on the rehearsal run. It still requires equal counts across all 72 archives.
3. **Weight tolerance:** OFF-mode cost equality with PyMatching's `return_weight` is tested to 1e-5, not exact, because PyMatching discretizes weights internally (an observed gap of about 5e-7 on a cost of about 32.7).
