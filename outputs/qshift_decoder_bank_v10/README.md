# Decoder bank v10: remediation of Codex's DB8 audit

Base: `codex/qshift-db8-independent-audit` at 426afe894. Branch: `claude/qshift-decoder-bank-v10-remediation`.

No study is defined or run here. No Stim sampling, no sealed data, and no change to v1-v9. DB8 stays NO ADVANCE and CF2 stays NOT CONFIRMED. This is Claude's own work, not an independent audit.

| Finding | Response | Where |
|---|---|---|
| F1 | One builder per backend; a build check of every fixed key the scored arms use | `decoder_factory.py` |
| F2 | Wording corrected | `ERRATA_DB8.md` |
| F3 | A3 provenance corrected; `sampling_started` and `committed` logged separately | `ERRATA_DB8.md`, `runkit2.py` |
| F4 | One seed-use specification for runner and analyser; launch-to-analysis preflight | `seed_spec.py`, tests |
| F5 | States, keys, sources and rules checked; analysis bound to head, freeze, run id, journal and commits, using the verified bytes | `validate.py`, `analyze10.py` |
| F6 | CB memory must be named; fallback-then-tie test; sensitivity replay | `controller.py`, `DB8_ADDENDUM.json` |
| F7 | Startup inside failure handling; atomic commit per episode; explicit record of partial attempts | `runkit2.py` |
| F8 | Documented; needs a future prespecified design | `ERRATA_DB8.md` |
| F9 | The selector raises when no candidate is eligible | `controller.py` |
| F10 | Definitions and cap effects stated per arm | `ERRATA_DB8.md`, `DB8_ADDENDUM.json` |
| F11 | Split onset table published; bootstrap deliberately not computed after the fact | `db8_addendum.py` |
| C1 | Protocol section 8 deviation disclosed (not ranked in the audit) | `ERRATA_DB8.md` |

## Checks

Python 3.12.10 with the pinned packages, Windows. Run from the repository root:

```
py -3.12 -B outputs/qshift_decoder_bank_v10/tests/test_v10.py -v
py -3.12 -B outputs/qshift_decoder_bank_v10/db8_addendum.py --check
py -3.12 -B -m unittest -v outputs.qshift_decoder_bank_v9.tests.test_db8.TruthInvarianceTests
```

`QSHIFT_DB8_EVIDENCE=<v9 folder with work/dev_a3>` adds the read-only check of the 64 saved archives.

| Check | Result |
|---|---|
| v10 tests, saved archives included | 30 of 30 pass, 64 s. One earlier run had 29 of 30: the fallback-then-tie fixture used a risk gap below CB's 0.0005 tolerance |
| 64 committed DB8 records under the stricter validator | all pass; 28 mutations all rejected |
| 64 saved archives, reanalysed through `analyze10.py` | decision, criteria, pooled errors and episode rows equal `ANALYSIS.json` |
| v9 tests other than truth invariance | 22 of 22 pass |
| v9 truth invariance (sampler-free) | 1 of 1 passes, 572 s. Run by Claude, so Codex's NOT VERIFIED stands as its own finding |

## Limits

- Not wired into an episode runner. A future study must use these modules, then have its own protocol, fidelity gate and freeze.
- Keys learned during an episode cannot be build-checked in advance. A failure there still stops the run fail-closed.
- The preflight uses committed DB8 metadata with synthetic error bits. It tests plumbing, not the real decoding loop.
- The analysis reuses DB8's criteria code, so agreement with `ANALYSIS.json` is a regression check, not an independent recount.
- Saved archives hold error bits only. Decoder predictions cannot be replayed from them.
- Directory entries are not fsynced, so power-loss durability is not claimed. Before `recover`, the operator must confirm that no process of the run is alive.
- The sampler-free identifiability and abstention study Codex proposes is not started. It needs its own protocol.
