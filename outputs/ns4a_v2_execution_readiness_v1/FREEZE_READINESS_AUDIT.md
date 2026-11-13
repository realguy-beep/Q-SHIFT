# NS-4A V2 prepare-only freeze-readiness audit

**Decision: HOLD — not ready to submit for execution authorization.** This audit prepares a candidate implementation contract; it does not activate a freeze or authorize sampling. Research Codex remains on HOLD.

## Scope and evidence boundary

Reviewed the PR #7 checkpoint `762771a6f7648ebdf69af2883d71e3d26ea92522` in a separate non-cone sparse worktree. The allowlist contains the NS-4A original and V2 protocol/configuration, five approved generator/protocol inputs, Q-SHIFT decoder identity/runtime interfaces, and the lock-matched deterministic preflight package. No historical outcome files or Stage 5 paths were materialized or inspected. PRs #2–#7 were not changed. No sampler, random detector-event generator, training, model selector, statistical analysis, or numerical seed allocator was invoked.

V2 records `sampling_authorized=false`, `sampling_performed=false`, no numeric seed inventory, and Research Codex `HOLD`. These remain the governing state.

## Readiness findings

| Area | Finding | Readiness |
|---|---|---|
| Six conditions and 304,000-shot allocation | V2 specifies 64,000 selection and 240,000 evaluation shots; selection uses 8 roots per each of six cells, 1,333 base shots/cell-root plus a deterministic 16-shot remainder; evaluation uses 10 roots × 4,000 in each of six cells. | Documented; not executed |
| Candidate selection | V2 defines 6 assumed-model families × 2 PyMatching modes = 12 candidates, all evaluated on the same six-condition selection partition; choose one global candidate by equal-condition mean root LER and fixed tie order. | Protocol specified; scorer/runner absent |
| DEMs and BeliefMatching compatibility | PR #7 deterministic preflight records 6/6 circuit/DEM constructions and 12/12 PyMatching/BM compatibility rows, alias guard PASS, same DEM/provenance parity, and zero sampler/labels. | Compatibility only; not performance evidence |
| Seeds and collision screen | V2 seeds are explicitly unallocated. This task defines disjoint future stream domains but does not allocate numeric seeds or inspect seed inventories. | Not ready; later allowlisted collision screen required |
| Runner, analysis, auditor | No NS-4A V2 scientific runner, selection scorer, full statistical implementation, or saved-array independent auditor is present in the reviewed package. | Blocking implementation gap |
| Statistical freeze | Primary bootstrap and sign-flip are described, but the exact p-value method for the Holm secondary family, percentile quantile convention, and selection-rank bootstrap replicate count/seed are not specified. | Blocking clarification |
| Resources/resumption | 1,800 s, 2 GiB RSS, 1 GiB free-disk reserve are proposed limits. PR #7 fixture timings are tiny deterministic diagnostics only; end-to-end sampling, I/O, RSS, deadline, and crash-resume were not measured. | UNKNOWN; execution gate not met |
| Historical exposure limitation | V2 documents the accidental historical-outcome exposure and unresolved influence/workspace-isolation uncertainty. This audit does not revisit or certify non-use. | Must remain disclosed |

## Protocol version reconciliation

The original `outputs/qshift_ns4a_pilot_protocol/` proposal is preserved historical context and is not the V2 execution design. It describes eight candidates and four selection conditions. V2 explicitly supersedes that selection plan with twelve candidates and six selection conditions, while retaining the 304,000-shot cap and the six evaluation cells. The older `NS4A_STATISTICAL_DESIGN.md` therefore must not be treated as a complete V2 statistical specification. No historical document was edited.

The five deliverables bound by the V2 revision manifest have the same Git blob IDs at the V2 checkpoint `612c5e1381d75ca069bc6952d057c798ab10e9ab` and PR #7 base `762771a6f7648ebdf69af2883d71e3d26ea92522`. The historical revision manifest records working-tree hashes/byte counts that do not directly match this sparse checkout's LF-normalized working-tree bytes for several files; the PR #7 source inventory documents the worktree-versus-Git-blob hash convention. The original manifest and files were preserved, not rewritten or rebaselined. The new manifest records both current file SHA-256 and base Git blob OID.

## Audit conclusion

The immutable input and compatibility records are adequate to prepare an implementation handoff, not to freeze executable science. Before a later freeze is submitted for owner authorization, complete the runner, selection scorer, independent saved-array auditor, deterministic failure/recovery tests, explicit secondary-test and rank-bootstrap rules, numeric seed inventory and collision screen, and a full-pipeline resource benchmark using separately authorized non-evaluation benchmark seeds. Then hash the exact code/configuration and independently verify the freeze. None of those requirements authorizes sampling here.

Full input and artifact hashes are in `SOURCE_AND_DEPENDENCY_MANIFEST.json`. The limitations in this report are not claims of failure of the deterministic PR #7 compatibility preflight.

## Prepare-only verification performed

- Rehashed all 39 allowlisted local source/protocol/evidence inputs listed in the new manifest: 39/39 matched.
- Rechecked V2 configuration state and accounting: authorization flags false; 12 candidate cross-product; 64,000 selection + 240,000 evaluation = 304,000 cap.
- Cross-checked all six DEM digests against the twelve-row PR #7 compatibility matrix; all six found. Matrix rows record alias guard PASS, no sampled detector events, and no supplied labels.
- Compared the five V2 deliverable Git blob IDs between the V2 checkpoint and PR #7 base: all five identical.
- Ran `python outputs/ns4a_v2_lockmatched_env_recovery_v1/verify_artifact_manifest.py` in the recorded lock-matched environment: **PASS**, 16 listed files, no failures.
- No stochastic tests or sampler tests were run in this prepare-only task. This package is documentation and manifest only; it does not claim a new code-test result.
