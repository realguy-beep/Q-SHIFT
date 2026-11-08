# Stage 5 prospective amendment v2: verified inference and pre-test runner

**Created before Stage 5 evaluation sampling. No Stage 5 evaluation shots have been generated.** This v2 amendment supersedes only the readiness and implementation candidate in `STAGE5_PRETEST_FREEZE.json`; that earlier candidate is preserved with status `PRETEST_FROZEN_NOT_AUTHORIZED` and is not the active runner freeze. It does not rewrite the historical Stage 5 v2 protocol, the n=1,210 primary design validation, the failed Welch/Holm analysis, or any Stage 4 result.

## Scientific choices held fixed

- Primary Endpoint B: equal-weight mean of four nonzero-condition, root-paired adaptive-minus-fixed logical-error-rate differences.
- Practical threshold: `-0.0002`; planning effect: `-0.0003`.
- Five conditions `p = 0, .004, .008, .012, .016`; 1,210 independent roots per condition.
- Per root: 2,000 detector-only calibration shots and 2,500 paired evaluation shots; total 27,225,000 unique shots if later authorized.
- Frozen Stage 4C profile-adaptive PyMatching method and fixed/oracle comparison arms; no CNN or new selection rule.
- Primary calibrated inference and the separate `p=0` no-harm boundary/cutoff remain as frozen in the n=1,210 design.

## Secondary analysis amendment

The earlier four-condition Student-t/Welch-reference p-values are rejected because they fail the prespecified size gate for skewed and tied/asymmetric root effects. The replacement is the finite six-family location-scale envelope with DKW upper CDF bands and Holm correction described in `STATISTICAL_JUSTIFICATION.md`. Its validated simulation output, independent count replay and independent Wilson-bound audit are hash-bound by the v2 pre-test freeze. The guarantee is conditional on the specified family and independent-root assumptions; it is not distribution-free.

## Version 2 implementation and safety

`stage5_sampling_runner_v2.py` and `stage5_saved_array_audit_v2.py` are the active frozen implementations. The runner has an explicit no-shot preflight, exact seed/configuration checks, atomic per-root arrays/status, fail-closed in-flight RNG handling, persisted failure tracebacks, and hard shot/time/RSS/disk limits. Sampling requires both `--run` and `--authorize-stage5-sampling`; those flags are not authorization by themselves and must not be used before the user separately approves sampling.

The v2 seed allocation is the 12,100-entry inventory in `STAGE5_SAMPLE_SEED_INVENTORY.json`. It is distinct from the 18 statistical-validation streams and from all recoverable historical nonsealed integer values recorded across 25 metadata sources. The seed scan cannot rule out undocumented historical RNG use.

## Readiness state

The v2 freeze records `PRETEST_FROZEN_NOT_AUTHORIZED` and is created before the final no-sampling preflight. The separate `STAGE5_NO_SAMPLING_PREFLIGHT_V2.json` records actual environment/graph checks. Only after that check passes will the readiness report say GO for readiness; neither the freeze nor the report authorizes Stage 5 sampling.
