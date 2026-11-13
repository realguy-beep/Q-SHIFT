# NS-4A V2 deterministic implementation handoff

Base: PR #8 accepted readiness commit `7e99b1495dbec401257d85d0436b4c30f25c310f`.
Branch: `codex/ns4a-v2-statistical-implementation`.

This branch adds the prospective statistical addendum and deterministic components for the frozen 12-candidate selection score, primary/secondary statistics, selection-rank uncertainty, paired detector-only decoder interfaces, seed-inventory collision validation, sample/archive schema validation, atomic checkpoint/resume checks, and a separately implemented saved-array audit. It does **not** implement a Stage 4A production runner or activate any freeze.

## Safety state

- `sampling_authorized=false`; no production seed inventory exists and no numeric production seeds were allocated.
- Test and package code import no Stim or PyMatching sampler/model constructors.
- `sampling_guard.activate_sampling()` always raises.
- Tests use only fixed source-defined arrays/counts. Bootstrap and sign-flip tests use unit-test-only deterministic RNG seeds; they are not experiment seeds. Seed-inventory validation uses test-only literal fixture values in memory and writes no inventory.
- No Stage 5, protected outcome, evaluation outcome, or historical result file was accessed.
- No real detector events, model selection on real outcomes, training, inference benchmark, or scientific sampling occurred.

## Review points

- Review the addendum's NumPy 2.2.6 linear quantile, three independent secondary-analysis domains, 20,000 paired selection-rank resamples, and deterministic tie reporting.
- The independently coded archive auditor does not import the package's selection or statistical aggregation implementation.
- Source and dependency hashes are in `SOURCE_HASH_MANIFEST.json`; self-hash is excluded. `verify_source_manifest.py` checks the explicit allowlist.
- Focused command result: `24 passed`; compilation passed. Exact commands and the initial corrected failures are in `TEST_RESULTS.md`.
- Remaining execution blockers are in `UNRESOLVED_BLOCKERS.md`; current recommendation remains **HOLD**.

## Reproduction

From repository root, with the existing lock-matched environment:

```powershell
$py = '<path-to-lock-matched-venv>\Scripts\python.exe'
$env:PYTHONPATH = (Get-Location).Path
& $py -m pytest -q outputs/ns4a_v2_deterministic_implementation_v1/tests
& $py -m compileall -q outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic outputs/ns4a_v2_deterministic_implementation_v1/tests
& $py outputs/ns4a_v2_deterministic_implementation_v1/verify_source_manifest.py
```

These commands execute deterministic contract tests only. They do not import a Stim sampler or start an experiment.
