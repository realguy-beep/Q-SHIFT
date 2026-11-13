# NS-2D Dependency and Provenance

## Source origin

- Research branch: `codex/ns3b-beliefmatching-research`
- Research commit: `e4ff201e3db18a2d18e7474bef4a83542eaa3da8`
- Parent / engineering base: `d66346d8c7ad54b9567ecdd190e0d54ee7b93f0f`
- Upstream BeliefMatching: version 0.2.0, commit `4458c278bbec273c8c1a26411dadccc49222f8ef`
- Published adapter SHA-256 and imported-copy SHA-256: `702dc36ef4dedd38347b0e78541d1d2d2ff063c2462dbab29aa2095f583c2106`
- Published NS-3 source manifest SHA-256: `f6d43436d5cbe7420378564a1fde8dceaa6d6a3668f7b4b26f0c4b0f40d0528c`
- Published strong-baseline protocol SHA-256: `8b815dd402cbeff448f409fee6ea4d997b8405fcc360ada61dda9e2c3b2fdfaf`
- Local pinned lock SHA-256: `2434af4afd1b5a7d501f80f8cfb2c9f20257107411603a30be17b8923c208c3d`

The source manifest records 36 published file entries. Their published hashes and byte sizes were recomputed successfully. Its five “unchanged base dependency” hashes match the engineering-base checkout. All 16 documented copy transformations match their recorded published hashes; those transformations are identified as Markdown whitespace normalization and removal of a machine-specific absolute path. The two publication-authored files are Markdown. No code transformation is recorded in those publication-scope categories. The imported adapter hash matches the specified expected SHA exactly.

## Isolated environment

The exact NS-3B lock was copied to `requirements-ns3b.lock.txt` and installed in the integration worktree’s ignored `.venv`; the global Python installation was not changed. The installed lock-relevant versions were:

- Python 3.12.10
- Stim 1.16.0
- PyMatching 2.4.0
- NumPy 2.2.6
- SciPy 1.18.1
- BeliefMatching 0.2.0 at pinned commit `4458c278bbec273c8c1a26411dadccc49222f8ef`

The complete environment is pinned in the lock file. The installed `pip freeze` matched its entries, including the editable upstream commit.

## Scope

Research files and published branches were read-only. The integration branch contains an exact adapter copy, a separate NS-2C registration wrapper, deterministic tests, and engineering-only reports/evidence. No NS-3B source history was merged or cherry-picked; the integration branch remains based on the requested engineering commit.
