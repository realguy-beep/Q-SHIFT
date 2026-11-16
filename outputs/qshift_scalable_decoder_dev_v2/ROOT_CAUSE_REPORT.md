# Root-cause report — scalable decoder V2

## Scope and evidence boundary

This report uses the V1 protocol/source/tests/report, the V1.6b committed replay and calibration reports, and deterministic source-defined fixtures only. No Stim sampler, random generator, held-out outcome, saved evaluation array, or sealed test was accessed in this V2 work. V1 source, V1 fixture results, and V1.6b evidence remain unchanged.

V2 protocol was committed first at `4948bc43b442f651a4d845dd249980a68cbf0bce`. It froze the solver settings and correction scope before V2 implementation changes.

## Findings by suspected cause

| Area | Finding | Classification |
|---|---|---|
| Factor-to-variable update | The parity-check LLR equation `2 atanh((-1)^s product tanh(m/2))` and the variable-to-check prior-plus-other-messages update agree with exhaustive enumeration on tree factor graphs, including a two-detector hyperedge. | No equation defect found in these checks. |
| Damping/scheduling | V1/V2 use synchronous flooding, LLR messages, damping 0.5, tolerance 1e-8, and 50 iterations. Residual traces for q=0 fixtures mostly decrease over the final iterations, with occasional increases; they do not establish a stable fixed point by the cap. A small three-check cycle stalled at a nonzero residual rather than showing a two-step cycle. | Loopy-BP convergence limitation is observed; a particular oscillation mechanism is not established. No schedule or damping sweep was run because that would tune a new algorithm on the fixed fixture set. |
| Convergence criterion | V1/V2 declare message convergence only when the maximum change in damped detector-factor messages is below tolerance. q=0 nonzero fixtures end above tolerance; they are correctly marked nonconverged. A converged message state is not an exact-posterior guarantee on a loopy graph. | Criterion is conservative for the implemented messages; it does not explain or cure loopy approximation error. |
| Logical observable | V1 multiplied individual fault marginal parities to form `p1`, which is not generally the joint parity probability when logical-bearing faults are correlated by detector checks. On the exact two-mechanism example, the true logical probability is exactly 0 or 1 from the detector, while V1 returned about 0.0526 or 0.5740. | V1 output contract was misleading if read as an exact logical-class posterior. V2 labels it `logical_p1_approx` and flags when random logical bits are detector-connected. General joint logical inference remains unresolved. |
| p=0 / p=1 | V1 removed p=0 mechanisms correctly. At p=1 it used a finite clipped log-odds and accepted an impossible syndrome. | Confirmed boundary/feasibility defect. V2 absorbs p=1 faults into a fixed affine detector/logical offset and rejects syndromes outside the remaining mechanisms' exact GF(2) support. |
| Logical-only mechanisms | A V2 fast path initially dropped random logical-only mechanisms when the DEM had no detector incidences. A deterministic test exposed it; V2 now routes those models through the logical parity calculation and identifies the independent product as exact. | Confirmed V2 defect, repaired and covered by regression test. |
| Numerical stability | V1 uses probability clipping to form priors and an O(degree²) loop for each parity-factor outgoing product. V2 uses `log1p(-p)-log(p)` for interior probabilities, exact p=0/p=1 handling, bounded atanh arguments, and prefix/suffix products for the same parity equation. | Boundary stability corrected; O(degree) update is an algebraically equivalent performance improvement. Near-endpoint finite-output tests pass. |
| DEM parsing | Stim defines DEM error mechanisms as independent Bernoulli mechanisms; `^` only suggests a decomposition of one mechanism. V1's handling of `^` by retaining all non-separator targets as one mechanism is consistent with that semantics. V2 tests the same rule, duplicate target parity, hyperedges, and observable parity. | No separator-splitting defect found. Stim primary documentation: https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md (error instruction and separator target). |
| Noise/DEM fidelity | Stim DEM conversion is configured with `approximate_disjoint_errors=True`. The exact decoder is exact for the resulting DEM, not necessarily the originating circuit's mutually exclusive Pauli channels. | Model approximation limitation, not a BP parser defect. |

## Why q=0 and q=0.01 behave differently

The two candidates do not share a fixed graph with only different edge weights. The burst parameter changes which positive-probability mechanisms appear in the DEM. In every tested distance, q=0.01 adds five mechanisms and changes detector incidences and cycle rank. The change is deterministic and visible in the model summaries:

| Distance | q | Active mechanisms | Detector incidences | Incidence cycle rank | Maximum check degree |
|---:|---:|---:|---:|---:|---:|
| 3 | 0 | 443 | 1,188 | 706 | 56 |
| 3 | 0.01 | 448 | 1,203 | 716 | 56 |
| 5 | 0 | 1,677 | 5,004 | 3,208 | 80 |
| 5 | 0.01 | 1,682 | 5,024 | 3,223 | 80 |
| 7 | 0 | 3,695 | 11,412 | 7,478 | 80 |
| 7 | 0.01 | 3,700 | 11,432 | 7,493 | 80 |

All graphs are connected and highly loopy. Thus the better convergence at q=0.01 cannot be attributed to a cleaner graph; it coincides with both new correlated mechanisms and changed priors. This two-condition contrast cannot isolate topology from probability effects.

## Convergence trace interpretation

With the frozen 50-iteration budget, q=0 converged on 1/6 fixtures at each distance; q=0.01 converged on 6/6 at each distance. The q=0 d=3 final residuals ranged from `9.97e-8` to `1.14e-4`; q=0 d=5 reached `1.45e-3`; q=0 d=7 reached `1.52e-2`. The q=0.01 maximum final residual across the six distance/condition groups was below `1e-8`.

For d=3 q=0, five nonzero fixtures mostly showed declining residuals over the final ten updates, although several had a few intermediate residual increases. The minimal three-check cycle's residual approached and then plateaued near `0.00606`; its final two-step message difference was about `0.0121`, so this fixture did not show a period-two fixed-point oscillation. It is not evidence that larger graphs cannot oscillate. We did not alter iteration count, damping, or scheduling to force convergence.

## Root-cause conclusion

There were two confirmed implementation defects: p=1/impossible-syndrome handling in V1 and the V2 zero-incidence logical-only fast path. Both are repaired and tested. The V1 detector message equations passed exact tree checks. Remaining q=0 nonconvergence is consistent with a bounded synchronous BP method operating on dense loopy incidence graphs, but the exact mechanism is not proven. The large d=3 logical-probability error is a limitation of the product-of-marginals approximation, not evidence that the detector-message equations are algebraically wrong.

V2 is therefore a corrected and faster BP prototype, not a reliable logical-class decoder. It remains a **REVISE** result.
