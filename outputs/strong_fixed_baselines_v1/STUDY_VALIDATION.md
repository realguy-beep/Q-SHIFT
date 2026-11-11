# Study validation record

**Classification:** completed development study with a declared implementation deviation. No confirmatory inference.

## Sampling and audit status

- Unique shots recorded: 3,660,000.
- Paired final-development evaluation: 1,500,000 shots, 600 roots, 120 roots per condition.
- Final run status: `sampling_completed`; local status records all 600 roots and the full evaluation allocation committed.
- A separate saved-array reconstruction checked all 600 evaluation roots and exact decoder predictions for 1,500,000 shots. The machine-readable audit is `run_recovery_v5/INDEPENDENT_AUDIT.json`, with status `PASS_WITH_PROTOCOL_DEVIATION_RECONSTRUCTION`.
- `POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json` independently reproduces aggregate errors, paired discordance counts, root-bootstrap intervals and the zero-burst upper bound; its `audit_status` is `PASS`.
- Stage 5 evaluation files and outcomes were not accessed. The Stage 5 audit documents were available from the earlier workspace at `outputs/qshift_independent_audit_v1/`; the report/manifest were read as historical audit documentation only. No Stage 5 raw archives were opened.

## Confirmed deviation and disposition

The first runner fitted detector profiles from final-calibration batches that retained the generating-condition tags. The frozen pooled-static procedure required profiles from independent templates and an estimate from pooled calibration detector rows only. The original run remains intact. The corrected estimate `p=0.00804` and predictions were built under a later reconstruction freeze before final evaluation outcomes were audited. The original estimate was `p=0.00831`; the two models happened to give identical predictions on the saved evaluation arrays. This coincidence does not turn the initial run into a compliant execution. Results remain development evidence with a declared deviation.

## Automated tests

Command:

```powershell
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
```

Result: **PASS**, 16 tests, 0 failures, 1.338 seconds in the recorded validation run. Package versions available in the current environment: Stim 1.16.0, PyMatching 2.4.0 and NumPy 2.5.3.

## Integrity warning

The independent audit implementation writes its machine-readable output to a fixed path, and its original console line hard-codes a generic `PASS`. The JSON audit status is the authoritative disposition. Avoid rerunning that script in place if preserving the original audit output hash is required. No frozen source, raw archive, Stage 5 file or sealed-test material was changed by this documentation work.
