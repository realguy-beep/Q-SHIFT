# Autonomous research and development workflow v1

This is execution guidance, not an experiment protocol, authorization, scheduler or live monitor. Existing AGENTS.md safeguards and task-specific evidence boundaries remain binding.

## Plan and resume

1. Start with a short plan. Establish the exact checkout, branch, HEAD, allowed source paths and current authorization. Inspect scoped changes without opening excluded material. Prefer exact-path discovery; avoid listing protected artifacts through broad status or searches where task boundaries prohibit it.
2. Use a native plan/progress API if available. Mirror the durable state in a new task directory using TASK_TEMPLATE.md. Otherwise use the Markdown checklist as the primary plan; never claim a native tool exists when it does not.
3. Divide substantial work into small milestones with inputs, acceptance evidence, tests, budgets and STOP conditions. Track ☐ pending, ◐ running, ☑ verified and ⚠ blocked. Show all completed tasks and verified/total progress after meaningful milestones; progress counts milestones, not runtime or sampled shots.
4. Save a dated checkpoint after each milestone, recording branch/HEAD, exact changed paths, verification commands/results, failures, remaining budget and next action. Append checkpoints; do not overwrite historical reports. Write new checkpoint files through temporary files and atomic replacement where supported; report durability limitations. Keep plans outside frozen artifact directories.
5. On interruption, read the task plan and latest checkpoint, recheck source identity, permissions and actual process/lock state. Reconcile saved artifacts and counts before continuing. A lock file alone proves neither a live process nor a stale lock. Never automatically restart an ambiguous or expensive failed run.

## Approved implementation

Proceed autonomously through approved milestones and repair ordinary implementation errors. Run focused, permitted tests after each implementation stage; record failures as well as final results. Do not run a test that samples or opens excluded evidence under a deterministic-only authorization. Do not alter historical expected hashes to make checks pass.

Use independent subagents when useful for read-only review or genuinely disjoint tasks. Give each an exact source/evidence allowlist, authority limits, owned files and deliverable. Shared filesystem access is not isolation: prohibit overlapping edits and conflicting runs. Integrate only after verifying each result. Review is independent of an implementation when it checks the contract or evidence rather than repeating the implementation's assertions; disclose shared code/data assumptions.

## Experiment gate and monitoring

Before expensive computation, require explicit approval for the exact scope, immutable protocol/source/seed identity, budget and inference rules. Separate approval is required for expensive sampling, blind evaluation, new dependencies and publication claims. Previous approvals do not authorize a different study. Never open hidden burst seals or sealed evaluations without explicit matching authorization.

Preregister before evaluation-outcome access. Freeze paired-sample design, independent roots, calibration/selection boundaries, statistics, thresholds and STOP conditions. Stop immediately on preregistered failure conditions. Never tune on held-out data. Distinguish development evidence from independent confirmation.

Perform an authorized short preflight. Estimate whole-run time, RAM, disk and output sizes; label measured components versus estimates and unknowns. Specify timeout, process ownership, checkpoint boundaries, duplicate prevention and exact-seed recovery before execution. Logs and outputs must use new versioned paths, safe writes and retained failed-attempt evidence.

For an authorized long run, use an actual active tool/process monitor and record its handle/PID, polling interval and coverage. Report committed batches/shots, generated counts separately, elapsed time, estimated remaining time and failures. Unknown completion/ETA stays unknown. A workflow document, future callback or disconnected process is not live monitoring. Distinguish sampled memory measurements from hard OS enforcement and process memory from process-tree memory.

The explicit deadline includes initialization, sampling, decoding, analysis, auditing and finalization. On budget breach, stop through the reviewed safe termination path, preserve evidence and report incomplete/blocked. Do not silently retry an expensive failed run, extend a budget or substitute seeds. Resume only within existing explicit recovery authorization; otherwise request a separate recovery decision.

## Completion and publication

Verify persisted counts, identities, hashes and results independently where feasible. A successful exit alone is insufficient. Evidence unavailable for review remains unverified. Never mark ☑ without a named verification result. Explain negative results, deviations, uncertainty and unresolved risks.

Finish with the full checklist, verified/total progress, commands and tests, actual results, exact changed files, branch/HEAD, commit if one was created, remaining blockers and next action. Do not imply local changes are committed. Do not commit while an experiment writes. Review scoped diffs, sizes, secrets and evidence boundaries; stage explicit task paths only. Push or merge only with authorization. Claims of hardware validation or decoder improvement require supporting evidence and appropriate publication approval.
