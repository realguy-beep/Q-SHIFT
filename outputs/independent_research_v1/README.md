# Q-SHIFT independent research expedition

This package is an isolated scientific advisory effort on branch `codex/qshift-independent-research-v1`, based on Q-SHIFT `main` revision `7cbc2e791a854e40ed4e840393fc8b4368d95ac2`. Its active worktree is `/workspace/qshift-independent-research-v1`. The original checkout and Claude's active branch were left untouched.

The expedition is in progress. The checkpoint records repository revision, runtime limits, audited evidence, and the exact zero-failure sample-size calculation. A development-only BP+LSD screen has run on fresh circuit samples; no confirmatory or sealed test data has been accessed.

## Navigation

- `RESEARCH_LOG.md` records the initial audit and the remaining sequence.
- `FUNDAMENTAL_LIMITS.md` defines the 99.99% ratio and quantifies optimistic zero-error sampling requirements.
- `zero_failure_bounds.py` reproduces those sample counts using only the Python standard library.
- `LITERATURE_SURVEY.md` summarizes source-reviewed prior work and notes sources blocked during this session.
- `EXPERIMENT_RESULTS.md`, `FAILURE_ANALYSIS.md`, and `RESULTS.json` capture actual outcomes and limitations.
- `dem_preflight.py` and `dem_threshold_scan.py` reproduce deterministic, no-sampling Stim conversion checks.
- `REPRODUCE.md` documents environment setup and checks.
- `CLAUDE_HANDOFF.md` and `RECOMMENDATIONS.md` provide interim research guidance.
- `CANDIDATE_MATRIX.md` compares decoder, inference, learning, adaptation, and code-design directions for the next research phase.

The remaining requested reports and any prototype are pending. Treat all conclusions as preliminary until the literature references, the named Stage E and Stage S material, decoder implementations, and additional historical audits have been reviewed. No results in this package support a superiority claim.
- `EXPERIMENT_RESULTS.md` reports the deterministic DEM-conversion blocker and the negative categorical sum-product toy screen.
- `FAILURE_ANALYSIS.md` records why both paths stopped before circuit-scale evaluation.
- `EXPERIMENT_PROTOCOLS.md` contains the unrun native categorical inference feasibility plan.
- `WORK_LOG.md` records resumed execution and active hypotheses.

- Added a qecsim MPS-vs-MWPM runtime/validity preflight. It passed decoder validity but stopped at the predeclared runtime gate; see `EXPERIMENT_RESULTS.md`.

- Added a paired, development-only BP+LSD screen (30,000 new circuit shots). All three tested configurations lost to correlation-enabled PyMatching; details and scope limits are in `EXPERIMENT_RESULTS.md` and `bplsd_results.json`.
