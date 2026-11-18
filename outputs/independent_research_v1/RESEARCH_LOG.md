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
