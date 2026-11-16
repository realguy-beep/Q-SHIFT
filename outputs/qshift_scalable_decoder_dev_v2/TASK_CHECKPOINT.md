# V2 task checkpoint

Base branch: `codex/qshift-correlated-decoder-v1-6`  
Base HEAD: `84ff46a4eac4dfc4769521508243065fbfebb7d9`

## Checklist

- ☑ Confirmed research worktree/branch and reviewed V1 protocol, source, tests, fixtures, report, and manifest.
- ☑ Inspected exact DEM separator semantics and ran deterministic counterexamples before V2 edits.
- ◐ Freeze V2 protocol before algorithm modifications.
- ☐ Implement bounded V2 correctness fixes and independent exact toy oracle.
- ☐ Run deterministic tests and six existing synthetic fixture conditions.
- ☐ Independently inspect source/results and prepare decision.
- ☐ Commit verified V2 implementation/results locally.

## Evidence gathered before V2 edits

- Tracked worktree clean at the base HEAD; existing unrelated untracked data was not opened or modified.
- V1 tree detector equations matched exact enumeration in the existing test.
- V1 logical product-of-marginals failed the two-mechanism correlated-logical counterexample: exact logical probabilities 0 and 1 versus approximately 0.0526 and 0.5740.
- V1 p=1 boundary returned an answer for an impossible syndrome rather than rejecting it.
- d=3 q=0 and q=0.01 produce different graph sizes and cycle ranks; nonconvergence therefore needs to be separated from a message-equation defect.
- Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3 observed in the current interpreter. No packages installed.

## Current checkpoint

V2 protocol drafted. Next: commit protocol/checkpoint alone, then edit implementation. No sampling or protected-data access occurred.
