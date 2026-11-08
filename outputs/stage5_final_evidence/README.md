# Q-SHIFT Stage 5 final evidence

This directory publishes the verified results of the completed, simulation-based Stage 5 recovery. It contains the final statistical decisions, a per-root audit record, archive/checkpoint hash manifests, and recovery provenance. Raw shot archives and binary predictions remain local and are not uploaded.

## Quick result

- **6,050/6,050 roots; 27,225,000 unique shots.**
- **Endpoint B: PASS.** Equal-weight nonzero-condition adaptive-minus-fixed LER = −0.00154595; calibrated upper bound = −0.00152107, below the frozen −0.0002 boundary.
- **Zero-burst no-harm: PASS.** Upper bound = +0.00000744, below the +0.0002 boundary.
- **Secondary family:** all four Holm-adjusted finite-envelope p-values = 0.00866841.
- **Internal independent saved-array audit: PASS.** It is not an external third-party audit.

## Review order

1. Read [FINAL_STAGE5_REPORT.md](FINAL_STAGE5_REPORT.md).
2. Review [STATISTICAL_DECISIONS.md](STATISTICAL_DECISIONS.md) and [EXPERIMENT_ACCOUNTING.md](EXPERIMENT_ACCOUNTING.md).
3. Read [INDEPENDENT_AUDIT.md](INDEPENDENT_AUDIT.md) and [LIMITATIONS.md](LIMITATIONS.md).
4. Run the read-only [published-package verifier](verify_published_package.py) using the command in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
5. Inspect `RESULTS.json`, `PER_ROOT_RESULTS.csv`, `INDEPENDENT_AUDIT.json`, `ROOT_ARCHIVE_MANIFEST.json`, `FINALIZATION_MANIFEST.json`, and `RECOVERY_JOURNAL_V44.json`.

`ORIGINAL_STAGE5_RECOVERY_RESULTS.md`, `RESULTS.json`, `EXECUTION_RECORD.json`, `SOURCE_RESULTS_MANIFEST.json`, and the included audit/manifest artifacts are unchanged copies of the local completion evidence unless explicitly labeled redacted. The unredacted recovery provenance remains local; its hash is recorded in the publication manifest.

## Frozen implementation snapshot

The `source/v3.4.4/` directory contains byte-for-byte copies of the small recovery-safety source, configuration, tests, and audit reports listed in the v3.4.4 frozen manifest. The core Stage 5 sampling, audit, and statistical source/configuration artifacts are in the repository at the base revision and are listed by SHA-256 in `EVIDENCE_MANIFEST.json`. Seed inventory contents are not duplicated here; only their frozen hash and repository-relative path are recorded. The v3.4.4 source freeze predates recovery execution; execution status and outputs are evidenced separately by the included recovery records.
