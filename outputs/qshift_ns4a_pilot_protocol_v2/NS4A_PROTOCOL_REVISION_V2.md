# NS-4A Prospective Protocol Revision V2

**Status: proposed document-only revision. Not frozen, not authorized for sampling, and not an execution command.** It preserves the original proposal at outputs/qshift_ns4a_pilot_protocol/NS4A_SCIENTIFIC_PROTOCOL.md and proposed_config.json unchanged. It incorporates the accepted source-only audit at commit 7860a32e727270ca9f6069964f1d5d9522300b9c. This revision does not authorize deterministic DEM construction, sampling, training, model selection, or access to protected outcomes.

## Scope and question

NS-4A is limited to Pauli-composition variation and the Phase 3A synthetic spatial-burst mechanism. The question is whether BeliefMatching, given the same selected DEM information, changes paired logical-error outcomes relative to a single development-selected static PyMatching configuration on this finite set of six conditions.

This is an exploratory feasibility study. The six cells are **not a complete factorial**: the three Pauli-composition settings are evaluated without bursts, and the three burst strengths are evaluated only with balanced Pauli composition. No Pauli-bias-by-burst interaction is identified. No claim about hardware noise, generalization to other burst geometries, or adaptive superiority follows.

Native gate/measurement rate asymmetry is explicitly out of scope. It is reserved for a separate study described in NS4A_SCIENTIFIC_JUSTIFICATION_V2.md.

## Circuit and six evaluation conditions

Use the documented Stim rotated Z-memory surface code, distance 3, five rounds, with 40 detectors and one logical observable. The Phase 2B source defines balanced, x_biased, and z_biased categorical Pauli composition at gate fault mass 0.003, measurement flip probability 0.003, and bias ratio 10:1:1. Phase 3A adds a simultaneous X fault on data qubits 8 and 10 after each of five MR boundaries; the Bernoulli events are independent across boundaries. This is a synthetic spatial common-cause proxy, not a hardware-calibrated process or a temporally persistent error model.

| Evaluation cell | Pauli composition | Burst probability per MR boundary |
|---|---|---:|
| balanced_no_burst | balanced | 0 |
| x_biased_no_burst | X-biased | 0 |
| z_biased_no_burst | Z-biased | 0 |
| balanced_burst_0.005 | balanced | 0.005 |
| balanced_burst_0.010 | balanced | 0.010 |
| balanced_burst_0.015 | balanced | 0.015 |

The six original evaluation cells are retained. Source review found no source-level incompatibility requiring a cell change. The burst builder accepts probabilities in [0,1] and checks detector/observable counts, but this does **not** prove DEM validity, alias-guard safety, semantic detector-order identity, or decoder compatibility at the three proposed probabilities. Those remain a separately authorized deterministic preflight. No circuit or DEM was built as part of this revision.

The Phase 4C native depolarizing rate pairs are not relabeled as Pauli bias. In particular, “data-heavy” means gate-location noise is higher than measurement-flip noise; the native Stim gate channels are not restricted to data qubits.

## Partitions and unchanged total shot ceiling

The total remains 304,000 unique shots; the evaluation allocation is unchanged. Selection roots and evaluation roots/seeds must be disjoint. Numeric seeds remain unallocated and must be collision-screened in a later freeze.

| Partition | Conditions | Roots/cell | Shots/root-cell | Total |
|---|---:|---:|---:|---:|
| Model selection/calibration | all 6 cells | 8 | 1,333 base; deterministic +1 allocation below | 64,000 |
| Final development evaluation | all 6 cells | 10 | 4,000 | 240,000 |
| **Total** |  |  |  | **304,000** |

For selection, each of the 48 root-condition cells starts at 1,333 shots (63,984 total). Add one shot to the first three roots in each of the first four condition IDs in the table and to the first two roots in each of the last two IDs: 16 additional shots, for exactly 64,000. This deterministic allocation gives 10,667 shots in each of the first four conditions and 10,666 in each of the last two. Selection scores are computed as a mean of root-level LERs within each condition, then an equal-weight mean over the six conditions; the one-shot differences do not create shot-weighted condition weighting.

The selection budget is spread across more conditions than in the original proposal, so each selection root has fewer shots. Eight roots per cell and this allocation may leave the selected decoder uncertain. That uncertainty is reported rather than hidden. There is no claim that this pilot is powered for a small effect.

## Static baseline and estimand

The primary static comparator is the **selection-partition best single PyMatching configuration within a frozen finite candidate grid**, not the globally best conceivable static decoder.

