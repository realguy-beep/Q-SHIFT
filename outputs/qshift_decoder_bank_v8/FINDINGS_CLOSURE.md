# CF2 audit: findings closure matrix (v8 remediation)

| | |
|---|---|
| Audit | `outputs/qshift_decoder_bank_v7/CODEX_INDEPENDENT_AUDIT.md` at `63306649d` |
| CF2 evidence | `6bd35b752` |
| Branch | `claude/qshift-cf2-remediation-v8`, started from the audit commit |

**CF2 stays NOT CONFIRMED.** No v7 file, CF2 record, freeze, seed, hypothesis or verdict was changed: `git diff
63306649d -- outputs/qshift_decoder_bank_v7` is empty. The fixes live in `outputs/qshift_decoder_bank_v8/` and
protect future runs only. None is retrofitted onto CF2.

**Status key:**
- **FIXED:** corrected in v8 code, with a regression test.
- **DOCUMENTED:** a limitation of the frozen study, disclosed in `CF2_ADDENDUM.md`; it cannot be fixed without a
  new study.
- **OPEN:** still needs future work.

| ID | Severity | Finding | Reproduced (REPRODUCTION.json) | Status | Where | Regression test |
|---|---|---|---|---|---|---|
| F1 | high | The sign test targets frequency of improvement, not a mean margin or rare-harm safety; pooled binomial over fixed heterogeneous quotas; the bootstrap is blind to the tail | yes, the audit's counter-example is checked analytically in the addendum | **DOCUMENTED**; future estimand and design **OPEN** | addendum §1; feasibility §6 item 3 | none (statistical) |
| F2 | high | CP bounds assume i.i.d. trials; the 96 uses are clustered in 39 episodes; in-bank 0/93 against U 3/3 | yes (audit counts reproduced) | **DOCUMENTED**; cluster-aware design **OPEN** | addendum §2–3; feasibility §6 item 3 | none (statistical) |
| F3 | medium | The run accepted any caller-supplied HEAD; the runtime was not compared with the freeze; scipy and ldpc were not frozen | yes: v7 `cmd_run` reached pool creation with HEAD mocked to the result commit (no job started); freeze fields lack scipy and ldpc | **FIXED** (future runs) | `runkit.check_revision`, `runtime_identity`, `check_runtime` | `RevisionTests` (exact freeze commit; rejects a later commit, a wrong parent, a freeze commit that also changes code, a dirty tree, tracked results), `RuntimeTests` (ldpc/scipy present; mismatch and missing fields fail) |
| F4 | medium | The loader did not bind episode, archive and seed identity, or the exact row count | yes: v6 `load_checked` accepts a duplicated episode, a shared archive and eval = 1001; v8 rejects all three | **FIXED** | `runkit.load_strict` | `LoadStrictTests` (good input passes; duplicate episode, shared archive, eval 1001, seed mismatch, missing, failed or extra jobs, extra record file all fail) |
| F5 | medium | Reservation was check-then-write; an archive filename could be reused on retry; the retry had no timeout; failures were not fail-closed | yes, from source: check-then-write, no O_EXCL, untimed retry | **FIXED** | `runkit.Reservation` (O_EXCL, permanent), `Journal` (fsynced), `run_jobs` | `RunTests`: exclusive lock; success; retry only on a pre-write infrastructure error; a post-write error, a code error, a timeout and an interruption each fail closed, preserve partial outputs under `partial/`, and are not retried |
| F6 | medium | The "mocked" truth-invariance test used the real sampler; the commit's "no sampling" was inaccurate | yes, from source | **FIXED** (new test); the v7 wording is **DOCUMENTED** | `tests/test_v8.py::TruthInvarianceTests`; addendum §7 | Synthetic rows, with stim's samplers replaced by a function that raises. Five variants: base, flipped evaluation labels, flipped current-block labels, changed truth diagnostics, changed future-block detectors. Decisions are unchanged where they must be; the future-block change is visible only at that block; the overlay is exercised (`bank:B` at the onset) |
| F7 | low | The plan said 1 wrong use needs ≥ 95 uses; the correct figure is 93 | yes: 4.99940% at 1/93 | **FIXED** (helper) and **DOCUMENTED** | `runkit.cp_upper`, `cp_min_n`; addendum §4 | `BoundTests.test_g4_boundary` (1/93 passes, 1/92 fails, 3/96 = 7.8787%, minimum n = 59/93/124/153) |
| F8 | low | Eight descriptive contrasts carried unadjusted p values | yes (fields present in CF2 ANALYSIS.json) | **FIXED** (helper) and **DOCUMENTED** | `runkit.describe`; addendum §5 | `BoundTests.test_describe_has_no_p` |
| F9 | low | Wording: detector-only overlay vs labelled base, C2 scope, LA2's "31 wins", in-bank vs out-of-catalog, CF1 qualifications | n/a (wording) | **DOCUMENTED** | addendum §3, §6 | none |

## Open items (need a new, approved protocol)

1. A pre-registered estimand for magnitude and rare harm, with a design that accounts for panels (F1).
2. Episode- and cluster-aware intervals with fixed strata. Separate, pre-defined outcomes for wrong
   identification, harmful override and net error (F2).
3. Integrating `runkit` into an actual runner for that study, with its own fidelity and freeze. It is deliberately
   not wired into any study yet.
4. Out-of-bank states outside the learner catalog, and the stronger same-latency baselines (feasibility §5–6).

## Verification

Run from `outputs/qshift_decoder_bank_v8/` with Python 3.12.10, numpy 2.5.3, scipy 1.18.1, stim 1.16.0,
pymatching 2.4.0 and ldpc 2.4.1:

| Check | Result |
|---|---|
| `python -m unittest tests.test_v8` | **19 tests OK** in 506 s; the synthetic truth test is the slow one |
| `python reproduce_findings.py` | `REPRODUCTION.json`; launched no job and sampled nothing |
| `python research/phaseb.py` | `research/PHASEB.json`; two runs byte-identical; 648/648 DB6 blocks reproduced |
| `python ../qshift_decoder_bank_v7/audit_cf2_saved_evidence.py` (from the repo root) | every audit figure reproduced |
| v6 `tests.test_db6`, v7 `tests.test_cf2` | unchanged code; run earlier in this project and passing |

**Not verified here:**
- an independent replay of CF2's detector and observable sampling;
- native ldpc and stim build provenance;
- `check_revision` against a real git repository (tested only with a scripted git);
- `run_jobs` with real decoder jobs, since only fake jobs were used and no study was sampled.
