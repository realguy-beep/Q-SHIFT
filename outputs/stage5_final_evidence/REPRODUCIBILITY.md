# Reproducibility and verification

## Frozen revision and dependencies

- Repository: `realguy-beep/Q-SHIFT` (private repository).
- Publication base revision: `1bdeb32c53589ec26c103f1e408be6e7e5ed1ebc`.
- Original failed execution revision: `8c06750808582137f6a81e2170ad702a552594fb`.
- Execution path: audited v3.4.4 recovery runner.
- Statistical replay environment used for this publication check: Python 3.12.10 and NumPy 2.5.3. The sampler/decoder execution additionally used the project's frozen Stim/PyMatching environment; its configuration and source hashes are listed in `EVIDENCE_MANIFEST.json`.

## Verify published evidence

From the repository root, run:

```powershell
python -B outputs/stage5_final_evidence/verify_published_package.py
```

The read-only verifier checks the published-file hashes, 6,050 condition/root rows, archived per-root error counts, finalization/root manifests, primary and zero-burst decisions, and recomputes the frozen statistical output from the included auditor rows. It does not sample circuits or access raw Stage 5 shot arrays.

The original recovery copy's v3.4.4 audit was run during execution and is represented by `INDEPENDENT_AUDIT.json`, `FINALIZATION_MANIFEST.json`, and the original `RUNNER_SUMMARY.json`. The corresponding raw `.npz` archives remain local and are not included. To independently repeat detector decoding, an authorized reviewer would need access to those archives and the frozen decoder environment; the public package alone is sufficient to reproduce the aggregate error and inferential calculations, not the raw decoder audit.

## Seeds and partitions

The five conditions each contain 1,210 roots. Calibration and paired evaluation use their distinct preallocated streams. The run's 6,050 root/condition identities and seed mappings passed the frozen inventory audit. Actual seed values are not duplicated in this package; the source inventory path and SHA-256 are recorded in `EVIDENCE_MANIFEST.json`.

## Verify exact copied files

`EVIDENCE_MANIFEST.json` records SHA-256 and byte size for each package file and for relevant original source artifacts. `SOURCE_RESULTS_MANIFEST.json` is the prior result bundle's manifest, copied unchanged. The package verifier fails if a published copy differs from its manifest or if its aggregate results disagree with the saved independent-audit rows.

The manifest also enumerates the 53 active Stage 5 frozen source/configuration inputs and the 19 files in the v3.4.4 safety freeze. The safety source snapshot is included under `source/v3.4.4/`; the 53 active experiment inputs remain at their repository-relative paths. The seed inventory itself is verified by hash but its seed values are not reproduced in the package.

The package-local `.gitattributes` disables Git text conversion for these publication files so the recorded byte-level SHA-256 values remain stable across Windows and Linux checkouts.

No Stage 5 recovery command should be run to reproduce this completed evaluation. The package contains no sampling authorization and no raw sampling archives.