The revised grid contains six assumed-model families—one matching each evaluation cell's Pauli/burst specification—crossed with two PyMatching modes (ordinary and correlation-enabled): 12 configurations total. Every candidate is scored using the same 64,000 selection shots. Select exactly one configuration minimizing the equally weighted mean of the six condition-specific means of root-level LER. Tie order is the model-family order in the revised config, then ordinary before correlation-enabled. That one selected configuration is held fixed in every evaluation cell; no cell-specific decoder or condition label is supplied at inference.

This is a stronger, target-aligned finite-grid comparator than selecting over only four models using only four of the six target conditions. It remains finite-grid and selection-limited: it does not guarantee optimality over other DEM families, parameter values, decoders, or conditions. Report the selection score of all 12 candidates and root-stratified selection-rank frequencies using a separate selection-rank bootstrap stream. If rankings are unstable, explicitly mark the selected comparator as uncertain. Do not replace it using evaluation labels.

BeliefMatching uses the exact selected DEM and declared noise provenance, with detector inputs identical to those supplied to the selected pooled-fixed PyMatching arm. The paired comparison is between decoder implementations on a shared decomposed/approximate DEM; it does not establish equivalent inference semantics. The selector may use selection labels only in the scoring harness. Decoder constructors and calls receive detector batches, not logical labels, hidden generating parameters, or evaluation condition labels.

For condition c and evaluation root r, let d[c,r] be the paired difference in LER, BM minus selected pooled-fixed PyMatching. The primary finite-set estimand is the equal-condition-weighted mean of the six condition means of d[c,r]; negative favors BM. Each root-condition cell uses 4,000 identical paired evaluation shots for every decoder.

## Decoder arms

Retain the originally proposed arms:

1. Nominal ordinary PyMatching.
2. Nominal correlation-enabled PyMatching.
3. The single selected pooled-fixed PyMatching configuration (primary comparator).
4. Ordinary and correlation-enabled PyMatching controls on the selected DEM, with duplicate configurations identified without changing labels.
5. BeliefMatching on the exact selected DEM.

All candidates must pass the upstream detector-support/logical-signature alias guard and circuit-identity/order checks. Phase 2B's categorical PAULI_CHANNEL_2 requires Stim DEM conversion with approximate_disjoint_errors=True in the documented Phase 3A matching helper. The native Phase 4C rate generator instead uses decompose_errors=True without that option. These model families must not be mixed within this NS-4A comparison. Exact DEM construction and alias checking are not authorized by this document.

## Analysis and progression gate

Preserve the proposed root-cluster analysis: report per-cell paired root effects; use a root-stratified paired bootstrap (100,000 resamples, two-sided percentile 95% interval) as the primary interval; show root-level values, leave-one-root-out sensitivity, and a labeled t-interval sensitivity. The two-sided root sign-flip test with 100,000 assignments and add-one p-value is sensitivity evidence only and depends on independent roots plus a symmetric root-level null. Do not use shot-level McNemar as primary inference. Apply Holm correction to the same three prespecified secondary contrasts: BM versus selected-DEM ordinary PM, BM versus selected-DEM correlation-enabled PM, and selected pooled-fixed PM versus nominal ordinary PM. Per-condition contrasts are exploratory.

The feasibility screen is: integrity/compatibility checks pass; no decoder failures; the primary estimate favors BM; the primary 95% interval upper endpoint is below zero; and at least four of six cell means favor BM. Even if all are met, the result is **exploratory only**. It can support a request to review a new protocol; it is not confirmation, does not establish general superiority, and does not authorize automatic expansion, execution, confirmation, or a transition to NS-4B. A new study requires a separately reviewed practical margin, power plan, seed freeze, and explicit owner authorization. Negative, null, inconclusive, and invalid outcomes receive complete reporting.

## Evidence-boundary disclosure

The original NS-4A protocol was published before an accidental historical-outcome exposure. The command history records a search that included outputs/phase4a_integrity_reaudit/SCIENTIFIC_RECOMPUTATION.md and outputs/phase4b_replication/PHASE4A_VALIDATION.md; output from the former displayed outcome numbers, which are intentionally not repeated here. The command followed the original protocol's commit/push and PR #3 creation (recorded PR timestamp 2026-11-13T04:40:46Z; exact shell timestamp unavailable). The prior agent reported non-use and no subsequent protocol/configuration/model-selection/sampling changes, but non-use is not independently certifiable and no claim of no influence is made. A previous full-tree worktree was materialized; its exact file inventory is unknown, though no content inspection was reported. This remains an unresolved influence and workspace-isolation limitation for supervisor assessment.

## Status

This is a proposed revision only. sampling_authorized=false, sampling_performed=false, no numeric seed inventory, no freeze, and no execution command. Research Codex remains on HOLD.
