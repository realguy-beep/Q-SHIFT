# Q-SHIFT handoff: decoder-bank line (v6–v9), state at 2026-11-24

Give this file to a new Claude session as its first message. It contains everything the previous session (one long conversation) knew that is not obvious from the repository.

## 1. Project

- **What it is:** Q-SHIFT. Simulated d = 5 surface-code decoding under adaptive, correlated burst noise, for a state-level competition.
- **Repository:** GitHub `realguy-beep/Q-SHIFT`.
- **Local worktree:** `Documents\Codex\2026-11-15\qshift-correlated-decoder-v1_6` in the user's home folder. It is one of about 38 worktrees of the same repository under `Documents\Codex\<date>\...`. Many of them are Codex's.
- **Where work happens:** new studies go in a new versioned folder, `outputs/qshift_decoder_bank_vN/`. The decoder-bank line is v1–v9.
- **Who does what:** Claude builds and runs studies. Codex does independent audits on `codex/...` branches. The user is the project owner and approves every protocol, run, push and amendment.

## 2. Standing rules (binding)

**User and AGENTS.md rules:**

- Never modify frozen research evidence. Treat every protocol, freeze, dataset, record and result as historical evidence: never overwrite, regenerate, rename or reorganise it.
- Put new work in a new, clearly versioned folder.
- Never access sealed or restricted evaluation data. Keep these closed:
  - the RE1 H2 seal, the RE2 H3/H4 seals and the V1.6 d=3 seal;
  - `results/re1/records/R6_*.json` (never inspect);
  - any `HIDDEN_COMMITMENT` file.
- Don't run new large Monte Carlo studies, install dependencies, push or merge without the user's approval.
- Never merge, enable auto-merge, open or close a research PR unless the owner explicitly says so. No PR has ever been opened for this line.
- Don't commit or push while an experiment is writing.
- Don't tune on final or confirmatory results. CF1 and CF2 are confirmatory: never use them for design. Their seeds may only be used for screening.
- Never claim independent confirmation, hardware integration or decoder superiority without adequate evidence. **Claude cannot audit its own work as "independent".** Independent audits are Codex's.
- Preserve "CF2 NOT CONFIRMED" and "DB8 NO ADVANCE" permanently.
- Keep personal details out of committed files: no username, no email, no absolute local paths.
- Leave existing branches unchanged and create a new branch for new work.
- Commit messages end with a `Co-Authored-By: Claude ...` line.

## 3. Branch and commit map (all pushed)

| Branch | Head | Contents |
|---|---|---|
| `claude/qshift-decoder-bank-v6-proposal` | e7094d3b8 | DB6-dev (27 records); `DEV_RESULTS.md` |
| `claude/qshift-decoder-bank-v7` | 6bd35b752 | CF2 plan, code, fidelity, freeze 9b41acfac, results: **NOT CONFIRMED** |
| `codex/qshift-v7-cf2-independent-audit` | 63306649d | Codex's CF2 audit (findings F1–F9) |
| `claude/qshift-cf2-remediation-v8` | d7dc1b107 | v8 `runkit.py` (run guards), F3–F8 fixes, Phase B feasibility study |
| `claude/qshift-decoder-bank-v9-db8` | **2e4ef30e0e2cbe7c42b742244f9753c6c5a7dfbd** | DB8 protocol to results: **NO ADVANCE** (the audit target) |
| `claude/qshift-decoder-bank-v9-db8-evidence` | **1e3c26e06509b3192e898f81dcba7821aad97654** | 2e4ef30e0 plus the git-ignored `work/` run folders (204 files, `EVIDENCE_MANIFEST.json`) |
| `claude/qshift-decoder-bank-handoff` | (this file) | 2e4ef30e0 plus `outputs/qshift_decoder_bank_handoff_v1/QSHIFT_HANDOFF.md` only |

**Local checkout:** `qshift-correlated-decoder-v1_6` is on the **evidence** branch, and its tree is clean.

Don't `git switch` it to the DB8 branch. `work/` is tracked on the evidence branch but not on the DB8 branch, so git would delete the local `work/` folders. They are safe on GitHub, but still avoid it. To look at another branch, use `git worktree add --detach <scratch dir> <rev>`.

