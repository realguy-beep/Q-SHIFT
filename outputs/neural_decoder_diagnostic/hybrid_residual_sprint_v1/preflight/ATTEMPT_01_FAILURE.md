# Preflight attempt 1 failure record

- Command: `python outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/run_sprint.py --preflight`
- Result: failed during Windows atomic JSON metadata commit after all three 128-shot regime diagnostics were sampled and the NPZ archive was written.
- Exception: `OSError: [Errno 9] Bad file descriptor`
- Cause: `atomic_json` reopened the completed temporary file in read-only mode and passed that descriptor to `os.fsync`; Windows rejected the descriptor.
- Generated diagnostic shots: 384 total (128 per frozen regime), using only the three reserved diagnostic seeds. No production train, monitor, calibration, threshold-selection, or final-development partition was generated.
- Preserved archive: `preflight/diagnostic_samples.npz`; SHA-256 recorded in the sidecar and verified before recovery.
- Recovery: the complete temporary sidecar was copied for audit and promoted to `preflight/diagnostic_samples.json`. The archive was not regenerated. The initial freeze is preserved as `FREEZE_PREFLIGHT_ATTEMPT_1.json`.
- Next action: repair atomic writes and make preflight idempotently validate/reuse this authenticated archive; create a superseding production freeze before any production partition sampling.
