# Q-SHIFT V2.4 launch and resume safety protocol

**Status: review-only candidate. No sampling authorization is present.** V2.4 changes only launch/resume safety. It preserves the original V2 scientific config, runner, seed inventory, allocation, decoder settings, and inference rules, plus all V2.1–V2.3 candidate freezes.

## Confirmed completion-state defect

The frozen V2 runner's actual successful terminal write is `write_status(run_dir, "sampling_completed", ..., sampling_complete=True)` in `outputs/strong_fixed_baselines_v2/run_development_v2.py`. V2.3 rejected only `complete` and `completed`. V2.4 checks the status record before creating or verifying any run provenance and refuses `sampling_completed`, `complete`, `completed`, other recognized success aliases, or any record whose `sampling_complete` is boolean true. A status/flag contradiction is therefore rejected regardless of the other field.

## Status schema from the frozen runner

The actual V2 writer creates schema version 1 records with the required base fields `status`, `pid`, `started_unix`, `updated_unix`, `completed_archives`, `allocated_unique_shots`, `sampled_partition_shots`, and `final_evaluation_shots`. It emits the resumable states `running`, `running_final_evaluation`, and `failed`; the final-evaluation transition writes `pooled_p` and `safe_static_p`; root progress is persisted in paired `completed_evaluation_roots` / `final_evaluation_shots_committed` fields; failed status adds `error_type` and `error`. V2.4 accepts only those known states and fields, validates types, allocation, counters, probability/root bounds, timestamps, and paired-field consistency, and rejects unknown keys or malformed records. It rejects completed or full-allocation counters even if the terminal status write was interrupted. It also rejects expired wall-clock state because the frozen runner would refuse to resume it.

An existing run can resume only with `--resume`, a recognized incomplete status, the existing exact execution identity, and the exact matching approval receipt. Missing provenance is not repaired during resume. Unknown or ambiguous state fails closed for manual review. An absent run directory is a fresh launch only when `--resume` is not requested.

## Read-only rejection and authorization

No real approval file is present. After separate owner authorization, the local-only record path is `outputs/strong_fixed_baselines_v2_4/OWNER_APPROVAL_V2_4_TOKEN.json`; the existing `*token*` ignore rule excludes it and `outputs/strong_fixed_baselines_v2/run_v2_4_token/`.


Approval is verified against the clean exact commit, original V2 freeze/config/inventory/runner, V2.4 candidate freeze, V2.4 launch/verifier hashes, and runtime fingerprint before dispatch. A completed/invalid status is rejected before any provenance operation. Existing incomplete-run identity and receipt are validated read-only; they are never rewritten. No CLI or environment bypass exists. The only execution path still supplies the original runner an in-memory `sampling_authorized=true` guard only after approval succeeds; the on-disk config and original V2 freeze remain false.

## Freeze and experiment boundary

`PRETEST_FREEZE_V2_4.json` is create-only and review-only. It binds the V2.4 code/tests/docs, source/config/inventory, original V2 freeze, and V2.3 predecessor freeze/verifier. V2.3 transitively verifies V2.2 and V2.1. The V2.4 freeze records `sampling_authorized=false`, `sampling_performed=false`, and `sealed_test_access=false`. Synthetic approvals are only used in temporary fixture directories; the sampler is mocked. No real approval or experiment output is created.

