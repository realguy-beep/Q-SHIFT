# NS-4A V2 Supervisor Handoff

## Review requested

Approve, reject, or request changes to this prospective, document-only revision before any deterministic DEM preflight or sampling authorization. The research workstream remains on HOLD.

## Decision summary

- Keep NS-4A focused on categorical Pauli-composition settings and the Phase 3A synthetic spatial burst.
- Keep all six original evaluation cells and the 304,000-shot ceiling.
- Revise the separate 64,000-shot selection partition to cover all six cells, with eight roots per cell and 1,333 base shots plus a deterministic 16-shot remainder. This aligns the pooled-static selection estimand with the equal-weight six-cell evaluation estimand.
- Select one static PyMatching configuration from six assumed-model families × two modes (12 candidates). This is strong only within the finite candidate grid; ranking uncertainty must be reported.
- Treat any progression-gate pass as exploratory and as grounds only to request another review. It grants no execution or automatic scaling authority.
- Study the three native gate/measurement rate pairs in a separate future protocol.

## Incident disclosure

The prior command was:
    Get-Content outputs/phase4b_replication/run_phase4b.py | Select-Object -First 130; rg -n "def build|noise_model|p_gate|p_meas|data|measurement|NOISE" outputs/phase4a_integrity_reaudit/SCIENTIFIC_RECOMPUTATION.md outputs/phase4b_replication/run_phase4b.py outputs/phase4b_replication/PHASE4A_VALIDATION.md
The two prohibited files were outputs/phase4a_integrity_reaudit/SCIENTIFIC_RECOMPUTATION.md and outputs/phase4b_replication/PHASE4A_VALIDATION.md. The recorded PR #3 timestamp is 2026-11-13T04:40:46Z; the command followed protocol commit/push and PR creation, but exact shell time is unavailable. Search output contained historical outcome numbers; this handoff does not repeat them. Non-use was reported, not independently established. A previous full-tree worktree was materialized and its complete file inventory is unknown; no content inspection was reported. This is an unresolved influence/workspace-isolation limitation, not a certification of no contamination.

## Boundaries and validation performed

No protected outcome file was opened for this revision. No Stage 5 access, sampling, training, model selection, DEM construction, decoder evaluation, or protocol freeze occurred. The revision is configuration and documentation only. JSON syntax, source-input hashes, and whitespace will be checked before publication. PR #3 and PR #4 are not modified.

## Exact source inputs

The five source/protocol allowlist and the original NS-4A protocol/statistical design/configuration are hashed in NS4A_REVISION_INPUTS.json. The accepted controlled-audit report and its input metadata are also recorded as review provenance. No hash was taken from a prohibited historical outcome file.

## Remaining gates (separate authorization required)

1. Supervisor approval of this revised design.
2. A later deterministic DEM/circuit-identity/alias-guard preflight under a separate authorization.
3. A complete seed inventory and collision screen, including explicit stream separation.
4. A reviewed freeze binding protocol, configuration, runner, statistical implementation, and audit tooling.
5. Separate owner authorization before any sampling.

No gate is implied satisfied by this handoff. This PR makes no scientific performance claim.