## 4. Scientific history (short)

- **Setup:** 30-block stream. Per block: 2,000 detection rows, 250 labelled rows and 1,000 evaluation rows. Scored blocks are 6–29.
- **Bank states:** OFF, A, B, C, D. Out-of-bank state E = W06, support (9, 25, 53).
- **W0F:** the real-time arm confirmed in CF1.
- **LA overlay (one block of latency):** if AD3 alarms and the single-block plausible set P1 = {s}, it decodes with `bank:s`. The single-block fit g_s ~ noncentral χ² with 120 degrees of freedom; τ₁ = 202.42.
- **CF2, 48 episodes:** NOT CONFIRMED.
  - C1 passed: LA_W0F − W0F mean −6.06; 30 better, 0 worse, 18 tied; p 9.3e−10.
  - G4 failed: 3 of 96 uses were wrong (U read as A; Clopper–Pearson upper bound 7.88%).
- **Codex CF2 audit F1–F9:**
  - F3–F8 were fixed for future runs in v8 `runkit.py`: approved-revision and runtime enforcement, exact archive, episode and seed identity (`load_strict`), exclusive `Reservation`, fsynced `Journal`, fail-closed `run_jobs` that preserves partial outputs, and a sampler-free truth-invariance test.
  - F1, F2 and F9 are documented only.
- **Phase B (development data only):**
  - E-as-A misreads are a near-neighbour effect. Analytic λ(E, A) = 95.5, E[g] = 215.5 ≈ τ₁, P(E passes as A) ≈ 0.31.
  - A fit cap of 170–180 removes 86–89% of those misreads.
  - The lookahead's gains are concentrated at B onsets.

**DB8-dev (`PROTOCOL_DB8.md`):** 64 episodes.

- **Panels:** 24 in-bank (AA2 AB3 BA3 BB3 S1 2 S4 2 N_C2 N_OFF2 RX5), plus four unknown panels:

| Panel | State | Episodes |
|---|---|---|
| U_E | E | 8 |
| U_FAR | UF = V06 (1, 42, 47), after amendment A3 (originally X03) | 12 |
| U_OUT | UO = V01 + qubit 3 (1, 3, 12, 38), outside the learner catalog | 12 |
| U_NEAR | UN = X09 (7, 14, 42), λ 28.2 to B | 8 |

- **Arms:** LA_R1, LA_R2 (fit cap 180, primary), LA_R2_170 (secondary), CB and FIX_*.
- **Criteria:**
  - A1: in-bank retention ≥ 0.90 and sign test p ≤ 0.05.
  - A2: wrong-action episodes on U_FAR ∪ U_OUT ≤ 2 and ≤ LA_R1's.
  - A3: episode and block harm caps of 24; each unknown panel's pooled harm ≤ 0 and every episode ≤ 12.
  - A4: LA_R2 ≤ CB and ≤ LA_DB2.
- **ADVANCE** would only have permitted writing a CF3 plan.

