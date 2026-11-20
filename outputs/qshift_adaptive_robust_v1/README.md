# qshift_adaptive_robust_v1: adaptive and broadly robust QEC

This is a research program separate from every earlier frozen study. It started as a design milestone (milestone 0) and has since run a series of pre-registered development studies and one frozen evaluation (RE1), all in simulation at d=5.

**Start with `STATUS.md`:** the one-page status, the study ledger and the next decisions. `DECISION_REPORT.md` holds the milestone-0 decision and a dated addendum per study.

## Studies

Every study has the same set of files:

| | Files |
|---|---|
| Plan, protocol, report | `PLAN_*.md`, `*_PROTOCOL.md`, `*_RESULTS.md` |
| Freeze | `*_FREEZE.json`, `freeze_*.py` |
| Seeds | `*_SEEDS.json`, `prepare_*.py` |
| Preflight | `*_PREFLIGHT.json`, `preflight_*.py` |
| Runner | `<study>.py` with a `<study>_config.py` |
| Results | `results/<study>/` |

| Study | Runner | Estimator or stage |
|---|---|---|
| Step 1 floor re-decode | `redecode.py` | none |
| H-E1, H-E1b | `he1.py`, `he1b.py` | `adaptive/estimation.py` |
| OG and E2E (DEV2) | `dev2.py` | `estimate2.py` (B2) |
| RE1 frozen evaluation | `re1.py`, `re1_seal.py` | B2 |
| BRE | `bre.py`, `bre_census.py` | `estimate3.py` (E1) |
| BRS | `brs.py`, `brs0.py`, `brs0_rules.py` | `estimate4.py` (E1S) |
| BRT | `brt.py`, `brt0.py` | `estimate5.py` (E1T) |
| AD1 | `ad1.py`, `ad1_stream.py` | E1T in a rolling window |

**Frozen files:** every file named in any `*_FREEZE.json` is historical evidence. Never edit, regenerate or rename one.

**New studies:** use `studykit.py` for hashing, canonical JSON, write-once records, the freeze document and the run guard (expected head, clean tree, frozen hashes). It reproduces the existing freeze format exactly, which `tests/test_studykit.py` checks.

## Milestone-0 design documents

| Document | Contents |
|---|---|
| `BASELINE_AUDIT.md` | evidence matrix and record discrepancies |
| `RESEARCH_QUESTIONS.md` | hypotheses, each with a falsifier |
| `LITERATURE_REVIEW.md` | prior work |
| `ADAPTIVE_ARCHITECTURE.md` | the adaptive design |
| `BACKGROUND_ERROR_ANALYSIS.md` | dev-only floor diagnostic |
| `BROAD_NOISE_BENCHMARK.md`, `BASELINE_FAIRNESS.md`, `STATISTICAL_PROTOCOL.md` | benchmark design and statistics |
| `EXPERIMENT_ROADMAP.md`, `RISK_REGISTER.md` | the original plan and its risks |

**Code from milestone 0:**
- `adaptive/`: estimation, change detection, regime classifier and the causal controller;
- `benchmark/`: endpoints, gates and a draft suite;
- `floor_diagnostic.py` → `results/floor_diagnostic/`.

## Checking the package

From the repository root:

```
python outputs/qshift_adaptive_robust_v1/check_package.py
```

This verifies every freeze against the tree and runs each test file in its own process. Running all the test files in one `unittest discover` call fails two seed-screen tests: several frozen packages ship a module named `contract.py`, and Python's module cache serves whichever loads first. The check takes about 2 minutes and does no sampling.

The work directory `work/` (raw records and decoded-bit archives) is local and ignored by git. Committed records carry the archives' SHA-256 hashes.
