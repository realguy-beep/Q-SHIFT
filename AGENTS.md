# Instructions for future Codex sessions

## Research integrity

- Treat every existing protocol, freeze, dataset, prediction archive, checkpoint, manifest and report as historical evidence. Do not overwrite, regenerate, rename or reorganize it.
- Put new work in a new, clearly versioned directory. Read the relevant protocol and evidence audit first.
- Keep independent-test material sealed. Do not enumerate, open, sample, evaluate, summarize or upload it unless the user explicitly authorizes the corresponding frozen evaluation.
- Do not tune on final evaluation results. Freeze seeds, source/configuration hashes, selection rules and statistics before sampling.
- Report negative findings, deviations, missing calibration evidence and uncertainty. Never claim hardware integration or decoder superiority without adequate evidence.
- For a run, use paired samples across decoders, independent roots and the documented confidence/statistical procedures. Preserve failed runs.

## Preservation and files

- Do not delete or move files to make a manifest pass. Explain discrepancies and retain original hashes.
- `.gitignore` excludes large/raw local evidence but must not cause local files to be removed. Do not force-add ignored raw datasets, checkpoints, logs, credentials or sealed-test material.
- Keep source, tests, protocols, reports, seed inventories and lightweight summaries in version control. Review staged paths and file sizes before committing.
- Do not commit or push while an experiment is actively writing. Commit only after a verified milestone, using a descriptive message such as `feat(cnn): ...`, `fix(decoder): ...`, `test: ...`, `experiment: ...`, or `docs: ...`.

## Execution and verification

- Work from the repository root and use the installed project environment. Do not install software, access external services or request elevated privileges without a clear need and user authorization.
- Prefer focused unit tests and deterministic diagnostics. Do not launch large simulations or training jobs unless explicitly requested.
- Do not rely on a successful process exit alone: inspect persisted status, counts, checkpoint integrity and independent recomputation.
- Record exact commands, software versions, seed sources, runtime, memory, hashes and limitations in the corresponding experiment directory.
- When changing the dashboard, preserve local-only security, protect existing runs and test the affected API/UI path.

## Project-specific baseline

The strongest recurring conventional baseline is fixed PyMatching. Existing adaptive and neural results have not demonstrated a reliable improvement over it. A position-preserving CNN improved over the earlier pooled CNN on small development data but remained worse than PyMatching. Keep that distinction explicit.

## Supervisor review checkpoints

- Before acting on supervisor feedback, read the latest PR conversation and inline review comments; use the exact reviewed commit as the starting point and preserve the original comment's scope.
- Record each response in the repository-root `REVIEW_HANDOFF.md`, including reviewed commit, requested corrections, changed files, tests, evidence links/hashes, limitations, and whether additional sampling is authorized.
- If the supervisor requests a stop for another review, stop after pushing the reviewed corrections and handoff. Do not continue to the next phase while waiting.
- Never merge, enable auto-merge, or close a research PR unless the project owner explicitly authorizes that action. A request to open/update a PR is not merge authorization.
- Do not represent source review or unit tests as an independent raw-data replay. State which checks were actually rerun and which are prior local evidence.
