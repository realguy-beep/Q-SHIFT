# NS-3 research publication scope

This directory publishes the reviewed NS-3A decoder prototypes and deterministic evidence together with the NS-3B pinned BeliefMatching adapter, tests, dependency lock, benchmark records, and reports. It was copied from the standalone research workspace into a linked Git worktree based on engineering commit `d66346d8c7ad54b9567ecdd190e0d54ee7b93f0f` on branch `codex/ns3b-beliefmatching-research`.

The standalone workspace was left untouched. Its NS-3A 23-entry and NS-3B 36-entry manifests verified completely before copying. `SOURCE_MANIFEST.json` lists every published file and records the original manifest hashes, pinned upstream source revision, and unchanged base-checkout dependencies.

Two administrative reports had machine-specific absolute workspace paths replaced in the publication copies with a neutral description. Copied Markdown reports also received whitespace-only cleanup (trailing spaces and extra terminal blank lines) to satisfy the staged-diff check. No scientific results or conclusions were edited. The reports are `CONTINUATION_CHECKPOINT.md` and `RESEARCH_WORK_LOG.md`.

All nonempty NS-3A and NS-3B benchmark records were copied, including preserved partial NS-3A outputs and intermediate NS-3B snapshots. The three zero-byte placeholders remain only in the untouched standalone workspace; their names and hashes are listed in `SOURCE_MANIFEST.json`. The `.venv`, installed packages, caches, upstream checkout, protected artifacts, and unrelated files are not included.

No stochastic data were generated. BeliefMatching is experimental and disabled by default in the adapter. This publication makes no decoder-superiority claim and does not authorize a scientific evaluation.
