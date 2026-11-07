# Review-only Stage 5 candidate v3 readiness

The finite-envelope calibrated primary procedure passed the predeclared null-size and coverage criteria. In response, a separate n=666 candidate package was prepared for code review only:

- `outputs/stage5_candidate_v3_n666/stage5_runner_candidate.py` — root-count-parameterized runner with checkpoint/resume logic and a two-flag sampling guard.
- `outputs/stage5_candidate_v3_n666/stage5_saved_array_audit_candidate.py` — independent saved-array decoder/metric re-computation, not importing runner statistics.
- `outputs/stage5_candidate_v3_n666/STAGE5_V3_SEED_INVENTORY.json` — 6,660 prospective streams, 4,686 recoverable nonsealed seed integers scanned, zero collisions.
- `outputs/stage5_candidate_v3_n666/STAGE5_V3_CANDIDATE_FREEZE.json` — 18 hashes; SHA-256 `c4df4b557907bbb5c07557ddb2c27dd924cf37d067b114d438ce10a1180d25a2`.

Validation commands/results:

```powershell
python -m unittest outputs.stage5_candidate_v3_n666.tests.test_candidate_v3
python outputs/stage5_candidate_v3_n666/stage5_runner_candidate.py --preflight
python outputs/stage5_candidate_v3_n666/stage5_runner_candidate.py
```

The tests passed 3/3. No-shot preflight passed for all five DEM/Matching conditions at 40 detectors and one observable. The no-argument command explicitly refused to sample and created no run directory. The independent auditor was syntax-checked and its statistic implementation was cross-tested against the runner on fixed synthetic root vectors; it was not run on evaluation files because none exist.

**This is not a sampling GO.** The candidate's 14.985M allocation failed the frozen power criterion at the right-skew and tied 1.5× scenarios, and the secondary Holm inference still needs its own operating-characteristic validation. Do not use this package for Stage 5 until those issues are resolved and a separate sampling authorization is given. The v2 2.5M cap remains unchanged.
