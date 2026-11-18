# Independent research expedition log

## Checkpoint 0 — 2026-11-18

- Repository: `realguy-beep/Q-SHIFT`, published `main` revision `7cbc2e791a854e40ed4e840393fc8b4368d95ac2`.
- Original checkout `/workspace/Q-SHIFT` was clean on entry, branch `work`. Remote `main` resolves to the same revision. Claude's `codex/qshift-adaptive-robust-v1` remote branch resolves to `3a34a6abdeff0d3bb44386708f50fb645d5df686`. No checkout or modification of that branch occurred.
- Isolated worktree `/workspace/qshift-independent-research-v1`, branch `codex/qshift-independent-research-v1`, created from published main at the revision above.
- Runtime: Python 3.12.14, 5 CPU cores, 33 GiB RAM, approximately 60 GiB free workspace disk. No `nvidia-smi` executable or GPU observed.
- Available globally: NumPy 2.3.5 and SciPy 1.17.0. Stim, PyMatching, PyTorch, LDPC, Sinter, and NetworkX are not installed in the isolated worktree runtime. No packages have been installed. This means Stim-based experiment execution needs an isolated environment setup step before experiments.
- Read `AGENTS.md`, `RESEARCH_STATUS.md`, `EXPERIMENT_INDEX.md`, Phase 5D/5E findings and audits, and unified headroom audit summaries. No frozen test material was opened and no historical experiment was rerun.
- Current primary assessment from the inspected evidence: adaptive switching has not established superiority. Phase 5E ML and utility policies match pooled-fixed totals on the four short schedules, while hindsight is label-informed. Phase 4C Stage 2 has near-zero equal-regime primary effect (+0.00001556, reported p=0.6666) and missing calibration arrays. Existing source independently warns against scaling the current approach.
- No experiment has yet been run. No change to the previous cloud configuration draft or publication was made.
- Elapsed research time for this checkpoint was less than one hour. This is an interim checkpoint, not completion of the requested expedition.

## Next actions

1. Audit Stage E, Stage S, Stage 5, headroom feasibility, adaptive-robust latest materials, and relevant decoder implementations from source without opening any sealed evaluation material.
2. Complete a reference-checked literature survey and candidate matrix before selecting experiments.
3. Formalize the relative-reduction target and zero-failure sample bounds with reproducible code.
4. Decide whether an isolated CPU-only prototype is feasible and predeclare its development-only protocol before sampling.
5. Keep all files and generated outputs beneath this research directory. Do not access confirmatory data or change protected historical files.
- Existing-work audit found `outputs/research_direction_selection/` and `outputs/correlation_pilot/`. The pilot completed the exact 720,000-shot correlation-mode comparison proposed by the selection note, and its practical-effect gate failed. The raw pilot bundles are absent from this checkout. No repeat or post-hoc selector training was attempted.
- Found `outputs/correlation_mechanism_audit/FOLLOWUP_PROTOCOL.md`; its next experiment requires a non-approximated categorical DEM. My 6/6 deterministic Stim conversions failed because `PAULI_CHANNEL_2` requires the approximate-disjoint option. This closes that pretest gate without opening evaluation data.
- Existing `outputs/categorical_decoder_feasibility/` already exhaustively validates an exact decoder on small categorical toys and reports 2^609 full circuit assignments. I tested a distinct loopy categorical sum-product/Bethe prototype on those exact toys. It passed basic validation but performed poorly on one-qubit toy (LER 0.057354 vs exact MAP 0.002646, decision agreement 2/4) and matched exact MAP on the other toy (0.060000, agreement 4/4). The topology-dependent result is a negative feasibility result; no distance-3 sampling was run.
- Added tests `test_categorical_bp.py`; 2 tests passed. They validate outputs and invalid-input handling, not decoding performance.
- External literature endpoints: `export.arxiv.org` and `doi.org` failed with tunnel 403. Official Stim DEM format documentation at raw GitHub was accessible. Existing local reviews supply a detailed bibliography but cannot substitute for independent retrieval of inaccessible primary papers.
- Active hypothesis: direct categorical inference may need stronger structured elimination or correctly scoped local marginals; naive global parity BP is insufficient. Further circuit-scale testing is deferred until the method passes exact topology controls.
