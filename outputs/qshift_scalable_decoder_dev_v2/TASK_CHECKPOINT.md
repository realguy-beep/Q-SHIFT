# V2 task checkpoint

Branch: `codex/qshift-correlated-decoder-v1-6`
Starting HEAD: `84ff46a4eac4dfc4769521508243065fbfebb7d9`
Protocol commit: `4948bc43b442f651a4d845dd249980a68cbf0bce`

## Checklist

- ☑ Confirmed research worktree/branch and reviewed V1 protocol, source, tests, fixtures, report, and V1.6b replay/calibration evidence.
- ☑ Inspected exact DEM separator semantics and ran deterministic counterexamples before V2 edits.
- ☑ Committed V2 protocol/checkpoint before decoder edits.
- ☑ Implemented boundary/reachability/logical-output contract corrections and independent exact toy oracle.
- ☑ Ran 12 V2 tests and 6 selected no-random-generator V1.4 regressions.
- ☑ Replayed all six predeclared d=3/5/7, q=0/0.01 deterministic fixture cases; separate final result file preserved.
- ☑ Recorded residual traces, graph structure, exact d=3 comparisons, alternative dependency availability, and V1.6b evidence gaps.
- ◐ Finalize source manifest and local implementation/evidence commits.

## Verified findings

- V1.6b prior reports: 900-shot same-implementation replay passed bit-for-bit (5,400 predictions); 340 calibration reconstruction checks passed. Full 576,000-shot replay and independent decoder implementation remain unverified; metadata current-byte hashes were reported but were not independently bound by the original archive manifest.
- V1 BP check updates passed exact tree tests; q=0 nonconvergence is not shown to be an algebra defect. q=0 and q=0.01 DEM graphs differ structurally.
- V2 fixed p=0/p=1 handling, exact syndrome reachability and zero-incidence logical-only handling. Logical joint remains approximate for connected logical faults.
- Current V2 gate: REVISE. No sampling or protected evaluation is authorized or performed.

## Remaining

- Verify final source/evidence hashes, complete manifest, commit only new V2 files, and leave the branch unpushed/unmerged.

