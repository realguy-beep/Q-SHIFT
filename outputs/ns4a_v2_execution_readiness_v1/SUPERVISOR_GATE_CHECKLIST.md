# Supervisor gate checklist — NS-4A V2

**Current state: prepare-only package; execution is not authorized.** No live approval token, seed inventory, freeze activation, sampler invocation, or transition to NS-4B is permitted by this package.

## Before proposing a final freeze

- [ ] Resolve the exact secondary p-value procedure for all three Holm comparisons.
- [ ] Set and document the selection-rank bootstrap replicate count and its independent seed stream.
- [ ] Preserve V2's 12-candidate, six-condition selection; reconcile references to the historical V1 eight-candidate/four-condition plan without editing it.
- [ ] Implement candidate scorer: 12/12 candidates on byte-identical 64,000 selection samples; labels only in scorer; global winner and tie order persisted before evaluation.
- [ ] Implement production runner, independent saved-array auditor, transactional checkpoints, cross-process locking, deadline supervision, root uniqueness and duplicate prevention.
- [ ] Add deterministic tests for selection ties/ranks, sample identity, information isolation, zero-error statistics, failures, interruption and recovery.
- [ ] Run no-sampling freeze verification for exact source/config/environment and six DEM identities; verify the twelve-mode matrix is complete.
- [ ] Define named seed domains and then, only under a later approved freeze task, allocate numeric seeds and collision-screen against an enumerated allowlist of permitted historical metadata. Document exact coverage and gaps. Never access sealed Stage 5 outcomes.
- [ ] Measure end-to-end runtime, native/process RSS, disk, and recovery using separately approved benchmark-only seeds; validate conservative bounds against 1,800 seconds, 2 GiB RSS and 1 GiB reserve.
- [ ] Reconcile the execution authorization review checklist with V2 and this readiness package; preserve historical files.
- [ ] Keep the documented historical-outcome exposure and unresolved influence limitation visible.
- [ ] Obtain independent code/protocol/manifest audit and a separate explicit owner authorization naming the final immutable freeze and shot allocation.

## Frozen-proposal quantities to recheck

- Selection: 6 conditions × 8 roots, 64,000 total shots, 1,333/1,334 deterministic allocation.
- Evaluation: 6 conditions × 10 roots × 4,000 shots = 240,000.
- Total ceiling: exactly 304,000 unique shots.
- Model grid: six assumed DEM families × ordinary/correlation-enabled PyMatching = 12.
- No training; no hidden evaluation regime or label at inference; no automatic next phase.

## Explicit stop conditions

Stop and return for supervisor review on any source/config/hash drift, missing or extra candidate, alias-guard failure, DEM/provenance mismatch, duplicate seed/root/sample ID, selection/evaluation overlap, label access by a decoder, partial/corrupt output, ambiguous interrupted sampler call, missing archive prediction, statistical rule ambiguity, resource-limit breach, incomplete independent audit, or any request to open protected outcomes. Never replace a frozen seed or silently change an arm, allocation, threshold, estimand, or method.
