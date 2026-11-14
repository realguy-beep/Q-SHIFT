# Q-SHIFT — agent continuity handoff (2026-11-14)

> **Purpose:** Read this first when a new ChatGPT/Codex agent takes over. This is a *conversation handoff*, not a replacement for the repository's frozen protocols, `AGENTS.md`, source code, or audit evidence. Verify current branch/commit and newer work before acting. Do not interpret an administrative gate as a scientific result.

## Repository and working rules

- Repository: https://github.com/realguy-beep/Q-SHIFT ; default branch `main`.
- The user uses ChatGPT to plan, supervise, review evidence and write copy-paste Codex prompts; Codex/VS Code does implementation, runs and local file operations. Ask before initiating expensive experiments or accessing sealed tests.
- Follow `AGENTS.md`, `RESEARCH_STATUS.md`, `EXPERIMENT_INDEX.md`, and the relevant frozen protocol/audit documents. Keep original evidence, hashes, negative findings and deviations. Never silently substitute files, change frozen results, open independent tests, or promote a gate without explicit approval.
- This handoff was authored from the conversation and a user-provided Codex report; it is **not** an independent audit of the 47 local snapshot files. The Windows snapshot is not in GitHub.

## Scientific context — do not overclaim

Q-SHIFT is a **simulation-based** quantum error-correction decoder research prototype, using Stim detector samples, PyMatching fixed/calibrated decoder banks, adaptive/neural experiments, statistical audits and a local dashboard. **No quantum-hardware integration and no demonstrated general adaptive/neural advantage over strong fixed PyMatching.**

- Phase 4A measurement-heavy: 600,000 paired shots, fixed 1,118 errors versus calibrated 940.
- Phase 4B replication: fixed 1,165 versus calibrated 1,008; audit PASS WITH DEVIATION because 450k templates were regenerated instead of reused.
- Phase 4C held-out Stage 2: 1.8M shots; calibrated/pooled-fixed data-heavy 8,459/8,382; nominal 2,996/2,949; measurement-heavy 980/1,076. Equal-regime calibrated-minus-pooled +0.00001556, sign-flip p=0.6666; **no overall improvement**.
- Adaptive feasibility gate: NO-GO for tested bank. Neural exploratory work did not beat strong PyMatching. Phase 3A correlated-noise X-burst is synthetic; 256-shot correlation toggle had identical predictions; Phase 3B production not run.
- Check the latest `RESEARCH_STATUS.md` for full qualifications and more recent updates.

## Exhibition hardware — distinct from quantum hardware

A proposed ESP32-driven **visual teaching demonstration**, not a physical quantum computer: ESP32-WROOM-32, WS2812B LED modules (20 purchased/planned, 17 active proposed: 9 data-qubit + 8 stabilizer indicators), SN74HCT125N 3.3-to-5V level shifting, three pushbuttons, 330-ohm data resistor, 1000-uF LED supply capacitor, 100-nF buffer decoupling, portable regulated 5V/3A supply and common ground. The precise layout, firmware, purchase status and laptop/standalone control are **not confirmed**; inspect the relevant exhibition branch before asserting implementation.

## Active task: NS5B Gate 2C snapshot and administrative closure

**Pinned source commit:** `5c8f8391491427fab16845282a5c8c540746b145`

**Local approved destination (on user's Windows machine):**
`C:\Users\LENOVO\Documents\Codex\2026-11-14\qshift_ns5b_gate2c_snapshot_20261114_01`

Original allowlist: **48 approved paths**; eight separate `REFERENCE_ONLY` paths excluded. Stage 5 and incident-worktree material excluded.

### What actually happened

1. Initial writer: PowerShell child process got closed noninteractive stdin and exited before accepting bytes. Zero files saved.
2. Node binary-write round-trip preflight succeeded. GitHub connector Base64 contained LF wrapping; an overstrict validator rejected it. Later authorized bounded ASCII-whitespace normalization and strict decode, Git blob SHA-1 checks, SHA-256 calculation and disk reread.
3. **47/48 approved files saved and reread**, total **402,771 bytes**. For all 47, locally calculated Git blob SHA-1 matched the connector-reported blob SHA-1; locally calculated SHA-256 recorded. For `AGENTS.md` alone, both SHA-1 and SHA-256 also matched independently *previously approved* expected values.
4. One missing file: `outputs/phase3a_correlated_noise_preflight/prototype.py`. Exact-path GitHub Contents API returned **404** at pinned commit. A directory listing at that revision had 16 entries, including `simulator.py`, but **not** `prototype.py`. A path-specific commit-history query bounded to that revision returned zero results. No rename was established; **do not substitute** `simulator.py`.
5. Connector URL and blob hash consistency do **not** independently prove Git commit-tree membership, path/type or redirect provenance. For the other 46 saved files, no separately approved expected hashes were available, so call them **verified against connector responses**, not independently authenticated against an approved hash list.
6. No source code executed, tests run, research performed, Stage 5 material accessed, or Gate 3 started in this workflow.

### Gate decision and next action

- **Original 48-file retrieval complete: FALSE.**
- **Gate 2C:** 47 verified-and-saved, 1 absent/unavailable at pinned revision according to GitHub API; no unattempted paths. Original manifest must remain unchanged, with a **formal non-destructive addendum** recording the exception and provenance limitations.
- Previous supervisor recommendation: prepare a `GATE_2C_CLOSED_WITH_DOCUMENTED_EXCEPTION` administrative addendum and assess whether the 47-file snapshot suffices for the *specific* Gate 3 scope. **This is a recommendation, not evidence that the addendum was created or the gate closed.**
- **Gate 3 is NOT authorized**. Obtain explicit authorization after reviewing closure evidence and dependency on the missing file. Do not restart 47 successful downloads just because the 48th is absent.
- Ask the user for the final Gate 2C closure report/addendum (and Gate 3 protocol, if moving forward). The user-provided retrieval report has a complete 47-file per-path manifest; this handoff intentionally does not duplicate all 47 hashes.

## How to resume in a fresh conversation

1. Read this file and `AGENTS.md`, `RESEARCH_STATUS.md`, `EXPERIMENT_INDEX.md` at the *relevant branch and revision*.
2. Ask which track is active: NS5B gate closure/research, exhibition hardware, or another workstream. Do not mix them.
3. For NS5B: request the latest closure addendum and original approved 48-file manifest; check pinned revision and exact missing-file exception. If unavailable, say so; do not fabricate completion.
4. Preserve scientific distinctions: development vs held-out, fixed vs calibrated vs adaptive, synthetic vs hardware-calibrated, and provenance limitations.
5. After each material milestone, append a dated update here rather than rewriting history.

**Status as of 2026-11-14:** GitHub API missing-path investigation completed; 47 local snapshot files saved; administrative closure addendum proposed but not confirmed; Gate 3 unauthorized.
