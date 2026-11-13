# NS-4A V2 Scientific Readiness Review

**Review basis:** Q-SHIFT V7 commit `033e98e873d503056b9e9b05a496c3b7cff06ccc` (reviewed from the published commit through targeted file reads). This is a read-only review; it does not authorize a freeze or execution.

## Decision

**CORRECTIONS_REQUIRED.** NS-4A V2 is a coherent, bounded *exploratory decoder-feasibility* question, but it is not ready for separate execution authorization. The principal blockers are unresolved influence from the documented historical-outcome exposure, no allocated/collision-screened production seed inventory, no demonstrated full-workload runtime or recovery, a 1,800 s protocol deadline that the available V7 watchdog rejects, and a memory limit whose current Windows measurement does not implement the configured peak-RSS quantity. The evaluation allocation also has no empirical power basis and no prespecified practical-effect threshold.

The reviewed experiment is **not adaptive decoder switching**. It compares one BeliefMatching implementation with one globally selected static PyMatching configuration on a finite synthetic condition set.

## Exact scientific question

For a distance-3, five-round rotated Z-memory Stim surface-code circuit, does BeliefMatching on the selected assumed detector error model (DEM) change paired logical-error outcomes relative to one calibration-selected, pooled-fixed PyMatching decoder across the six specified synthetic conditions? The primary estimand is the equal-weight mean across those six conditions of each condition's mean over ten paired evaluation roots of `LER(BeliefMatching) − LER(pooled-selected PyMatching)`. Negative values favor BeliefMatching.

The six conditions are three categorical Pauli compositions at zero added burst probability (balanced, X-biased, Z-biased), plus three burst strengths (0.005, 0.010, 0.015 per measurement boundary) at balanced composition. A burst is a synthetic simultaneous X fault on data qubits 8 and 10 after each of five measurement boundaries, with independent boundary events. This is a spatial common-cause proxy; it is not a calibrated hardware process or a temporally persistent drift model. The six cells are not a factorial: Pauli-composition-by-burst interaction is not identified.

## Information parity and selection

The V2 design supplies BM and the selected pooled-fixed PM arm the same selected DEM bytes and declared assumed-noise provenance. Both decode the same detector arrays; decoder calls do not receive logical labels or hidden generating probabilities. In selection, all 12 candidate configurations receive the same detector bytes; the selection scorer reads labels only after predictions have been returned. Evaluation uses a separately allocated partition, and the selected candidate is frozen before evaluation begins. The independent saved-array audit recomputes the winner and outcomes from persisted archives.

This is fair **model-information parity**, not a claim that BM and PM use the DEM identically. BM's algorithm may exploit the supplied structure differently. The model grid consists of the six condition-matched DEM families crossed with ordinary and correlation-enabled PyMatching. One global candidate is chosen using equal condition weighting over the selection roots. At evaluation, no condition-specific model switch occurs.

The comparator is strong and target-aligned **within that finite 12-candidate grid**. It is not the globally strongest possible fixed decoder: the grid excludes other weights, model families, burst locations, parameter values, or decoder implementations. Selection over 12 candidates with only eight roots per condition can yield an uncertain winner; the planned rank bootstrap describes that uncertainty but does not remove it. The primary evaluation interval is conditional on the selected candidate.

The selected DEM encodes a prespecified family of plausible noise models, including the tested burst assumptions. That is not evaluation-label leakage: it is model information supplied to both primary arms and the selected configuration is global. It does, however, make the claim specifically about BM versus PM given this approximate DEM construction, not about inferring unknown noise or learning a deployable adaptive policy.

## Statistical scope and historical independence

The V2 configuration allocates 64,000 selection shots (48 root-condition units, eight roots in each of six cells, 1,333/1,334 shots per root) and 240,000 evaluation shots (60 root-condition units, ten roots per cell, 4,000 shots each), for 304,000 unique shots. Numeric scientific seeds are explicitly unallocated. The source validator requires 108 unique root seeds plus six independent analysis seeds and collision screening against a complete, allowlisted historical seed set; that inventory and collision screen do not yet exist.

The V2 protocol records an accidental historical-outcome exposure before the V2 revision. The incident record says values were displayed, records a reported non-use claim, and explicitly says non-use and absence of influence cannot be independently certified; it also records uncertainty about a prior full-tree worktree. No historical outcome values are repeated here. This does not prove contamination of the proposed independent partitions, but it prevents this review from certifying investigator-level independence. Consequently the experiment cannot be presented as confirmatory, regardless of the eventual p-values.

The protocol calls the work exploratory and fixes an exploratory progression gate. It does not assert confirmation, hardware performance, universal decoder superiority, or adaptation. Even if the gate passes, the protocol only permits a request to review a new development protocol; it does not authorize automatic expansion.

## Prior Q-SHIFT evidence relevant to interpretation

Phase 4C baseline-selection documentation chose a pooled fixed native-rate PyMatching model at gate/measurement rates `(0.001, 0.003)` and a distinct minimax model at `(0.006, 0.003)`; condition-specific choices differed. Its interpretation says development selections are descriptive and close development rates do not identify unique superiority; held-out test evidence was not yet available in that Phase 4C record. Those native depolarizing-rate experiments are not the categorical Pauli-plus-burst generator in NS-4A and should not be pooled or treated as direct accuracy evidence for this comparison.

## Evidence classifications

| Finding | Classification | Basis / limitation |
|---|---|---|
| V2 estimand, conditions, arms, allocations, and exploratory gate | Verified from committed documents | `proposed_config_v2.json`, `NS4A_PROTOCOL_REVISION_V2.md`, and statistical addendum at the review commit |
| Label isolation, paired inputs, fixed global winner, exact DEM identity checks | Verified in source contract | deterministic `selection.py`, integrated `runner.py`, `models.py`, and saved-array `audit.py`; source validation is not proof that a future execution occurred correctly |
| Six-condition DEM compatibility and alias checks | Previously accepted deterministic preflight | Lock-matched NS-4A preflight history; deterministic fixture/DEM checks are not decoder-accuracy evidence |
| Historical-outcome exposure / influence | Verified as an unresolved disclosure | V2 protocol documents exposure, displayed output, reported non-use, and unknown influence; no protected file was reopened |
| Actual V6 benchmark report and timing values | Partly available only in earlier review-session record | Exact JSON is absent from this checkout and GitHub contents lookup returns 404; see Engineering review. Values are not freshly rehashed here |
| Independent roots / no seed overlap | Not yet established for V2 | Production seeds are not allocated and collision screening is not done |
| Improvement, effect size, power, runtime, full-scale memory | Unknown | No V2 sampling or full-workload benchmark is authorized or available |

## Readiness conclusion

There is a scientifically interpretable, bounded question worth retaining. The current evidence supports a cautious exploratory comparison design, not an adaptive claim and not a confirmatory paper result. Resolve the items in `REQUIRED_CORRECTIONS.md` and obtain independent supervisor review before any owner authorization is prepared.

No sampling, training, decoder benchmark, or sealed-outcome access occurred in this review. Historical protocols and evidence were not edited.
