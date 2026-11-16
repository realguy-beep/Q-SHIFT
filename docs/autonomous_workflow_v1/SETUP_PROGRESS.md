# Workflow setup — 2026-11-16

Scope: documentation configuration only; no experiments, dependency installation, commit, push or merge.
Checkout: exhibition-demo-final @ f537f7fafa164d38bffd854d3af2c0aabaecf935.

| Status | Milestone | Evidence |
|---|---|---|
| ☑ | Inspect instructions and checkout | AGENTS.md; root tracked-path inventory; branch/HEAD/status |
| ☑ | Review relevant protocol and work record | dashboard/EXPERIMENT_PROTOCOL.md; outputs/phase2b_pauli_bias/FREEZE_CHANGELOG.md |
| ☑ | Add workflow and reusable checklist | WORKFLOW.md, TASK_TEMPLATE.md, additive AGENTS.md section |
| ☑ | Verify preservation and configuration | Original AGENTS.md byte-prefix SHA-256 matches SETUP_BASELINE.json; four workflow artifacts present; git diff --check passes; only AGENTS.md is a tracked change |

Progress: 4/4 verified. No native plan-update API was exposed; this file is the persistent progress fallback. No live experiment monitor is running.

Initial inspection found existing untracked work, including artifact filenames in Git status; none of those artifact contents were opened. Existing protocols, freezes, research outcomes and untracked work are not edited. Frozen experiment files were identified through tracked path metadata; their protected contents and validity were not audited. The inspected dashboard protocol includes historical engineering-smoke results; these were not used for experimental decisions.

Checkpoint: setup verified and left uncommitted for review. Documentation checks only; no application tests or experiments were run. Next action: owner reviews these local configuration changes. Any future research task needs its own bounded plan and authorization.

## Commit review checkpoint — 2026-11-16

Owner authorized a local workflow-only commit; push, merge, branch switching and experiments remain unauthorized.

- ☑ Original AGENTS.md byte prefix matches the recorded SHA-256.
- ☑ Existing instructions retained; added guidance defers to research safeguards and task STOP conditions.
- ☑ Tracked diff contains only the additive AGENTS.md section; four new workflow documents reviewed.
- ☑ No research implementation, protocol, freeze or outcome file changed in the tracked diff.
- ☑ Documentation whitespace check passed; no application tests needed for guidance-only changes.
- ◐ Stage exactly the five reviewed files and verify the commit inventory.
- ☐ Report local commit and remaining unrelated changes in the final handoff.

Unrelated untracked material is excluded from writes and staging. Its path inventory was observed without opening contents; no original checksum inventory exists to establish historical byte identity. The earlier setup checkpoint remains a record of the state before this authorization.