**DB8 result: NO ADVANCE.** Both arms pass A1 (retention 1.00 and 0.974; 19 better, 0 worse, 5 tied; p 1.9e−6), A2 (1 of 24 against LA_R1's 9) and A4 (3,210 and 3,167 against CB 10,081 and LA_DB2 3,724). Both fail **A3 on U_NEAR only:**

- every U_NEAR episode fired once at onset, to `bank:B`, costing 41–55 errors in that block;
- pooled harm +375 (LA_R2) and +327 (LA_R2_170); worst episode +55.

The fit cap stops far-state misreads but not near-state ones. Full numbers: `outputs/qshift_decoder_bank_v9/DEV_RESULTS.md` and `results/dev/ANALYSIS.json`.

## 5. DB8 run history (all documented in v9)

1. **Attempt 1** (freeze `DB8_FREEZE.json`, 7d2aec31a; folder `work/dev`): `cmd_run` never created `records/`, so the first episode stopped the run fail-closed. 7 partial archives were kept and never opened (`RUN_ATTEMPT1.md`).
2. **Freezes A2 and A2b** were never used. On a default Windows checkout, `text=auto` turned `.jsonl` and then `.gitattributes` into CRLF, so their hashes failed. The v9 `.gitattributes` now pins both to LF.
3. **Attempt 2** (freeze A2c, 48161c830; folder `work/dev_a2`): the X03 decoder can't be built (pymatching rejects its decomposed error model), and ORACLE needs it. 28 outputs were kept and never opened (`RUN_ATTEMPT2.md`).
4. **Amendment A3** (cdf8a7774, owner-approved before any U_FAR data existed): the far-state rule also requires buildable decoders and excludes UO's base label. X03 and V01 are skipped and V06 is chosen (`AMENDMENT_A3.md`, `SELECTION_A3.json`).
5. **Attempt 3** (freeze `DB8_FREEZE_A3.json`, 7ac49b16c; folder `work/dev_a3`): 64 of 64 jobs, no reruns.
6. **Analyser fix** (e4f9bed49, owner-approved, before any result was read): `seeds_for` had expected evaluation seeds for unscored blocks 0–5 (`ANALYSIS_FIX.md`). The analysis then ran twice with byte-identical output.

**Seeds:** all three attempts used the same `DB8_SEEDS.json`. Seeds are keyed by panel name, so U_FAR kept its seeds after the state change.

**Local evidence is intact.** All 64 attempt-3 archives match their record hashes; attempt 2 matches 56 of 56; attempt 1 matches 7 of 7. Fidelity has no original hash manifest; it only has the evidence-branch manifest, made later.

## 6. Pending next step

- **Codex's independent DB8 audit** has not started. The user has the audit prompt, which targets 2e4ef30e0 with the evidence branch 1e3c26e06. Codex should write `outputs/qshift_decoder_bank_v9/CODEX_INDEPENDENT_AUDIT.md` on `codex/qshift-db8-independent-audit`.
- **Claude's next job:** once the audit exists, remediate its legitimate findings in a new versioned folder (v10) on a new branch. Don't touch DB8's evidence, and don't use the U_NEAR failures to tune a method.
- **Candidate research directions** (not started, and not to be designed against the 8 U_NEAR episodes): formal identifiability analysis (X09 against B), sequential evidence accumulation, decision-focused or robust decoder selection, and risk-aware abstention.

## 7. Practical tips for this machine

- **Shells:** PowerShell is primary; Git Bash is also available.
- **rtk:** a "Rust Token Killer" hook rewrites shell commands (`git` becomes `rtk git`). It can **swallow or reshape git output**, for example `git ls-tree` piped to `wc` returned 0. For exact output, call git from Python `subprocess`, or use `rtk proxy <cmd>`.
- **Remote commands:** `git fetch` can hang with no output. Use `timeout 60 git ls-remote ... </dev/null`.
- **Module-name clash:** both the v1_6 learner catalog and `qshift_d5_lowp_regime_v1` define a module named `contract`. Run screening chains in a `spawn` child that never imports `db8_config` (see `prepare_db8.py`).
- **Import order:** in spawned children, import `db6_config` or `db8_config` before `ad2`.
- **Runtimes:**

| Job | Time |
|---|---|
| A DB8 episode | about 55 minutes |
| A 64-episode run on 8 workers | about 7.5 hours |
| Fidelity gate | about 45 minutes |
| `tests/test_db8.py` quick tests (21) | about 2 s |
| `TruthInvarianceTests` | about 19 minutes |

- **Software (pinned by the freezes):** Python 3.12.10, numpy 2.5.3, scipy 1.18.1, stim 1.16.0, pymatching 2.4.0, ldpc 2.4.1.
- **Verifying a freeze:** check it on a fresh `git worktree add --detach` checkout with default Windows settings, then remove the worktree.
- **Long runs:** start them in the background, write a log to a scratch folder, and keep the machine awake.

## 8. Starter message for the new account

> Read `outputs/qshift_decoder_bank_handoff_v1/QSHIFT_HANDOFF.md` (on branch `claude/qshift-decoder-bank-handoff`; a local copy is at the root of the worktree `Documents\Codex\2026-11-15\qshift-correlated-decoder-v1_6` in my home folder) and follow its rules. We're continuing the Q-SHIFT decoder-bank line after DB8 (NO ADVANCE). Wait for Codex's independent DB8 audit; don't start new experiments until I approve.
