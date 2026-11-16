# Alternative-method assessment and next direction

## Contributions and limitations across V1.1–V1.6b

| Scientific component | What it means | Evidence interpretation / limitation |
|---|---|---|
| Exact logical-class inference | Sum probability over all fault assignments in each logical class, rather than choose the single most likely fault pattern. | This can exploit degeneracy on small distance-3 DEMs. The V1.6b reduction cannot be attributed to this alone because other components changed with it; exact variable elimination scales with DEM width. It is exact for the converted DEM, whose Pauli-channel construction may itself be approximate. |
| Correlated-noise representation | Retain multi-detector common-cause mechanisms instead of representing only independent graph edges. | V1.1 and V1.6 use synthetic burst mechanisms and explicit DEM assumptions. A strong fixed PyMatching baseline can already absorb some graphlike pair bursts; changing q may then rarely change predictions. |
| Learned burst support | Estimate which predetermined detector signature family is present from calibration detectors. | A true-support arm is privileged; learned support needs its own independent calibration validation and support-selection uncertainty. It must not be described as deployable if truth was supplied. |
| Rate adaptation/calibration | Estimate q from detector-only calibration or per-root detectors and update a decoder model. | The scalar-profile sprint found no prediction changes for pooled versus per-root profile matching on its saved evaluation set. That is a failure of this estimator/setting, not proof that all adaptation is useless. |

The V1.6b reported 61.5% reduction is not adaptation-specific: exact logical-class decoding, correlated support, learned support, and per-root rate estimation all contribute. Its strong static comparator and privileged true-support references answer different questions. The earlier scalar-profile experiment returned NO-GO for that profile setting; V1.6b is still development evidence rather than independent confirmation. The existing 900-shot replay does not verify all 576,000 predictions and uses the same frozen decoder implementation.

## Candidate comparison

| Method | Correlated DEM support | Logical degeneracy | Scaling/complexity | Availability here | Main risk |
|---|---|---|---|---|---|
| Current sum-product factor BP | Represents each independent DEM mechanism as a variable connected to every detector in its support; hyperedges are retained. | Current product of fault marginals is not a joint logical-class calculation. | Each sweep is O(incidence edges); convergence can stall on loopy graphs. | Implemented; d=3/5/7 deterministic fixtures run. | Nonconvergence at q=0, large d=3 logical-probability error, high degree/cycle rank. |
| BP + ordered-statistics decoding (BP+OSD) | A DEM maps naturally to a binary parity-check matrix whose columns are the full detector signatures of independent mechanisms; a hyperedge remains one column. | OSD produces a syndrome-consistent fault pattern. It does not automatically sum probability over logical classes, so degeneracy must be tested. | Sparse BP plus an OSD search; practical cost depends strongly on OSD order and can grow sharply in hard cases. | `ldpc` is not importable in the current environment; no install attempted. | Could report a good fault pattern while choosing the wrong logical class; worst-case OSD cost. |
| BeliefMatching | Potentially useful where the correlation model can be represented with the method's supported graph/correlation structure. | Must validate output against exact d=3 logical-class reference; semantics cannot be presumed. | Dependency-specific; no measurements in this phase. | `beliefmatching` is not importable and its adapter source is not present on this branch. | Unknown support for arbitrary higher-order DEM mechanisms; importing results from another branch would exceed this task's scope. |
| Exact DEM logical-class decoder | Full independent-mechanism model. | Exact aggregation over logical classes. | Exact variable elimination can be exponential in open width; use as small-distance reference, not presumed scalable. | Existing d=3 implementation; used as reference in fixtures. | DEM approximation remains; d=5/7 cost and feasibility not measured here. |

## Recommended next stage: deterministic BP+OSD feasibility

**Decision for the current FactorBP method: REVISE.** Do not run a stochastic pilot or claim the decoder is ready for a larger study. Its q=0 convergence failures and d=3 logical-class approximation errors are substantive.

If the owner wants to continue scalable decoder development, the strongest next bounded method is a separate BP+OSD prototype after approval to use a pinned `ldpc` dependency. Use the existing DEM as a parity-check matrix with one column per independent mechanism, preserve the mechanism probability and logical bit, and retain any multi-detector support as one column. Before any sampling, require deterministic checks for matrix/observable ordering, exact d=3 logical-error decisions on all feasible fixed fixtures plus independent exhaustive toy graphs, hyperedge handling, duplicate-column degeneracy, impossible syndromes, and bounded OSD order/runtime. Compare against unchanged strong static PyMatching on the same detector inputs and equal assumed-model/calibration information; keep exact d=3 as reference. Clearly label any true-model arm privileged.

BeliefMatching remains a plausible alternative only after its pinned source is available and its precise DEM/hyperedge semantics are independently checked. It is not selected here because its dependency and adapter are unavailable in this worktree.

Any development-only statistical study requires a separate preregistered protocol, disjoint seeds, paired roots, prespecified uncertainty/stopping rules, and explicit authorization. No 50% reduction target is inferred from the deterministic fixtures.
