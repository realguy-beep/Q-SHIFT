# Deterministic validation results

## Final validation

Environment: isolated lock-matched virtual environment; Python 3.12.10, NumPy 2.2.6, SciPy 1.18.1, pytest 9.2.0.

Commands, run from repository root:

```powershell
$py = '<path-to-lock-matched-venv>\Scripts\python.exe'
$env:PYTHONPATH = (Get-Location).Path
& $py -m pytest -q outputs/ns4a_v2_deterministic_implementation_v1/tests
& $py -m compileall -q outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic outputs/ns4a_v2_deterministic_implementation_v1/tests
& $py outputs/ns4a_v2_deterministic_implementation_v1/verify_source_manifest.py
```

Results:

- Focused pytest suite: **PASS — 24 passed**.
- Python compilation: **PASS**.
- Explicit source/dependency manifest: **PASS — 33 file hashes verified; manifest self-hash excluded**.
- Tests cover 64,000/240,000/304,000 allocation arithmetic, twelve-candidate completeness/tie ordering, detector-only paired inputs, delayed label access, row identity, equal-condition weighting, 100,000/20,000 replicate counts, linear percentile endpoints, sign-flip add-one correction, exactly-three Holm correction, zero-error/all-tie behavior, root/seed/archive duplicates, missing roots, sample schema, independent saved-array recomputation, atomic-write failure handling, checkpoint hash/resume rejection, and permanently disabled sampling.
- Fixed fixtures only: no sampling, random detector-event generation, decoder construction, training, production seed allocation, or protected-outcome access.

## Failure and repair record

The first test run had five failures. Three were incorrect test expectations (checkpoint error wording, fixed root shot count, and assertion wording); two exposed lower-level sample-ID validation exceptions escaping selection/evaluation wrappers. The wrapper boundary was updated to raise its domain-specific validation exception, tests were corrected to match the frozen V2 1,333/1,334 allocation and equal-root scoring rule, and the final complete suite passed. No frozen protocol, experiment result, or historical artifact was modified.

The pass verifies deterministic software contracts only. It is not evidence of decoder accuracy, model validity, runtime feasibility, successful production resume, or scientific benefit.
